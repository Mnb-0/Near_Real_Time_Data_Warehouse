#####################################################################
# Just splitting the big CSVs into smaller chunks and keeping track. #
#####################################################################

import os
import csv
import json

CUSTOMER_MASTER_FILE = 'customer_master_data.csv'
PRODUCT_MASTER_FILE = 'product_master_data.csv'

PARTITION_SIZE = 500

CUST_PART_DIR = 'partitions/customer'
PROD_PART_DIR = 'partitions/product'
CUST_INDEX_FILE = 'cust_index.json'
PROD_INDEX_FILE = 'prod_index.json'

def build_partitions_and_index(master_file, key_index, partition_dir, index_file):
    # Taking the giant CSV, chopping it up, and making a quick map of where stuff goes.
    print(f"Processing: {master_file}")

    os.makedirs(partition_dir, exist_ok=True)

    index = {}
    partition_num = 0
    records_in_partition = 0

    try:
        with open(master_file, 'r', encoding='utf-8') as f_in:
            reader = csv.reader(f_in)
            header = next(reader)

            partition_filename = os.path.join(partition_dir, f'part_{partition_num}.csv')
            f_out = open(partition_filename, 'w', encoding='utf-8', newline='')
            writer = csv.writer(f_out)
            writer.writerow(header)

            for row in reader:
                try:
                    key = row[key_index]
                except IndexError:
                    print(f"  skipping weird row: {row}")
                    continue

                writer.writerow(row)
                records_in_partition += 1
                index[key] = partition_filename  # assuming keys won't fight each other

                if records_in_partition >= PARTITION_SIZE:
                    f_out.close()
                    print(f"  made a partition: {partition_filename}")
                    partition_num += 1
                    records_in_partition = 0

                    partition_filename = os.path.join(partition_dir, f'part_{partition_num}.csv')
                    f_out = open(partition_filename, 'w', encoding='utf-8', newline='')
                    writer = csv.writer(f_out)
                    writer.writerow(header)

            f_out.close()
            if records_in_partition > 0:
                print(f"  made a partition: {partition_filename}")

    except FileNotFoundError:
        print(f"Couldn't find: {master_file}")
        return None

    try:
        with open(index_file, 'w', encoding='utf-8') as f_json:
            json.dump(index, f_json, indent=2)
        print(f"  index saved -> {index_file}")
    except Exception as e:
        print(f"Problem writing index {index_file}: {e}")
        return None

    print(f"Done with: {master_file}")
    return index

def main():
    print("Starting partitioning...")

    build_partitions_and_index(
        master_file=CUSTOMER_MASTER_FILE,
        key_index=1,
        partition_dir=CUST_PART_DIR,
        index_file=CUST_INDEX_FILE
    )

    build_partitions_and_index(
        master_file=PRODUCT_MASTER_FILE,
        key_index=1,
        partition_dir=PROD_PART_DIR,
        index_file=PROD_INDEX_FILE
    )

    print("Everything's split up and indexed.")

if __name__ == "__main__":
    main()
