# #####################################################################
# ## FILE: gui_runner.py (CORRECTED)
# ##
# ## Fixes:
# ## 1. Imported 'BOTTOM', 'Y', 'N', 'S', 'E', 'W' from tkinter.
# ## 2. Replaced 'multi=True' with a robust statement splitter.
# ## 3. Added checks for 'process.stdout' being None.
# ## 4. Added check for 'cursor.description' being None.
# #####################################################################

import tkinter as tk
# --- FIX 1: Import all required tkinter constants ---
from tkinter import scrolledtext, messagebox, END, BOTH, LEFT, RIGHT, TOP, X, Y, SUNKEN, N, S, E, W, BOTTOM
from tkinter import ttk
import threading
import queue
import subprocess
import mysql.connector
from mysql.connector import errorcode

# Import the queries from our separate file
from sql_queries import QUERIES

# --- Define script filenames ---
SQL_SCRIPT_FILE = 'Create-DW.sql'
POPULATE_SCRIPT = 'populate_dimensions.py'
BUILD_INDEX_SCRIPT = 'build_index.py'
HYBRID_JOIN_SCRIPT = 'hybrid_join.py'


class ProjectRunner(tk.Tk):
    """Main application window for the DWH Project Runner."""
    
    def __init__(self):
        super().__init__()
        self.title("DWH Project Runner")
        self.geometry("800x600")

        # --- 1. Create Notebook (Tabs) ---
        self.notebook = ttk.Notebook(self)
        
        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab1, text='ETL Pipeline Runner')
        self.notebook.add(self.tab2, text='Data Analysis Queries')
        
        self.notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # --- 2. Populate Tab 1 (ETL Pipeline) ---
        self.setup_tab1()
        
        # --- 3. Populate Tab 2 (Query Runner) ---
        self.setup_tab2()

        # --- 4. Setup Log Processing Queue ---
        self.log_queue = queue.Queue()
        self.after(100, self.process_log_queue)

    def setup_tab1(self):
        """Creates all widgets for the ETL Pipeline tab."""
        
        # --- Credentials Frame ---
        cred_frame = tk.Frame(self.tab1, bd=2, relief=SUNKEN)
        cred_frame.pack(side=TOP, fill=X, padx=5, pady=5)
        
        self.credentials = {}
        defaults = {
            "host": "localhost",
            "user": "root",
            "password": "meow",
            "database": "walmart",
            "port": "3306"
        }

        for i, (key, val) in enumerate(defaults.items()):
            label = tk.Label(cred_frame, text=f"{key.capitalize()}:")
            label.grid(row=i, column=0, padx=5, pady=2, sticky="e")
            
            entry = tk.Entry(cred_frame, width=30)
            entry.insert(0, val)
            if key == "password":
                entry.config(show="*")
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            self.credentials[key] = entry

        # --- Button Frame ---
        button_frame = tk.Frame(self.tab1)
        button_frame.pack(side=TOP, fill=X, padx=5, pady=5)

        self.run_button = tk.Button(
            button_frame, 
            text="RUN FULL PROJECT PIPELINE", 
            command=self.start_pipeline,
            font=("Helvetica", 12, "bold"),
            bg="#4CAF50", fg="white"
        )
        self.run_button.pack(fill=X, expand=True)

        # --- Console Frame ---
        console_frame = tk.Frame(self.tab1, bd=2, relief=SUNKEN)
        console_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        self.console = scrolledtext.ScrolledText(
            console_frame, 
            wrap=tk.WORD, 
            bg="#2b2b2b", 
            fg="#cccccc",
            font=("Consolas", 10)
        )
        self.console.pack(fill=BOTH, expand=True)

    def setup_tab2(self):
        """Creates all widgets for the Data Analysis tab."""
        
        # --- Query Selection Frame ---
        query_frame = tk.Frame(self.tab2, bd=2, relief=SUNKEN)
        query_frame.pack(side=TOP, fill=X, padx=5, pady=5)
        
        tk.Label(query_frame, text="Select Query:").pack(side=LEFT, padx=5)
        
        self.query_var = tk.StringVar()
        query_names = list(QUERIES.keys())
        self.query_var.set(query_names[0]) # Set default
        
        query_menu = ttk.OptionMenu(query_frame, self.query_var, query_names[0], *query_names)
        query_menu.pack(side=LEFT, fill=X, expand=True, padx=5)
        
        self.run_query_button = tk.Button(
            query_frame, 
            text="Run Query", 
            command=self.start_query_thread,
            font=("Helvetica", 10, "bold"),
            bg="#007BFF", fg="white"
        )
        self.run_query_button.pack(side=RIGHT, padx=5)
        
        # --- Results Frame ---
        results_frame = tk.Frame(self.tab2, bd=2, relief=SUNKEN)
        results_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.results_tree = ttk.Treeview(results_frame, show='headings')
        
        # Add scrollbars
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side=RIGHT, fill=Y)
        hsb.pack(side=BOTTOM, fill=X)
        self.results_tree.pack(fill=BOTH, expand=True)

    # --- LOGGING ---
    def log(self, message):
        self.console.insert(END, message + "\n")
        self.console.see(END)

    def process_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log(message)
        except queue.Empty:
            self.after(100, self.process_log_queue)

    def queue_log(self, message):
        self.log_queue.put(message)

    # --- PIPELINE (TAB 1) LOGIC ---
    def start_pipeline(self):
        self.run_button.config(text="... PIPELINE RUNNING ...", state=tk.DISABLED)
        self.log("="*60)
        self.log("=== STARTING FULL PROJECT PIPELINE ===")
        
        self.creds_dict = {key: entry.get() for key, entry in self.credentials.items()}
        
        self.pipeline_thread = threading.Thread(
            target=self.run_pipeline_thread, 
            daemon=True
        )
        self.pipeline_thread.start()

    def run_pipeline_thread(self):
        """THE MAIN WORKER THREAD - Runs all ETL scripts in order."""
        try:
            # --- STEP 1: Run Create-DW.sql ---
            self.queue_log("\n--- [STEP 1] Running Create-DW.sql ---")
            if not self._run_sql_script(SQL_SCRIPT_FILE):
                raise Exception("Failed to create DWH schema. Halting.")
            self.queue_log("--- [STEP 1] COMPLETED ---")

            # --- STEP 2: Run populate_dimensions.py ---
            self.queue_log("\n--- [STEP 2] Running populate_dimensions.py ---")
            if not self._run_python_script(POPULATE_SCRIPT):
                raise Exception("Failed to populate dimensions. Halting.")
            self.queue_log("--- [STEP 2] COMPLETED ---")
            
            # --- STEP 3: Run build_index.py ---
            self.queue_log("\n--- [STEP 3] Running build_index.py ---")
            if not self._run_python_script(BUILD_INDEX_SCRIPT):
                raise Exception("Failed to build indexes. Halting.")
            self.queue_log("--- [STEP 3] COMPLETED ---")

            # --- STEP 4: Run hybrid_join.py ---
            self.queue_log("\n--- [STEP 4] Running hybrid_join.py (This will take time...) ---")
            if not self._run_python_script(HYBRID_JOIN_SCRIPT):
                raise Exception("Main ETL script (hybrid_join.py) failed.")
            self.queue_log("--- [STEP 4] COMPLETED ---")
            
            self.queue_log("\n" + "="*60)
            self.queue_log("✅ === PIPELINE COMPLETED SUCCESSFULLY! ===")
            self.queue_log("You can now switch to the 'Data Analysis Queries' tab to run queries.")

        except Exception as e:
            self.queue_log("\n" + "="*60)
            self.queue_log(f"❌ === PIPELINE FAILED ===")
            self.queue_log(f"[FATAL] {str(e)}")
            messagebox.showerror("Pipeline Failed", f"An error occurred: {e}")
        finally:
            self.run_button.config(text="RUN FULL PROJECT PIPELINE", state=tk.NORMAL)

    def _run_sql_script(self, script_file):
        """Connects to MySQL and runs a .sql file."""
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            self.queue_log("[SQL] Connecting to server...")
            conn = mysql.connector.connect(
                host=self.creds_dict['host'],
                user=self.creds_dict['user'],
                password=self.creds_dict['password'],
                port=int(self.creds_dict['port']) # Ensure port is int
            )
            cursor = conn.cursor()
            
            # --- FIX 2: Replace 'multi=True' with a robust splitter ---
            # This avoids the "Unread result found" error from SELECT statements
            # in the Create-DW.sql file.
            self.queue_log("[SQL] Executing full DDL script...")
            statements = [s for s in sql_script.split(';') if s.strip()]
            
            for stmt in statements:
                self.queue_log(f"[SQL] ...executing: {stmt[:60].strip()}...")
                cursor.execute(stmt)
                # Consume any potential results (like from SELECT)
                # to prevent "Unread result" errors.
                try:
                    _ = cursor.fetchall()
                except mysql.connector.Error as e:
                    if e.errno != errorcode.CR_NO_RESULT_SET:
                        raise
            # --- END FIX 2 ---
            
            cursor.close()
            conn.close()
            self.queue_log("[SQL] DDL script finished.")
            return True
            
        except mysql.connector.Error as err:
            self.queue_log(f"[SQL Error] {err}")
            return False
        except FileNotFoundError:
            self.queue_log(f"[Error] SQL script not found: {script_file}")
            return False
        except Exception as e:
            self.queue_log(f"[SQL Error] An unexpected error occurred: {e}")
            return False

    def _run_python_script(self, script_name):
        """Runs a Python script as a subprocess and logs its output."""
        cmd = [
            'python', script_name,
            '--host', self.creds_dict['host'],
            '--user', self.creds_dict['user'],
            '--password', self.creds_dict['password'],
            '--database', self.creds_dict['database'],
            '--port', self.creds_dict['port']
        ]
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                text=True, encoding='utf-8', bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # --- FIX 3: Add check for None stdout ---
            if process.stdout is None:
                self.queue_log(f"[Error] Could not capture output from {script_name}.")
                process.wait() # Wait for it to finish
                return False # Assume failure if we can't see output

            for line in iter(process.stdout.readline, ''):
                self.queue_log(f"[{script_name}] {line.strip()}")
            
            process.stdout.close()
            return_code = process.wait()
            # --- END FIX 3 ---

            if return_code != 0:
                self.queue_log(f"[Error] {script_name} exited with code {return_code}")
                return False
            return True
            
        except FileNotFoundError:
            self.queue_log(f"[Error] 'python' command not found. Is Python in your PATH?")
            return False
        except Exception as e:
            self.queue_log(f"[Error] Subprocess failed: {e}")
            return False

    # --- QUERY (TAB 2) LOGIC ---
    def start_query_thread(self):
        """Starts the query runner in a new thread."""
        self.run_query_button.config(text="...", state=tk.DISABLED)
        # Log to the ETL console (Tab 1)
        self.queue_log("="*60)
        self.queue_log(f"--- [QUERY] Running: {self.query_var.get()} ---")
        
        self.query_thread = threading.Thread(
            target=self.run_query_thread, 
            daemon=True
        )
        self.query_thread.start()

    def run_query_thread(self):
        """THE WORKER THREAD - Connects to DB and runs one query."""
        try:
            sql_text = QUERIES[self.query_var.get()]
            creds = {key: entry.get() for key, entry in self.credentials.items()}

            conn = mysql.connector.connect(
                host=creds['host'],
                user=creds['user'],
                password=creds['password'],
                database=creds['database'], # Connect directly to walmart
                port=int(creds['port']) # Ensure port is int
            )
            cursor = conn.cursor()
            
            self.queue_log(f"[QUERY] Executing: {sql_text[:100]}...")
            cursor.execute(sql_text)
            
            # --- FIX 4: Check if cursor.description is None ---
            # This happens for 'CREATE VIEW' statements
            if cursor.description is None:
                conn.commit()
                self.queue_log(f"[QUERY] Success: View was created/replaced.")
                self.after(0, self.update_results_tree, ["Status"], [["View Created Successfully!"]])
            else:
                headers = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                self.queue_log(f"[QUERY] Success: {len(rows)} rows returned.")
                self.after(0, self.update_results_tree, headers, rows)
            # --- END FIX 4 ---
                
            cursor.close()
            conn.close()

        except mysql.connector.Error as err:
            self.queue_log(f"[QUERY ERROR] {err}")
            messagebox.showerror("Query Failed", f"{err}")
        except Exception as e:
            self.queue_log(f"[QUERY ERROR] {e}")
            messagebox.showerror("Query Failed", f"An unexpected error occurred: {e}")
        finally:
            self.run_query_button.config(text="Run Query", state=tk.NORMAL)

    def update_results_tree(self, headers, rows):
        """Safely updates the results table from the main GUI thread."""
        try:
            self.results_tree.delete(*self.results_tree.get_children())
            self.results_tree.config(columns=headers)
            
            for header in headers:
                self.results_tree.heading(header, text=header)
                self.results_tree.column(header, width=100, anchor='w')
                
            for row in rows:
                self.results_tree.insert('', 'end', values=row)
        except Exception as e:
            self.queue_log(f"[GUI ERROR] Failed to update results table: {e}")

# --- NEW: Import 'os' for the subprocess fix ---
import os

if __name__ == "__main__":
    app = ProjectRunner()
    app.mainloop()