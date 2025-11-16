# #####################################################################
# PART 3 : HYBRID JOIN
# File: hybrid_join.py
# #####################################################################

import threading
import queue
import csv
import time
import random
import mysql.connector
import getpass
import json
from collections import defaultdict
from mysql.connector import errorcode
from doubly_linked_list import DoublyLinkedList

# Big enough hash area so we don't choke when streaming slightly large files
HASH_SLOTS = 10000
STREAM_BUFFER_MAX_SIZE = 2000

STREAM_FILE = 'transactional_data.csv'
CUST_INDEX_FILE = 'cust_index.json'
PROD_INDEX_FILE = 'prod_index.json'


class HybridJoinStage:
    def __init__(self, index_data, get_key_from_s, key_index_in_r):
        # Index holds which R-partition CSV file each key belongs to
        self.index = index_data

        # Function that extracts the join-key from S side
        self.get_key_from_s = get_key_from_s

        # Which column inside R partition holds the join-key
        self.key_index_in_r = key_index_in_r

        # In-memory hash table of buffered S tuples
        self.hash_table = defaultdict(list)

        # Doubly linked list to track S-tuple eviction order
        self.queue = DoublyLinkedList()

        # Remaining space in memory-partition W
        self.available_slots_w = HASH_SLOTS

        # Small disk buffer for currently loaded R-partition
        self.disk_buffer = {}
        self.disk_buffer_filename = None

    def _load_r_partition(self, key):
        # Attempt to pull the R-partition filename from the index
        try:
            partition_file = self.index[key]
        except KeyError:
            print(f"[Stage] No matching R-partition for key {key}. Ignoring it.")
            return False

        # Skip reloading if same file already in buffer
        if partition_file == self.disk_buffer_filename:
            return True

        print(f"[Stage] Loading R partition: {partition_file}")
        self.disk_buffer.clear()

        try:
            with open(partition_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                for r_tuple in reader:
                    r_key = r_tuple[self.key_index_in_r]
                    self.disk_buffer[r_key] = r_tuple

            self.disk_buffer_filename = partition_file
            return True

        except FileNotFoundError:
            print(f"[Stage] R-partition file missing: {partition_file}")
            return False

    def add_stream_tuple(self, s_tuple):
        # No free memory slots left, cannot store
        if self.available_slots_w <= 0:
            return False

        # Add S tuple to eviction list and to hash table
        q_node = self.queue.append(s_tuple)
        s_key = self.get_key_from_s(s_tuple)
        self.hash_table[s_key].append((s_tuple, q_node))

        self.available_slots_w -= 1
        return True

    def join(self):
        # Nothing buffered
        if self.queue.is_empty():
            return []

        # Check the oldest S tuple and its join-key
        s_oldest = self.queue.peek_front()
        oldest_key = self.get_key_from_s(s_oldest)

        # Load the appropriate R partition
        if not self._load_r_partition(oldest_key):
            # No R-side match exists, so drop the tuple
            print(f"[Stage] Tossing S-tuple with dead key {oldest_key}")
            s_tuple, q_node = self.hash_table[oldest_key].pop(0)
            self.queue.delete_node(q_node)
            self.available_slots_w += 1
            return []

        joined_outputs = []

        # Compare R-buffered rows against H(S)
        for r_key, r_tuple in list(self.disk_buffer.items()):
            if r_key in self.hash_table:
                matches = self.hash_table.pop(r_key)
                for (s_tuple, q_node) in matches:
                    joined_outputs.append((s_tuple, r_tuple))
                    self.queue.delete_node(q_node)
                    self.available_slots_w += 1

        return joined_outputs


class JoinOrchestrator:
    def __init__(self, db_conn, cust_index, prod_index):
        self.db_conn = db_conn

        # Queue buffers streaming records from disk → joiner thread
        self.stream_buffer = queue.Queue(maxsize=STREAM_BUFFER_MAX_SIZE)

        # Stage 1: Customer side join
        self.stage1_customer = HybridJoinStage(
            index_data=cust_index,
            get_key_from_s=lambda s: s[2],   # customer_id position in S
            key_index_in_r=1
        )

        # Stage 2: Product side join
        self.stage2_product = HybridJoinStage(
            index_data=prod_index,
            get_key_from_s=lambda s_prime: s_prime[0][3],
            key_index_in_r=1
        )

        self.stream_complete = False
        self.processed_count = 0

        # DB batch insert buffer
        self.insert_buffer = []
        self.batch_size = 100

    def stream_loader_task(self):
        print("[Loader] Starting stream read...")

        try:
            with open(STREAM_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # header

                for row in reader:
                    # simulate incoming real-time stream
                    time.sleep(random.uniform(0.001, 0.01))
                    self.stream_buffer.put(tuple(row))

        except FileNotFoundError:
            print(f"[Loader] Stream file not found: {STREAM_FILE}")

        except Exception as e:
            print(f"[Loader] Unexpected read error: {e}")

        finally:
            # Sentinel indicating no more input
            self.stream_buffer.put(None)
            print("[Loader] Stream reading done.")

    def hybrid_join_task(self):
        print("[Joiner] Join thread running...")

        while True:

            # Fill Stage 1 while memory slots are free
            while not self.stream_buffer.empty() and self.stage1_customer.available_slots_w > 0:
                s_tuple = self.stream_buffer.get()

                if s_tuple is None:
                    self.stream_complete = True
                    break

                self.stage1_customer.add_stream_tuple(s_tuple)

            # Customer-side join phase
            intermediate = self.stage1_customer.join()

            # Push intermediate pairs to Stage 2
            for s_prime in intermediate:
                if self.stage2_product.available_slots_w > 0:
                    self.stage2_product.add_stream_tuple(s_prime)
                else:
                    print("[Joiner] Stage 2 buffer full. Slowing down.")
                    break

            # Product-side join phase
            final_outputs = self.stage2_product.join()

            for (s_prime, r_prod_tuple) in final_outputs:
                (s_tuple, r_cust_tuple) = s_prime

                enriched = self._enrich_and_finalize(s_tuple, r_prod_tuple)
                if enriched:
                    self.insert_buffer.append(enriched)
                    self.processed_count += 1

            # Push batch to DB
            if len(self.insert_buffer) >= self.batch_size:
                self._flush_insert_buffer(self.db_conn.cursor())

            # Termination condition
            if self.stream_complete and \
               self.stream_buffer.empty() and \
               self.stage1_customer.queue.is_empty() and \
               self.stage2_product.queue.is_empty():

                print("[Joiner] No more work left. Exiting.")
                break

        if self.insert_buffer:
            self._flush_insert_buffer(self.db_conn.cursor())

        print(f"[Joiner] Finished. Processed {self.processed_count} records.")

    def _enrich_and_finalize(self, s_tuple, r_prod_tuple):
        # Build final FactSales row
        try:
            order_id = s_tuple[1]
            cust_id = int(s_tuple[2])
            prod_id = s_tuple[3]
            qty = float(s_tuple[4])
            date_raw = s_tuple[5]

            price = float(r_prod_tuple[3])
            date_key = int(date_raw.replace('-', ''))
            total_amt = qty * price

            return (order_id, cust_id, prod_id, date_key, total_amt)

        except Exception as e:
            print(f"[Enrich] Couldn't process row: {e}")
            return None

    def _flush_insert_buffer(self, cursor):
        print(f"[DB] Inserting {len(self.insert_buffer)} rows...")

        try:
            query = """
                INSERT IGNORE INTO FactSales (
                    Transaction_ID, Customer_ID, Product_ID, Date_Key, Purchase_Amount
                ) VALUES (%s, %s, %s, %s, %s)
            """
            cursor.executemany(query, self.insert_buffer)
            self.db_conn.commit()
            self.insert_buffer.clear()

        except mysql.connector.Error as err:
            print(f"[DB] Insert failed: {err}")
            self.db_conn.rollback()

        finally:
            cursor.close()


def main():
    print("=== HYBRID JOIN ETL Start ===")

    # Load indexes for customer + product partitions
    try:
        with open(CUST_INDEX_FILE, 'r') as f:
            cust_index = json.load(f)
        with open(PROD_INDEX_FILE, 'r') as f:
            prod_index = json.load(f)

        print("Index files loaded successfully.")

    except FileNotFoundError:
        print("Missing index files. Build them before running the join.")
        return

    # DB Connection
    try:
        conn = mysql.connector.connect(
            database="walmart",
            user="root",
            password="meow",
            host="localhost",
            port="3306",
            autocommit=False
        )
        print("Connected to MySQL.")

    except mysql.connector.Error as err:
        print(f"DB connection failed: {err}")
        return

    orchestrator = JoinOrchestrator(conn, cust_index, prod_index)

    loader = threading.Thread(target=orchestrator.stream_loader_task)
    joiner = threading.Thread(target=orchestrator.hybrid_join_task)

    loader.start()
    joiner.start()

    loader.join()
    print("[Main] Loader thread completed.")

    joiner.join()
    print("[Main] Joiner thread completed.")

    conn.close()
    print("=== ETL Done ===")


if __name__ == "__main__":
    main()
