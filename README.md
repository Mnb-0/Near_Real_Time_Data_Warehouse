# Walmart Near-Real-Time Data Warehouse Prototype

This is an academic project that simulates a near-real-time data warehouse.

It uses a multi-threaded Python script to perform an "Extract, Transform, Load" (ETL) process. This script reads a fast-arriving "stream" of sales transactions, joins it with large "master" files on the disk, and loads the final, clean data into a MySQL database.

The core of the project is the implementation of a specific HYBRIDJOIN algorithm, which is designed to handle this "stream-to-disk" join by loading the stream data into a hash table and probing it with partitions from the master files.

---

## Project-Specific Assumptions

This project runs on a few key assumptions you must be aware of:

* **Ambiguous Price Data:** The `product_master_data.csv` file has store information, meaning one product can have multiple prices. The `transactional_data.csv` (the stream) does not say which store a sale happened at.
* **The "As-Is" Solution:** This code (specifically `build_index.py`) proceeds by handling the ambiguity using a **"Last One Wins"** behavior. This means the price used for a sale will be the last price found for that product in the master file. This is not financially accurate, but it allows the ETL to run.
* **Credentials:** The Python scripts (`populate_dimensions.py` and `hybrid_join.py`) and the `gui_runner.py` will ask for your MySQL credentials. They default to `root` and `meow` if you just press Enter, which is why **Step 1** is recommended.

---

## Requirements (What You Need)

Before you begin, you must have this software installed on your machine.

1.  **MySQL Server (Version 8.0 or newer):**
    * This is the database that will store all the data.
    * Installing **MySQL Workbench** is recommended. It makes database management easier.
    * Download Page: `https://dev.mysql.com/downloads/mysql/`

2.  **Python (Version 3.10 or newer):**
    * This is the programming language used to run the project. (3.10 is the minimum for the `|` type hint syntax used in `doubly_linked_list.py`).
    * Download Page: `https://www.python.org/downloads/`
    * **CRITICAL:** During installation, make sure to check the box that says **"Add Python to PATH"**.

3.  **Project Files:**
    * You need all **11 project files** in a single folder (e.g., `C:\DWBI_Project`):
        1.  `customer_master_data.csv`
        2.  `product_master_data.csv`
        3.  `transactional_data.csv`
        4.  `Create-DW.sql`
        5.  `populate_dimensions.py`
        6.  `build_index.py`
        7.  `hybrid_join.py`
        8.  `doubly_linked_list.py`
        9.  `Run-Queries.sql`
        10. **(NEW)** `sql_queries.py`
        11. **(NEW)** `gui_runner.py`

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

*(Note: If you don't want to change your password, you can just type your real password into the GUI in Step 4.)*

### Step 2: Create the Database Tables (DDL)

1.  Find the file `Create-DW.sql` in your project folder.
2.  Open it, **copy the entire contents**, and paste it into your MySQL Workbench SQL editor.
3.  Execute the entire script (click the lightning bolt icon).
4.  When it's done, right-click the "SCHEMAS" panel on the left and click **"Refresh All"**. You should now see the `walmart` database.

*(Note: If you plan to use the GUI in Step 4, it will run this script for you. This step is only required for the manual process.)*

### Step 3: Install the Python Library

1.  Open your computer's **Command Prompt** (on Windows, search for "cmd") or **Terminal**.
2.  Type the following command and press Enter:

<!-- end list -->

```bash
python -m pip install mysql-connector-python
```

### Step 4: Run the Project

You have two options to run the ETL pipeline. The GUI is the easiest and recommended way.

#### Option A (Recommended): The GUI Runner

1.  In your Command Prompt/Terminal, navigate to your project folder:
    ```bash
    cd C:\Near_Real_Time_Data_Warehouse
    ```
2.  Run the GUI script:
    ```bash
    python gui_runner.py
    ```
3.  A window will open. If your password is not "meow", update the credentials in the "ETL Pipeline Runner" tab.
4.  Click the **"RUN FULL PROJECT PIPELINE"** button.
5.  This single click will automatically run Step 2 (Create-DW), `populate_dimensions.py`, `build_index.py`, and `hybrid_join.py` in the correct order. You can watch the progress in the log window.
6.  When you see " === PIPELINE COMPLETED SUCCESSFULLY\! ===", the data is loaded.

#### Option B: Manual Terminal Mode

If you do not want to use the GUI, run the scripts one-by-one in your terminal:

```bash
# Make sure you are in your project folder (cd C:\Near_Real_Time_Data_Warehouse)

# 1. This loads data into DimDate, DimCustomer, DimProduct, etc.
python populate_dimensions.py

# 2. This creates the 'partitions' folder and index files
python build_index.py

# 3. This is the main ETL. It will take several minutes.
python hybrid_join.py
```

-----

## Step 5: Check Your Results & Run Queries

#### If you used the GUI:

1.  Click the **"Data Analysis Queries"** tab.
2.  **First**, select the query `Q_VIEW: CREATE v_SalesAnalysis` and click **"Run Query"**. This is required before any other queries will work.
3.  **Then**, select any other query (e.g., `Q1/Q11: Top 5 Products`) and click **"Run Query"** to see the results in the table.

#### If you used the Manual Mode:

1.  Go back to **MySQL Workbench**.
2.  Open the `Run-Queries.sql` file.
3.  **First**, execute the `CREATE OR REPLACE VIEW v_SalesAnalysis ...` command.
4.  **Then**, you can execute any of the 20 analytical queries to see your results.

-----

## Troubleshooting

  * **Error:** `python is not recognized as an internal or external command`
      * **Fix:** Re-install Python with "Add to PATH" enabled.
  * **Error:** `No module named 'mysql.connector'`
      * **Fix:** Run `python -m pip install mysql-connector-python`.
  * **Error:** `Access denied for user 'root'@'localhost'`
      * **Fix:** Your MySQL password is not `meow`. Either run Step 1 or, in the GUI, just type your correct password into the "Password" box.
  * **Error:** `[FATAL] Database 'walmart' does not exist.`
      * **Fix:** **Step 2** was not executed correctly. Run the `Create-DW.sql` script or just use the GUI, which does it for you.
  * **Error:** `[ERROR] Failed to populate DimDate...`
      * **Fix:** You must be using **MySQL 8.0 or newer**.
  * **Error:** `[FATAL] File not found: ... .csv`
      * **Fix:** Your `.csv` and `.py` files are not all in the same folder.
  * **If you stop `hybrid_join.py`:** Restarting is safe. The script uses `INSERT IGNORE` and will skip duplicates.
