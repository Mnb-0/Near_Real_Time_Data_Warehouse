# #####################################################################
# ## FILE: populate_dimensions.py
# ##
# ## This script populates all four dimension tables:
# ## DimDate, DimCustomer, DimProduct, DimStore, and DimSupplier.
# #####################################################################

import mysql.connector
import csv
import getpass
from mysql.connector import errorcode
import argparse

# --- File paths ---
CUSTOMER_MASTER_FILE = 'customer_master_data.csv'
PRODUCT_MASTER_FILE = 'product_master_data.csv'


def populate_dim_date(cursor):
    """
    Populate DimDate using a recursive CTE. Requires MySQL 8.0+.
    """
    print("[DimDate] Starting population of date dimension...")

    # Set a safe recursion depth for the session
    set_limit_query = "SET SESSION cte_max_recursion_depth = 3000;"

    date_query = """
    INSERT IGNORE INTO DimDate (
        Date_Key, Full_Date, Day_Of_Week_Name, Day_Of_Week_Num,
        Is_Weekend, Month_Name, Month_Num, Quarter, Year
    )
    WITH RECURSIVE DateRange AS (
        SELECT '2019-01-01' AS datum -- start date
        UNION ALL
        SELECT DATE_ADD(datum, INTERVAL 1 DAY)
        FROM DateRange
        WHERE datum < '2025-12-31' -- end date
    )
    SELECT
        CAST(DATE_FORMAT(datum, '%Y%m%d') AS UNSIGNED) AS Date_Key,
        datum AS Full_Date,
        DAYNAME(datum) AS Day_Of_Week_Name,
        DAYOFWEEK(datum) AS Day_Of_Week_Num,
        CASE WHEN DAYOFWEEK(datum) IN (1, 7) THEN 1 ELSE 0 END AS Is_Weekend,
        MONTHNAME(datum) AS Month_Name,
        MONTH(datum) AS Month_Num,
        QUARTER(datum) AS Quarter,
        YEAR(datum) AS Year
    FROM DateRange;
    """

    try:
        cursor.execute(set_limit_query)
        cursor.execute(date_query)
        print(f"[DimDate] Done. INSERT IGNORE affected {cursor.rowcount} rows.")
    except mysql.connector.Error as err:
        print(f"[DimDate][ERROR] Could not populate DimDate: {err}")
        raise


def populate_dim_customer(cursor):
    """
    Read CUSTOMER_MASTER_FILE and populate DimCustomer.
    (This function is unchanged)
    """
    print("[DimCustomer] Starting population from customer CSV...")

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
            header = next(reader, None)  # skip header

            for row in reader:
                if len(row) < 8:
                    continue # Skip malformed row
                try:
                    data_to_insert.append((
                        int(row[1]),  # Customer_ID
                        row[2],       # Gender
                        row[3],       # Age_Group (from 'Age' col)
                        row[4],       # Occupation
                        row[5],       # City_Category
                        row[6],       # Stay_In_Current_City_Years
                        int(row[7])   # Marital_Status
                    ))
                except ValueError:
                    print(f"[DimCustomer] Skipping row with invalid data: {row}")
                    continue

        if data_to_insert:
            cursor.executemany(query, data_to_insert)
            print(f"[DimCustomer] Done. INSERT IGNORE affected {cursor.rowcount} rows.")
        else:
            print("[DimCustomer] Warning: No valid rows found in customer CSV.")

    except FileNotFoundError:
        print(f"[DimCustomer][ERROR] File not found: {CUSTOMER_MASTER_FILE}")
    except Exception as e:
        print(f"[DimCustomer][ERROR] Unexpected error: {e}")

# ---
# ## THIS IS THE NEW, CORRECTED FUNCTION ##
# ---
def populate_product_store_supplier(cursor):
    """
    Reads the (ambiguous) product_master_data.csv and populates
    DimProduct, DimStore, and DimSupplier independently.
    
    Uses INSERT IGNORE to handle duplicates gracefully.
    """
    print("[DimProduct/Store/Supplier] Starting population...")
    
    # Define the three queries
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
    
    # We use sets to hold data for batch insertion.
    # This is *much* faster than inserting one row at a time.
    products_to_insert = set()
    stores_to_insert = set()
    suppliers_to_insert = set()
    
    try:
        with open(PRODUCT_MASTER_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # skip header

            # Ensure we actually read a header row
            if header is None:
                print(f"[ERROR] No header found in {PRODUCT_MASTER_FILE}.")
                return

            # Cache header length and get column indices from header
            header_len = len(header)
            col_map = {name: idx for idx, name in enumerate(header)}
            
            # Check for required columns
            required_cols = ['Product_ID', 'Product_Category', 'storeID', 'storeName', 'supplierID', 'supplierName']
            for col in required_cols:
                if col not in col_map:
                    print(f"[ERROR] Missing required column '{col}' in {PRODUCT_MASTER_FILE}.")
                    return

            for row in reader:
                if len(row) < header_len:
                    continue # Skip malformed row
                
                try:
                    # Extract data for DimProduct
                    prod_id = row[col_map['Product_ID']]
                    prod_cat = row[col_map['Product_Category']]
                    if prod_id and prod_cat:
                        products_to_insert.add((prod_id, prod_cat))
                    
                    # Extract data for DimStore
                    store_id = row[col_map['storeID']]
                    store_name = row[col_map['storeName']]
                    if store_id:
                        stores_to_insert.add((store_id, store_name))
                        
                    # Extract data for DimSupplier
                    supp_id = row[col_map['supplierID']]
                    supp_name = row[col_map['supplierName']]
                    if supp_id:
                        suppliers_to_insert.add((supp_id, supp_name))
                        
                except Exception as e:
                    print(f"[ERROR] Error processing row {row}: {e}")

        # --- Execute batch inserts ---
        if products_to_insert:
            cursor.executemany(query_product, list(products_to_insert))
            print(f"[DimProduct] Done. INSERT IGNORE affected {cursor.rowcount} rows.")
            
        if stores_to_insert:
            cursor.executemany(query_store, list(stores_to_insert))
            print(f"[DimStore] Done. INSERT IGNORE affected {cursor.rowcount} rows.")

        if suppliers_to_insert:
            cursor.executemany(query_supplier, list(suppliers_to_insert))
            print(f"[DimSupplier] Done. INSERT IGNORE affected {cursor.rowcount} rows.")

    except FileNotFoundError:
        print(f"[ERROR] File not found: {PRODUCT_MASTER_FILE}")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")

def main():
    """
    Connect to MySQL then run all dimension-population functions.
    """
    print("=== DIMENSION POPULATION: BEGIN ===")

    conn = None
    cursor = None

    # --- THIS BLOCK IS MODIFIED ---
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=None, help="MySQL host")
    parser.add_argument("--user", default=None, help="MySQL user")
    parser.add_argument("--password", default=None, help="MySQL password")
    parser.add_argument("--database", default=None, help="MySQL database")
    # --- ADD THIS LINE ---
    parser.add_argument("--port", default=None, help="MySQL port")
    args = parser.parse_args()

    # If args were passed, use them. Otherwise, ask the user (normal behavior).
    db_host = args.host or input("Enter MySQL host (default: localhost): ") or "localhost"
    db_user = args.user or input("Enter MySQL user (default: root): ") or "root"
    db_password = args.password or getpass.getpass("Enter MySQL password: ") or "meow"
    db_name = args.database or input("Enter database name (default: walmart): ") or "walmart"
    # --- ADD THIS LINE ---
    db_port = args.port or input("Enter MySQL port (default: 3306): ") or "3306"
    # --- END MODIFIED BLOCK ---

    try:
        # --- THIS BLOCK IS MODIFIED ---
        conn = mysql.connector.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            # --- ADD THIS LINE ---
            port=db_port
        )
        # --- END MODIFIED BLOCK ---
        
        cursor = conn.cursor()
        print(f"[Main] Connected to database '{db_name}' as user '{db_user}'.")

        # --- Run Population Steps ---
        populate_dim_date(cursor)
        populate_dim_customer(cursor)
        populate_product_store_supplier(cursor)

        # Commit everything
        conn.commit()
        print("[Main] All changes committed.")

    # --- THIS BLOCK IS MODIFIED (to be more robust) ---
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("[Main][FATAL] Access denied. Check MySQL credentials.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"[Main][FATAL] Database '{db_name}' does not exist.")
        else:
            print(f"[Main][FATAL] Database error: {err}")
    # --- END MODIFIED BLOCK ---
    except Exception as e:
        print(f"[Main][FATAL] Unexpected error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("[Main] Database connection closed.")

    print("=== DIMENSION POPULATION: END ===")


if __name__ == "__main__":
    main()