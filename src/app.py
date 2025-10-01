import os, sys
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QPixmap, QPainter, QPalette, QBrush, QIcon,
    QFontDatabase, QFont, QColor,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QMessageBox, QFileDialog,
    QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem,
)
from core.paths import ROOTDIR, resource_path
from core.io import parse_rengoku_data
from core.excel import create_excel_from_bin, export_excel_to_bin
from core.mhfdat_io import parse_mhfdat

from ui.monster_points_editor import MonsterPointsEditor
from ui.styles import app_stylesheet
from ui.dialogs import InAppEditor, ModeChooser

class RengokuWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Blaze Road Editor")
        self.setFixedSize(750, 560)
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

        bg = QPixmap(str(ROOTDIR / "./asset/bg6.png"))
        if not bg.isNull():
            bg = bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            tmp = QPixmap(bg.size()); tmp.fill(Qt.transparent)
            p = QPainter(tmp); p.setOpacity(0.25); p.drawPixmap(0, 0, bg); p.end()
            pal = self.palette(); pal.setBrush(QPalette.ColorRole.Window, QBrush(tmp)); self.setPalette(pal)

        outer = QHBoxLayout(central)
        outer.addStretch(1)
        column = QVBoxLayout()
        outer.addLayout(column)
        outer.addStretch(1)

        from PySide6.QtGui import QFontDatabase, QFont
        from core.paths import resource_path

        column.addStretch(1)

        # Robust font load
        font_path = str(resource_path("asset", "Monster_hunter_frontier.ttf"))
        font_id = QFontDatabase.addApplicationFont(font_path)
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id != -1 else []

        header = QLabel("Hunting Road Editor", self)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #66CCFF; font-size: 28px; font-weight: bold;")
        header.setObjectName("appHeader")

        # 🔹 Apply glow effect
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(20)
        glow.setColor(QColor("#00FFFF"))
        glow.setOffset(0, 0)
        header.setGraphicsEffect(glow)

        if families:
            header.setFont(QFont(families[0], 22))
        else:
            print(f"[WARN] Could not load font at: {font_path}")
            header.setFont(QFont("Segoe UI", 22))  # explicit fallback

        column.addWidget(header)

        # --- Two-column button grid ---
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)  # space between left/right columns
        grid.setVerticalSpacing(14)  # space between rows
        grid.setContentsMargins(0, 10, 0, 10)

        def prep(btn):
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumWidth(260)  # keeps columns visually equal
            btn.setMinimumHeight(40)
            return btn

        # Left column: Load Rengoku Data, Export, Import, Open Editor
        self.load_button = prep(QPushButton("Load Rengoku Data", self))
        self.load_button.clicked.connect(self.load_rengoku_data)
        grid.addWidget(self.load_button, 0, 0)

        self.export_button = prep(QPushButton("Export to Excel Sheet", self))
        self.export_button.clicked.connect(self.export_to_excel)
        grid.addWidget(self.export_button, 1, 0)

        self.import_button = prep(QPushButton("Import from Excel Sheet", self))
        self.import_button.clicked.connect(self.import_from_excel)
        grid.addWidget(self.import_button, 2, 0)

        self.editor_button = prep(QPushButton("Open In-App Editor", self))
        self.editor_button.clicked.connect(self.open_in_app_editor)
        grid.addWidget(self.editor_button, 3, 0)

        # Right column: Load mhfdat.bin, Edit Monster Points
        self.load_mhfdat_button = prep(QPushButton("Load MHF Dat", self))
        self.load_mhfdat_button.clicked.connect(self.load_mhfdat_data)
        grid.addWidget(self.load_mhfdat_button, 0, 1)

        self.edit_points_button = prep(QPushButton("Edit Monster Points", self))
        self.edit_points_button.clicked.connect(self.open_monster_points_editor)
        self.edit_points_button.setEnabled(False)
        grid.addWidget(self.edit_points_button, 1, 1)

        # Balance the grid (empty cells where needed)
        grid.addItem(QSpacerItem(0, 0), 2, 1)
        grid.addItem(QSpacerItem(0, 0), 3, 1)

        # About button centered below both columns (spans 2 columns)
        self.help_button = prep(QPushButton("About", self))
        self.help_button.clicked.connect(self.open_help)
        grid.addWidget(self.help_button, 4, 0)

        # Make both columns share space evenly
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        # Add the grid into your main vertical layout
        column.addLayout(grid)
        column.addStretch(5)

        for w in [self.export_button, self.import_button, self.editor_button]:
            w.setEnabled(False)

    def load_mhfdat_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open mhfdat File", "", "Binary Files (*.bin)")
        if not file_path:
            return
        try:
            self.mhfdat_parsed = parse_mhfdat(file_path)
            self.mhfdat_path = file_path
            QMessageBox.information(self, "Success", "mhfdat data loaded successfully!")
            self.edit_points_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to parse mhfdat:\n{e}")
            self.edit_points_button.setEnabled(False)

    def open_monster_points_editor(self):
        if not hasattr(self, "mhfdat_parsed"):
            QMessageBox.warning(self, "Error", "No mhfdat data loaded!")
            return
        dlg = MonsterPointsEditor(self.mhfdat_path, self.mhfdat_parsed, self)
        dlg.exec()

    def open_help(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("About (Help)")
        msg.setTextFormat(Qt.RichText)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setText("""
            <h2 style="color:#444;">Blaze Hunting Road Editor</h2>
            <p><b>Important:</b> Both <code>rengoku_data.bin</code> and <code>mhfdat.bin</code> 
            must be <u>decompressed</u> before loading.</p>
            <ul>
              <li><b>Load Rengoku Data</b> — open <b>rengoku_data.bin</b> to enable the in-app editor and Excel tools.</li>
              <li><b>Export to Excel</b> — creates an .xlsx with Floor Stats &amp; Spawn Tables, plus helpful key sheets.</li>
              <li><b>Import from Excel</b> — applies your edited sheet back into a template BIN and saves an updated BIN.</li>
              <li><b>Open In-App Editor</b> — launches a modal editor (choose Multi or Solo) with neat, editable tables.</li>
              <li><b>Load mhfdat.bin</b> — open <b>mhfdat.bin</b> (decompressed) to work with Monster Points data.</li>
              <li><b>Edit Monster Points</b> — enabled after loading mhfdat.bin; lets you edit monster entries and the RoadEntries counter.</li>
            </ul>

            <p><b>Note:</b> The base Monster Points used in Hunting Road come directly from 
            <code>mhfdat.bin</code>. To adjust how many points a monster gives, you must edit it through 
            <b>Load mhfdat.bin</b> → <b>Edit Monster Points</b>.<br>
            This is important when adding monsters that are not normally present on hunting road.</p>

            <p style="margin-top:15px; font-size:90%; color:#666;">
              For questions or issues, please visit the project on 
              <a href="https://github.com/BlazeMH/Blaze-Hunting-Road-Editor">GitHub</a>.
            </p>
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
