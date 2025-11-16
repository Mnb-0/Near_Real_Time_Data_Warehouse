# Walmart Near-Real-Time Data Warehouse Prototype

This is an academic project that simulates a near-real-time data warehouse.

It uses a multi-threaded Python script to perform an "Extract, Transform, Load" (ETL) process. This script reads a fast-arriving "stream" of sales transactions, joins it with large "master" files on the disk, and loads the final, clean data into a MySQL database.

The core of the project is the implementation of a specific HYBRIDJOIN algorithm, which is designed to handle this "stream-to-disk" join by loading the stream data into a hash table and probing it with partitions from the master files.

---

## Project-Specific Assumptions

This project runs on a few key assumptions you must be aware of:

* **Ambiguous Price Data:** The `product_master_data.csv` file has store information, meaning one product can have multiple prices. The `transactional_data.csv` (the stream) does not say which store a sale happened at.
* **The "As-Is" Solution:** This code (specifically `build_index.py`) proceeds by handling the ambiguity using a **"Last One Wins"** behavior. This means the price used for a sale will be the last price found for that product in the master file. This is not financially accurate, but it allows the ETL to run.
* **Credentials:** The Python scripts (`populate_dimensions.py` and `hybrid_join.py`) will ask for your MySQL credentials. They default to `root` and `meow` if you just press Enter, which is why **Step 1** is recommended.

---

## Requirements (What You Need)

Before you begin, you must have this software installed on your machine.

1.  **MySQL Server (Version 8.0 or newer):**
    * This is the database that will store all the data.
    * Installing **MySQL Workbench** is recommended. It makes database management easier.
    * Download Page: `https://dev.mysql.com/downloads/mysql/`

2.  **Python (Version 3.10 or newer):**
    * This is the programming language used to run the project. (Version 3.14 is not an official release; 3.10 is the minimum for the `|` type hint syntax used in `doubly_linked_list.py`).
    * Download Page: `https://www.python.org/downloads/`
    * **CRITICAL:** During installation, make sure to check the box that says **"Add Python to PATH"**.

3.  **Project Files:**
    * You need all 9 project files in a single folder (e.g., `C:\DWBI_Project`):
        1.  `customer_master_data.csv`
        2.  `product_master_data.csv`
        3.  `transactional_data.csv`
        4.  `Create-DW.sql`
        5.  `populate_dimensions.py`
        6.  `build_index.py`
        7.  `hybrid_join.py`
        8.  `doubly_linked_list.py`
        9.  `Run-Queries.sql`

---

## Step-by-Step Execution

Follow these steps in order. Do not skip any.

### Step 1: Set Your MySQL Password

This step ensures your MySQL password matches the script's default (`meow`) for easy execution.

1.  Open **MySQL Workbench** and connect to your local database.
2.  Open a new SQL editor.
3.  Copy and paste the command below.
4.  Execute it by clicking the lightning bolt (⚡) icon. This sets your `root` user's password to `meow`.

```sql
-- Sets the password for your 'root' user to 'meow'
ALTER USER 'root'@'localhost' IDENTIFIED BY 'meow';
```

*(Note: If you don't want to change your password, you can just type your real password when the scripts ask for it in Step 4.)*

### Step 2: Create the Database Tables (DDL)

1.  Find the file `Create-DW.sql` in your project folder.
2.  Open it, **copy the entire contents**, and paste it into your MySQL Workbench SQL editor.
3.  Execute the entire script (click the lightning bolt icon).
4.  When it's done, right-click the "SCHEMAS" panel on the left and click **"Refresh All"**. You should now see the `walmart` database.

### Step 3: Install the Python Library

1.  Open your computer's **Command Prompt** (on Windows, search for "cmd") or **Terminal**.
2.  Type the following command and press Enter:

<!-- end list -->

```bash
pip install mysql-connector-python
```

### Step 4: Run the Python Scripts

1.  In your Command Prompt/Terminal, navigate to your project folder.
    (This path now matches the example in "Requirements")

    ```bash
    cd C:\DWBI_Project
    ```

2.  Run the scripts in this **specific order**. When prompted for credentials, you can just press **Enter** at each step (Host, User, Password, DB Name) to accept the defaults we set up (`localhost`, `root`, `meow`, `walmart`).

    ```bash
    # 1. This loads data into DimDate, DimCustomer, DimProduct, etc.
    python populate_dimensions.py

    # 2. This creates the 'partitions' folder and index files
    python build_index.py

    # 3. This is the main ETL. It will take several minutes.
    python hybrid_join.py
    ```

-----

## What to Expect (During Script 3)

You will see logs like:

```
[Joiner] Loading R partition: partitions/product/part_1.csv
[Joiner] Joined 10 tuples.
[DB] Inserting 100 rows...
```

This is normal and means it's working.

-----

## Step 5: Check Your Results

Go back to **MySQL Workbench**. In a new SQL tab, run these queries:

```sql
-- See the first 20 rows of data you loaded
SELECT * FROM FactSales LIMIT 20;
```

```sql
-- See how many total rows were loaded
SELECT COUNT(*) FROM FactSales;
```

-----

## Troubleshooting

  * **Error:** `python is not recognized as an internal or external command`
      * **Fix:** Re-install Python with "Add to PATH" enabled.
  * **Error:** `No module named 'mysql.connector'`
      * **Fix:** Run `pip install mysql-connector-python`.
  * **Error:** `Access denied for user 'root'@'localhost'`
      * **Fix:** You didn't run **Step 1** correctly, OR you typed a password instead of just pressing Enter. Either run Step 1 or re-run the script and enter your correct password.
  * **Error:** `[FATAL] Database 'walmart' does not exist.`
      * **Fix:** **Step 2** was not executed correctly. Run the `Create-DW.sql` script again.
  * **Error:** `[ERROR] Failed to populate DimDate...`
      * **Fix:** You must be using **MySQL 8.0 or newer**.
  * **Error:** `[FATAL] File not found: ... .csv`
      * **Fix:** Your CSV files are not in the same folder as your `.py` scripts.
  * **If you stop `hybrid_join.py`:** Restarting is safe. The script uses `INSERT IGNORE` and will skip duplicates.
