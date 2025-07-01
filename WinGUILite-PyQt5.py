import sys
import subprocess
import threading
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QTextEdit, QMessageBox,
    QStackedWidget, QSizePolicy
)
from PyQt5.QtCore import Qt

all_ids = []

def run_command(command):
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error executing command: {e}"

def run_command_live(command, output_widget, install_btn, uninstall_btn):
    def task():
        try:
            install_btn.setEnabled(False)
            uninstall_btn.setEnabled(False)
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", f'chcp 65001 >$null; {command}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            output_widget.setReadOnly(False)
            output_widget.clear()
            while True:
                chunk = process.stdout.readline()
                if not chunk:
                    break
                cleaned = chunk.strip().replace('\r', '')
                output_widget.append(cleaned)
            output_widget.append("\nDone.\n")
        except Exception as e:
            output_widget.append(f"Error: {e}")
        finally:
            output_widget.setReadOnly(True)
            install_btn.setEnabled(True)
            uninstall_btn.setEnabled(True)

    threading.Thread(target=task, daemon=True).start()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wingui Lite")
        self.setGeometry(100, 100, 700, 500)
        self.stacked = QStackedWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.stacked)

        self.search_widget = QWidget()
        self.setup_search_screen()
        self.stacked.addWidget(self.search_widget)

        self.detail_widget = QWidget()
        self.setup_detail_screen()
        self.stacked.addWidget(self.detail_widget)

        self.stacked.setCurrentWidget(self.search_widget)
        self.raw_list = []

    def setup_search_screen(self):
        layout = QVBoxLayout(self.search_widget)
        header = QHBoxLayout()
        lbl = QLabel("Wingui Lite - A Lite GUI For Microsoft Winget")
        lbl.setStyleSheet("font-weight: bold; font-size: 16px; background: lightgray;")
        header.addWidget(lbl)
        layout.addLayout(header)
        layout.addWidget(QLabel("Search for a package:"))
        self.entry_search = QLineEdit()
        layout.addWidget(self.entry_search)
        btn_search = QPushButton("Search")
        btn_search.clicked.connect(self.search_packages)
        layout.addWidget(btn_search)
        self.tree_results = QTreeWidget()
        self.tree_results.setColumnCount(3)
        self.tree_results.setHeaderLabels(["Name", "ID", "Version"])
        self.tree_results.setSelectionBehavior(self.tree_results.SelectRows)
        self.tree_results.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree_results.itemSelectionChanged.connect(self.on_package_select)
        layout.addWidget(self.tree_results)

    def setup_detail_screen(self):
        layout = QVBoxLayout(self.detail_widget)
        btn_back = QPushButton("< Back")
        btn_back.clicked.connect(self.back_to_search)
        layout.addWidget(btn_back, alignment=Qt.AlignLeft)
        self.label_pkg_name = QLabel("")
        self.label_pkg_name.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.label_pkg_name, alignment=Qt.AlignLeft)
        btns = QHBoxLayout()
        self.install_btn = QPushButton("Install")
        self.uninstall_btn = QPushButton("Uninstall")
        btns.addWidget(self.install_btn)
        btns.addWidget(self.uninstall_btn)
        layout.addLayout(btns)
        self.txt_info = QTextEdit()
        self.txt_info.setReadOnly(True)
        layout.addWidget(self.txt_info)

    def back_to_search(self):
        self.stacked.setCurrentWidget(self.search_widget)

    def show_detail_screen(self, package_name, description, package_id):
        self.label_pkg_name.setText(package_name)
        try:
            self.install_btn.clicked.disconnect()
        except TypeError:
            pass
        try:
            self.uninstall_btn.clicked.disconnect()
        except TypeError:
            pass
        self.install_btn.clicked.connect(lambda: self.install_package(package_id))
        self.uninstall_btn.clicked.connect(lambda: self.uninstall_package(package_id))

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
        selected = self.tree_results.selectedItems()
        if not selected:
            return
        item = selected[0]
        name, pkg_id, _ = [item.text(i) for i in range(3)]

        # Find the matching raw entry
        matching_raw = next((raw for raw in self.raw_list if pkg_id in raw), None)
        if not matching_raw:
            self.show_detail_screen(name, "Description not available.", pkg_id)
            return

        lines = matching_raw.splitlines()
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
        description = '\n'.join(desc_lines) if desc_lines else "Description not provided by package."
        self.show_detail_screen(name, description, pkg_id)

    def fetch_package_details(self):
        self.raw_list.clear()
        for pkg_id in all_ids:
            details = run_command(f"winget show {pkg_id}")
            self.raw_list.append(details)

    def search_packages(self):
        query = re.sub(r'\s+', ' ', self.entry_search.text().strip())
        if not query:
            QMessageBox.warning(self, "Input Error", "Please enter a search term.")
            return

        all_ids.clear()
        self.tree_results.clear()
        output = run_command(f'winget search "{query}"')

        if "No package found" in output or not output.strip():
            QMessageBox.information(self, "No Results", "No packages found for your search.")
            return

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
                QTreeWidgetItem(self.tree_results, [cols[0], cols[1], cols[2]])

        self.txt_info.setPlainText("Fetching package details...")
        threading.Thread(target=self.fetch_package_details, daemon=True).start()

    def install_package(self, pkg_id):
        run_command_live(
            f"winget install --id {pkg_id} -e --accept-source-agreements --accept-package-agreements",
            self.txt_info, self.install_btn, self.uninstall_btn
        )

    def uninstall_package(self, pkg_id):
        run_command_live(
            f"winget uninstall --id {pkg_id} -e",
            self.txt_info, self.install_btn, self.uninstall_btn
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
