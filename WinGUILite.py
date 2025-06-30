import sys  # Παρέχει πρόσβαση σε ορίσματα και συναρτήσεις του συστήματος
import subprocess  # Για την εκτέλεση εξωτερικών εντολών (π.χ. winget)
import threading  # Για εκτέλεση εντολών σε ξεχωριστό νήμα (thread)
import re  # Για κανονικές εκφράσεις (regex)
from PyQt5.QtWidgets import (
    QApplication,  # Η βασική εφαρμογή PyQt5
    QWidget,  # Βασικό widget παραθύρου
    QVBoxLayout, QHBoxLayout,  # Διατάξεις για κάθετη/οριζόντια στοίχιση widgets
    QLabel,  # Ετικέτα κειμένου
    QLineEdit,  # Πεδίο εισαγωγής κειμένου
    QPushButton,  # Κουμπί
    QTreeWidget, QTreeWidgetItem,  # Δενδρική λίστα για εμφάνιση αποτελεσμάτων
    QTextEdit,  # Περιοχή εμφάνισης κειμένου (πολλαπλών γραμμών)
    QMessageBox,  # Μηνύματα διαλόγου (προειδοποιήσεις, πληροφορίες)
    QStackedWidget,  # Widget που κρατάει πολλά widgets και εμφανίζει ένα κάθε φορά
    QSizePolicy  # Πολιτική μεγέθους για widgets
)
from PyQt5.QtCore import Qt  # Παρέχει σταθερές για στοίχιση, κλπ.

def run_command(command):
    """
    Εκτελεί μια εντολή PowerShell και επιστρέφει το αποτέλεσμα ως string.
    Χρησιμοποιείται για απλές εντολές που δεν χρειάζονται live ενημέρωση.
    command: str - Η εντολή PowerShell προς εκτέλεση.
    Επιστρέφει: str - Η έξοδος της εντολής ή μήνυμα λάθους.
    """
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],  # Εκτέλεση PowerShell με την εντολή
            capture_output=True,  # Καταγραφή εξόδου
            text=True  # Επιστροφή ως string
        )
        return result.stdout.strip()  # Επιστροφή μόνο της stdout εξόδου
    except Exception as e:
        return f"Error executing command: {e}"

def run_command_live(command, output_widget, install_btn, uninstall_btn):
    """
    Εκτελεί μια εντολή PowerShell και ενημερώνει ζωντανά το QTextEdit με την έξοδο.
    Χρησιμοποιείται για εγκατάσταση/απεγκατάσταση ώστε να φαίνεται η πρόοδος.
    command: str - Η εντολή PowerShell προς εκτέλεση.
    output_widget: QTextEdit - Το widget όπου εμφανίζεται η έξοδος.
    install_btn: QPushButton - Το κουμπί εγκατάστασης (για enable/disable).
    uninstall_btn: QPushButton - Το κουμπί απεγκατάστασης (για enable/disable).
    """
    def task():
        try:
            install_btn.setEnabled(False)  # Απενεργοποίηση κουμπιού εγκατάστασης
            uninstall_btn.setEnabled(False)  # Απενεργοποίηση κουμπιού απεγκατάστασης
            process = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", f'chcp 65001 >$null; {command}'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8'
            )
            output_widget.setReadOnly(False)  # Ενεργοποίηση επεξεργασίας για ενημέρωση
            output_widget.clear()  # Καθαρισμός προηγούμενης εξόδου
            while True:
                chunk = process.stdout.readline()  # Ανάγνωση κάθε γραμμής εξόδου
                if not chunk:
                    break
                if '\r' in chunk:
                    # Ενημέρωση τελευταίας γραμμής (πρόοδος)
                    cleaned = chunk.strip().replace('\r', '')
                    cursor = output_widget.textCursor()
                    cursor.movePosition(cursor.End)
                    cursor.select(cursor.LineUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deletePreviousChar()
                    output_widget.append(cleaned)
                elif 'KB' in chunk or 'MB' in chunk:
                    # Ενημέρωση γραμμής προόδου με μέγεθος
                    progress = re.sub(r'\r', '', chunk).strip()
                    cursor = output_widget.textCursor()
                    cursor.movePosition(cursor.End)
                    cursor.select(cursor.LineUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deletePreviousChar()
                    output_widget.append(progress)
                elif chunk.strip() in {'-', '\\', '|', '/'}:
                    # Ενημέρωση γραμμής spinner
                    cursor = output_widget.textCursor()
                    cursor.movePosition(cursor.End)
                    cursor.select(cursor.LineUnderCursor)
                    cursor.removeSelectedText()
                    cursor.deletePreviousChar()
                    output_widget.append(chunk.strip())
                else:
                    # Κανονική γραμμή εξόδου
                    output_widget.append(chunk.rstrip())
            output_widget.append("\nDone.\n")  # Τέλος διαδικασίας
            install_btn.setEnabled(True)  # Ενεργοποίηση κουμπιού εγκατάστασης
            uninstall_btn.setEnabled(True)  # Ενεργοποίηση κουμπιού απεγκατάστασης
            output_widget.setReadOnly(True)  # Απενεργοποίηση επεξεργασίας
        except Exception as e:
            output_widget.append(f"Error: {e}")
            output_widget.setReadOnly(True)
            install_btn.setEnabled(True)
            uninstall_btn.setEnabled(True)
    threading.Thread(target=task, daemon=True).start()  # Εκτέλεση σε νέο thread

class MainWindow(QWidget):
    """
    Η κύρια κλάση παραθύρου της εφαρμογής.
    Περιέχει το GUI, τη λογική αναζήτησης, εμφάνισης λεπτομερειών και εγκατάστασης/απεγκατάστασης.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wingui Lite")  # Τίτλος παραθύρου
        self.setGeometry(100, 100, 700, 500)  # Θέση και μέγεθος παραθύρου
        self.stacked = QStackedWidget(self)  # Widget για εναλλαγή οθονών (αναζήτηση/λεπτομέρειες)
        layout = QVBoxLayout(self)  # Κύρια κάθετη διάταξη
        layout.addWidget(self.stacked)
        # Οθόνη αναζήτησης
        self.search_widget = QWidget()  # Widget για την οθόνη αναζήτησης
        self.setup_search_screen()  # Ρύθμιση widgets αναζήτησης
        self.stacked.addWidget(self.search_widget)
        # Οθόνη λεπτομερειών
        self.detail_widget = QWidget()  # Widget για την οθόνη λεπτομερειών
        self.setup_detail_screen()  # Ρύθμιση widgets λεπτομερειών
        self.stacked.addWidget(self.detail_widget)
        self.stacked.setCurrentWidget(self.search_widget)  # Εμφάνιση οθόνης αναζήτησης

    def setup_search_screen(self):
        """
        Ρυθμίζει τα widgets και τη διάταξη της οθόνης αναζήτησης.
        """
        layout = QVBoxLayout(self.search_widget)  # Κάθετη διάταξη για το widget αναζήτησης
        header = QHBoxLayout()  # Οριζόντια διάταξη για τον τίτλο
        lbl = QLabel("Wingui Lite - A Lite GUI For Microsoft Winget")  # Ετικέτα τίτλου
        lbl.setStyleSheet("font-weight: bold; font-size: 16px; background: lightgray;")
        header.addWidget(lbl)
        layout.addLayout(header)
        layout.addWidget(QLabel("Search for a package:"))  # Ετικέτα οδηγίας
        self.entry_search = QLineEdit()  # Πεδίο εισαγωγής αναζήτησης
        layout.addWidget(self.entry_search)
        btn_search = QPushButton("Search")  # Κουμπί αναζήτησης
        btn_search.clicked.connect(self.search_packages)  # Σύνδεση με τη συνάρτηση αναζήτησης
        layout.addWidget(btn_search)
        self.tree_results = QTreeWidget()  # Δενδρική λίστα για τα αποτελέσματα
        self.tree_results.setColumnCount(3)  # Τρεις στήλες: Όνομα, ID, Έκδοση
        self.tree_results.setHeaderLabels(["Name", "ID", "Version"])
        self.tree_results.setSelectionBehavior(self.tree_results.SelectRows)  # Επιλογή γραμμών
        self.tree_results.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tree_results.itemSelectionChanged.connect(self.on_package_select)  # Callback επιλογής πακέτου
        layout.addWidget(self.tree_results)

    def setup_detail_screen(self):
        """
        Ρυθμίζει τα widgets και τη διάταξη της οθόνης λεπτομερειών.
        """
        layout = QVBoxLayout(self.detail_widget)  # Κάθετη διάταξη για το widget λεπτομερειών
        btn_back = QPushButton("< Back")  # Κουμπί επιστροφής στην αναζήτηση
        btn_back.clicked.connect(self.back_to_search)
        layout.addWidget(btn_back, alignment=Qt.AlignLeft)
        self.label_pkg_name = QLabel("")  # Ετικέτα με το όνομα του πακέτου
        self.label_pkg_name.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.label_pkg_name, alignment=Qt.AlignLeft)
        btns = QHBoxLayout()  # Οριζόντια διάταξη για τα κουμπιά εγκατάστασης/απεγκατάστασης
        self.install_btn = QPushButton("Install")  # Κουμπί εγκατάστασης
        self.uninstall_btn = QPushButton("Uninstall")  # Κουμπί απεγκατάστασης
        btns.addWidget(self.install_btn)
        btns.addWidget(self.uninstall_btn)
        layout.addLayout(btns)
        self.txt_info = QTextEdit()  # Περιοχή εμφάνισης πληροφοριών/προόδου
        self.txt_info.setReadOnly(True)
        layout.addWidget(self.txt_info)

    def back_to_search(self):
        """
        Επιστρέφει στην οθόνη αναζήτησης.
        """
        self.stacked.setCurrentWidget(self.search_widget)

    def show_detail_screen(self, package_name, description, package_id):
        """
        Εμφανίζει την οθόνη λεπτομερειών για το επιλεγμένο πακέτο.
        package_name: str - Το όνομα του πακέτου.
        description: str - Η περιγραφή του πακέτου.
        package_id: str - Το ID του πακέτου (για εγκατάσταση/απεγκατάσταση).
        """
        self.label_pkg_name.setText(package_name)
        # Ασφαλής αποσύνδεση προηγούμενων callbacks (αν υπάρχουν)
        try:
            self.install_btn.clicked.disconnect()
        except TypeError:
            pass
        try:
            self.uninstall_btn.clicked.disconnect()
        except TypeError:
            pass
        # Σύνδεση κουμπιών με τις αντίστοιχες συναρτήσεις
        self.install_btn.clicked.connect(lambda: self.install_package(package_id))
        self.uninstall_btn.clicked.connect(lambda: self.uninstall_package(package_id))
        # Καθαρισμός και εμφάνιση περιγραφής
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
        Callback όταν ο χρήστης επιλέγει πακέτο από τη λίστα.
        Εμφανίζει τις λεπτομέρειες του πακέτου.
        """
        selected = self.tree_results.selectedItems()  # Επιλεγμένα αντικείμενα στη λίστα
        if not selected:
            return
        item = selected[0]  # Το πρώτο επιλεγμένο αντικείμενο
        name, pkg_id, _ = [item.text(i) for i in range(3)]  # Όνομα, ID, Έκδοση
        # Φιλτράρισμα άσχετων γραμμών
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
        """ Λαμβάνει λεπτομέρειες για όλα τα πακέτα που βρέθηκαν.
        Χρησιμοποιείται για να εμφανίσει τις λεπτομέρειες όταν ο χρήστης επιλέγει ένα πακέτο."""
        for programm_id in all_ids:
            self.raw = run_command(f"winget show {programm_id}")

    def search_packages(self):
        """
        Εκτελεί αναζήτηση πακέτων με βάση το κείμενο του πεδίου αναζήτησης.
        Ενημερώνει τη λίστα αποτελεσμάτων.
        """
        query = self.entry_search.text().strip()  # Το κείμενο αναζήτησης
        query= query.replace(' ', '')  # Αφαίρεση κενών για καλύτερη αναζήτηση
        print(f"Searching for: {query}")  # Εκτύπωση ερωτήματος για debugging
        if not query:
            QMessageBox.warning(self, "Input Error", "Please enter a search term.")
            return
        output = run_command(f'winget search "{query}"')  # Εκτέλεση αναζήτησης
        if "No package found" in output or not output.strip():
            QMessageBox.information(self, "No Results", "No packages found for your search.")
            return
        self.tree_results.clear()  # Καθαρισμός προηγούμενων αποτελεσμάτων
        header_passed = False  # Flag για να αγνοήσουμε τις γραμμές header
        for line in output.splitlines():
            if re.match(r"^-{5,}", line):
                header_passed = True
                continue
            if not header_passed:
                continue
            cols = re.split(r"\s{2,}", line.strip())  # Διαχωρισμός σε στήλες
            if len(cols) >= 3:  # Έλεγχος ότι υπάρχουν τουλάχιστον 3 στήλες (Name, ID, Version)
                all_ids.append(cols[1])  # Αποθήκευση ID πακέτου
                print(f"Found package ID: {all_ids}")  # Εκτύπωση ID πακέτου για debugging
                QTreeWidgetItem(self.tree_results, [cols[0], cols[1], cols[2]])  # Προσθήκη αποτελέσματος
        threading.Thread(target=self.fetch_package_details, daemon=True).start()  # Εκκίνηση νήματος για λήψη λεπτομερειών πακέτων

    def install_package(self, pkg_id):
        """
        Ξεκινά εγκατάσταση του πακέτου με το δοσμένο ID.
        pkg_id: str - Το ID του πακέτου.
        """
        run_command_live(
            f"winget install --id {pkg_id} -e --accept-source-agreements --accept-package-agreements",
            self.txt_info, self.install_btn, self.uninstall_btn
        )

    def uninstall_package(self, pkg_id):
        """
        Ξεκινά απεγκατάσταση του πακέτου με το δοσμένο ID.
        pkg_id: str - Το ID του πακέτου.
        """
        run_command_live(
            f"winget uninstall --id {pkg_id} -e",
            self.txt_info, self.install_btn, self.uninstall_btn
        )

if __name__ == "__main__":
    all_ids = []  # Λίστα για αποθήκευση όλων των IDs πακέτων
    # Εκκίνηση της εφαρμογής PyQt5
    app = QApplication(sys.argv)  # Δημιουργία αντικειμένου εφαρμογής
    win = MainWindow()  # Δημιουργία κύριου παραθύρου
    win.show()  # Εμφάνιση παραθύρου
    sys.exit(app.exec_())  # Εκκίνηση event loop και έξοδος όταν κλείσει το παράθυρο
