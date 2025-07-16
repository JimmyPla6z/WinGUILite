import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font
import subprocess
import threading
import re
import os
import sys
import json

# --- Multiple Installer Utility (from Multiple_installer.py) ---
def clear_spaces(name):
    return name.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")

class InstallerApp(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("🎈 Multi installer utility (Tkinter) 🎈")
        self.geometry("700x500")
        self.resizable(False, False)
        self.configure(bg="#f5f6fa")

        self.title_font = font.Font(family='Segoe UI', size=16, weight='bold')
        self.label_font = font.Font(family='Segoe UI', size=11)
        self.button_font = font.Font(family='Segoe UI', size=10, weight='bold')

        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TNotebook", background="#f5f6fa", borderwidth=0)
        style.configure("TNotebook.Tab", font=self.label_font, padding=[16, 8], background="#eaf0fb", foreground="#274472")
        style.map("TNotebook.Tab", background=[("selected", "#d6e0f0")])
        style.configure("TFrame", background="#f5f6fa")
        style.configure("TLabel", background="#f5f6fa", font=self.label_font)
        style.configure("TButton", font=self.button_font, padding=6, background="#4078c0", foreground="#fff")
        style.map("TButton", background=[('active', '#274472')])
        style.configure("TCheckbutton", background="#f5f6fa", font=self.label_font)
        style.configure("TMenubutton", background="#eaf0fb", font=self.label_font)

        self.categories = {
            "media": {"label": "Media & Video", "data": {}, "vars": {}},
            "browsers": {"label": "Web Browsers", "data": {}, "vars": {}},
            "utilities": {"label": "System Utilities", "data": {}, "vars": {}},
            "documentation": {"label": "Office + PDF", "data": {}, "vars": {}},
            "developing": {"label": "Development Tools", "data": {}, "vars": {}},
        }
        self.load_packages()
        self.create_widgets()

    def load_packages(self):
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        for cat, info in self.categories.items():
            json_filename = f"{cat if cat != 'document' else 'documentation'}.json"
            json_path = os.path.join(base_path, "packages", json_filename)
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    info["data"] = json.load(f)
            except FileNotFoundError:
                messagebox.showerror("Error", f"File {json_filename} not found in 'packages' folder.")
                self.destroy()

    def create_widgets(self):
        header = tk.Frame(self, bg="#4078c0", height=48)
        header.pack(fill='x')
        header_lbl = tk.Label(
            header,
            text="Multi installer utility - Select and install multiple applications",
            font=self.title_font,
            bg='#4078c0',
            fg='white'
        )
        header_lbl.pack(side='left', padx=18, pady=8)

        self.selected_label = ttk.Label(self, text="🛒 You have selected 0 for installation.", font=self.label_font)
        self.selected_label.pack(pady=(18, 10))

        menubar = tk.Menu(self)
        basket_menu = tk.Menu(menubar, tearoff=0)
        basket_menu.add_command(label="Show Selected", command=self.show_basket_window)
        basket_menu.add_command(label="Install Selected", command=self.start_install_thread)
        menubar.add_cascade(label="🛒 Basket", menu=basket_menu)
        self.config(menu=menubar)

        self.notebook = ttk.Notebook(self)
        self.frames = {}
        for cat, info in self.categories.items():
            frame = ttk.Frame(self.notebook)
            self.frames[cat] = frame
            self.notebook.add(frame, text=info["label"])
            for name in info["data"]:
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(frame, text=name, variable=var, command=self.update_selected, style="TCheckbutton")
                cb.pack(anchor="w", padx=18, pady=4)
                info["vars"][name] = var
        self.notebook.pack(expand=True, fill="both", padx=18, pady=10)

        btns_frame = tk.Frame(self, bg="#f5f6fa")
        btns_frame.pack(pady=(0, 12))
        self.show_btn = ttk.Button(btns_frame, text="👀 Show Selected", command=self.show_selected)
        self.show_btn.pack(side='left', padx=8)
        self.install_btn = ttk.Button(btns_frame, text="🚀 Install Selected", command=self.start_install_thread)
        self.install_btn.pack(side='left', padx=8)

    def update_selected(self):
        total = 0
        for info in self.categories.values():
            total += sum(var.get() for var in info["vars"].values())
        self.selected_label.config(text=f"🛒 You have selected {total} for installation.")

    def show_selected(self):
        selected = []
        for cat, info in self.categories.items():
            for name, var in info["vars"].items():
                if var.get():
                    selected.append(f"{info['label']}: {name}")
        if selected:
            messagebox.showinfo("Selected Applications", "\n".join(selected))
        else:
            messagebox.showinfo("Selected Applications", "No applications selected.")

    def show_basket_window(self):
        selected = []
        for cat, info in self.categories.items():
            for name, var in info["vars"].items():
                if var.get():
                    selected.append((info['label'], name, cat))
        win = tk.Toplevel(self)
        win.title("🛒 Basket - Selected Applications")
        win.geometry("400x400")
        win.configure(bg="#f5f6fa")
        lbl = ttk.Label(win, text="Applications you have selected:", font=self.label_font)
        lbl.pack(pady=10)
        listbox = tk.Listbox(win, font=("Segoe UI", 10), bg="#f8f9fa", bd=0, highlightthickness=1, highlightbackground="#d1d8e0")
        for label, name, _ in selected:
            listbox.insert(tk.END, f"{label}: {name}")
        listbox.pack(expand=True, fill="both", padx=10, pady=10)
        if selected:
            btn = ttk.Button(win, text="🚀 Install Selected", command=lambda: [win.destroy(), self.start_install_thread()])
            btn.pack(pady=10)
        else:
            lbl2 = ttk.Label(win, text="No applications selected.", foreground="red")
            lbl2.pack(pady=10)

    def start_install_thread(self):
        threading.Thread(target=self.install_selected, daemon=True).start()

    def install_selected(self):
        selected = []
        for cat, info in self.categories.items():
            for name, var in info["vars"].items():
                if var.get():
                    selected.append((cat, name))
        if not selected:
            messagebox.showinfo("Installation", "No applications selected.")
            return
        for cat, name in selected:
            order = self.categories[cat]["data"][name]
            self.show_status(f"Installing {name}...")
            subprocess.run(f"winget install -e --id {order} --accept-source-agreements --accept-package-agreements --silent", shell=True)
        self.show_status("Installation completed!")

    def show_status(self, msg):
        self.selected_label.config(text=msg)
        self.update_idletasks()

# --- Update Manager Utility (from Update-Manager.py) ---
class UpdateManagerApp(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
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
        self.status_label.config(text="Searching for available updates...")
        try:
            result = subprocess.run(
                ["winget", "upgrade"],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )
            lines = result.stdout.splitlines()
            start = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("Name"):
                    start = i + 1
                    break
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
        selected = [self.updates[name] for name, var in self.vars.items() if var.get()]
        if not selected:
            messagebox.showinfo("Update", "No applications selected for update.")
            return
        self.status_label.config(text="Updating selected applications...")
        threading.Thread(target=self.run_updates, args=(selected,), daemon=True).start()

    def update_all(self):
        all_ids = list(self.updates.values())
        if not all_ids:
            messagebox.showinfo("Update", "No applications available for update.")
            return
        self.status_label.config(text="Updating all applications...")
        threading.Thread(target=self.run_updates, args=(all_ids,), daemon=True).start()

    def run_updates(self, pkg_ids):
        for pkg_id in pkg_ids:
            self.status_label.config(text=f"Updating {pkg_id}...")
            subprocess.run(
                f'winget upgrade --id {pkg_id} --accept-source-agreements --accept-package-agreements --silent',
                shell=True
            )
        self.status_label.config(text="Update process completed!")
        messagebox.showinfo("Update", "Selected applications have been updated.")

# --- Main WinGUILite GUI (original code, with launchers updated) ---
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font
import subprocess
import threading
import re
import os
import sys
import json

# List to store all package IDs
all_ids = []
package_details = {}  # Store raw details per package ID

def run_command(command):
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error executing command: {e}"

def run_command_live(command, output_widget, install_btn, uninstall_btn):
    def task():
        try:
            install_btn.config(state='disabled')
            uninstall_btn.config(state='disabled')
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", f'chcp 65001 >$null; {command}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            output_widget.config(state='normal')
            output_widget.delete('1.0', tk.END)

            while True:
                chunk = process.stdout.readline()
                if not chunk:
                    break

                if '\r' in chunk:
                    cleaned = chunk.strip().replace('\r', '')
                    output_widget.delete("end-2l", "end-1l")
                    output_widget.insert(tk.END, cleaned + '\n')
                elif 'KB' in chunk or 'MB' in chunk:
                    progress = re.sub(r'\r', '', chunk).strip()
                    output_widget.delete("end-2l", "end-1l")
                    output_widget.insert(tk.END, progress + '\n')
                elif chunk.strip() in {'-', '\\', '|', '/'}:
                    output_widget.delete("end-2l", "end-1l")
                    output_widget.insert(tk.END, chunk.strip() + '\n')
                else:
                    output_widget.insert(tk.END, chunk)

                output_widget.see(tk.END)
                output_widget.update_idletasks()

            output_widget.insert(tk.END, "\nDone.\n")
        except Exception as e:
            output_widget.insert(tk.END, f"Error: {e}")
        finally:
            output_widget.config(state='disabled')
            install_btn.config(state='normal')
            uninstall_btn.config(state='normal')

    threading.Thread(target=task, daemon=True).start()

def back_to_search():
    detail_frame.pack_forget()
    search_frame.pack(fill='both', expand=True)

def show_detail_screen(package_name, description, package_id):
    label_pkg_name.config(text=package_name)
    install_btn.config(command=lambda: install_package(package_id))
    uninstall_btn.config(command=lambda: uninstall_package(package_id))

    txt_info.config(state='normal')
    txt_info.delete('1.0', tk.END)
    clean_desc = []
    for line in description.splitlines():
        line = line.replace('â€™', "'").replace('â€“', '–').replace('Â©', '©')
        if line:
            clean_desc.append(line)
    txt_info.insert(tk.END, '\n'.join(clean_desc))
    txt_info.config(state='disabled')

    search_frame.pack_forget()
    detail_frame.pack(fill='both', expand=True)

def on_package_select(event):
    selected = tree_results.selection()
    if not selected:
        return
    item_id = selected[0]
    name, pkg_id, _ = tree_results.item(item_id, 'values')
    raw = package_details.get(pkg_id, "")
    if not raw:
        messagebox.showinfo("Please wait", "Data is still loading... please wait a few seconds")
        return

    lines = [l for l in raw.splitlines() if not re.match(r"^Found\s.+\s\[[^\]]*\]$", l)]
    desc_lines = []
    in_desc = False
    for line in lines:
        if line.strip().startswith('Description:'):
            in_desc = True
            part = line.split('Description:', 1)[1].strip()
            if part:
                desc_lines.append(part)
            continue
        if in_desc:
            if line.startswith('  '):
                desc_lines.append(line.strip())
            else:
                break

    description = '\n'.join(desc_lines) if desc_lines else 'Description: Not provided by package.'
    show_detail_screen(name, description, pkg_id)

def fetch_package_details():
    for programm_id in all_ids:
        package_details[programm_id] = run_command(f"winget show {programm_id}")

def search_packages():
    query = entry_search.get().strip().replace(' ', '')
    if not query:
        messagebox.showwarning("Input Error", "Please enter a search term.")
        return

    output = run_command(f'winget search "{query}"')
    if "No package found" in output or not output.strip():
        messagebox.showinfo("No Results", "No packages found for your search.")
        return

    tree_results.delete(*tree_results.get_children())
    all_ids.clear()
    package_details.clear()
    header_passed = False

    for line in output.splitlines():
        if re.match(r"^-{5,}", line):
            header_passed = True
            continue
        if not header_passed:
            continue
        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) >= 3:
            all_ids.append(cols[1])
            tree_results.insert('', 'end', values=(cols[0], cols[1], cols[2]))

    threading.Thread(target=fetch_package_details, daemon=True).start()

def install_package(pkg_id):
    run_command_live(
        f"winget install --id {pkg_id} -e --accept-source-agreements --accept-package-agreements",
        txt_info, install_btn, uninstall_btn
    )

def uninstall_package(pkg_id):
    run_command_live(
        f"winget uninstall --id {pkg_id} -e",
        txt_info, install_btn, uninstall_btn
    )

def multi_select_mode():
    InstallerApp(root)

def update_packages_mode():
    UpdateManagerApp(root)

def start_main_app():
    startup_frame.pack_forget()
    option_frame.pack(fill='x', padx=0, pady=(0, 8))
    search_frame.pack(fill='both', expand=True)

# --- GUI Setup ---
root = tk.Tk()
root.title("WinGUILite")
root.geometry("780x540")
root.configure(bg="#f5f6fa")

title_font = font.Font(family='Segoe UI', size=16, weight='bold')
label_font = font.Font(family='Segoe UI', size=11)
button_font = font.Font(family='Segoe UI', size=10, weight='bold')

style = ttk.Style()
style.theme_use('clam')
style.configure("Treeview", font=('Segoe UI', 10), rowheight=28, background="#f8f9fa", fieldbackground="#f8f9fa")
style.configure("Treeview.Heading", font=('Segoe UI', 11, 'bold'), background="#d1d8e0")
style.map("Treeview", background=[('selected', '#d6e0f0')])
style.configure("TButton", font=button_font, padding=6, background="#4078c0", foreground="#fff")
style.map("TButton", background=[('active', '#274472')])

search_frame = tk.Frame(root, bg="#f5f6fa")
search_frame.pack(fill='both', expand=True)

search_header = tk.Frame(search_frame, bg='#4078c0', height=48)
search_header.pack(fill='x')
search_title = tk.Label(search_header, text="WinGUILite - A Lite GUI For Microsoft Winget", font=title_font, bg='#4078c0', fg='white')
search_title.pack(side='left', padx=18, pady=8)

tk.Label(search_frame, text="Search for a package:", font=label_font, bg="#f5f6fa").pack(pady=(18, 0))
entry_search = ttk.Entry(search_frame, width=44, font=label_font)
entry_search.pack(pady=7)
ttk.Button(search_frame, text="Search", command=search_packages).pack(pady=7)

cols = ("Name", "ID", "Version")
tree_results = ttk.Treeview(search_frame, columns=cols, show='headings', height=9)
for c in cols:
    tree_results.heading(c, text=c)
tree_results.pack(pady=14, fill='x', padx=18)
tree_results.bind('<<TreeviewSelect>>', on_package_select)

detail_frame = tk.Frame(root, bg="#f5f6fa")
btn_back = ttk.Button(detail_frame, text="⬅ Back", command=back_to_search)
btn_back.pack(anchor='nw', padx=18, pady=(18, 0))

label_pkg_name = tk.Label(detail_frame, text="", font=title_font, bg="#f5f6fa", fg="#274472")
label_pkg_name.pack(anchor='nw', padx=18, pady=(0, 8))

btns_frame = tk.Frame(detail_frame, bg="#f5f6fa")
btns_frame.pack(anchor='ne', padx=18, pady=(0, 10))
install_btn = ttk.Button(btns_frame, text="Install")
install_btn.pack(side='left', padx=4)
uninstall_btn = ttk.Button(btns_frame, text="Uninstall")
uninstall_btn.pack(side='left', padx=4)

txt_info = tk.Text(detail_frame, wrap='word', font=('Segoe UI', 10), bg="#f8f9fa", relief='flat', bd=1, highlightthickness=1, highlightbackground="#d1d8e0")
txt_info.pack(fill='both', expand=True, padx=18, pady=12)
txt_info.config(state='disabled')

option_frame = tk.Frame(root, bg="#eaf0fb", bd=1, relief='solid')
option_frame.pack(fill='x', padx=0, pady=(0, 8))

option_label = tk.Label(option_frame, text="Select and download multiple applications together.", font=label_font, bg="#eaf0fb", fg="#274472")
option_label.pack(side='left', padx=18, pady=8)

startup_frame = tk.Frame(root, bg="#eaf0fb", bd=1, relief='solid')
startup_frame.pack(fill='both', expand=True)

startup_label = tk.Label(startup_frame, text="Please select one of the following options:", font=title_font, bg="#eaf0fb", fg="#274472")
startup_label.pack(pady=(60, 30))

btn_multi = ttk.Button(startup_frame, text="Select and download multiple applications together.", style="TButton", command=multi_select_mode)
btn_multi.pack(pady=12, ipadx=12, ipady=6)

btn_single = ttk.Button(startup_frame, text="Or search for a specific one", style="TButton", command=start_main_app)
btn_single.pack(pady=12, ipadx=12, ipady=6)

btn_update = ttk.Button(startup_frame, text="Update installed applications", style="TButton", command=update_packages_mode)
btn_update.pack(pady=12, ipadx=12, ipady=6)

option_frame.pack_forget()
search_frame.pack_forget()

root.mainloop()