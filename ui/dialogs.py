
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QTableView,
                               QGroupBox, QAbstractItemView, QHeaderView, QFileDialog,
                               QMessageBox, QTextEdit, QTableWidget, QTableWidgetItem, QComboBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPalette, QBrush, QColor, QFont
import openpyxl
from numpy.distutils.misc_util import cyan_text

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
        header.setStyleSheet("color: cyan; font-size: 24px; font-weight: bold;")
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

        self.btn_notes = QPushButton("Notes", self)
        self.btn_notes.clicked.connect(self.show_notes2)
        tools.addWidget(self.btn_notes)
        tools.addStretch(1)
        layout.addLayout(tools)

        # Floor Stats group
        fs_group = QGroupBox("Floor Stats", self)
        fs_v = QVBoxLayout(fs_group)
        self.tv_floor = QTableView(fs_group)
        self._style_table(self.tv_floor)
        fs_v.addWidget(self.tv_floor)
        fs_group.setStyleSheet("color: cyan;")
        layout.addWidget(fs_group, 1)

        # Spawn Tables group
        sp_group = QGroupBox("Spawn Tables", self)
        sp_v = QVBoxLayout(sp_group)
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Group:", sp_group))
        sp_group.setStyleSheet("color: cyan;")
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
            ("Default/Stage Param", 4294967295),
            ("Shakalaka (0)", 0),
            ("Blango Spawns (1)", 1),
            ("King Shakalaka (2)", 2),
            ("Custom Spawn 1 (3)", 3),
            ("Custom Spawn 2 (4)", 4),
            ("Custom Spawn 3 (5)", 5),
        ]
        flag_items = [
            ("Default (0)", 0),
            ("Forced Spawn (2) Used for Fatalis as default", 2),
            ("Bonus Stage Flag (4) Enables Purple Text + Road Medal Reward", 4),
            ("Forced Bonus Stage (6) A combination of flag 4 and 2. ", 6),
            ("Spawn Disabled? (8) Prevents this monster slot from spawning. (Needs Tests)", 8),
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

  # Data: (Monster, Result)
    def show_notes2(self):
        notes = [
            ("Akantor", "Functions without issues."),
            ("Amatsu","The fight functions well and without issues, but Amatsu will spawn right at the player spawn point."),
            ("Anorupatisu", "Functions without issues."),
            ("Blinking Nargacuga", "Functions, but his nuke attack will have weird coordinates."),
            ("Bulldrome", "Functions but practically has no HP."),
            ("Burning Freezing Elzelion", "Functions."),
            ("Cephadrome", "Functions without issues."),
            ("Crimson Fatalis", "Functions but outdated fight."),
            ("Crimson Fatalis G", "Half his attacks take him out of bounds. Functions but not recommended."),
            ("Disufiroa","As 1 player, fight/cutscene functioned without issues. In multiplayer, the cutscene caused a softlock. Still needs testing."),
            ("Forokururu", "Functions without issues."),
            ("Gendrome", "Functions without issues."),
            ("Gogomoa","Functions; one move has invisible debris. Pairing with Kokomoa can softlock as he runs away once Gogomoa is killed."),
            ("Guanzorumu", "In Solo, functioned well; cutscene & phase transitions OK; no crash after kill. In multiplayer, caused a softlock. Still needs testing."),
            ("Gurenzeburu", "Functions without issues."),
            ("Howling Zinogre", "Functions without issues."),
            ("Inagami (Non Zenith)", "Functions without issues."),
            ("Inagami (Zenith)", "Should not be added until it is learned how to make his Bamboo properly spawn."),
            ("Iodrome", "Functions without issues."),
            ("Mi Ru", "Functions without issues."),
            ("Musou Bogabadorumu", "Functions without issues."),
            ("Odibatorasu", "Functions without issues. May benefit from custom stats for more HP."),
            ("Phantom Dora", "Functions without issues."),
            ("Poborubarumu", "Functions without issues."),
            ("Rusted Kushala Daora", "Functions without issues. May benefit from custom stats for more HP."),
            ("Shagaru Magala", "Functions without issues."),
            ("Sparkling Zerureusu", "Functions, but his hp-based attack has awkward coordinates out of bounds."),
            ("Starving Deviljho", "Functions without issues."),
            ("Supremacy Dora", "Functions without issues. May benefit from custom stats for more HP."),
            ("Supremacy Teostra", "Functions without issues."),
            ("Taikun Zamuza (Zenith)","When tested, softlocks the road after being killed. The launcher attack causes an issue with player zone loading."),
            ("Unknown", "Functions; no obvious issues."),
            ("White Monoblos", "Functions without issues."),
            ("Yama Kurai", "Functions; no obvious issues."),
            ("Yama Tsukami", "Untested "),
        ]

        dlg = QDialog(self)
        dlg.setWindowTitle("Monster Notes — Hunting Road")
        dlg.resize(780, 540)
        dlg.setWindowModality(Qt.NonModal)
        dlg.setModal(False)

        v = QVBoxLayout(dlg)

        # Header note with black text
        lbl = QLabel(
            "<b style='color:#111;'>Monster Notes (Hunting Road)</b><br>"
            "<span style='color:#111;'>Quick reference for which monsters function properly when added to Hunting Road.<br>"
            "<i>Note:</i> These results are based on personal testing and may change as more information is gathered.<br>"
            "If you discover additional details on these or monsters not listed here, please let me know.</span>"
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet("background: #e1ecf4; border-radius: 4px; padding: 8px;")
        v.addWidget(lbl)

        # Table setup
        tbl = QTableWidget(dlg)
        tbl.setColumnCount(2)
        tbl.setHorizontalHeaderLabels(["Monster", "Result"])
        tbl.setRowCount(len(notes))
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.NoSelection)
        tbl.setShowGrid(True)
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setHighlightSections(False)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        tbl.setWordWrap(True)

        # Style (dark table, black header block)
        tbl.setStyleSheet("""
            QTableWidget {
                background-color: #0e1c2c;
                alternate-background-color: #132437;
                color: #cde9f5;
                gridline-color: #253b50;
                selection-background-color: #18324a;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #2b3f55;
                color: cyan;
                padding: 6px 8px;
                border: none;
                font-weight: 600;
                text-align: left;
            }
            QTableCornerButton::section {
                background-color: #2b3f55;
                border: none;
            }
            QPushButton {
                background-color: #101b2b;
                border: 1px solid #2b4a66;
                border-radius: 6px;
                color: cyan;
                font-weight: bold;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #16314a;
            }
        """)

        # Populate rows
        for r, (monster, result) in enumerate(notes):
            it0 = QTableWidgetItem(monster)
            it0.setForeground(QColor(0, 255, 255))
            it0.setFont(QFont("Segoe UI", 10, QFont.Bold))
            it0.setFlags(Qt.ItemIsEnabled)
            tbl.setItem(r, 0, it0)

            it1 = QTableWidgetItem(result if result else "—")
            it1.setFlags(Qt.ItemIsEnabled)
            it1.setForeground(QColor("#cde9f5"))
            tbl.setItem(r, 1, it1)

            if r % 2 == 1:
                it0.setBackground(QColor("#0b1a28"))
                it1.setBackground(QColor("#0b1a28"))

        v.addWidget(tbl)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton("Close", dlg)
        btn_close.clicked.connect(dlg.close)
        btn_row.addWidget(btn_close)
        v.addLayout(btn_row)

        dlg.show()


class ModeChooser(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Choose Road Type")
        self.setFixedSize(420, 400)

        bg = QPixmap(str(ROOTDIR / "./asset/bg2.jpg"))
        if not bg.isNull():
            bg = bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            tmp = QPixmap(bg.size()); tmp.fill(Qt.transparent)
            p = QPainter(tmp); p.setOpacity(0.50); p.drawPixmap(0, 0, bg); p.end()
            pal = self.palette(); pal.setBrush(QPalette.ColorRole.Window, QBrush(tmp)); self.setPalette(pal)

        v = QVBoxLayout(self)
        label = QLabel("Road Mode Selection", self)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #66CCFF; font-weight: bold;")
        label.setProperty("class", "header")
        v.addWidget(label)
        btns = QVBoxLayout()
        self.btn_multi = QPushButton("Multiplayer Road", self)
        self.btn_solo = QPushButton("Solo Road", self)

        btns.addStretch(1)
        btns.addWidget(self.btn_multi, 0, Qt.AlignHCenter)
        btns.addSpacing(12)
        btns.addWidget(self.btn_solo, 0, Qt.AlignHCenter)
        btns.addStretch(1)

        v.addLayout(btns)
        self.choice = None
        self.btn_multi.clicked.connect(self._pick_multi)
        self.btn_solo.clicked.connect(self._pick_solo)
    def _pick_multi(self):
        self.choice = "multi"; self.accept()
    def _pick_solo(self):
        self.choice = "solo"; self.accept()
