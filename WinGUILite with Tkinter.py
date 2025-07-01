import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import re

# List to store all package IDs
all_ids = []
raw = None  # Global variable to store raw details for selected package

def run_command(command):
    """Executes a shell command using PowerShell for winget compatibility."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8"  # Force utf-8 to avoid UnicodeDecodeError
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error executing command: {e}"

def run_command_live(command, output_widget, install_btn, uninstall_btn):
    """Executes a command and updates output in the Text widget."""
    def task():
        try:
            install_btn.config(state='disabled')  # Disable button during installation
            uninstall_btn.config(state='disabled')  # Disable uninstall button during install

            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", f'chcp 65001 >$null; {command}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',  # Force utf-8 to avoid UnicodeDecodeError
                errors='replace'   # Replace unrecognized characters
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
            install_btn.config(state='normal')
            uninstall_btn.config(state='normal')
            output_widget.config(state='disabled')
        except Exception as e:
            output_widget.insert(tk.END, f"Error: {e}")
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
    global raw  # Use global raw to get details from fetch_package_details
    selected = tree_results.selection()
    if not selected:
        return
    name, pkg_id, _ = tree_results.item(selected, 'values')
    lines = [l for l in raw.splitlines() if not re.match(r"^Found\s.+\s\[[^\]]*\]$", l)]

    desc_lines = []
    in_desc = False
    for line in lines:
        if line.strip().startswith('Description:'):
            in_desc = True
            part = line.split('Description:',1)[1].strip()
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
    global raw
    """Fetches details for all found packages (runs in a separate thread after search)."""
    for programm_id in all_ids:
        # Here you can store or process the details if you want
        raw = run_command(f"winget show {programm_id}")

def search_packages():
    query = entry_search.get().strip()
    query = query.replace(' ', '')  # Remove spaces for correct search
    print(f"Searching for: {query}")  # Debug print
    if not query:
        messagebox.showwarning("Input Error", "Please enter a search term.")
        return
    output = run_command(f'winget search "{query}"')
    if "No package found" in output or not output.strip():
        messagebox.showinfo("No Results", "No packages found for your search.")
        return
    tree_results.delete(*tree_results.get_children())
    all_ids.clear()  # Clear previous IDs
    header_passed = False
    for line in output.splitlines():
        if re.match(r"^-{5,}", line):
            header_passed = True
            continue
        if not header_passed:
            continue
        cols = re.split(r"\s{2,}", line.strip())
        if len(cols) >= 3:
            all_ids.append(cols[1])  # Store package ID
            print(f"Found package ID: {all_ids}")  # Debug print for IDs
            tree_results.insert('', 'end', values=(cols[0], cols[1], cols[2]))
    # Start thread to fetch details for all packages after search
    threading.Thread(target=fetch_package_details, daemon=True).start()

def install_package(pkg_id):
    run_command_live(f"winget install --id {pkg_id} -e --accept-source-agreements --accept-package-agreements", txt_info, install_btn, uninstall_btn)

def uninstall_package(pkg_id):
    run_command_live(f"winget uninstall --id {pkg_id} -e", txt_info, install_btn, uninstall_btn)

# Main Window Setup
root = tk.Tk()
root.title("Wingui Lite")  # Updated name here
root.geometry("700x500")

# Search Frame
search_frame = tk.Frame(root)
search_frame.pack(fill='both', expand=True)

search_header = tk.Frame(search_frame, bg='lightgray', height=40)
search_header.pack(fill='x')
search_title = tk.Label(
    search_header,
    text="Wingui Lite - A Lite GUI For Microsoft Winget",  # Updated header name here
    font=('Arial', 14, 'bold'),
    bg='lightgray'
)
search_title.pack(side='left', padx=10)

tk.Label(search_frame, text="Search for a package:").pack(pady=(10, 0))
entry_search = tk.Entry(search_frame, width=40)
entry_search.pack(pady=5)
tk.Button(
    search_frame,
    text="Search",
    command=search_packages
).pack(pady=5)

cols = ("Name", "ID", "Version")
tree_results = ttk.Treeview(search_frame, columns=cols, show='headings', height=8)
for c in cols:
    tree_results.heading(c, text=c)
tree_results.pack(pady=10, fill='x')
tree_results.bind('<<TreeviewSelect>>', on_package_select)

# Detail Frame
detail_frame = tk.Frame(root)

btn_back = tk.Button(
    detail_frame,
    text="< Back",
    command=back_to_search
)
btn_back.pack(anchor='nw', padx=10, pady=(10, 0))

label_pkg_name = tk.Label(
    detail_frame,
    text="",
    font=('Arial', 16)
)
label_pkg_name.pack(anchor='nw', padx=10)

install_btn = tk.Button(detail_frame, text="Install")
install_btn.pack(anchor='ne', padx=10, pady=(0, 10))

uninstall_btn = tk.Button(detail_frame, text="Uninstall")
uninstall_btn.pack(anchor='ne', padx=10, pady=(0, 10))

txt_info = tk.Text(detail_frame, wrap='word')
txt_info.pack(fill='both', expand=True, padx=10, pady=10)
txt_info.config(state='disabled')

root.mainloop()