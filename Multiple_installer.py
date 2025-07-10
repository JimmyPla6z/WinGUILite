import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import json
import subprocess
from threading import Thread

# --- Custom Style & Fonts (like in WinGUILite-Tkinter.py) ---
from tkinter import font

def clear_spaces(name):
    """Replaces spaces and special characters in a string with underscores."""
    return name.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")

class InstallerApp(tk.Tk):
    """
    Main application window for selecting and installing multiple applications using winget.
    The UI is styled to match the look and feel of WinGUILite-Tkinter.py.
    """
    def __init__(self):
        super().__init__()
        self.title("🎈 Multi installer utility (Tkinter) 🎈")
        self.geometry("700x500")
        self.resizable(False, False)

        # --- Custom fonts for consistent modern look ---
        self.title_font = font.Font(family='Segoe UI', size=16, weight='bold')
        self.label_font = font.Font(family='Segoe UI', size=11)
        self.button_font = font.Font(family='Segoe UI', size=10, weight='bold')

        # --- ttk Style Customization for modern look ---
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

        self.configure(bg="#f5f6fa")

        # Categories for application selection. Each category loads its package list from a JSON file.
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
        """
        Loads the available packages for each category from JSON files located in the 'packages' folder.
        The folder must be in the same directory as this script.
        """
        base_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        for cat, info in self.categories.items():
            json_filename = f"{cat if cat != 'document' else 'documentation'}.json"
            json_path = os.path.join(base_path, "packages", json_filename)
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    info["data"] = json.load(f)
            except FileNotFoundError:
                messagebox.showerror("Error", f"File {json_filename} not found in 'packages' folder.")
                sys.exit(1)

    def create_widgets(self):
        """
        Creates and places all main widgets: header, menu, notebook (tabs), and action buttons.
        """
        # Header bar with title
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

        # Label showing the number of selected applications
        self.selected_label = ttk.Label(self, text="🛒 You have selected 0 for installation.", font=self.label_font)
        self.selected_label.pack(pady=(18, 10))

        # Menu bar with basket options
        menubar = tk.Menu(self)
        basket_menu = tk.Menu(menubar, tearoff=0)
        basket_menu.add_command(label="Show Selected", command=self.show_basket_window)
        basket_menu.add_command(label="Install Selected", command=self.start_install_thread)
        menubar.add_cascade(label="🛒 Basket", menu=basket_menu)
        self.config(menu=menubar)

        # Notebook (tabbed interface) for categories
        self.notebook = ttk.Notebook(self)
        self.frames = {}
        for cat, info in self.categories.items():
            frame = ttk.Frame(self.notebook)
            self.frames[cat] = frame
            self.notebook.add(frame, text=info["label"])
            # Add a checkbox for each available application in the category
            for name in info["data"]:
                var = tk.BooleanVar()
                cb = ttk.Checkbutton(frame, text=name, variable=var, command=self.update_selected, style="TCheckbutton")
                cb.pack(anchor="w", padx=18, pady=4)
                info["vars"][name] = var
        self.notebook.pack(expand=True, fill="both", padx=18, pady=10)

        # Action buttons below the notebook
        btns_frame = tk.Frame(self, bg="#f5f6fa")
        btns_frame.pack(pady=(0, 12))
        self.show_btn = ttk.Button(btns_frame, text="👀 Show Selected", command=self.show_selected)
        self.show_btn.pack(side='left', padx=8)
        self.install_btn = ttk.Button(btns_frame, text="🚀 Install Selected", command=self.start_install_thread)
        self.install_btn.pack(side='left', padx=8)

    def update_selected(self):
        """
        Updates the label to show the current number of selected applications.
        """
        total = 0
        for info in self.categories.values():
            total += sum(var.get() for var in info["vars"].values())
        self.selected_label.config(text=f"🛒 You have selected {total} for installation.")

    def show_selected(self):
        """
        Shows a message box with the list of currently selected applications.
        """
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
        """
        Opens a new window listing all selected applications and provides an install button.
        """
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
        """
        Starts the installation process in a separate thread to keep the UI responsive.
        """
        Thread(target=self.install_selected, daemon=True).start()

    def install_selected(self):
        """
        Installs all selected applications using winget in silent mode.
        """
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
        """
        Updates the status label with a message.
        """
        self.selected_label.config(text=msg)
        self.update_idletasks()

if __name__ == "__main__":
    # Entry point for the application
    app = InstallerApp()
    app.mainloop()
