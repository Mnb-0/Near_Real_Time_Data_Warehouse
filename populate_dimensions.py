# #####################################################################
# ## File: populate_dimensions.py
# ##
# ## Populates dimension tables: DimDate, DimCustomer, DimProduct
# ## Intended to run BEFORE the main ETL.
# #####################################################################

import mysql.connector
import csv
import getpass
from mysql.connector import errorcode

# --- File paths ---
CUSTOMER_MASTER_FILE = 'customer_master_data.csv'
PRODUCT_MASTER_FILE = 'product_master_data.csv'


def populate_dim_date(cursor):
    """
    Populate DimDate using a recursive CTE. Requires MySQL 8.0+.
    This function sets a safe recursion depth for the session, runs
    the date-range INSERT and reports how many rows were added.
    """
    print("[DimDate] Starting population of date dimension...")

    # Increase CTE recursion budget so the WITH RECURSIVE completes
    set_limit_query = "SET SESSION cte_max_recursion_depth = 3000;"

    date_query = """
    INSERT IGNORE INTO DimDate (
        Date_Key, Full_Date, Day_Of_Week_Name, Day_Of_Week_Num,
        Is_Weekend, Month_Name, Month_Num, Quarter, Year
    )
    WITH RECURSIVE DateRange AS (
        SELECT '2019-01-01' AS datum -- start date (inclusive)
        UNION ALL
        SELECT DATE_ADD(datum, INTERVAL 1 DAY)
        FROM DateRange
        WHERE datum < '2025-12-31' -- end date (inclusive)
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
        # Note: rowcount is for the last execute
        print(f"[DimDate] Done. INSERT IGNORE affected {cursor.rowcount} rows.")
    except mysql.connector.Error as err:
        print(f"[DimDate][ERROR] Could not populate DimDate: {err}")
        raise


def populate_dim_customer(cursor):
    """
    Read CUSTOMER_MASTER_FILE and populate DimCustomer.
    Expects CSV columns such that Customer_ID is at index 1 and so on.
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
            header = next(reader, None)  # skip header if present

            for row in reader:
                # Defensive parsing: skip short/malformed rows
                if len(row) < 8:
                    print(f"[DimCustomer] Skipping malformed row: {row}")
                    continue

                try:
                    customer_id = int(row[1])
                except ValueError:
                    print(f"[DimCustomer] Invalid customer id '{row[1]}', skipping row.")
                    continue

                gender = row[2]
                age_group = row[3]              # e.g., "0-17"
                occupation = row[4]
                city_category = row[5]
                stay_in_years = row[6]
                try:
                    marital_status = int(row[7])
                except ValueError:
                    # If marital status is invalid, set to NULL-like 0 (or change as needed)
                    marital_status = 0

                data_to_insert.append((
                    customer_id, gender, age_group, occupation,
                    city_category, stay_in_years, marital_status
                ))

        if data_to_insert:
            cursor.executemany(query, data_to_insert)
            print(f"[DimCustomer] Done. INSERT IGNORE affected {cursor.rowcount} rows.")
        else:
            print("[DimCustomer] Warning: No valid rows found in customer CSV.")

    except FileNotFoundError:
        print(f"[DimCustomer][ERROR] File not found: {CUSTOMER_MASTER_FILE}")
    except Exception as e:
        print(f"[DimCustomer][ERROR] Unexpected error: {e}")


def populate_dim_product(cursor):
    """
    Read PRODUCT_MASTER_FILE and populate DimProduct.
    Only Product_Category_1 is used here; columns 2/3 left NULL by design.
    """
    print("[DimProduct] Starting population from product CSV...")


    query = """
    INSERT IGNORE INTO DimProduct (
        Product_ID, Product_Category
    ) VALUES (%s, %s)
    """

    data_to_insert = []

    try:
        with open(PRODUCT_MASTER_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)  # skip header if present

            for row in reader:
                if len(row) < 3:
                    print(f"[DimProduct] Skipping malformed row: {row}")
                    continue

                product_id = row[1]
                product_category_1 = row[2]

                data_to_insert.append((product_id, product_category_1))

        if data_to_insert:
            cursor.executemany(query, data_to_insert)
            print(f"[DimProduct] Done. INSERT IGNORE affected {cursor.rowcount} rows.")
        else:
            print("[DimProduct] Warning: No valid rows found in product CSV.")

    except FileNotFoundError:
        print(f"[DimProduct][ERROR] File not found: {PRODUCT_MASTER_FILE}")
    except Exception as e:
        print(f"[DimProduct][ERROR] Unexpected error: {e}")


def main():
    """
    Connect to MySQL then run the three dimension-population functions.
    Commits at the end and always attempts to close DB resources.
    """
    print("=== DIMENSION POPULATION: BEGIN ===")

    conn = None
    cursor = None

    db_name = "walmart"
    db_user = "root"
    db_pass = "meow"
    db_host = "localhost"

    try:
        conn = mysql.connector.connect(
            database=db_name,
            user=db_user,
            password=db_pass,
            host=db_host
        )
        cursor = conn.cursor()
        print(f"[Main] Connected to database '{db_name}' as user '{db_user}'.")

        # Run population steps
        populate_dim_date(cursor)
        populate_dim_customer(cursor)
        populate_dim_product(cursor)

        # Commit everything in one go
        conn.commit()
        print("[Main] All changes committed.")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("[Main][FATAL] Access denied. Check MySQL credentials.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"[Main][FATAL] Database '{db_name}' does not exist.")
        else:
            print(f"[Main][FATAL] Database error: {err}")
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
