
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
                               QTableView, QGroupBox, QAbstractItemView, QHeaderView,
                               QFileDialog, QSpinBox, QWidget, QFormLayout)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QPalette, QBrush
from ui.utils import apply_dialog_background
from core.paths import ROOTDIR
from core.constants import MONSTERS
from core.mhfdat_io import parse_mhfdat, save_mhfdat, MonsterPoints
from .models import SpawnTableModel, IntDelegate, FloatDelegate, MonsterDelegate  # reuse delegates
from .models import EDITOR_TEXT_STYLE  # cyan editing

class MonsterPointsModel(SpawnTableModel):
    """Reuse SpawnTableModel skeleton but adapt to MonsterPoints columns."""
    COLS = ["monster_id","monster_flag","base_points",
            "level1_points","level2_points","level3_points","level4_points","level5_points"]

    HEADER_TITLES = [
        "Monster", "Flag", "Base Points",
        "Level 1 Points", "Level 2 Points", "Level 3 Points",
        "Level 4 Points", "Level 5 Points"
    ]

    def __init__(self, rows, parent=None):
        super().__init__(rows, parent=parent)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            try:
                return self.HEADER_TITLES[section]
            except IndexError:
                return ""
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section + 1
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        obj  = self.rows[index.row()]
        coln = self.COLS[index.column()]
        val  = getattr(obj, coln)
        if role in (Qt.DisplayRole, Qt.EditRole):
            if coln == "monster_id":
                try:
                    return MONSTERS[val]
                except Exception:
                    return val
            return val
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        obj  = self.rows[index.row()]
        coln = self.COLS[index.column()]
        try:
            if coln == "monster_id":
                if isinstance(value, str):
                    value = MONSTERS.index(value) if not value.isdigit() else int(value)
            else:
                value = int(value)
            setattr(obj, coln, value)
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        except Exception:
            return False

class MonsterPointsEditor(QDialog):
    def __init__(self, mhfdat_path: str, parsed: dict, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Monster Points Editor")
        self.setStyleSheet("color: #66CCFF; font-weight: bold;")
        self.resize(1000, 700)

        apply_dialog_background(self, image_name="bg2.jpg", opacity=0.65)  # or your current file
        # Allow maximize
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint |
                            Qt.WindowMaximizeButtonHint | Qt.WindowTitleHint)

        # background
        bg = QPixmap(str(ROOTDIR / "asset" / "bg2.jpg"))
        if not bg.isNull():
            bg = bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            tmp = QPixmap(bg.size()); tmp.fill(Qt.transparent)
            p = QPainter(tmp); p.setOpacity(0.65); p.drawPixmap(0, 0, bg); p.end()
            pal = self.palette(); pal.setBrush(QPalette.ColorRole.Window, QBrush(tmp)); self.setPalette(pal)

        self.mhfdat_path = mhfdat_path
        self.parsed = parsed

        layout = QVBoxLayout(self)
        header = QLabel("Monster Points Editor", self)
        header.setAlignment(Qt.AlignCenter)
        header.setProperty("class", "header")
        layout.addWidget(header)

        # Top controls: RoadEntries
        top_box = QGroupBox("Data Counters", self)
        form = QFormLayout(top_box)
        self.spn_road_entries = QSpinBox(top_box)
        self.spn_road_entries.setRange(0, 10000)
        self.spn_road_entries.setValue(parsed['counters'].RoadEntries)
        self.spn_road_entries.setStyleSheet(EDITOR_TEXT_STYLE)
        label = QLabel("RoadEntries:", self)
        label.setStyleSheet("color: #66CCFF;")
        form.addRow(label, self.spn_road_entries)
       # form.addRow("RoadEntries:", self.spn_road_entries)
        layout.addWidget(top_box)

        # Table group
        grp = QGroupBox("Monster Data", self)
        v = QVBoxLayout(grp)
        self.table = QTableView(grp)
        self._style_table(self.table)
        v.addWidget(self.table)
        layout.addWidget(grp, 1)

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_add = QPushButton("Add Row", self)
        self.btn_add.clicked.connect(self._add_row)
        btns.addWidget(self.btn_add)

        self.btn_delete = QPushButton("Delete Selected", self)
        self.btn_delete.clicked.connect(self._delete_selected)
        btns.addWidget(self.btn_delete)
        self.btn_save = QPushButton("Save Changes to Mhfdat", self)
        self.btn_save.clicked.connect(self._save)
        btns.addWidget(self.btn_save)
        btns.addStretch(1)
        layout.addLayout(btns)

        # Model + delegates
        self.model = MonsterPointsModel(parsed['monster_rows'], self)
        self.table.setModel(self.model)
        # Delegates: monster_id as dropdown, rest as int spinboxes
        self.table.setItemDelegateForColumn(0, MonsterDelegate(self.table))
        for col in range(1, self.model.columnCount()):
            self.table.setItemDelegateForColumn(col, IntDelegate(0, 65535, self.table))

        # widen monster_id column
        hv = self.table.horizontalHeader()
        hv.setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 240)

    def _style_table(self, tv:QTableView):
        tv.setAlternatingRowColors(True)
        tv.setSortingEnabled(False)
        tv.setSelectionBehavior(QAbstractItemView.SelectRows)
        tv.setSelectionMode(QAbstractItemView.SingleSelection)
        tv.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked | QAbstractItemView.EditKeyPressed)
        tv.verticalHeader().setVisible(True)
        tv.verticalHeader().setDefaultSectionSize(24)
        hv = tv.horizontalHeader()
        hv.setStretchLastSection(True)
        hv.setMinimumSectionSize(60)
        hv.setSectionResizeMode(QHeaderView.ResizeToContents)
        tv.setWordWrap(False)
        tv.setShowGrid(True)

    def _refresh_model(self):
        # Rebuild table model from list, preserving selection if desired
        self.model.beginResetModel()
        self.model.endResetModel()

    def _add_row(self):
        from core.mhfdat_io import MonsterPoints
        # Append a sensible default row (monster_id=1, zeros elsewhere)
        self.parsed['monster_rows'].append(
            MonsterPoints(
                monster_id=1, monster_flag=0, base_points=0,
                level1_points=0, level2_points=0, level3_points=0,
                level4_points=0, level5_points=0, offset=-1  # -1 indicates "new row" (no original offset)
            )
        )
        self._refresh_model()

    def _delete_selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return
        row = idx.row()
        if 0 <= row < len(self.parsed['monster_rows']):
            del self.parsed['monster_rows'][row]
            self._refresh_model()

    def _save(self):
        self.parsed['counters'].RoadEntries = self.spn_road_entries.value()
        out_path, _ = QFileDialog.getSaveFileName(self, "Save mhfdat File", "", "Binary Files (*.bin)")
        if not out_path:
            return
        from core.mhfdat_io import save_mhfdat
        # Force EOF placement + add padding
        save_mhfdat(
            self.mhfdat_path,
            out_path,
            self.parsed,
            always_move_to_eof=True,
            eof_align=0x10,
            end_padding=0x400  # extra trailing pad after the block
        )


