# #####################################################################
# ## PART 3: THE HYBRIDJOIN ETL SCRIPT (S-Cached)
# ## File: hybrid_join_etl.py
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
from doubly_linked_list import DoublyLinkedList # Import our new class

# --- Configuration Constants ---
HASH_SLOTS = 10000
STREAM_BUFFER_MAX_SIZE = 2000 # For the initial stream buffer

# --- File Paths ---
STREAM_FILE = 'transactional_data.csv'
CUST_INDEX_FILE = 'cust_index.json'
PROD_INDEX_FILE = 'prod_index.json'


class HybridJoinStage:
    """
    Implements one stage of the HYBRIDJOIN algorithm (S-Cached).
    This class is *not* thread-safe by itself; it's designed
    to be run by a single "Joiner" thread.
    """
    def __init__(self, index_data, get_key_from_s, key_index_in_r):
        self.index = index_data
        self.get_key_from_s = get_key_from_s # Function to get key from S
        self.key_index_in_r = key_index_in_r # Column index of key in R
        
        # Core data structures from the spec
        self.hash_table = defaultdict(list)
        self.queue = DoublyLinkedList()
        self.available_slots_w = HASH_SLOTS
        
        self.current_r_partition = None
        self.disk_buffer = {} # Holds the loaded R partition
        self.disk_buffer_filename = None

    def _load_r_partition(self, key):
        """Loads the relevant R partition for the given key."""
        try:
            partition_file = self.index[key]
        except KeyError:
            print(f"  [Warn] Key {key} not found in index. Cannot load partition.")
            return False # Key not in index
            
        # Check if this partition is already in the disk buffer
        if partition_file == self.disk_buffer_filename:
            return True # Already loaded
            
        # No, load new partition
        print(f"  [Joiner] Loading R partition: {partition_file}")
        self.disk_buffer.clear()
        try:
            with open(partition_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                for r_tuple in reader:
                    r_key = r_tuple[self.key_index_in_r]
                    self.disk_buffer[r_key] = r_tuple
            self.disk_buffer_filename = partition_file
            return True
        except FileNotFoundError:
            print(f"  [Error] Partition file not found: {partition_file}")
            return False
            
    def add_stream_tuple(self, s_tuple):
        """Adds one stream tuple to this stage's H and Q."""
        if self.available_slots_w <= 0:
            return False # Hash table is full
            
        # 1. Add to Queue
        q_node = self.queue.append(s_tuple)
        
        # 2. Add to Hash Table
        s_key = self.get_key_from_s(s_tuple)
        self.hash_table[s_key].append( (s_tuple, q_node) )
        
        # 3. Update 'w'
        self.available_slots_w -= 1
        return True

    def join(self):
        """
        Runs the core join logic as described.
        Returns a list of joined_outputs.
        """
        if self.queue.is_empty():
            return [] # Nothing to join
            
        # 1. Get oldest key from Queue
        s_oldest = self.queue.peek_front()
        oldest_key = self.get_key_from_s(s_oldest)
        
        # 2. Load relevant R partition
        if not self._load_r_partition(oldest_key):
            # Failed to load partition (e.g., bad key).
            # We must discard the bad stream tuple to avoid an infinite loop.
            print(f"  [Error] Discarding tuple with un-joinable key: {oldest_key}")
            s_tuple, q_node = self.hash_table[oldest_key].pop(0)
            self.queue.delete_node(q_node)
            self.available_slots_w += 1
            return [] # Try again on next loop
            
        # 3. Inner loop: Probe H with tuples from R's disk buffer
        joined_outputs = []
        tuples_in_r_partition = list(self.disk_buffer.items())
        
        for r_key, r_tuple in tuples_in_r_partition:
            
            # Probe H and "pop" the list of matches
            if r_key in self.hash_table:
                matches = self.hash_table.pop(r_key)
                
                # 4. Generate outputs, delete from H/Q
                for (s_tuple, q_node) in matches:
                    
                    # Create the output
                    joined_outputs.append( (s_tuple, r_tuple) )
                    
                    # Delete from Q
                    self.queue.delete_node(q_node)
                    
                    # Increment 'w'
                    self.available_slots_w += 1
                    
        return joined_outputs


class JoinOrchestrator:
    """
    Manages the two threads and the two-stage join pipeline.
    """
    def __init__(self, db_conn, cust_index, prod_index):
        self.db_conn = db_conn
        
        # Thread-safe queue from Loader -> Joiner
        self.stream_buffer = queue.Queue(maxsize=STREAM_BUFFER_MAX_SIZE)
        
        # --- Stage 1: (S + R_cust) -> S' ---
        self.stage1_customer = HybridJoinStage(
            index_data=cust_index,
            # S tuple format: (, orderID, Customer_ID, Product_ID, quantity, date)
            # Index:           (0, 1,       2,           3,          4,        5)
            get_key_from_s=lambda s: s[2], # Get Customer_ID
            # R_cust format: (, Customer_ID, Gender, ...)
            key_index_in_r=1 # Customer_ID is at index 1
        )
        
        # --- Stage 2: (S' + R_prod) -> Final ---
        self.stage2_product = HybridJoinStage(
            index_data=prod_index,
            # S' tuple format: (s_tuple, r_cust_tuple)
            get_key_from_s=lambda s_prime: s_prime[0][3], # Get Product_ID from s_tuple
            # R_prod format: (, Product_ID, Category, price$, ...)
            key_index_in_r=1 # Product_ID is at index 1
        )
        
        self.stream_complete = False
        self.processed_count = 0
        
        # Final buffer for the DB loader
        self.insert_buffer = []
        self.batch_size = 100
        
    def stream_loader_task(self):
        """[THREAD 1] Loads data into the stream_buffer."""
        print("[Loader] Stream loader thread started...")
        try:
            with open(STREAM_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    time.sleep(random.uniform(0.001, 0.01))
                    self.stream_buffer.put(tuple(row))
        except FileNotFoundError:
            print(f"[Loader] ERROR: Stream file not found: {STREAM_FILE}")
        except Exception as e:
            print(f"[Loader] ERROR reading stream: {e}")
        finally:
            self.stream_buffer.put(None) # Sentinel
            print("[Loader] Stream loading complete.")

    def hybrid_join_task(self):
        """[THREAD 2] Runs the entire join pipeline."""
        print("[Joiner] HYBRIDJOIN processor thread started...")
        
        while True:
            # --- 1. Load from Stream Buffer into Stage 1 ---
            # "load up to w... tuples into the hash table"
            while not self.stream_buffer.empty() and self.stage1_customer.available_slots_w > 0:
                s_tuple = self.stream_buffer.get()
                if s_tuple is None:
                    self.stream_complete = True
                    break
                self.stage1_customer.add_stream_tuple(s_tuple)
            
            # --- 2. Run Join for Stage 1 (S + R_cust) ---
            # This generates intermediate (S') tuples
            intermediate_tuples = self.stage1_customer.join()
            
            # --- 3. Load (S') tuples into Stage 2 ---
            for s_prime in intermediate_tuples:
                if self.stage2_product.available_slots_w > 0:
                    self.stage2_product.add_stream_tuple(s_prime)
                else:
                    # Stage 2 is full, data will stay in Stage 1's H/Q
                    # until space is available. This is natural backpressure.
                    print("[Joiner] Backpressure: Stage 2 H is full.")
                    break
            
            # --- 4. Run Join for Stage 2 (S' + R_prod) ---
            final_outputs = self.stage2_product.join()
            
            # --- 5. Process Final Outputs ---
            for (s_prime, r_prod_tuple) in final_outputs:
                (s_tuple, r_cust_tuple) = s_prime
                
                # We have (s_tuple, r_cust_tuple, r_prod_tuple)
                # Now, create the final record for the database
                enriched_record = self._enrich_and_finalize(s_tuple, r_prod_tuple)
                
                if enriched_record:
                    self.insert_buffer.append(enriched_record)
                    self.processed_count += 1
            
            # --- 6. Flush to DB if batch is full ---
            if len(self.insert_buffer) >= self.batch_size:
                self._flush_insert_buffer(self.db_conn.cursor())
            
            # --- 7. Check for exit condition ---
            if self.stream_complete and \
               self.stream_buffer.empty() and \
               self.stage1_customer.queue.is_empty() and \
               self.stage2_product.queue.is_empty():
                
                print("[Joiner] Pipeline empty and stream complete. Exiting.")
                break

        # Final flush
        if self.insert_buffer:
            self._flush_insert_buffer(self.db_conn.cursor())
            
        print(f"[Joiner] Join processing complete. Total processed: {self.processed_count}")

    def _enrich_and_finalize(self, s_tuple, r_prod_tuple):
        """Helper to create the final tuple for FactSales."""
        try:
            # S: (, orderID, Customer_ID, Product_ID, quantity, date)
            # I: (0, 1,       2,           3,          4,        5)
            s_order_id = s_tuple[1]
            s_cust_id_int = int(s_tuple[2])
            s_prod_id = s_tuple[3]
            s_quantity = float(s_tuple[4])
            s_date = s_tuple[5]
            
            # R_prod: (, Product_ID, Category, price$, ...)
            # I:      (0, 1,          2,        3)
            p_price = float(r_prod_tuple[3])
            
            # Transformations
            date_key = int(s_date.replace('-', ''))
            purchase_amount = s_quantity * p_price
            
            # (Transaction_ID, Customer_ID, Product_ID, Date_Key, Purchase_Amount)
            return (
                s_order_id,
                s_cust_id_int,
                s_prod_id,
                date_key,
                purchase_amount
            )
        except Exception as e:
            print(f"[Enrich] Error finalizing tuple {s_tuple}: {e}")
            return None

    def _flush_insert_buffer(self, cursor):
        """Performs a batch INSERT into the FactSales table."""
        print(f"  [Loader] Flushing {len(self.insert_buffer)} records to DWH...")
        try:
            query = """
                INSERT IGNORE INTO FactSales (
                    Transaction_ID, Customer_ID, Product_ID, Date_Key, Purchase_Amount
                ) VALUES (%s, %s, %s, %s, %s)
            """
            cursor.executemany(query, self.insert_buffer)
            self.db_conn.commit()
            self.insert_buffer.clear() # Clear the batch
        except mysql.connector.Error as err:
            print(f"  [Loader] ERROR flushing to database: {err}")
            self.db_conn.rollback()
        finally:
            cursor.close()

def main():
    print("--- Near-Real-Time DWH ETL Started (S-Cached HYBRIDJOIN) ---")
    
    # --- 1. Load Indexes into Memory ---
    try:
        with open(CUST_INDEX_FILE, 'r') as f: cust_index = json.load(f)
        with open(PROD_INDEX_FILE, 'r') as f: prod_index = json.load(f)
        print("Indexes loaded successfully.")
    except FileNotFoundError:
        print("FATAL: Index files not found. Please run 'build_index.py' first.")
        return
        
    # --- 2. Get DB Connection ---
    try:
        db_name = "walmart"
        db_user = "root"
        db_pass = "meow"
        db_host = "localhost"
        db_port = "3306"
        
        conn = mysql.connector.connect(
            database=db_name, user=db_user, password=db_pass,
            host=db_host, port=db_port or 3306,
            autocommit=False
        )
        print("Database connection successful.")
    except mysql.connector.Error as err:
        print(f"FATAL: Unable to connect to the database. {err}")
        return

    # --- 3. Start Threads ---
    orchestrator = JoinOrchestrator(conn, cust_index, prod_index)

    loader_thread = threading.Thread(
        target=orchestrator.stream_loader_task, name="StreamLoaderThread"
    )
    joiner_thread = threading.Thread(
        target=orchestrator.hybrid_join_task, name="JoinProcessorThread"
    )

    loader_thread.start()
    joiner_thread.start()

    # --- 4. Wait for Completion ---
    loader_thread.join()
    print("[Main] Loader thread has finished.")
    joiner_thread.join()
    print("[Main] Processor thread has finished.")

    conn.close()
    print("--- ETL Process Finished ---")

if __name__ == "__main__":
    main()