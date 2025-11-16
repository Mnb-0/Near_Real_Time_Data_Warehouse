# #####################################################################
# ## File: populate_dimensions.py (Corrected)
# ##
# ## This script populates the Dimension tables (Date, Customer, Product)
# ## BEFORE the main ETL script is run.
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
    Executes the recursive CTE to populate DimDate.
    Requires MySQL 8.0+.
    """
    print("Populating DimDate...")
    
    # --- FIX ---
    # 1. Set the recursion limit for this session.
    set_limit_query = "SET SESSION cte_max_recursion_depth = 3000;"
    
    # 2. The INSERT query, now without the invalid OPTION clause.
    date_query = """
    INSERT IGNORE INTO DimDate (
        Date_Key, Full_Date, Day_Of_Week_Name, Day_Of_Week_Num,
        Is_Weekend, Month_Name, Month_Num, Quarter, Year
    )
    WITH RECURSIVE DateRange AS (
        SELECT '2019-01-01' AS datum -- Start date
        UNION ALL
        SELECT DATE_ADD(datum, INTERVAL 1 DAY)
        FROM DateRange
        WHERE datum < '2025-12-31' -- End date
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
        # Execute the commands in order
        cursor.execute(set_limit_query)
        cursor.execute(date_query)
        print(f"  Success: DimDate populated with {cursor.rowcount} new days.")
    except mysql.connector.Error as err:
        print(f"  [ERROR] Failed to populate DimDate: {err}")
        raise # Stop the script if this fails

def populate_dim_customer(cursor):
    """
    Reads customer_master_data.csv and populates DimCustomer.
    """
    print("Populating DimCustomer...")
    
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
            header = next(reader) # Skip header
            
            for row in reader:
                # CSV: (, Customer_ID, Gender, Age, Occupation, City_Category, Stay..., Marital...)
                # Idx: (0, 1,           2,      3,   4,          5,             6,       7)
                
                customer_id = int(row[1])
                gender = row[2]
                age_group = row[3] # The 'Age' column (e.g., "0-17") is our 'Age_Group'
                occupation = row[4]
                city_category = row[5]
                stay_in_years = row[6]
                marital_status = int(row[7])
                
                data_to_insert.append((
                    customer_id, gender, age_group, occupation,
                    city_category, stay_in_years, marital_status
                ))

        if data_to_insert:
            cursor.executemany(query, data_to_insert)
            print(f"  Success: DimCustomer populated with {cursor.rowcount} new customers.")
        else:
            print("  Warning: No data found in customer CSV.")
            
    except FileNotFoundError:
        print(f"  [ERROR] File not found: {CUSTOMER_MASTER_FILE}")
    except Exception as e:
        print(f"  [ERROR] Failed to populate DimCustomer: {e}")

def populate_dim_product(cursor):
    """
    Reads product_master_data.csv and populates DimProduct.
    """
    print("Populating DimProduct...")
    
    query = """
    INSERT IGNORE INTO DimProduct (
        Product_ID, Product_Category_1, Product_Category_2, Product_Category_3
    ) VALUES (%s, %s, NULL, NULL)
    """
    
    data_to_insert = []
    
    try:
        with open(PRODUCT_MASTER_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader) # Skip header
            
            for row in reader:
                # CSV: (, Product_ID, Product_Category, price$, ...)
                # Idx: (0, 1,          2,                3)
                
                product_id = row[1]
                product_category_1 = row[2]
                
                data_to_insert.append((product_id, product_category_1))

        if data_to_insert:
            cursor.executemany(query, data_to_insert)
            print(f"  Success: DimProduct populated with {cursor.rowcount} new products.")
        else:
            print("  Warning: No data found in product CSV.")

    except FileNotFoundError:
        print(f"  [ERROR] File not found: {PRODUCT_MASTER_FILE}")
    except Exception as e:
        print(f"  [ERROR] Failed to populate DimProduct: {e}")

def main():
    """
    Main function to connect to MySQL and run all population steps.
    """
    print("--- Starting Dimension Population Script ---")
    
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
        print(f"\nSuccessfully connected to {db_name} as {db_user}.")

        # --- Run Population Steps ---
        populate_dim_date(cursor)
        populate_dim_customer(cursor)
        populate_dim_product(cursor)
        
        # --- Commit changes ---
        conn.commit()
        print("\nAll changes committed to the database.")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("[FATAL] Access denied. Check your MySQL username/password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"[FATAL] Database '{db_name}' does not exist.")
        else:
            print(f"[FATAL] Database error: {err}")
    except Exception as e:
        print(f"[FATAL] An unexpected error occurred: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()