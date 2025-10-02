# ui/catshop_editor.py
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QPixmap, QPainter, QPalette, QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QGroupBox, QFormLayout, QSpinBox,
    QTableView, QHeaderView, QAbstractItemView, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox
)

from core.paths import ROOTDIR, resource_path
from ui.utils import apply_dialog_background
from core.catshop_io import parse_catshop, save_catshop, CatShopItem, CatShopParsed
from .models import IntDelegate
from .models import EDITOR_TEXT_STYLE

# ---------- helpers ----------
def load_item_names() -> dict[int, str]:
    """
    Load item ID -> name from asset/Items.xlsx (first sheet).
    Expected headers include something like: ID (or ItemID), Name (or ItemName).
    """
    try:
        from openpyxl import load_workbook
    except Exception:
        return {}

    # Try app bundle path
    xlsx_path = resource_path("asset", "Items.xlsx")
    p = Path(xlsx_path)
    if not p.exists():
        # Fallback: raw relative (dev)
        p = Path("asset/Items.xlsx")
        if not p.exists():
            return {}

    try:
        wb = load_workbook(str(p), read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        # find columns
        headers = {c.value.strip().lower(): idx for idx, c in enumerate(next(ws.iter_rows(min_row=1, max_row=1))[0:]) if c.value}
        # heuristic for ID and Name keys
        id_idx = None
        name_idx = None
        for key, idx in headers.items():
            if key in ("id", "itemid", "item_id"):
                id_idx = idx
            if key in ("name", "itemname", "item_name"):
                name_idx = idx
        if id_idx is None or name_idx is None:
            # fallback: assume first two columns
            id_idx, name_idx = 0, 1

        mapping: dict[int, str] = {}
        for row in ws.iter_rows(min_row=2):
            try:
                rid = row[id_idx].value
                rname = row[name_idx].value
                if rid is None or rname is None:
                    continue
                rid = int(rid)
                mapping[rid] = str(rname)
            except Exception:
                continue
        return mapping
    except Exception:
        return {}


class CatShopModel(QAbstractTableModel):
    """
    Exposes: Item ID | Item Name | Item ID 2 | Item Name 2
    Only the ID columns are editable. Names come from a read-only mapping.
    """
    COLS = ["item_id", "item_name", "item_id2", "item_name2"]
    HEADERS = ["Item ID", "Item Name", "Item ID 2", "Item Name 2"]

    # Signal to notify the editor that item IDs changed (for counter recompute)
    idsChanged = Signal()

    def __init__(self, rows: list[CatShopItem], id_to_name: dict[int, str], parent=None):
        super().__init__(parent)
        self.rows = rows
        self.id_to_name = id_to_name

    def rowCount(self, _=QModelIndex()) -> int: return len(self.rows)
    def columnCount(self, _=QModelIndex()) -> int: return len(self.COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return section + 1

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        col_name = self.COLS[index.column()]
        editable = col_name in ("item_id", "item_id2")
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return base | (Qt.ItemIsEditable if editable else Qt.NoItemFlags)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        col_name = self.COLS[index.column()]
        if role in (Qt.DisplayRole, Qt.EditRole):
            if col_name == "item_id":
                return row.item_id
            elif col_name == "item_id2":
                return row.item_id2
            elif col_name == "item_name":
                return self.id_to_name.get(int(row.item_id), f"Unknown ({row.item_id})")
            elif col_name == "item_name2":
                return self.id_to_name.get(int(row.item_id2), f"Unknown ({row.item_id2})")
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        row = self.rows[index.row()]
        col_name = self.COLS[index.column()]
        try:
            ival = int(value)
            changed = False
            if col_name == "item_id":
                if row.item_id != ival:
                    row.item_id = ival
                    changed = True
            elif col_name == "item_id2":
                if row.item_id2 != ival:
                    row.item_id2 = ival
                    changed = True
            else:
                return False
            if changed:
                self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
                self.idsChanged.emit()
            return True
        except Exception:
            return False

    def begin_full_reset(self): self.beginResetModel()
    def end_full_reset(self): self.endResetModel()


class CatShopEditor(QDialog):
    """
    Road Cat Item Shop editor:
      - Reads entries via pointer 0xB10 until terminator (unk1 != 0xFFFFFFFF)
      - Shows: Item ID | Item Name | Item ID 2 | Item Name 2
      - Add/Delete rows
      - Has a counter spinbox (u16). It auto-syncs to the total number of items (not rows).
      - On Save: writes EOF block, updates pointer 0xB10, and writes u16 counter (c_unk3).
    """
    def __init__(self, mhfdat_path: str, mhfdat_parsed: dict, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Road Cat Item Shop")
        self.resize(1000, 640)

        # Background
        try:
            apply_dialog_background(self, image_name="bg2.jpg", opacity=0.65)
        except Exception:
            bg = QPixmap(str(ROOTDIR / "asset" / "bg2.jpg"))
            if not bg.isNull():
                bg = bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                tmp = QPixmap(bg.size()); tmp.fill(Qt.transparent)
                p = QPainter(tmp); p.setOpacity(0.65); p.drawPixmap(0, 0, bg); p.end()
                pal = self.palette(); pal.setBrush(QPalette.ColorRole.Window, QBrush(tmp)); self.setPalette(pal)

        # Window controls
        self.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint | Qt.WindowTitleHint
        )

        # Keep references
        self.mhfdat_path = mhfdat_path
        self.mhfdat_parsed = mhfdat_parsed or {}
        self.counters = self.mhfdat_parsed.get("counters")

        # Load items mapping
        self.id_to_name = load_item_names()

        parsed = parse_catshop(mhfdat_path) or CatShopParsed(rows=[])
        self.parsed = parsed

        # ----- UI -----
        root = QVBoxLayout(self)

        header = QLabel("Road Cat Item Shop", self)
        header.setAlignment(Qt.AlignCenter)
        header.setProperty("class", "header")
        root.addWidget(header)

        # Counter (u16) group
        grp = QGroupBox("Shop Counter", self)
        form = QFormLayout(grp)
        self.spn_count = QSpinBox(grp)
        self.spn_count.setRange(0, 65535)
        self.spn_count.setStyleSheet(EDITOR_TEXT_STYLE)
        self.spn_count.setToolTip("Auto-syncs to the total number of items (Item ID + Item ID 2 across all rows).")
        form.addRow("Total Items:", self.spn_count)
        root.addWidget(grp)

        # Table
        self.table = QTableView(self)
        self._style_table(self.table)
        root.addWidget(self.table, 1)

        # Model + delegates
        self.model = CatShopModel(self.parsed.rows, self.id_to_name, self)
        self.model.idsChanged.connect(self._update_counter_from_rows)
        self.table.setModel(self.model)
        # IDs are u16
        self.table.setItemDelegateForColumn(0, IntDelegate(0, 65535, self.table))
        self.table.setItemDelegateForColumn(2, IntDelegate(0, 65535, self.table))
        # name columns are read-only (no delegates needed)

        hv = self.table.horizontalHeader()
        hv.setSectionResizeMode(QHeaderView.ResizeToContents)
        hv.setStretchLastSection(True)
        hv.setDefaultAlignment(Qt.AlignCenter)

        # Buttons row
        row = QHBoxLayout()
        row.addStretch(1)

        self.btn_add = QPushButton("Add Row", self);  self.btn_add.clicked.connect(self._add_row)
        row.addWidget(self.btn_add)

        self.btn_del = QPushButton("Delete Selected", self); self.btn_del.clicked.connect(self._delete_selected)
        row.addWidget(self.btn_del)

        self.btn_save = QPushButton("Save", self); self.btn_save.clicked.connect(self._save)
        row.addWidget(self.btn_save)

        row.addStretch(1)
        root.addLayout(row)

        # Initial counter sync
        self._update_counter_from_rows()

    # ---------- helpers ----------
    def _style_table(self, tv: QTableView):
        tv.setAlternatingRowColors(True)
        tv.setSortingEnabled(False)
        tv.setSelectionBehavior(QAbstractItemView.SelectRows)
        tv.setSelectionMode(QAbstractItemView.SingleSelection)
        tv.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.EditKeyPressed
        )
        tv.verticalHeader().setVisible(True)
        tv.verticalHeader().setDefaultSectionSize(24)
        tv.setWordWrap(False)
        tv.setShowGrid(True)

    def _refresh_model(self):
        self.model.begin_full_reset()
        self.model.end_full_reset()
        self._update_counter_from_rows()

    def _computed_item_count(self) -> int:
        # Count non-zero IDs across both columns for each row
        total = 0
        for r in self.parsed.rows:
            if int(r.item_id) != 0:
                total += 1
            if int(r.item_id2) != 0:
                total += 1
        return total

    def _update_counter_from_rows(self):
        self.spn_count.blockSignals(True)
        self.spn_count.setValue(self._computed_item_count())
        self.spn_count.blockSignals(False)

    # ---------- actions ----------
    def _add_row(self):
        self.parsed.rows.append(CatShopItem(item_id=0, item_id2=0))
        self._refresh_model()

    def _delete_selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return
        r = idx.row()
        if 0 <= r < len(self.parsed.rows):
            del self.parsed.rows[r]
            self._refresh_model()

    def _save(self):
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Save mhfdat.bin", "mhfdat.bin", "Binary Files (*.bin)"
        )
        if not out_path:
            return
        try:
            # Enforce the counter to match the total number of items (not rows)
            computed = self._computed_item_count()
            # Reflect that in the spinbox (even if user typed something else)
            self.spn_count.setValue(computed)

            save_catshop(
                self.mhfdat_path,
                out_path,
                self.parsed,
                counters=self.counters,               # has .offset and CatShopItemCounter (c_unk3)
                counter_items_count=computed,         # u16 written to counters
                always_move_to_eof=True,
                eof_align=0x10,
                end_padding=0x400
            )
            QMessageBox.information(
                self, "Saved",
                "Cat Shop written to EOF, pointer (0xB10) updated, and counter synced to total items."
            )
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Failed to save Cat Shop:\n{e}")
