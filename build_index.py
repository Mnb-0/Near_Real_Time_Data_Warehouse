# #####################################################################
# ## PART 1: PRE-PROCESSING SCRIPT
# ## File: build_index.py
# ##
# ## Run this script ONCE to build the partitions and indexes
# ## required by the HYBRIDJOIN algorithm.
# #####################################################################

import os
import csv
import json

# --- Configuration ---
# Use the new file names you provided
CUSTOMER_MASTER_FILE = 'customer_master_data.csv'
PRODUCT_MASTER_FILE = 'product_master_data.csv'
PARTITION_SIZE = 500  # As specified: "vP... 500 tuples"

# --- Output Files ---
CUST_PART_DIR = 'partitions/customer'
PROD_PART_DIR = 'partitions/product'
CUST_INDEX_FILE = 'cust_index.json'
PROD_INDEX_FILE = 'prod_index.json'

def build_partitions_and_index(master_file, key_index, partition_dir, index_file):
    """
    Reads a master CSV, splits it into partition files, and
    creates a JSON index mapping keys to partition filenames.
    """
    print(f"--- Processing {master_file} ---")
    
    os.makedirs(partition_dir, exist_ok=True)
    
    index = {}  # In-memory index
    partition_num = 0
    records_in_partition = 0
    
    try:
        with open(master_file, 'r', encoding='utf-8') as f_in:
            reader = csv.reader(f_in)
            header = next(reader)  # Read header
            
            partition_filename = os.path.join(partition_dir, f'part_{partition_num}.csv')
            f_out = open(partition_filename, 'w', encoding='utf-8', newline='')
            writer = csv.writer(f_out)
            writer.writerow(header) # Write header
            
            for row in reader:
                try:
                    # Key is at index 1 (Customer_ID or Product_ID)
                    key = row[key_index] 
                except IndexError:
                    print(f"  [Warn] Skipping bad row: {row}")
                    continue
                
                writer.writerow(row)
                records_in_partition += 1
                
                # Map this key to the current partition file
                index[key] = partition_filename
                
                # Check if partition is full
                if records_in_partition >= PARTITION_SIZE:
                    f_out.close()
                    print(f"  [+] Created partition: {partition_filename}")
                    
                    partition_num += 1
                    records_in_partition = 0
                    
                    partition_filename = os.path.join(partition_dir, f'part_{partition_num}.csv')
                    f_out = open(partition_filename, 'w', encoding='utf-8', newline='')
                    writer = csv.writer(f_out)
                    writer.writerow(header)
            
            f_out.close()
            if records_in_partition > 0:
                print(f"  [+] Created partition: {partition_filename}")

    except FileNotFoundError:
        print(f"FATAL ERROR: Master file not found: {master_file}")
        return None
    
    # Save the completed index to a JSON file
    try:
        with open(index_file, 'w', encoding='utf-8') as f_json:
            json.dump(index, f_json, indent=2)
        print(f"  [+] Successfully created index file: {index_file}")
    except Exception as e:
        print(f"FATAL ERROR writing index file {index_file}: {e}")
        return None
        
    print(f"--- Finished processing {master_file} ---")
    return index

def main():
    print("Starting pre-processing for Naeem's HYBRIDJOIN...")
    
    # Process Customer Data: Key is at index 1 (Customer_ID)
    build_partitions_and_index(
        master_file=CUSTOMER_MASTER_FILE,
        key_index=1, 
        partition_dir=CUST_PART_DIR,
        index_file=CUST_INDEX_FILE
    )
    
    # Process Product Data: Key is at index 1 (Product_ID)
    build_partitions_and_index(
        master_file=PRODUCT_MASTER_FILE,
        key_index=1,
        partition_dir=PROD_PART_DIR,
        index_file=PROD_INDEX_FILE
    )
    print("All pre-processing complete. You can now run the ETL script.")

if __name__ == "__main__":
    main()