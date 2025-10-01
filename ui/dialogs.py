
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QTableView,
                               QGroupBox, QAbstractItemView, QHeaderView, QFileDialog,
                               QMessageBox, QTextEdit, QTableWidget, QTableWidgetItem, QComboBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPalette, QBrush
import openpyxl

from core.paths import ROOTDIR
from core.constants import DETAILS_XLSX_DEFAULT, NOTES_TEXT
from core.io import save_structs_to_bin
from .models import (FloorStatsModel, SpawnTableModel, MonsterDelegate, IntDelegate, FloatDelegate, EnumDelegate,
                     DROPDOWN_STYLE)

class InAppEditor(QDialog):
    def __init__(self, structs, rengoku_path, mode:str, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(f"In-App Editor — {'Multi Road' if mode=='multi' else 'Solo Road'}")
        self.resize(980, 680)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowTitleHint
        )
        self.structs = structs
        self.rengoku_path = rengoku_path
        self.mode = mode

        # Background with lower opacity so tables are readable
        self.bakimg = QPixmap(str(ROOTDIR / "./asset/bg2.jpg"))
        if not self.bakimg.isNull():
            self.bakimg = self.bakimg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            tmp = QPixmap(self.bakimg.size())
            tmp.fill(Qt.transparent)
            p = QPainter(tmp)
            p.setOpacity(0.55)
            p.drawPixmap(0, 0, self.bakimg)
            p.end()
            pal = self.palette()
            pal.setBrush(QPalette.ColorRole.Window, QBrush(tmp))
            self.setPalette(pal)

        layout = QVBoxLayout(self)

        header = QLabel(f"In-App Editor — {'Multi Road' if mode=='multi' else 'Solo Road'}", self)
        header.setStyleSheet("color: cyan; font-size: 18px; font-weight: bold;")
        header.setAlignment(Qt.AlignCenter)
        header.setProperty("class", "header")
        layout.addWidget(header)

        # Toolbar row
        tools = QHBoxLayout()
        tools.addStretch(1)
        self.save_btn = QPushButton("Save Changes to BIN", self)
        self.save_btn.clicked.connect(self.save_to_bin)
        tools.addWidget(self.save_btn)

        self.notes_btn = QPushButton("Variant Flags", self)  # renamed from "Notes"
        self.notes_btn.clicked.connect(self.show_notes)
        tools.addWidget(self.notes_btn)

        self.extra_btn = QPushButton("Extra Details", self)
        self.extra_btn.clicked.connect(self.show_extra_details)
        tools.addWidget(self.extra_btn)
        tools.addStretch(1)
        layout.addLayout(tools)

        # Floor Stats group
        fs_group = QGroupBox("Floor Stats", self)
        fs_v = QVBoxLayout(fs_group)
        self.tv_floor = QTableView(fs_group)
        self._style_table(self.tv_floor)
        fs_v.addWidget(self.tv_floor)
        layout.addWidget(fs_group, 1)

        # Spawn Tables group
        sp_group = QGroupBox("Spawn Tables", self)
        sp_v = QVBoxLayout(sp_group)
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Group:", sp_group))
        self.group_combo = QComboBox(sp_group)
        self.group_combo.setStyleSheet(DROPDOWN_STYLE)
        top_row.addWidget(self.group_combo, 0)
        sp_v.addLayout(top_row)
        self.tv_spawn = QTableView(sp_group)
        self._style_table(self.tv_spawn)
        self.tv_spawn.setStyleSheet("QTableView{selection-color: cyan;}")
        sp_v.addWidget(self.tv_spawn)
        layout.addWidget(sp_group, 1)

        self._wire_models()

    def _style_table(self, tv:QTableView):
        tv.setAlternatingRowColors(True)
        tv.setSortingEnabled(False)
        tv.setSelectionBehavior(QAbstractItemView.SelectRows)
        tv.setSelectionMode(QAbstractItemView.SingleSelection)
        tv.setEditTriggers(
            QAbstractItemView.DoubleClicked |
            QAbstractItemView.SelectedClicked |
            QAbstractItemView.EditKeyPressed
        )
        tv.verticalHeader().setVisible(True)
        tv.verticalHeader().setDefaultSectionSize(24)
        hv = tv.horizontalHeader()
        hv.setStretchLastSection(True)
        hv.setMinimumSectionSize(60)
        hv.setSectionResizeMode(QHeaderView.ResizeToContents)
        tv.setWordWrap(False)
        tv.setShowGrid(True)

    def _wire_models(self):
        spawn_tables, floor_stats, _multi_def, spawn_tables_solo, floor_stats_solo, _solo_def = self.structs
        if self.mode == "multi":
            self.floor_model = FloorStatsModel(floor_stats, self)
            self.spawn_tables = spawn_tables
        else:
            self.floor_model = FloorStatsModel(floor_stats_solo, self)
            self.spawn_tables = spawn_tables_solo

        self.tv_floor.setModel(self.floor_model)
        # floor delegates
        self.tv_floor.setItemDelegateForColumn(0, IntDelegate(0, 99999, self.tv_floor))
        self.tv_floor.setItemDelegateForColumn(1, IntDelegate(0, 99999, self.tv_floor))
        self.tv_floor.setItemDelegateForColumn(2, IntDelegate(0, 99999, self.tv_floor))
        self.tv_floor.setItemDelegateForColumn(3, FloatDelegate(-1e6, 1e6, 0.1, 3, self.tv_floor))
        self.tv_floor.setItemDelegateForColumn(4, FloatDelegate(-1e6, 1e6, 0.1, 3, self.tv_floor))
        self.tv_floor.setItemDelegateForColumn(5, IntDelegate(0, 99999, self.tv_floor))

        # group combo + spawn table view
        self.group_combo.clear()
        self.group_combo.addItems([str(i) for i in range(len(self.spawn_tables))])
        self.group_combo.currentIndexChanged.connect(self._load_group)
        self._load_group(0)

    def _install_spawn_delegates(self, table:QTableView):
        map_items = [
            ("Default/Stage Param (0)", 0),
            ("Shakalaka (0)", 0),
            ("Blango Spawns (1)", 1),
            ("King Shakalaka (2)", 2),
            ("Custom Spawn 1 (3)", 3),
            ("Custom Spawn 2 (4)", 4),
            ("Custom Spawn 3 (5)", 5),
        ]
        flag_items = [
            ("Default (0)", 0),
            ("Forced Spawn (2)", 2),
            ("Bonus Stage Flag (4)", 4),
            ("Forced Bonus Stage (6)", 6),
            ("Spawn Disabled? (8)", 8),
        ]
        # columns: 0 monster,1 int,2 monster,3 int,4 int,5 map enum,6 int,7 flag enum
        table.setItemDelegateForColumn(0, MonsterDelegate(table))
        table.setItemDelegateForColumn(1, IntDelegate(0, 9999, table))
        table.setItemDelegateForColumn(2, MonsterDelegate(table))
        table.setItemDelegateForColumn(3, IntDelegate(0, 9999, table))
        table.setItemDelegateForColumn(4, IntDelegate(0, 999999, table))
        table.setItemDelegateForColumn(5, EnumDelegate(map_items, parent=table))
        table.setItemDelegateForColumn(6, IntDelegate(0, 999999, table))
        table.setItemDelegateForColumn(7, EnumDelegate(flag_items, parent=table))

    def _load_group(self, idx:int):
        if idx < 0 or idx >= len(self.spawn_tables): return
        self.spawn_model = SpawnTableModel(self.spawn_tables[idx], self)
        self.tv_spawn.setModel(self.spawn_model)
        self._install_spawn_delegates(self.tv_spawn)

        # Make columns wider: FirstMonsterID (0), SecondMonsterID (2), Bonus Spawns (5)
        hv = self.tv_spawn.horizontalHeader()
        for col, width in ((0, 220), (2, 220), (5, 260)):
            hv.setSectionResizeMode(col, QHeaderView.Interactive)
            self.tv_spawn.setColumnWidth(col, width)

    def save_to_bin(self):
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Rengoku Data File", "", "Binary Files (*.bin)")
        if not out_path: return
        try:
            save_structs_to_bin(self.rengoku_path, out_path, self.structs)
            QMessageBox.information(self, "Success", "Saved edited data to BIN successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Saving failed:\n{e}")

    def show_notes(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Variant Flags")
        dlg.resize(560, 520)
        v = QVBoxLayout(dlg)
        te = QTextEdit(dlg)
        te.setReadOnly(True)
        te.setPlainText(NOTES_TEXT)
        v.addWidget(te)
        btn = QPushButton("Close", dlg)
        btn.clicked.connect(dlg.accept)
        v.addWidget(btn, 0, Qt.AlignRight)
        dlg.exec()

    def show_extra_details(self):
        path = os.environ.get("ROAD_DETAILS_XLSX", DETAILS_XLSX_DEFAULT)
        if not os.path.exists(path):
            QMessageBox.warning(self, "Extra Details", f"extra_details.xlsx not found at:\n{path}")
            return
        try:
            wb = openpyxl.load_workbook(path, data_only=True)
            if not wb.sheetnames:
                QMessageBox.warning(self, "Extra Details", "Workbook has no sheets.")
                return
            ws = wb[wb.sheetnames[0]]

            dlg = QDialog(self)
            dlg.setWindowTitle("Extra Details")
            dlg.resize(900, 600)
            v = QVBoxLayout(dlg)

            table = QTableWidget(dlg)

            max_row = ws.max_row
            max_col = ws.max_column

            headers = [str(ws.cell(1, c).value or "").strip() for c in range(1, max_col + 1)]
            drop_terms = {"video", "color codes", "untested"}
            keep_idx = []
            keep_headers = []
            for i, h in enumerate(headers, start=1):
                hl = h.lower()
                if hl in drop_terms:
                    continue
                keep_idx.append(i)
                keep_headers.append(h if h else f"Column {i}")

            if not keep_idx:
                keep_idx = list(range(1, max_col + 1))
                keep_headers = [f"Column {i}" for i in keep_idx]

            data_rows = max(0, max_row - 1)
            table.setRowCount(data_rows)
            table.setColumnCount(len(keep_idx))
            table.setHorizontalHeaderLabels(keep_headers)

            for r in range(2, max_row + 1):
                for ci, c in enumerate(keep_idx):
                    val = ws.cell(r, c).value
                    table.setItem(r - 2, ci, QTableWidgetItem("" if val is None else str(val)))

            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            table.verticalHeader().setDefaultSectionSize(22)
            v.addWidget(table)

            close_btn = QPushButton("Close", dlg)
            close_btn.clicked.connect(dlg.accept)
            v.addWidget(close_btn, 0, Qt.AlignRight)

            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Extra Details", f"Failed to load Excel:\n{e}")


class ModeChooser(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Choose Road Type")
        self.resize(420, 240)

        bg = QPixmap(str(ROOTDIR / "./asset/bg.png"))
        if not bg.isNull():
            bg = bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            tmp = QPixmap(bg.size()); tmp.fill(Qt.transparent)
            p = QPainter(tmp); p.setOpacity(0.75); p.drawPixmap(0, 0, bg); p.end()
            pal = self.palette(); pal.setBrush(QPalette.ColorRole.Window, QBrush(tmp)); self.setPalette(pal)

        v = QVBoxLayout(self)
        label = QLabel("Open which road to edit?", self)
        label.setAlignment(Qt.AlignCenter)
        label.setProperty("class", "header")
        v.addWidget(label)
        btns = QHBoxLayout()
        self.btn_multi = QPushButton("Multi Road", self)
        self.btn_solo = QPushButton("Solo Road", self)
        btns.addStretch(1); btns.addWidget(self.btn_multi); btns.addSpacing(12); btns.addWidget(self.btn_solo); btns.addStretch(1)
        v.addLayout(btns)
        self.choice = None
        self.btn_multi.clicked.connect(self._pick_multi)
        self.btn_solo.clicked.connect(self._pick_solo)
    def _pick_multi(self):
        self.choice = "multi"; self.accept()
    def _pick_solo(self):
        self.choice = "solo"; self.accept()
