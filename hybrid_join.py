# #####################################################################
# ## FILE: hybrid_join.py (CORRECT)
# ##
# ## This script fixes:
# ## 1. The ValueError (3-tuple unpack) in hybrid_join_task.
# ## 2. The incorrect key_index_in_r for Stage 2.
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

# --- Configuration ---
HASH_SLOTS = 10000
STREAM_BUFFER_MAX_SIZE = 2000
STREAM_FILE = 'transactional_data.csv'
CUST_INDEX_FILE = 'cust_index.json'
PROD_INDEX_FILE = 'prod_index.json'


class HybridJoinStage:
    """
    Implements one stage of the S-Cached HYBRIDJOIN.
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
        self.header_map = {} # Holds the header for the loaded partition

    def _load_r_partition(self, key):
        try:
            partition_file = self.index[key]
        except KeyError:
            print(f"[Stage] No matching R-partition for key {key}. Ignoring it.")
            return False
        if partition_file == self.disk_buffer_filename:
            return True

        print(f"[Stage] Loading R partition: {partition_file}")
        self.disk_buffer.clear()
        try:
            with open(partition_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                # Store the header map
                self.header_map = {name: idx for idx, name in enumerate(header)}
                for r_tuple in reader:
                    r_key = r_tuple[self.key_index_in_r]
                    self.disk_buffer[r_key] = r_tuple
            self.disk_buffer_filename = partition_file
            return True
        except FileNotFoundError:
            print(f"[Stage] R-partition file missing: {partition_file}")
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
            print(f"[Stage] Tossing S-tuple with dead key {oldest_key}")
            for i, (s_tuple, q_node) in enumerate(self.hash_table[oldest_key]):
                if s_tuple == s_oldest:
                    self.hash_table[oldest_key].pop(i)
                    self.queue.delete_node(q_node)
                    self.available_slots_w += 1
                    break
            return []

        joined_outputs = []
        for r_key, r_tuple in list(self.disk_buffer.items()):
            if r_key in self.hash_table:
                matches = self.hash_table.pop(r_key)
                for (s_tuple, q_node) in matches:
                    # Pass the header map for the *current* relation
                    joined_outputs.append((s_tuple, r_tuple, self.header_map))
                    self.queue.delete_node(q_node)
                    self.available_slots_w += 1
        return joined_outputs


class JoinOrchestrator:
    """
    Manages the two-stage pipeline.
    """
    def __init__(self, db_conn, cust_index, prod_index):
        self.db_conn = db_conn
        self.stream_buffer = queue.Queue(maxsize=STREAM_BUFFER_MAX_SIZE)

        # Stage 1: Customer join
        self.stage1_customer = HybridJoinStage(
            index_data=cust_index,
            # S: (, orderID, Customer_ID, Product_ID, quantity, date)
            get_key_from_s=lambda s: s[2], # S[2] is Customer_ID
            key_index_in_r=1              # R_cust[1] is Customer_ID
        )

        # Stage 2: Product join
        self.stage2_product = HybridJoinStage(
            index_data=prod_index,
            # S_prime[0] is the original s_tuple
            get_key_from_s=lambda s_prime: s_prime[0][3], # S[3] is Product_ID
            # This now matches build_index.py
            key_index_in_r=1 # R_prod[1] is Product_ID
        )

        self.stream_complete = False
        self.processed_count = 0
        self.insert_buffer = []
        self.batch_size = 100

    def stream_loader_task(self):
        """[THREAD 1] Loads raw data from CSV into stream buffer."""
        print("[Loader] Starting stream read...")
        try:
            with open(STREAM_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # header
                for row in reader:
                    time.sleep(random.uniform(0.001, 0.01))
                    self.stream_buffer.put(tuple(row))
        except FileNotFoundError:
            print(f"[Loader] Stream file not found: {STREAM_FILE}")
        except Exception as e:
            print(f"[Loader] Unexpected read error: {e}")
        finally:
            self.stream_buffer.put(None) # Sentinel
            print("[Loader] Stream reading done.")

    def hybrid_join_task(self):
        """[THREAD 2] Runs the full 2-stage join and load pipeline."""
        print("[Joiner] Join thread running...")

        while True:
            # Fill Stage 1
            while not self.stream_buffer.empty() and self.stage1_customer.available_slots_w > 0:
                s_tuple = self.stream_buffer.get()
                if s_tuple is None:
                    self.stream_complete = True
                    break
                self.stage1_customer.add_stream_tuple(s_tuple)
            
            # Check for exit condition
            if self.stream_complete and self.stream_buffer.empty() and \
               self.stage1_customer.queue.is_empty() and self.stage2_product.queue.is_empty():
                break 

            # Run Stage 1 Join
            intermediate = self.stage1_customer.join()

            # Push to Stage 2
            for s_prime in intermediate:
                # s_prime from Stage 1 is (s_tuple, r_cust_tuple, cust_header_map)
                if self.stage2_product.available_slots_w > 0:
                    self.stage2_product.add_stream_tuple(s_prime)
                else:
                    print("[Joiner] Stage 2 buffer full. Slowing down.")
                    # Re-add the *original* stream tuple back to Stage 1
                    self.stage1_customer.add_stream_tuple(s_prime[0])
                    break
            
            # Run Stage 2 Join
            final_outputs = self.stage2_product.join()
            
            for (s_prime, r_prod_tuple, r_prod_header_map) in final_outputs:
                # s_prime is the 3-part tuple from Stage 1
                # ---
                # ## THIS IS THE FIX ##
                # ---
                (s_tuple, r_cust_tuple, _) = s_prime # Unpack 3 parts
                
                # Pass all components to be enriched
                enriched = self._enrich_and_finalize(s_tuple, r_prod_tuple, r_prod_header_map)
                if enriched:
                    self.insert_buffer.append(enriched)
                    self.processed_count += 1

            if len(self.insert_buffer) >= self.batch_size:
                self._flush_insert_buffer(self.db_conn.cursor())

        # Final flush
        if self.insert_buffer:
            self._flush_insert_buffer(self.db_conn.cursor())
        print(f"[Joiner] Finished. Processed {self.processed_count} records.")

    def _enrich_and_finalize(self, s_tuple, r_prod_tuple, r_header_map):
        """Builds the final FactSales row from all joined components."""
        try:
            # S: (, orderID, Customer_ID, Product_ID, quantity, date)
            order_id = s_tuple[1]
            cust_id = int(s_tuple[2])
            prod_id = s_tuple[3]
            qty = int(float(s_tuple[4])) # Get quantity
            date_raw = s_tuple[5]
            date_key = int(date_raw.replace('-', ''))

            # R_prod: Use the header map to get columns *by name*
            price = float(r_prod_tuple[r_header_map['price$']])
            store_id = r_prod_tuple[r_header_map['storeID']]
            supplier_id = r_prod_tuple[r_header_map['supplierID']]
            
            total_amt = qty * price

            # (Transaction_ID, Customer_ID, Product_ID, Store_ID, 
            #  Supplier_ID, Date_Key, Price, Quantity, Purchase_Amount)
            return (
                order_id, cust_id, prod_id, store_id, 
                supplier_id, date_key, price, qty, total_amt
            )
        except Exception as e:
            print(f"[Enrich] Couldn't process row: {e}. S_Tuple: {s_tuple}, R_Tuple: {r_prod_tuple}")
            return None

    def _flush_insert_buffer(self, cursor):
        """Inserts a batch of records into the 9-column FactSales table."""
        print(f"[DB] Inserting {len(self.insert_buffer)} rows...")
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
    print("=== HYBRID JOIN ETL Start ===")

    try:
        with open(CUST_INDEX_FILE, 'r') as f:
            cust_index = json.load(f)
        with open(PROD_INDEX_FILE, 'r') as f:
            prod_index = json.load(f)
        print("Index files loaded successfully.")
    except FileNotFoundError:
        print("Missing index files. Run 'build_index.py' first.")
        return
    
    # [cite_start]Get credentials as required by rubric [cite: 201]
    db_host = input("Enter MySQL host (default: localhost): ") or "localhost"
    db_user = input("Enter MySQL user (default: root): ") or "root"
    db_password = getpass.getpass("Enter MySQL password: ") or "meow"
    db_name = input("Enter database name (default: walmart): ") or "walmart"
    db_port = input("Enter MySQL port (default: 3306): ") or "3306"

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