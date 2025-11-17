
# Walmart Near-Real-Time Data Warehouse Prototype

This project simulates a near-real-time data warehouse. It pulls in a fast-arriving stream of sales transactions, joins them with large on-disk master files, and loads the final cleaned dataset into MySQL. The highlight is a custom HYBRIDJOIN algorithm designed to handle this kind of stream-to-disk join efficiently (Please check the report for the reference paper from where this algorithm was picked).

A full GUI has now been added so you no longer have to run the project entirely through the terminal. The GUI wraps all steps, manages credentials, and executes the full pipeline with one click. Manual execution is still fully supported.

---

## Project Assumptions

A few rules this project relies on:

* **Price Ambiguity:** The product master file includes store-level pricing. The streamed transactions do not indicate store ID.
* **Resolution Method:** The system resolves this by using a **last-one-wins** approach during indexing. Not financially perfect, but it keeps the ETL consistent for academic use.
* **Credentials:**

  * The GUI and Python scripts ask for MySQL credentials.
  * If you just press Enter, they default to `root` and `meow`.
  * You can either set your MySQL password to `meow` (Step 1) or type your real password into the GUI.

---

## Requirements

Before running anything, make sure you have:

### 1. MySQL Server (8.0 or newer)

Used as the main database.
Workbench recommended for convenience.

Download: [https://dev.mysql.com/downloads/mysql/](https://dev.mysql.com/downloads/mysql/)

### 2. Python 3.10 or newer

Required for the project and type hints in the scripts.
Ensure you check **Add Python to PATH** when installing.

Download: [https://www.python.org/downloads/](https://www.python.org/downloads/)

### 3. Project Files (11 total)

Place all files into one folder, for example:

```
C:\Near_Real_Time_Data_Warehouse
```

Files required:

1. customer_master_data.csv
2. product_master_data.csv
3. transactional_data.csv
4. Create-DW.sql
5. populate_dimensions.py
6. build_index.py
7. hybrid_join.py
8. doubly_linked_list.py
9. Run-Queries.sql
10. sql_queries.py
11. gui_runner.py

---

## Step-by-Step Setup

### Step 1: Set (or confirm) MySQL Password

If you want everything to run smoothly with zero typing, change your root password to `meow`.

In MySQL Workbench:

```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'meow';
```

If you do not want to change your password, just enter your actual password inside the GUI later.

---

## Step 2: Create the Database Schema (DDL)

You can skip this step if you plan to use the GUI, because the GUI executes the Create-DW script automatically.

Manual process:

1. Open `Create-DW.sql` in MySQL Workbench.
2. Copy the entire script.
3. Execute it.
4. Refresh your schema list. You should now see `walmart`.

---

## Step 3: Install Required Python Package

```bash
python -m pip install mysql-connector-python
```

---

## Step 4: Run the ETL Pipeline

You now have **two** ways to run the pipeline.

---

### Option A: GUI Runner (Recommended)

This is the easiest way. Everything is automated:

1. Open Terminal/Command Prompt.
2. Navigate to your project folder:

   ```bash
   cd C:\Near_Real_Time_Data_Warehouse
   ```
3. Run:

   ```bash
   python gui_runner.py
   ```
4. A window will open with multiple tabs:

   * **ETL Pipeline Runner**
   * **Database Setup (DDL)**
   * **Data Analysis Queries**

The GUI lets you enter MySQL credentials. If your password is not `meow`, simply type your real password in the fields.

5. In the ETL tab, click:

   **RUN FULL PROJECT PIPELINE**

This single button automatically performs:

* Running Create-DW.sql
* populate_dimensions.py
* build_index.py
* hybrid_join.py

The order is handled internally. Progress logs appear in the window.

When it says:

```
=== PIPELINE COMPLETED SUCCESSFULLY! ===
```

you’re done.

---

### Option B: Manual Terminal Execution

If you prefer full control:

```bash
cd C:\Near_Real_Time_Data_Warehouse

python populate_dimensions.py
python build_index.py
python hybrid_join.py
```

The final step may take several minutes.

---

## Step 5: Run Analytical Queries

### If using the GUI:

1. Go to the **Data Analysis Queries** tab.

2. Start by running:

   **Q_VIEW: CREATE v_SalesAnalysis**

   This creates the unified fact-dimension view required by other queries.

3. Select any other query from the dropdown (e.g., Top 5 Products) and click **Run Query**.

The results display directly in the table inside the GUI.

### If running manually:

1. Open `Run-Queries.sql` in MySQL Workbench.
2. Execute the `CREATE OR REPLACE VIEW v_SalesAnalysis` block first.
3. Then run any of the other analytical queries.

---

## Troubleshooting

**python is not recognized**
Install Python again and enable Add to PATH.

**ModuleNotFoundError: mysql.connector**
Install the dependency:

```bash
python -m pip install mysql-connector-python
```

**Access denied for user 'root'@'localhost'**
Your password isn’t `meow`.
Fix options:

* run Step 1, or
* type your actual password into the GUI.

**Database 'walmart' does not exist**
The DDL was not executed. Run Create-DW.sql or let the GUI do it.

**Failed to populate DimDate...**
You need MySQL 8.0 or newer.

**File not found… .csv**
Your CSVs and Python files must all be in the same directory.

**Stopped hybrid_join.py mid-run**
Safe to restart. Inserts use `INSERT IGNORE` to avoid duplicates.

