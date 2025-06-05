import os
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ast
import re

DB_NAME = 'mobdrops.db'
MOBDROP_CONFIG = 'mobdropconfig.txt'
ITEM_IDS_FILE = 'item_ids.txt'
EXPORT_FILE = 'mobdropconfig_update.txt'

# Create DB if not exists
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS mobdrops (
            MOB TEXT NOT NULL,
            ITEM TEXT,
            COUNT INT NOT NULL,
            DROP_RATE FLOAT NOT NULL
        )''')
        conn.commit()

# Parse mobdropconfig.txt and insert to DB
def import_from_config():
    if not os.path.exists(MOBDROP_CONFIG):
        open(MOBDROP_CONFIG, 'w').close()
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        with open(MOBDROP_CONFIG, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return

            try:
                data = ast.literal_eval('{' + content + '}')
            except Exception as e:
                print(f"Error parsing config: {e}")
                return

            for mob, entries in data.items():
                c.execute("DELETE FROM mobdrops WHERE MOB = ?", (mob,))

                if not entries:
                    c.execute("INSERT INTO mobdrops (MOB, ITEM, COUNT, DROP_RATE) VALUES (?, NULL, 0, 0.0)", (mob,))
                    continue

                pattern = r'{id:"(.*?)",Count:(\d+)b,tag:{dropchance:(\d*\.?\d+)d}}'
                matches = re.findall(pattern, entries)
                for item_id, count, drop_rate in matches:
                    c.execute("INSERT INTO mobdrops (MOB, ITEM, COUNT, DROP_RATE) VALUES (?, ?, ?, ?)",
                              (mob, item_id, int(count), float(drop_rate)))
        conn.commit()

# Read item_ids.txt for suggestions
def load_item_ids():
    if not os.path.exists(ITEM_IDS_FILE):
        return []
    with open(ITEM_IDS_FILE, 'r') as f:
        return [line.strip().strip("'") for line in f if line.strip()]

class MobDropEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Mob Drop Editor")
        self.conn = sqlite3.connect(DB_NAME)
        self.item_ids = load_item_ids()
        self.selected_mob = None

        self.setup_ui()
        self.load_mobs()

    def setup_ui(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True)

        # Column 1: Search + Browse
        left_frame = tk.Frame(self.main_frame)
        left_frame.grid(row=0, column=0, sticky='ns', padx=10, pady=10)

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(left_frame, textvariable=self.search_var)
        search_entry.pack(fill='x')
        search_entry.bind('<KeyRelease>', self.filter_mobs)

        self.mob_listbox = tk.Listbox(left_frame)
        self.mob_listbox.pack(fill='both', expand=True)
        self.mob_listbox.bind('<<ListboxSelect>>', self.on_mob_select)

        # Column 2: Entries + Export + Add
        right_frame = tk.Frame(self.main_frame)
        right_frame.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)

        self.entry_frame = tk.Frame(right_frame)
        self.entry_frame.pack(fill='both', expand=True)

        button_frame = tk.Frame(right_frame)
        button_frame.pack(fill='x')

        export_button = tk.Button(button_frame, text="Export", command=self.export_config)
        export_button.pack(side='left', padx=5)

        add_button = tk.Button(button_frame, text="Add Entry", command=self.add_entry)
        add_button.pack(side='left', padx=5)

        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        self.status_var = tk.StringVar()
        self.status_label = tk.Label(self.root, textvariable=self.status_var, anchor='w', relief='sunken', bd=1)
        self.status_label.pack(fill='x', side='bottom')

    def show_status(self, message, error=False):
        self.status_var.set(message)
        self.status_label.config(fg='red' if error else 'green')
        self.root.after(4000, lambda: self.status_var.set(''))

    def load_mobs(self):
        self.mob_listbox.delete(0, tk.END)
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT MOB FROM mobdrops")
        self.mobs = [row[0] for row in cursor.fetchall()]
        for mob in self.mobs:
            self.mob_listbox.insert(tk.END, mob)

    def filter_mobs(self, event):
        query = self.search_var.get().lower()
        self.mob_listbox.delete(0, tk.END)
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT MOB FROM mobdrops WHERE LOWER(MOB) LIKE ? OR MOB IN (SELECT MOB FROM mobdrops WHERE LOWER(ITEM) LIKE ?)", (f"%{query}%", f"%{query}%"))
        filtered = [row[0] for row in cursor.fetchall()]
        for mob in filtered:
            self.mob_listbox.insert(tk.END, mob)

    def on_mob_select(self, event):
        selection = self.mob_listbox.curselection()
        if not selection:
            return
        mob = self.mob_listbox.get(selection[0])
        self.selected_mob = mob
        self.display_entries(mob)

    def display_entries(self, mob):
        for widget in self.entry_frame.winfo_children():
            widget.destroy()

        cursor = self.conn.cursor()
        cursor.execute("SELECT rowid, ITEM, COUNT, DROP_RATE FROM mobdrops WHERE MOB = ?", (mob,))
        entries = cursor.fetchall()

        for i, (rowid, item, count, drop_rate) in enumerate(entries):
            row_frame = tk.Frame(self.entry_frame)
            row_frame.pack(fill='x', pady=2)

            item_var = tk.StringVar(value=item)
            count_var = tk.IntVar(value=count)
            rate_var = tk.DoubleVar(value=drop_rate)

            combobox = ttk.Combobox(row_frame, textvariable=item_var)
            combobox['values'] = self.item_ids
            if item:
                combobox.set(item)
            combobox.pack(side='left', fill='x', expand=True)

            count_entry = tk.Entry(row_frame, textvariable=count_var, width=5)
            count_entry.pack(side='left')
            rate_entry = tk.Entry(row_frame, textvariable=rate_var, width=7)
            rate_entry.pack(side='left')

            def make_edit_cmd(rid, iv, cv, rv):
                return lambda: self.save_edit(mob, rid, iv, cv, rv)

            save_button = tk.Button(row_frame, text="✔", command=make_edit_cmd(rowid, item_var, count_var, rate_var))
            save_button.pack(side='left')
            cancel_button = tk.Button(row_frame, text="✖", command=self.load_mobs)
            cancel_button.pack(side='left')
            delete_button = tk.Button(row_frame, text="DEL", command=lambda r=rowid: self.delete_entry(mob, r))
            delete_button.pack(side='left')

            # Bind Enter key for saving
            for widget in (combobox, count_entry, rate_entry):
                widget.bind('<Return>', lambda e: save_button.invoke())

        self.mob_listbox.selection_clear(0, tk.END)
        try:
            idx = self.mobs.index(mob)
            self.mob_listbox.selection_set(idx)
            self.mob_listbox.see(idx)
        except ValueError:
            pass

    def add_entry(self):
        if not self.selected_mob:
            self.show_status("Please select a mob first.", error=True)
            messagebox.showwarning("No Mob Selected", "Please select a mob ID from the left panel first.")
            return

        add_window = tk.Toplevel(self.root)
        add_window.title("Add Entry")

        item_var = tk.StringVar()
        count_var = tk.IntVar(value=1)
        rate_var = tk.DoubleVar(value=0.1)

        tk.Label(add_window, text="Item ID:").pack()
        combobox = ttk.Combobox(add_window, textvariable=item_var)
        combobox['values'] = self.item_ids
        combobox.pack(fill='x')

        tk.Label(add_window, text="Count:").pack()
        count_entry = tk.Entry(add_window, textvariable=count_var)
        count_entry.pack(fill='x')

        tk.Label(add_window, text="Drop Rate (0.0 - 1.0):").pack()
        rate_entry = tk.Entry(add_window, textvariable=rate_var)
        rate_entry.pack(fill='x')

        def save():
            item = item_var.get()
            try:
                count = int(count_var.get())
                rate = float(rate_var.get())
            except Exception:
                self.show_status("Invalid number input.", error=True)
                messagebox.showerror("Invalid Input", "Count must be integer, rate must be float.")
                return
            if not item or count < 1 or not (0.0 <= rate <= 1.0):
                self.show_status("Invalid input when adding entry.", error=True)
                messagebox.showerror("Invalid Input", "Make sure all fields are valid.")
                return
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO mobdrops (MOB, ITEM, COUNT, DROP_RATE) VALUES (?, ?, ?, ?)",
                           (self.selected_mob, item, count, rate))
            self.conn.commit()
            add_window.destroy()
            self.display_entries(self.selected_mob)
            self.show_status(f"Added entry for {self.selected_mob}")

        add_button = tk.Button(add_window, text="Add", command=save)
        add_button.pack(pady=5)

        for widget in (combobox, count_entry, rate_entry):
            widget.bind('<Return>', lambda e: add_button.invoke())

    def save_edit(self, mob, rowid, item_var, count_var, rate_var):
        item = item_var.get()
        count = count_var.get()
        rate = rate_var.get()
        if not 0.0 <= rate <= 1.0:
            self.show_status("Invalid drop rate when saving.", error=True)
            messagebox.showerror("Invalid", "Drop rate must be between 0.0 and 1.0")
            return

        cursor = self.conn.cursor()
        cursor.execute("UPDATE mobdrops SET ITEM = ?, COUNT = ?, DROP_RATE = ? WHERE rowid = ?",
                       (item, count, rate, rowid))
        self.conn.commit()
        self.display_entries(mob)
        self.show_status(f"Updated entry for {mob}")

    def delete_entry(self, mob, rowid):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM mobdrops WHERE rowid = ?", (rowid,))
        self.conn.commit()
        self.display_entries(mob)
        self.show_status(f"Deleted entry from {mob}")

    def export_config(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT MOB FROM mobdrops")
        mobs = [row[0] for row in cursor.fetchall()]

        try:
            with open(EXPORT_FILE, 'w') as f:
                for mob in mobs:
                    cursor.execute("SELECT ITEM, COUNT, DROP_RATE FROM mobdrops WHERE MOB = ? AND ITEM IS NOT NULL", (mob,))
                    entries = cursor.fetchall()
                    if not entries:
                        f.write(f"'{mob}':'',\n")
                        continue
                    parts = []
                    for item, count, rate in entries:
                        parts.append(f"{{id:\"{item}\",Count:{count}b,tag:{{dropchance:{rate}d}}}}")
                    line = f"'{mob}':'{','.join(parts)}',\n"
                    f.write(line)
            self.show_status("Exported successfully.")
        except Exception as e:
            self.show_status(f"Export failed: {e}", error=True)

if __name__ == '__main__':
    init_db()
    import_from_config()

    root = tk.Tk()
    app = MobDropEditor(root)
    root.mainloop()
