import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading

class UpdateManagerApp(tk.Tk):
    """
    GUI for listing available updates for installed applications via winget.
    User can select which apps to update, or update all with one click.
    """
    def __init__(self):
        super().__init__()
        self.title("WinGUILite - Update Manager")
        self.geometry("600x500")
        self.resizable(False, False)
        self.configure(bg="#f5f6fa")

        self.updates = {}  # {name: id}
        self.vars = {}     # {name: BooleanVar}

        self.create_widgets()
        threading.Thread(target=self.fetch_updates, daemon=True).start()

    def create_widgets(self):
        header = tk.Frame(self, bg="#4078c0", height=48)
        header.pack(fill='x')
        tk.Label(
            header,
            text="Update Manager - Select applications to update",
            font=("Segoe UI", 16, "bold"),
            bg="#4078c0",
            fg="white"
        ).pack(side='left', padx=18, pady=8)

        self.status_label = ttk.Label(self, text="Searching for available updates...", font=("Segoe UI", 11))
        self.status_label.pack(pady=(18, 10))

        self.list_frame = tk.Frame(self, bg="#f5f6fa")
        self.list_frame.pack(expand=True, fill="both", padx=18, pady=10)

        self.checkbuttons = []

        btns_frame = tk.Frame(self, bg="#f5f6fa")
        btns_frame.pack(pady=12)
        self.update_btn = ttk.Button(btns_frame, text="Update Selected", command=self.update_selected)
        self.update_btn.pack(side='left', padx=8)
        self.update_all_btn = ttk.Button(btns_frame, text="Update All", command=self.update_all)
        self.update_all_btn.pack(side='left', padx=8)

    def fetch_updates(self):
        # Get list of updatable packages using winget
        self.status_label.config(text="Searching for available updates...")
        try:
            result = subprocess.run(
                ["winget", "upgrade"],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            lines = result.stdout.splitlines()
            # Find header line
            start = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("Name"):
                    start = i + 1
                    break
            # Parse update lines
            for line in lines[start:]:
                cols = [c for c in line.strip().split("  ") if c]
                if len(cols) >= 3:
                    name = cols[0].strip()
                    pkg_id = cols[1].strip()
                    self.updates[name] = pkg_id
            self.show_updates()
        except Exception as e:
            self.status_label.config(text=f"Error fetching updates: {e}")

    def show_updates(self):
        # Display checkboxes for each updatable package
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.vars.clear()
        self.checkbuttons.clear()
        if not self.updates:
            self.status_label.config(text="No updates available.")
            return
        self.status_label.config(text=f"Found {len(self.updates)} updates available.")
        for name, pkg_id in self.updates.items():
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(self.list_frame, text=f"{name} ({pkg_id})", variable=var)
            cb.pack(anchor="w", padx=8, pady=4)
            self.vars[name] = var
            self.checkbuttons.append(cb)

    def update_selected(self):
        # Update only checked packages
        selected = [self.updates[name] for name, var in self.vars.items() if var.get()]
        if not selected:
            messagebox.showinfo("Update", "No applications selected for update.")
            return
        self.status_label.config(text="Updating selected applications...")
        threading.Thread(target=self.run_updates, args=(selected,), daemon=True).start()

    def update_all(self):
        # Update all updatable packages
        all_ids = list(self.updates.values())
        if not all_ids:
            messagebox.showinfo("Update", "No applications available for update.")
            return
        self.status_label.config(text="Updating all applications...")
        threading.Thread(target=self.run_updates, args=(all_ids,), daemon=True).start()

    def run_updates(self, pkg_ids):
        # Run winget upgrade for each package id
        for pkg_id in pkg_ids:
            self.status_label.config(text=f"Updating {pkg_id}...")
            subprocess.run(
                f'winget upgrade --id {pkg_id} --accept-source-agreements --accept-package-agreements --silent',
                shell=True
            )
        self.status_label.config(text="Update process completed!")
        messagebox.showinfo("Update", "Selected applications have been updated.")

if __name__ == "__main__":
    app = UpdateManagerApp()
    app.mainloop()
