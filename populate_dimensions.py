# Just filling the dimension tables. Nothing fancy.

import csv
import getpass
import argparse
import mysql.connector
from mysql.connector import errorcode

CUSTOMER_MASTER_FILE = 'customer_master_data.csv'
PRODUCT_MASTER_FILE = 'product_master_data.csv'


def populate_dim_date(cursor):
    # generating a whole date table because typing dates manually is pain
    print("[DimDate] Kicking off date dimension fill...")

    set_limit_query = "SET SESSION cte_max_recursion_depth = 3000;"

    date_query = """
    INSERT IGNORE INTO DimDate (
        Date_Key, Full_Date, Day_Of_Week_Name, Day_Of_Week_Num,
        Is_Weekend, Month_Name, Month_Num, Quarter, Year
    )
    WITH RECURSIVE DateRange AS (
        SELECT '2019-01-01' AS datum
        UNION ALL
        SELECT DATE_ADD(datum, INTERVAL 1 DAY)
        FROM DateRange
        WHERE datum < '2025-12-31'
    )
    SELECT
        CAST(DATE_FORMAT(datum, '%Y%m%d') AS UNSIGNED),
        datum,
        DAYNAME(datum),
        DAYOFWEEK(datum),
        CASE WHEN DAYOFWEEK(datum) IN (1, 7) THEN 1 ELSE 0 END,
        MONTHNAME(datum),
        MONTH(datum),
        QUARTER(datum),
        YEAR(datum)
    FROM DateRange;
    """

    try:
        cursor.execute(set_limit_query)
        cursor.execute(date_query)
        print(f"[DimDate] Done. Rows inserted/ignored: {cursor.rowcount}")
    except mysql.connector.Error as err:
        print(f"[DimDate][ERROR] Could not load DimDate: {err}")
        raise


def populate_dim_customer(cursor):
    # reading the customer file and stuffing rows into DimCustomer
    print("[DimCustomer] Loading customer CSV into dimension table...")

    query = """
    INSERT IGNORE INTO DimCustomer (
        Customer_ID, Gender, Age_Group, Occupation, City_Category,
        Stay_In_Current_City_Years, Marital_Status
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    data_to_insert = []
    
    try:
        with open(CUSTOMER_MASTER_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # skipping header

            for row in reader:
                if len(row) < 8:
                    continue
                try:
                    data_to_insert.append((
                        int(row[1]),
                        row[2],
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                        int(row[7])
                    ))
                except ValueError:
                    print(f"[DimCustomer] Skipped a broken row: {row}")

        if data_to_insert:
            cursor.executemany(query, data_to_insert)
            print(f"[DimCustomer] Inserted/Ignored rows: {cursor.rowcount}")
        else:
            print("[DimCustomer] No usable data found in the CSV.")

    except FileNotFoundError:
        print(f"[DimCustomer][ERROR] Can't find the customer CSV.")
    except Exception as e:
        print(f"[DimCustomer][ERROR] Something went wrong: {e}")


def populate_product_store_supplier(cursor):
    # this file is a mess but we take what we can get
    print("[DimProduct/Store/Supplier] Parsing product master file...")

    query_product = """
    INSERT IGNORE INTO DimProduct (Product_ID, Product_Category) 
    VALUES (%s, %s)
    """
    query_store = """
    INSERT IGNORE INTO DimStore (Store_ID, Store_Name) 
    VALUES (%s, %s)
    """
    query_supplier = """
    INSERT IGNORE INTO DimSupplier (Supplier_ID, Supplier_Name) 
    VALUES (%s, %s)
    """
    
    products = set()
    stores = set()
    suppliers = set()
    
    try:
        with open(PRODUCT_MASTER_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)

            if header is None:
                print("[ERROR] Product CSV has no header. Not dealing with that.")
                return

            col_map = {n: i for i, n in enumerate(header)}
            required = ['Product_ID', 'Product_Category', 'storeID', 'storeName', 'supplierID', 'supplierName']

            for col in required:
                if col not in col_map:
                    print(f"[ERROR] Missing column '{col}' in product CSV.")
                    return

            for row in reader:
                if len(row) < len(header):
                    continue

                try:
                    prod_id = row[col_map['Product_ID']]
                    prod_cat = row[col_map['Product_Category']]
                    if prod_id:
                        products.add((prod_id, prod_cat))

                    store_id = row[col_map['storeID']]
                    store_name = row[col_map['storeName']]
                    if store_id:
                        stores.add((store_id, store_name))

                    supp_id = row[col_map['supplierID']]
                    supp_name = row[col_map['supplierName']]
                    if supp_id:
                        suppliers.add((supp_id, supp_name))

                except Exception as e:
                    print(f"[ERROR] Couldn't parse row {row}: {e}")

        if products:
            cursor.executemany(query_product, list(products))
            print(f"[DimProduct] Inserted/Ignored rows: {cursor.rowcount}")
        if stores:
            cursor.executemany(query_store, list(stores))
            print(f"[DimStore] Inserted/Ignored rows: {cursor.rowcount}")
        if suppliers:
            cursor.executemany(query_supplier, list(suppliers))
            print(f"[DimSupplier] Inserted/Ignored rows: {cursor.rowcount}")

    except FileNotFoundError:
        print("[ERROR] Product CSV missing.")
    except Exception as e:
        print(f"[ERROR] Unexpected issue: {e}")


def main():
    # connection setup + running the loaders
    print("=== Starting dimension population ===")

    conn = None
    cursor = None

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--database", default=None)
    parser.add_argument("--port", default=None)
    args = parser.parse_args()

    db_host = args.host or input("MySQL host (localhost): ") or "localhost"
    db_user = args.user or input("MySQL user (root): ") or "root"
    db_password = args.password or getpass.getpass("MySQL password: ") or "meow"
    db_name = args.database or input("Database name (walmart): ") or "walmart"
    db_port = args.port or input("MySQL port (3306): ") or "3306"

    try:
        conn = mysql.connector.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        
        cursor = conn.cursor()
        print(f"[Main] Connected to {db_name} as {db_user}")

        populate_dim_date(cursor)
        populate_dim_customer(cursor)
        populate_product_store_supplier(cursor)

        conn.commit()
        print("[Main] All good. Changes saved.")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("[Main][FATAL] Wrong MySQL username/password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"[Main][FATAL] Database '{db_name}' doesn't exist.")
        else:
            print(f"[Main][FATAL] MySQL died: {err}")
    except Exception as e:
        print(f"[Main][FATAL] Something blew up: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("[Main] Connection closed.")

    print("=== Done with dimension population ===")


if __name__ == "__main__":
    main()
