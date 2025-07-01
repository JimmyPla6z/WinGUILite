import sys  # Provides access to system arguments and functions
import subprocess  # For running external commands (e.g., winget)
import threading  # For running commands in a separate thread
import re  # For regular expressions
from PyQt5.QtWidgets import (
    QApplication,  # The main PyQt5 application object
    QWidget,  # Basic window widget
    QVBoxLayout, QHBoxLayout,  # Layouts for vertical/horizontal arrangement of widgets
    QLabel,  # Text label
    QLineEdit,  # Text input field
    QPushButton,  # Button
    QTreeWidget, QTreeWidgetItem,  # Tree list for displaying results
    QTextEdit,  # Multi-line text display area
    QMessageBox,  # Dialog messages (warnings, info)
    QStackedWidget,  # Widget that holds multiple widgets and shows one at a time
    QSizePolicy  # Widget size policy
)
from PyQt5.QtCore import Qt  # Provides alignment and other Qt constants

# List to store all package IDs for later use (threaded fetch)
all_ids = []

def run_command(command):
    """
    Executes a PowerShell command and returns the result as a string.
    Used for simple commands that do not need live output.
    command: str - The PowerShell command to execute.
    Returns: str - The command output or an error message.
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],  # Run PowerShell with the command
            capture_output=True,  # Capture output
            text=True  # Return as string
        )
        return result.stdout.strip()  # Return only stdout
    except Exception as e:
        return f"Error executing command: {e}"

def run_command_live(command, output_widget, install_btn, uninstall_btn):
    """
    Executes a PowerShell command and updates the QTextEdit widget live with the output.
    Used for install/uninstall to show progress.
    command: str - The PowerShell command to execute.
    output_widget: QTextEdit - The widget to display output.
    install_btn: QPushButton - The install button (for enable/disable).
    uninstall_btn: QPushButton - The uninstall button (for enable/disable).
    """
    def task():
        try:
            install_btn.setEnabled(False)  # Disable install button during operation
            uninstall_btn.setEnabled(False)  # Disable uninstall button during operation
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", f'chcp 65001 >$null; {command}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            output_widget.setReadOnly(False)  # Enable editing for updating output
            output_widget.clear()  # Clear previous output
            while True:
                chunk = process.stdout.readline()  # Read each output line
                if not chunk:
                    break
                if '\r' in chunk:
                    # Update last line (progress)
                    cleaned = chunk.strip().replace('\r', '')
                    cursor = output_widget.textCursor()
                    cursor.movePosition(cursor.End)
                    cursor.select(cursor.LineUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deletePreviousChar()
                    output_widget.append(cleaned)
                elif 'KB' in chunk or 'MB' in chunk:
                    # Update progress line with size
                    progress = re.sub(r'\r', '', chunk).strip()
                    cursor = output_widget.textCursor()
                    cursor.movePosition(cursor.End)
                    cursor.select(cursor.LineUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deletePreviousChar()
                    output_widget.append(progress)
                elif chunk.strip() in {'-', '\\', '|', '/'}:
                    # Update spinner line
                    cursor = output_widget.textCursor()
                    cursor.movePosition(cursor.End)
                    cursor.select(cursor.LineUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deletePreviousChar()
                    output_widget.append(chunk.strip())
                else:
                    # Normal output line
                    output_widget.append(chunk.rstrip())
            output_widget.append("\nDone.\n")  # End of process
            install_btn.setEnabled(True)  # Enable install button
            uninstall_btn.setEnabled(True)  # Enable uninstall button
            output_widget.setReadOnly(True)  # Disable editing
        except Exception as e:
            output_widget.append(f"Error: {e}")
            output_widget.setReadOnly(True)
            install_btn.setEnabled(True)
            uninstall_btn.setEnabled(True)
    threading.Thread(target=task, daemon=True).start()  # Run in a new thread

class MainWindow(QWidget):
    """
    Main application window class.
    Contains the GUI, search logic, detail display, and install/uninstall logic.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wingui Lite")  # Window title
        self.setGeometry(100, 100, 700, 500)  # Window position and size
        self.stacked = QStackedWidget(self)  # Widget for switching between search/details screens
        layout = QVBoxLayout(self)  # Main vertical layout
        layout.addWidget(self.stacked)
        # Search screen
        self.search_widget = QWidget()  # Widget for the search screen
        self.setup_search_screen()  # Setup search widgets
        self.stacked.addWidget(self.search_widget)
        # Detail screen
        self.detail_widget = QWidget()  # Widget for the detail screen
        self.setup_detail_screen()  # Setup detail widgets
        self.stacked.addWidget(self.detail_widget)
        self.stacked.setCurrentWidget(self.search_widget)  # Show search screen
        self.raw_list = []  # List to store details for all found packages

    def setup_search_screen(self):
        """
        Sets up the widgets and layout for the search screen.
        """
        layout = QVBoxLayout(self.search_widget)  # Vertical layout for search widget
        header = QHBoxLayout()  # Horizontal layout for title
        lbl = QLabel("Wingui Lite - A Lite GUI For Microsoft Winget")  # Title label
        lbl.setStyleSheet("font-weight: bold; font-size: 16px; background: lightgray;")
        header.addWidget(lbl)
        layout.addLayout(header)
        layout.addWidget(QLabel("Search for a package:"))  # Instruction label
        self.entry_search = QLineEdit()  # Search input field
        layout.addWidget(self.entry_search)
        btn_search = QPushButton("Search")  # Search button
        btn_search.clicked.connect(self.search_packages)  # Connect to search function
        layout.addWidget(btn_search)
        self.tree_results = QTreeWidget()  # Tree list for results
        self.tree_results.setColumnCount(3)  # Three columns: Name, ID, Version
        self.tree_results.setHeaderLabels(["Name", "ID", "Version"])
        self.tree_results.setSelectionBehavior(self.tree_results.SelectRows)  # Row selection
        self.tree_results.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree_results.itemSelectionChanged.connect(self.on_package_select)  # Callback for selection
        layout.addWidget(self.tree_results)

    def setup_detail_screen(self):
        """
        Sets up the widgets and layout for the detail screen.
        """
        layout = QVBoxLayout(self.detail_widget)  # Vertical layout for detail widget
        btn_back = QPushButton("< Back")  # Back to search button
        btn_back.clicked.connect(self.back_to_search)
        layout.addWidget(btn_back, alignment=Qt.AlignLeft)
        self.label_pkg_name = QLabel("")  # Label for package name
        self.label_pkg_name.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.label_pkg_name, alignment=Qt.AlignLeft)
        btns = QHBoxLayout()  # Horizontal layout for install/uninstall buttons
        self.install_btn = QPushButton("Install")  # Install button
        self.uninstall_btn = QPushButton("Uninstall")  # Uninstall button
        btns.addWidget(self.install_btn)
        btns.addWidget(self.uninstall_btn)
        layout.addLayout(btns)
        self.txt_info = QTextEdit()  # Area for info/progress
        self.txt_info.setReadOnly(True)
        layout.addWidget(self.txt_info)

    def back_to_search(self):
        """
        Returns to the search screen.
        """
        self.stacked.setCurrentWidget(self.search_widget)

    def show_detail_screen(self, package_name, description, package_id):
        """
        Shows the detail screen for the selected package.
        package_name: str - The package name.
        description: str - The package description.
        package_id: str - The package ID (for install/uninstall).
        """
        self.label_pkg_name.setText(package_name)
        # Safely disconnect previous callbacks (if any)
        try:
            self.install_btn.clicked.disconnect()
        except TypeError:
            pass
        try:
            self.uninstall_btn.clicked.disconnect()
        except TypeError:
            pass
        # Connect buttons to their respective functions
        self.install_btn.clicked.connect(lambda: self.install_package(package_id))
        self.uninstall_btn.clicked.connect(lambda: self.uninstall_package(package_id))
        # Clean and display description
        clean_desc = []
        for line in description.splitlines():
            line = line.replace('â€™', "'").replace('â€“', '–').replace('Â©', '©')
            if line:
                clean_desc.append(line)
        self.txt_info.setReadOnly(False)
        self.txt_info.clear()
        self.txt_info.setPlainText('\n'.join(clean_desc))
        self.txt_info.setReadOnly(True)
        self.stacked.setCurrentWidget(self.detail_widget)

    def on_package_select(self):
        """
        Callback when the user selects a package from the list.
        Shows the package details.
        """
        selected = self.tree_results.selectedItems()  # Selected items in the list
        if not selected:
            return
        item = selected[0]  # The first selected item
        name, pkg_id, _ = [item.text(i) for i in range(3)]  # Name, ID, Version
        # Filter out irrelevant lines
        lines = [l for l in win.raw.splitlines() if not re.match(r"^Found\s.+\s\[[^\]]*\]$", l)]
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
        self.show_detail_screen(name, description, pkg_id)

    def fetch_package_details(self):
        """
        Fetches details for all found packages (runs in a separate thread after search).
        Used to display details when the user selects a package.
        """
        for programm_info in all_ids:
            self.raw_list.append(run_command(f"winget show {programm_info}"))

    def search_packages(self):
        """
        Searches for packages based on the search field text.
        Updates the results list.
        """
        query = self.entry_search.text().strip()  # The search text
        query = query.replace(' ', '')  # Remove spaces for correct search
        print(f"Searching for: {query}")  # Debug print
        if not query:
            QMessageBox.warning(self, "Input Error", "Please enter a search term.")
            return
        output = run_command(f'winget search "{query}"')  # Run search
        if "No package found" in output or not output.strip():
            QMessageBox.information(self, "No Results", "No packages found for your search.")
            return
        self.tree_results.clear()  # Clear previous results
        header_passed = False  # Flag to skip header lines
        for line in output.splitlines():
            if re.match(r"^-{5,}", line):
                header_passed = True
                continue
            if not header_passed:
                continue
            cols = re.split(r"\s{2,}", line.strip())  # Split into columns
            if len(cols) >= 3:  # Ensure at least 3 columns (Name, ID, Version)
                all_ids.append(cols[1])  # Store package ID for later use
                print(f"Found package ID: {all_ids}")  # Debug print for IDs
                QTreeWidgetItem(self.tree_results, [cols[0], cols[1], cols[2]])  # Add result
        # Start thread to fetch details for all found packages after search
        threading.Thread(target=self.fetch_package_details, daemon=True).start()

    def install_package(self, pkg_id):
        """
        Starts installation of the package with the given ID.
        pkg_id: str - The package ID.
        """
        run_command_live(
            f"winget install --id {pkg_id} -e --accept-source-agreements --accept-package-agreements",
            self.txt_info, self.install_btn, self.uninstall_btn
        )

    def uninstall_package(self, pkg_id):
        """
        Starts uninstallation of the package with the given ID.
        pkg_id: str - The package ID.
        """
        run_command_live(
            f"winget uninstall --id {pkg_id} -e",
            self.txt_info, self.install_btn, self.uninstall_btn
        )

if __name__ == "__main__":
    # Start the PyQt5 application
    app = QApplication(sys.argv)  # Create application object
    win = MainWindow()  # Create main window
    win.show()  # Show window
    sys.exit(app.exec_())  # Start event loop and exit when window closes
