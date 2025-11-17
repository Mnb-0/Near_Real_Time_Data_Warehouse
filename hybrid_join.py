#####################################################################
# HYBRID JOIN ETL
#####################################################################

import csv
import json
import time
import queue
import random
import getpass
import argparse
import threading
import mysql.connector
from collections import defaultdict
from mysql.connector import errorcode
from doubly_linked_list import DoublyLinkedList

# tiny config stuff
HASH_SLOTS = 10000
STREAM_BUFFER_MAX_SIZE = 2000
STREAM_FILE = 'transactional_data.csv'
CUST_INDEX_FILE = 'cust_index.json'
PROD_INDEX_FILE = 'prod_index.json'


class HybridJoinStage:
    """
    One stage of the S-cached join. Each stage pulls in the right R-partition
    and tries to match whatever S-tuple it has hanging around.
    """
    def __init__(self, index_data, get_key_from_s, key_index_in_r):
        self.index = index_data
        self.get_key_from_s = get_key_from_s
        self.key_index_in_r = key_index_in_r
        self.hash_table = defaultdict(list)
        self.queue = DoublyLinkedList()
        self.available_slots_w = HASH_SLOTS
        self.disk_buffer = {}
        self.disk_buffer_filename = None
        self.header_map = {}   # so we know what column is where in the R file

    def _load_r_partition(self, key):
        try:
            partition_file = self.index[key]
        except KeyError:
            print(f"[Stage] Nothing for key {key}, skipping it.")
            return False

        if partition_file == self.disk_buffer_filename:
            return True

        print(f"[Stage] Pulling R partition into memory: {partition_file}")
        self.disk_buffer.clear()
        try:
            with open(partition_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                self.header_map = {name: idx for idx, name in enumerate(header)}
                for r_tuple in reader:
                    r_key = r_tuple[self.key_index_in_r]
                    self.disk_buffer[r_key] = r_tuple
            self.disk_buffer_filename = partition_file
            return True
        except FileNotFoundError:
            print(f"[Stage] Can't find partition file: {partition_file}")
            return False

    def add_stream_tuple(self, s_tuple):
        if self.available_slots_w <= 0:
            return False

        q_node = self.queue.append(s_tuple)
        s_key = self.get_key_from_s(s_tuple)
        self.hash_table[s_key].append((s_tuple, q_node))
        self.available_slots_w -= 1
        return True

    def join(self):
        if self.queue.is_empty():
            return []

        s_oldest = self.queue.peek_front()
        oldest_key = self.get_key_from_s(s_oldest)

        if not self._load_r_partition(oldest_key):
            print(f"[Stage] Key {oldest_key} leads nowhere. Dropping the tuple.")
            for i, (s_tuple, q_node) in enumerate(self.hash_table[oldest_key]):
                if s_tuple == s_oldest:
                    self.hash_table[oldest_key].pop(i)
                    self.queue.delete_node(q_node)
                    self.available_slots_w += 1
                    break
            return []

        joined = []
        for r_key, r_tuple in list(self.disk_buffer.items()):
            if r_key in self.hash_table:
                matches = self.hash_table.pop(r_key)
                for (s_tuple, q_node) in matches:
                    joined.append((s_tuple, r_tuple, self.header_map))
                    self.queue.delete_node(q_node)
                    self.available_slots_w += 1

        return joined


class JoinOrchestrator:
    """
    This just coordinates the two join stages and pushes the final result into MySQL.
    """
    def __init__(self, db_conn, cust_index, prod_index):
        self.db_conn = db_conn
        self.stream_buffer = queue.Queue(maxsize=STREAM_BUFFER_MAX_SIZE)

        # Stage 1: join with customer
        self.stage1_customer = HybridJoinStage(
            index_data=cust_index,
            get_key_from_s=lambda s: s[2],   # customer ID
            key_index_in_r=1
        )

        # Stage 2: join with product
        self.stage2_product = HybridJoinStage(
            index_data=prod_index,
            get_key_from_s=lambda s_prime: s_prime[0][3],  # product ID
            key_index_in_r=1
        )

        self.stream_complete = False
        self.processed_count = 0
        self.insert_buffer = []
        self.batch_size = 100

    def stream_loader_task(self):
        print("[Loader] Reading the stream file...")
        try:
            with open(STREAM_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)
                for row in reader:
                    time.sleep(random.uniform(0.001, 0.01))
                    self.stream_buffer.put(tuple(row))
        except FileNotFoundError:
            print(f"[Loader] Can't find {STREAM_FILE}")
        except Exception as e:
            print(f"[Loader] Something broke while reading: {e}")
        finally:
            self.stream_buffer.put(None)
            print("[Loader] Done pulling rows.")

    def hybrid_join_task(self):
        print("[Joiner] Thread for the join started.")

        while True:
            # stage 1 intake
            while not self.stream_buffer.empty() and self.stage1_customer.available_slots_w > 0:
                s_tuple = self.stream_buffer.get()
                if s_tuple is None:
                    self.stream_complete = True
                    break
                self.stage1_customer.add_stream_tuple(s_tuple)

            if self.stream_complete and self.stream_buffer.empty() and \
               self.stage1_customer.queue.is_empty() and self.stage2_product.queue.is_empty():
                break

            # run stage 1
            intermediate = self.stage1_customer.join()

            # forward them to stage 2
            for s_prime in intermediate:
                if self.stage2_product.available_slots_w > 0:
                    self.stage2_product.add_stream_tuple(s_prime)
                else:
                    print("[Joiner] Stage 2 is full. Putting this tuple back to stage 1.")
                    self.stage1_customer.add_stream_tuple(s_prime[0])
                    break

            # run stage 2
            final_outputs = self.stage2_product.join()

            for (s_prime, r_prod_tuple, r_prod_header_map) in final_outputs:
                (s_tuple, r_cust_tuple, _) = s_prime
                enriched = self._enrich_and_finalize(s_tuple, r_prod_tuple, r_prod_header_map)
                if enriched:
                    self.insert_buffer.append(enriched)
                    self.processed_count += 1

            if len(self.insert_buffer) >= self.batch_size:
                self._flush_insert_buffer(self.db_conn.cursor())

        if self.insert_buffer:
            self._flush_insert_buffer(self.db_conn.cursor())

        print(f"[Joiner] All done. Total processed: {self.processed_count}")

    def _enrich_and_finalize(self, s_tuple, r_prod_tuple, r_header_map):
        try:
            # S tuple
            order_id = s_tuple[1]
            cust_id = int(s_tuple[2])
            prod_id = s_tuple[3]
            qty = int(float(s_tuple[4]))
            date_raw = s_tuple[5]
            date_key = int(date_raw.replace('-', ''))

            # R tuple via header map
            price = float(r_prod_tuple[r_header_map['price$']])
            store_id = r_prod_tuple[r_header_map['storeID']]
            supplier_id = r_prod_tuple[r_header_map['supplierID']]

            total = qty * price

            return (
                order_id, cust_id, prod_id, store_id,
                supplier_id, date_key, price, qty, total
            )
        except Exception as e:
            print(f"[Enrich] Couldn't handle this row: {e}")
            print(f"         S: {s_tuple}")
            print(f"         R: {r_prod_tuple}")
            return None

    def _flush_insert_buffer(self, cursor):
        print(f"[DB] Pushing {len(self.insert_buffer)} rows into FactSales...")
        try:
            query = """
                INSERT IGNORE INTO FactSales (
                    Transaction_ID, Customer_ID, Product_ID, Store_ID, 
                    Supplier_ID, Date_Key, Price, Quantity, Purchase_Amount
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
    print("=== Starting ETL (HYBRID JOIN) ===")

    try:
        with open(CUST_INDEX_FILE, 'r') as f:
            cust_index = json.load(f)
        with open(PROD_INDEX_FILE, 'r') as f:
            prod_index = json.load(f)
        print("Index files loaded.")
    except FileNotFoundError:
        print("Index files missing. Run the index builder first.")
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--database", default=None)
    parser.add_argument("--port", default=None)
    args = parser.parse_args()

    db_host = args.host or input("MySQL host (default: localhost): ") or "localhost"
    db_user = args.user or input("MySQL user (default: root): ") or "root"
    db_password = args.password or getpass.getpass("Password: ") or "meow"
    db_name = args.database or input("Database (default: walmart): ") or "walmart"
    db_port = args.port or input("Port (default: 3306): ") or "3306"

    try:
        conn = mysql.connector.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            autocommit=False
        )
        print("Connected to MySQL.")
    except mysql.connector.Error as err:
        print(f"Connection failed: {err}")
        return

    orchestrator = JoinOrchestrator(conn, cust_index, prod_index)

    loader = threading.Thread(target=orchestrator.stream_loader_task)
    joiner = threading.Thread(target=orchestrator.hybrid_join_task)

    loader.start()
    joiner.start()

    loader.join()
    print("[Main] Loader finished.")
    joiner.join()
    print("[Main] Joiner finished.")

    conn.close()
    print("=== ETL Finished ===")


if __name__ == "__main__":
    main()
