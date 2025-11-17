# #####################################################################
# Main GUI app for running the DWH pipeline.
# #####################################################################

import os
import queue
import threading
import subprocess
import tkinter as tk
import mysql.connector
from tkinter import ttk
from sql_queries import QUERIES
from mysql.connector import errorcode
from tkinter import scrolledtext, messagebox, END, BOTH, LEFT, RIGHT, TOP, X, Y, SUNKEN, N, S, E, W, BOTTOM

SQL_SCRIPT_FILE = 'Create-DW.sql'
POPULATE_SCRIPT = 'populate_dimensions.py'
BUILD_INDEX_SCRIPT = 'build_index.py'
HYBRID_JOIN_SCRIPT = 'hybrid_join.py'


class ProjectRunner(tk.Tk):
    # Main window that handles the whole pipeline and the queries tab
    def __init__(self):
        super().__init__()
        self.title("DWH Project Runner")
        self.geometry("800x600")

        self.notebook = ttk.Notebook(self)
        
        self.tab1 = ttk.Frame(self.notebook)
        self.tab2 = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab1, text='ETL Pipeline Runner')
        self.notebook.add(self.tab2, text='Data Analysis Queries')
        
        self.notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.setup_tab1()
        self.setup_tab2()

        self.log_queue = queue.Queue()
        self.after(100, self.process_log_queue)

    def setup_tab1(self):
        # Tab with credentials, buttons, console output
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
        # Tab where user picks predefined queries and sees results
        query_frame = tk.Frame(self.tab2, bd=2, relief=SUNKEN)
        query_frame.pack(side=TOP, fill=X, padx=5, pady=5)
        
        tk.Label(query_frame, text="Select Query:").pack(side=LEFT, padx=5)
        
        self.query_var = tk.StringVar()
        query_names = list(QUERIES.keys())
        self.query_var.set(query_names[0])
        
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
        
        results_frame = tk.Frame(self.tab2, bd=2, relief=SUNKEN)
        results_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.results_tree = ttk.Treeview(results_frame, show='headings')
        
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_tree.xview)
        
        self.results_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side=RIGHT, fill=Y)
        hsb.pack(side=BOTTOM, fill=X)
        self.results_tree.pack(fill=BOTH, expand=True)

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

    def start_pipeline(self):
        # Runs the whole ETL pipeline in a separate thread
        self.run_button.config(text="... PIPELINE RUNNING ...", state=tk.DISABLED)
        self.log("="*60)
        self.log("Starting the full ETL pipeline")

        self.creds_dict = {key: entry.get() for key, entry in self.credentials.items()}
        
        self.pipeline_thread = threading.Thread(
            target=self.run_pipeline_thread, 
            daemon=True
        )
        self.pipeline_thread.start()

    def run_pipeline_thread(self):
        # Actual pipeline steps executed here
        try:
            self.queue_log("\n--- STEP 1: Create-DW.sql ---")
            if not self._run_sql_script(SQL_SCRIPT_FILE):
                raise Exception("Schema creation failed.")
            self.queue_log("Step 1 done.")

            self.queue_log("\n--- STEP 2: populate_dimensions.py ---")
            if not self._run_python_script(POPULATE_SCRIPT):
                raise Exception("Dimension loading failed.")
            self.queue_log("Step 2 done.")
            
            self.queue_log("\n--- STEP 3: build_index.py ---")
            if not self._run_python_script(BUILD_INDEX_SCRIPT):
                raise Exception("Index creation failed.")
            self.queue_log("Step 3 done.")

            self.queue_log("\n--- STEP 4: hybrid_join.py ---")
            if not self._run_python_script(HYBRID_JOIN_SCRIPT):
                raise Exception("Main ETL failed.")
            self.queue_log("Step 4 done.")
            
            self.queue_log("\n" + "="*60)
            self.queue_log("Pipeline finished successfully. Queries tab is ready.")

        except Exception as e:
            self.queue_log("\n" + "="*60)
            self.queue_log("Pipeline crashed.")
            self.queue_log(str(e))
            messagebox.showerror("Pipeline Failed", f"Error: {e}")
        finally:
            self.run_button.config(text="RUN FULL PROJECT PIPELINE", state=tk.NORMAL)

    def _run_sql_script(self, script_file):
        # Reads the SQL file and executes each statement
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            self.queue_log("Connecting to MySQL...")
            conn = mysql.connector.connect(
                host=self.creds_dict['host'],
                user=self.creds_dict['user'],
                password=self.creds_dict['password'],
                port=int(self.creds_dict['port'])
            )
            cursor = conn.cursor()
            self.queue_log("Running SQL script...")
            statements = [s for s in sql_script.split(';') if s.strip()]
            
            for stmt in statements:
                self.queue_log(f"Executing: {stmt[:60].strip()}")
                cursor.execute(stmt)
                try:
                    _ = cursor.fetchall()
                except mysql.connector.Error as e:
                    if e.errno != errorcode.CR_NO_RESULT_SET:
                        raise
            
            cursor.close()
            conn.close()
            self.queue_log("SQL script done.")
            return True
            
        except mysql.connector.Error as err:
            self.queue_log(f"SQL Error: {err}")
            return False
        except FileNotFoundError:
            self.queue_log(f"SQL file missing: {script_file}")
            return False
        except Exception as e:
            self.queue_log(f"Unexpected SQL error: {e}")
            return False

    def _run_python_script(self, script_name):
        # Runs the helper ETL scripts with credentials passed as args
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

            if process.stdout is None:
                self.queue_log(f"Could not capture output from {script_name}.")
                process.wait()
                return False

            for line in iter(process.stdout.readline, ''):
                self.queue_log(f"{script_name}: {line.strip()}")
            
            process.stdout.close()
            return_code = process.wait()

            if return_code != 0:
                self.queue_log(f"{script_name} exited with code {return_code}")
                return False
            return True
            
        except FileNotFoundError:
            self.queue_log("Python not found. Check PATH.")
            return False
        except Exception as e:
            self.queue_log(f"Subprocess error: {e}")
            return False

    def start_query_thread(self):
        # Kicks off a thread for running the selected query
        self.run_query_button.config(text="...", state=tk.DISABLED)
        self.queue_log("="*60)
        self.queue_log(f"Running query: {self.query_var.get()}")
        
        self.query_thread = threading.Thread(
            target=self.run_query_thread, 
            daemon=True
        )
        self.query_thread.start()

    def run_query_thread(self):
        # Executes a single query from QUERIES.py
        try:
            sql_text = QUERIES[self.query_var.get()]
            creds = {key: entry.get() for key, entry in self.credentials.items()}

            conn = mysql.connector.connect(
                host=creds['host'],
                user=creds['user'],
                password=creds['password'],
                database=creds['database'],
                port=int(creds['port'])
            )
            cursor = conn.cursor()
            
            self.queue_log(f"Executing query...")
            cursor.execute(sql_text)
            
            if cursor.description is None:
                conn.commit()
                self.queue_log("View created successfully.")
                self.after(0, self.update_results_tree, ["Status"], [["View Created Successfully!"]])
            else:
                headers = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                self.queue_log(f"Returned {len(rows)} rows.")
                self.after(0, self.update_results_tree, headers, rows)
                
            cursor.close()
            conn.close()

        except mysql.connector.Error as err:
            self.queue_log("Query error.")
            self.queue_log(str(err))
            messagebox.showerror("Query Failed", f"{err}")
        except Exception as e:
            self.queue_log("Unexpected query error.")
            self.queue_log(str(e))
            messagebox.showerror("Query Failed", f"Unexpected error: {e}")
        finally:
            self.run_query_button.config(text="Run Query", state=tk.NORMAL)

    def update_results_tree(self, headers, rows):
        # Updates the table widget with new data
        try:
            self.results_tree.delete(*self.results_tree.get_children())
            self.results_tree.config(columns=headers)
            
            for header in headers:
                self.results_tree.heading(header, text=header)
                self.results_tree.column(header, width=100, anchor='w')
                
            for row in rows:
                self.results_tree.insert('', 'end', values=row)
        except Exception as e:
            self.queue_log(f"GUI update failed: {e}")


if __name__ == "__main__":
    app = ProjectRunner()
    app.mainloop()
