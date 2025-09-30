
import os, sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QMessageBox, QFileDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPalette, QBrush, QIcon

from core.paths import ROOTDIR
from core.io import parse_rengoku_data
from core.excel import create_excel_from_bin, export_excel_to_bin
from ui.styles import app_stylesheet
from ui.dialogs import InAppEditor, ModeChooser

class RengokuWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Blaze Road Editor")
        self.setFixedSize(760, 560)
        self.setWindowFlags(
            Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint |
            Qt.WindowMinimizeButtonHint | Qt.WindowTitleHint
        )
        # ✅ Set the window icon here
        self.setWindowIcon(QIcon(str(ROOTDIR / "./asset/icon.png")))

        self._initUI()

    def _initUI(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        bg = QPixmap(str(ROOTDIR / "./asset/bg.png"))
        if not bg.isNull():
            bg = bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            tmp = QPixmap(bg.size()); tmp.fill(Qt.transparent)
            p = QPainter(tmp); p.setOpacity(0.85); p.drawPixmap(0, 0, bg); p.end()
            pal = self.palette(); pal.setBrush(QPalette.ColorRole.Window, QBrush(tmp)); self.setPalette(pal)

        outer = QHBoxLayout(central)
        outer.addStretch(1)
        column = QVBoxLayout()
        outer.addLayout(column)
        outer.addStretch(1)

        column.addStretch(1)

        header = QLabel("Hunting Road Editor", self)
        header.setAlignment(Qt.AlignCenter)
        header.setProperty("class", "header")
        column.addWidget(header)

        self.load_button = QPushButton("Load Rengoku Data", self)
        self.load_button.clicked.connect(self.load_rengoku_data)
        column.addWidget(self.load_button, 0, Qt.AlignHCenter)

        self.export_button = QPushButton("Export to Excel", self)
        self.export_button.clicked.connect(self.export_to_excel)
        column.addWidget(self.export_button, 0, Qt.AlignHCenter)

        self.import_button = QPushButton("Import from Excel", self)
        self.import_button.clicked.connect(self.import_from_excel)
        column.addWidget(self.import_button, 0, Qt.AlignHCenter)

        self.editor_button = QPushButton("Open In-App Editor", self)
        self.editor_button.clicked.connect(self.open_in_app_editor)
        column.addWidget(self.editor_button, 0, Qt.AlignHCenter)

        self.help_button = QPushButton("About", self)
        self.help_button.clicked.connect(self.open_help)
        column.addWidget(self.help_button, 0, Qt.AlignHCenter)

        column.addStretch(2)

        for w in [self.export_button, self.import_button, self.editor_button]:
            w.setEnabled(False)

    def open_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("About (Help)")
        msg.setTextFormat(Qt.RichText)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setText("""
        <h2 style="color:#444;">Blaze Hunting Road Editor</h2>
        <ul>
          <li><b>Load Rengoku Data</b> to enable the in-app editor and sheet tools.</li>
          <li><b>Export to Excel</b> creates an .xlsx with Floor Stats &amp; Spawn Tables, plus Monster Key and Spawn Table Key.</li>
          <li><b>Import from Excel</b> applies your edited sheet back to a template BIN and saves an updated BIN.</li>
          <li><b>Open In-App Editor</b> launches a modal editor (choose Multi or Solo) with neat, editable tables.</li>
        </ul>
        """)
        msg.show()

    def load_rengoku_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Rengoku Data File", "", "Binary Files (*.bin)")
        if not file_path:
            return
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            QMessageBox.critical(self, "Error", "Failed to read the file size.")
            for w in [self.export_button, self.import_button, self.editor_button]:
                w.setEnabled(False)
            return

        if os.path.basename(file_path).lower() == 'rengoku_data.bin' and file_size < 10 * 1024:
            QMessageBox.critical(self, "Error",
                                 "The selected Rengoku file appears compressed or truncated (size < 10 KB). Decompress and try again.")
            for w in [self.export_button, self.import_button, self.editor_button]:
                w.setEnabled(False)
            return

        structs = parse_rengoku_data(file_path)
        if not structs:
            QMessageBox.critical(self, "Error", "Failed to parse Rengoku data.")
            for w in [self.export_button, self.import_button, self.editor_button]:
                w.setEnabled(False)
            return

        self.rengoku_path = file_path
        self.structs = structs
        QMessageBox.information(self, "Success", "Rengoku data loaded successfully!")

        for w in [self.export_button, self.import_button, self.editor_button]:
            w.setEnabled(True)

    def open_in_app_editor(self):
        if not hasattr(self, "structs"):
            QMessageBox.warning(self, "Error", "No Rengoku data loaded!")
            return
        chooser = ModeChooser(self)
        if chooser.exec() != QMessageBox.Accepted or chooser.choice is None:
            return
        editor = InAppEditor(self.structs, self.rengoku_path, chooser.choice, self)
        editor.exec()

    def export_to_excel(self):
        if not hasattr(self, 'structs'):
            QMessageBox.warning(self, "Error", "No Rengoku data loaded!")
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Excel File", "", "Excel Files (*.xlsx)")
        if not out_path: return
        try:
            create_excel_from_bin(self.structs, out_path)
            QMessageBox.information(self, "Success", "Exported to Excel (Details tab added if available).")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{e}")

    def import_from_excel(self):
        if not hasattr(self, 'structs'):
            QMessageBox.warning(self, "Error", "No Rengoku data loaded!")
            return
        excel_file, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel Files (*.xlsx)")
        if not excel_file: return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Rengoku Data File", "", "Binary Files (*.bin)")
        if not out_path: return
        template_file = getattr(self, "rengoku_path", None)
        if not template_file:
            template_file, _ = QFileDialog.getOpenFileName(self, "Open Rengoku Template File", "", "Binary Files (*.bin)")
            if not template_file: return
        try:
            export_excel_to_bin(excel_file, out_path, template_file)
            QMessageBox.information(self, "Success", "Imported from Excel and saved BIN.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Import failed:\n{e}")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(app_stylesheet())
    win = RengokuWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
