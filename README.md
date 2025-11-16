# Walmart Near-Real-Time Data Warehouse Prototype

This is an academic project that simulates a near-real-time data warehouse.

It uses a multi-threaded Python script to perform an "Extract, Transform, Load" (ETL) process. This script reads a fast-arriving "stream" of sales transactions, joins it with large "master" files on the disk, and loads the final, clean data into a MySQL database.

The core of the project is the implementation of a specific HYBRIDJOIN algorithm, which is designed to handle this "stream-to-disk" join by loading the stream data into a hash table and probing it with partitions from the master files.

---

## Project-Specific Assumptions

This project runs on a few key assumptions you must be aware of:

* Ambiguous Price Data: The `product_master_data.csv` file has store information, meaning one product can have multiple prices. The `transactional_data.csv` (the stream) does not say which store a sale happened at.
* The "As-Is" Solution: This code proceeds without changing the data files. It handles the ambiguity using a "Last One Wins" behavior. This means the price used for a sale will be the last price found for that product in the master file. This is not financially accurate, but it allows the ETL to run and populate the database.
* Hardcoded Credentials: All Python scripts are hardcoded to connect to a MySQL database named `walmart` with the username `root` and password `meow`. If your database password is different, you must edit the `.py` files.

---

## Requirements (What You Need)

Before you begin, you must have this software installed on your machine.

1. **MySQL Server (Version 8.0 or newer):**
   * This is the database that will store all the data.
   * Installing MySQL Workbench is recommended. It makes database management easier.
   * Download Page: `https://dev.mysql.com/downloads/mysql/`

2. **Python (Version 3.8 or newer):**
   * This is the programming language used to run the project.
   * Download Page: `https://www.python.org/downloads/`
   * During installation, make sure to check the box that says "Add Python to PATH".

3. **Project Files:**
   * You need all 7 project files (`.py` and `.csv`) in a single folder (for example: `C:\Walmart_Project`).

---

## Step-by-Step Execution

Follow these steps in order. Do not skip any.

### Step 1: Set Up the Database User & Schema

1. Open MySQL Workbench.
2. Connect to your local database.
3. Open a new SQL editor.
4. Copy and paste the two commands below.
5. Execute them.

```sql
-- 1. Creates the user and sets the password to "meow"
CREATE USER 'root'@'localhost' IDENTIFIED BY 'meow';
````

(This command may fail if the user already exists.)

```sql
-- 2. Sets the password for your 'root' user to 'meow'
ALTER USER 'root'@'localhost' IDENTIFIED BY 'meow';
```

### Step 2: Create the Database Tables (DDL)

Copy and execute all of this:

```sql
CREATE DATABASE IF NOT EXISTS walmart;
USE walmart;

SET FOREIGN_KEY_CHECKS=0;

-- Dimension: DimDate
DROP TABLE IF EXISTS DimDate;
CREATE TABLE DimDate (
    Date_Key          INT PRIMARY KEY,
    Full_Date         DATE NOT NULL,
    Day_Of_Week_Name  VARCHAR(10) NOT NULL,
    Day_Of_Week_Num   INT NOT NULL,
    Is_Weekend        TINYINT(1) NOT NULL,
    Month_Name        VARCHAR(10) NOT NULL,
    Month_Num         INT NOT NULL,
    Quarter           INT NOT NULL,
    Year              INT NOT NULL,
    INDEX idx_dimdate_full_date (Full_Date)
) ENGINE=InnoDB;

-- Dimension: DimCustomer
DROP TABLE IF EXISTS DimCustomer;
CREATE TABLE DimCustomer (
    Customer_ID                 INT PRIMARY KEY,
    Age_Group                   VARCHAR(10) NOT NULL,
    Gender                      CHAR(1) NOT NULL,
    Occupation                  VARCHAR(50) NOT NULL,
    City_Category               CHAR(1) NOT NULL,
    Stay_In_Current_City_Years  VARCHAR(5) NOT NULL,
    Marital_Status              INT NOT NULL,
    INDEX idx_dimcustomer_city_cat (City_Category),
    INDEX idx_dimcustomer_occupation (Occupation)
) ENGINE=InnoDB;

-- Dimension: DimProduct
DROP TABLE IF EXISTS DimProduct;
CREATE TABLE DimProduct (
    Product_ID          VARCHAR(20) PRIMARY KEY,
    Product_Category_1  VARCHAR(50) NOT NULL,
    Product_Category_2  VARCHAR(50),
    Product_Category_3  VARCHAR(50),
    INDEX idx_dimproduct_cat1 (Product_Category_1)
) ENGINE=InnoDB;

-- Fact Table: FactSales
DROP TABLE IF EXISTS FactSales;
CREATE TABLE FactSales (
    Transaction_ID      VARCHAR(50) NOT NULL,
    Customer_ID         INT NOT NULL,
    Product_ID          VARCHAR(20) NOT NULL,
    Date_Key            INT NOT NULL,
    Purchase_Amount     DECIMAL(12, 2) NOT NULL,
    PRIMARY KEY (Transaction_ID, Product_ID),
    CONSTRAINT fk_customer
        FOREIGN KEY(Customer_ID)
        REFERENCES DimCustomer(Customer_ID),
    CONSTRAINT fk_product
        FOREIGN KEY(Product_ID)
        REFERENCES DimProduct(Product_ID),
    CONSTRAINT fk_date
        FOREIGN KEY(Date_Key)
        REFERENCES DimDate(Date_Key),
    INDEX idx_factsales_date_key (Date_Key),
    INDEX idx_factsales_cust_prod (Customer_ID, Product_ID)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS=1;
```

### Step 3: Install the Python Library

Run:

```bash
pip install mysql-connector-python
```

### Step 4: Run the Python Scripts

Navigate to the project folder:

```bash
cd C:\Walmart_Project
```

Then run the scripts:

```bash
python populate_dimensions.py
python build_index.py
python hybrid_join_etl.py
```

---

## What to Expect (During Script 3)

You will see logs like:

```
[Joiner] Loading R partition: partitions/product/part_1.csv
[Joiner] Joined 10 tuples.
[Loader] Flushing 100 records to DWH...
```

This is normal.

---

## Step 5: Check Your Results

```sql
SELECT * FROM FactSales LIMIT 20;
```

This should return sample rows.

---

## Troubleshooting

* **Error:** `python is not recognized as an internal or external command`

  * Fix: Re-install Python with "Add to PATH" enabled.

* **Error:** `No module named 'mysql.connector'`

  * Fix: Run `pip install mysql-connector-python`.

* **Error:** `Access denied for user 'root'@'localhost'`

  * Fix: Either change your MySQL password to `meow` or edit the Python scripts to use your actual password.

* **Error:** `[FATAL] Database 'walmart' does not exist.`

  * Fix: Step 2 was not executed correctly.

* **Error:** `[ERROR] Failed to populate DimDate...`

  * Fix: Requires MySQL 8.0 or newer.

* **Error:** `[FATAL] File not found: ... .csv`

  * Fix: CSV files are not in the correct directory.

* If you stop the ETL script, restarting is safe because `INSERT IGNORE` skips duplicates.
