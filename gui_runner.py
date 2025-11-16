# #####################################################################
# ## FILE: gui_runner.py
# ##
# ## A simple Tkinter GUI to orchestrate the entire DWH project.
# #####################################################################

import tkinter as tk
from tkinter import scrolledtext, messagebox, END, BOTH, LEFT, RIGHT, TOP, X, Y, SUNKEN
import threading
import queue
import subprocess
import mysql.connector
from mysql.connector import errorcode

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

        # --- 1. Credentials Frame ---
        cred_frame = tk.Frame(self, bd=2, relief=SUNKEN)
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

        # --- 2. Button Frame ---
        button_frame = tk.Frame(self)
        button_frame.pack(side=TOP, fill=X, padx=5, pady=5)

        self.run_button = tk.Button(
            button_frame, 
            text="RUN FULL PROJECT PIPELINE", 
            command=self.start_pipeline,
            font=("Helvetica", 12, "bold"),
            bg="#4CAF50", fg="white"
        )
        self.run_button.pack(fill=X, expand=True)

        # --- 3. Console Frame ---
        console_frame = tk.Frame(self, bd=2, relief=SUNKEN)
        console_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        self.console = scrolledtext.ScrolledText(
            console_frame, 
            wrap=tk.WORD, 
            bg="#2b2b2b", 
            fg="#cccccc",
            font=("Consolas", 10)
        )
        self.console.pack(fill=BOTH, expand=True)

        self.queue = queue.Queue()
        self.after(100, self.process_queue)

    def log(self, message):
        """Helper to log messages to the console."""
        self.console.insert(END, message + "\n")
        self.console.see(END)

    def start_pipeline(self):
        """Starts the main pipeline in a new thread to avoid freezing the GUI."""
        self.run_button.config(text="... PIPELINE RUNNING ...", state=tk.DISABLED)
        self.log("="*60)
        self.log("=== STARTING FULL PROJECT PIPELINE ===")
        
        # Get credentials from GUI
        self.creds_dict = {key: entry.get() for key, entry in self.credentials.items()}
        
        # Run in a separate thread
        self.pipeline_thread = threading.Thread(
            target=self.run_pipeline_thread, 
            daemon=True
        )
        self.pipeline_thread.start()

    def process_queue(self):
        """Polls the message queue from the worker thread."""
        try:
            while True:
                message = self.queue.get_nowait()
                self.log(message)
        except queue.Empty:
            self.after(100, self.process_queue) # Check again in 100ms

    def queue_log(self, message):
        """Thread-safe way to log from the worker thread."""
        self.queue.put(message)
        
    def run_pipeline_thread(self):
        """THE MAIN WORKER THREAD - Runs all scripts in order."""
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
            self.queue_log("You can now close this window and run Run-Queries.sql in MySQL Workbench.")

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
            
            # Connect to MySQL *server*
            self.queue_log("[SQL] Connecting to server...")
            conn = mysql.connector.connect(
                host=self.creds_dict['host'],
                user=self.creds_dict['user'],
                password=self.creds_dict['password'],
                port=self.creds_dict['port']
            )
            cursor = conn.cursor()
            
            # Execute the script by splitting it into individual statements and running them sequentially.
            # This avoids relying on a 'multi' parameter which may not be supported in the installed connector.
            self.queue_log("[SQL] Executing full DDL script (splitting statements)...")
            # Naively split on semicolons and execute non-empty statements.
            statements = [s.strip() for s in sql_script.split(';') if s.strip()]
            for stmt in statements:
                try:
                    self.queue_log(f"[SQL] Executing statement: {stmt[:60]}...")
                    cursor.execute(stmt)
                    conn.commit()
                except mysql.connector.Error as stmt_err:
                    self.queue_log(f"[SQL Error] Failed to execute statement: {stmt_err}")
                    cursor.close()
                    conn.close()
                    return False

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
        
        # Build the command with arguments
        cmd = [
            'python', 
            script_name,
            '--host', self.creds_dict['host'],
            '--user', self.creds_dict['user'],
            '--password', self.creds_dict['password'],
            '--database', self.creds_dict['database'],
            '--port', self.creds_dict['port']
        ]

        try:
            # Use Popen to capture output in real-time
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                encoding='utf-8',
                bufsize=1 # Line-buffered
            )

            # Read line by line from the subprocess output; guard if stdout is None
            if process.stdout is None:
                # Unable to capture stdout; wait for process to finish and report error if any.
                self.queue_log(f"[Error] Failed to capture stdout for {script_name}")
                return_code = process.wait()
            else:
                for line in iter(process.stdout.readline, ''):
                    # If the process has ended and we read an empty line, break to avoid blocking.
                    if line == '' and process.poll() is not None:
                        break
                    self.queue_log(f"[{script_name}] {line.strip()}")
                
                process.stdout.close()
                return_code = process.wait()

            if return_code != 0:
                self.queue_log(f"[Error] {script_name} exited with code {return_code}")
                return False
            return True
            
        except FileNotFoundError:
            self.queue_log(f"[Error] Script not found: {script_name}")
            return False
        except Exception as e:
            self.queue_log(f"[Error] Subprocess failed: {e}")
            return False

if __name__ == "__main__":
    app = ProjectRunner()
    app.mainloop()