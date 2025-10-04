# ui/medalshop_editor.py
from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QGroupBox, QFormLayout,
    QTableView, QHeaderView, QAbstractItemView, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QPixmap, QPainter, QPalette, QBrush, QColor

from core.paths import ROOTDIR
from ui.utils import apply_dialog_background
from core.medalshop_io import parse_medal_shop, save_medal_shop, MedalItem
from .models import IntDelegate
from ui.catshop_editor import ItemListDialog, load_item_names
from core.json_io import medalshop_to_json, medalshop_from_json


class MedalShopModel(QAbstractTableModel):
    COLS = ["item", "item_name", "flag1", "flag2", "price"]
    HEADERS = ["Item ID", "Item Name", "Flag 1 (set to 4)", "Flag 2 (set to 1)", "Price"]

    counter_changed = Signal()

    def __init__(self, rows: list[MedalItem], id_to_name: dict[int, str], parent=None):
        super().__init__(parent)
        self.rows = rows
        self.id_to_name = id_to_name

    def rowCount(self, _=QModelIndex()):
        return len(self.rows)

    def columnCount(self, _=QModelIndex()):
        return len(self.COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        if role == Qt.DisplayRole and orientation == Qt.Vertical:
            return section + 1

        # Align only the "Price" header to the left
        if role == Qt.TextAlignmentRole and orientation == Qt.Horizontal:
            if self.COLS[section] == "price":
                return Qt.AlignLeft | Qt.AlignVCenter
            return Qt.AlignHCenter | Qt.AlignVCenter

        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        name = self.COLS[index.column()]
        # Only Item ID and Price editable; flags are fixed
        editable = name in ("item", "price")
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return base | (Qt.ItemIsEditable if editable else Qt.NoItemFlags)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        r = self.rows[index.row()]
        name = self.COLS[index.column()]

        if role in (Qt.DisplayRole, Qt.EditRole):
            if name == "item":
                return r.item
            elif name == "flag1":
                return r.random
            elif name == "flag2":
                return r.quantity
            elif name == "price":
                return r.price
            elif name == "item_name":
                return self.id_to_name.get(int(r.item), f"Unknown ({r.item})")

        if role == Qt.ForegroundRole:
            if name == "item":
                return QColor("cyan")

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        name = self.COLS[index.column()]
        r = self.rows[index.row()]
        try:
            ival = int(value)
        except ValueError:
            return False

        if name == "item":
            r.item = max(0, ival)
        elif name == "price":
            r.price = max(0, ival)
        else:
            return False

        # Always enforce flag values
        r.random = 4
        r.quantity = 1

        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        self.counter_changed.emit()
        return True

    def begin_full_reset(self):
        self.beginResetModel()

    def end_full_reset(self):
        self.endResetModel()
        self.counter_changed.emit()


class MedalShopEditor(QDialog):
    def __init__(self, mhfdat_path: str, mhfdat_parsed: dict, *, parent=None):
        super().__init__(parent=parent)
        self.setModal(True)
        self.setWindowTitle("Tower Medal Shop Editor")
        self.resize(900, 650)

        try:
            apply_dialog_background(self, image_name="bg2.jpg", opacity=0.65)
        except Exception:
            bg = QPixmap(str(ROOTDIR / "asset" / "bg2.jpg"))
            if not bg.isNull():
                bg = bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                tmp = QPixmap(bg.size())
                tmp.fill(Qt.transparent)
                p = QPainter(tmp)
                p.setOpacity(0.65)
                p.drawPixmap(0, 0, bg)
                p.end()
                pal = self.palette()
                pal.setBrush(QPalette.ColorRole.Window, QBrush(tmp))
                self.setPalette(pal)

        self.mhfdat_path = mhfdat_path
        self.parsed = parse_medal_shop(mhfdat_path)
        if self.parsed is None:
            QMessageBox.critical(self, "Error", "Failed to parse Medal Shop data.")
            self.close()
            return

        self.id_to_name = load_item_names()
        main = QVBoxLayout(self)

        # Header
        header = QLabel("Tower Medal Shop", self)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            color: cyan;
            font-weight: bold;
            font-size: 24px;      /* <- change size */
            padding: 8px 0;       /* <- extra height */
        """)
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(20)
        glow.setColor(QColor("#00FFFF"))
        glow.setOffset(0, 0)
        header.setGraphicsEffect(glow)
        main.addWidget(header)

        # Counter group
        grp = QGroupBox("Shop Counter", self)
        form = QFormLayout(grp)
        grp.setStyleSheet("color: cyan;")
        label = QLabel("Total Items:", self)
        label.setStyleSheet("color: #66CCFF")
        self.spn_counter = QLabel("0", grp)
        self.spn_counter.setStyleSheet("color: cyan; font-weight: bold;")
        form.addRow(label, self.spn_counter)
        main.addWidget(grp)

        # Table
        self.table = QTableView(self)
        self._style_table(self.table)
        main.addWidget(self.table, 1)

        self.model = MedalShopModel(self.parsed.rows, self.id_to_name, self)
        self.table.setModel(self.model)
        self.model.counter_changed.connect(self._refresh_counter)

        # Delegates
        self.table.setItemDelegateForColumn(0, IntDelegate(0, 0xFFFF, self.table))  # Item
        self.table.setItemDelegateForColumn(4, IntDelegate(0, 0xFFFF, self.table))  # Price

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setStretchLastSection(True)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_add = QPushButton("Add Entry", self)
        self.btn_add.clicked.connect(self._add_entry)
        btn_row.addWidget(self.btn_add)

        self.btn_remove = QPushButton("Remove Selected", self)
        self.btn_remove.clicked.connect(self._remove_selected)
        btn_row.addWidget(self.btn_remove)

        self.btn_info = QPushButton("Items List", self)
        self.btn_info.clicked.connect(self._show_items_list)
        btn_row.addWidget(self.btn_info)

        self.btn_export_json = QPushButton("Export JSON", self)
        self.btn_export_json.clicked.connect(self._export_json)
        btn_row.addWidget(self.btn_export_json)

        self.btn_import_json = QPushButton("Import JSON", self)
        self.btn_import_json.clicked.connect(self._import_json)
        btn_row.addWidget(self.btn_import_json)

        self.btn_save = QPushButton("Save", self)
        self.btn_save.clicked.connect(self._save)
        btn_row.addWidget(self.btn_save)

        btn_row.addStretch(1)
        main.addLayout(btn_row)

        self._refresh_counter()

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

    def _refresh_counter(self):
        total = sum(1 for r in self.parsed.rows if r.item != 0)
        self.spn_counter.setText(str(total))

    def _add_entry(self):
        self.parsed.rows.append(MedalItem(item=0, random=4, quantity=1, price=1))
        self.model.begin_full_reset()
        self.model.end_full_reset()

    def _remove_selected(self):
        idx = self.table.currentIndex()
        if not idx.isValid():
            return
        r = idx.row()
        if 0 <= r < len(self.parsed.rows):
            del self.parsed.rows[r]
            self.model.begin_full_reset()
            self.model.end_full_reset()

    def _show_items_list(self):
        if not self.id_to_name:
            QMessageBox.information(self, "No Items Mapping", "No item names loaded from Items.xlsx.")
            return
        dlg = ItemListDialog(self.id_to_name, self)
        dlg.exec()

    def _export_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export MedalShop JSON", "medalshop.json", "JSON Files (*.json)")
        if not path:
            return
        try:
            s = medalshop_to_json(self.parsed)
            with open(path, "w", encoding="utf-8") as f:
                f.write(s)
            QMessageBox.information(self, "Exported", f"Exported MedalShop JSON to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export JSON:\n{e}")

    def _import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import MedalShop JSON", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                s = f.read()
            new_parsed = medalshop_from_json(s)
            # Always enforce flags
            for mi in new_parsed.rows:
                mi.random = 4
                mi.quantity = 1
            self.parsed = new_parsed
            self.model.rows = self.parsed.rows
            self.model.begin_full_reset()
            self.model.end_full_reset()
            self._refresh_counter()
            QMessageBox.information(self, "Imported", f"Imported MedalShop JSON from {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import JSON:\n{e}")

    def _save(self):
        for mi in self.parsed.rows:
            if mi.price <= 0:
                QMessageBox.warning(self, "Invalid Entry", "Cannot save: all entries must have price > 0.")
                return
            # Enforce flags before writing
            mi.random = 4
            mi.quantity = 1

        out_path, _ = QFileDialog.getSaveFileName(self, "Save mhfdat.bin", "medalshop.bin", "Binary Files (*.bin)")
        if not out_path:
            return
        try:
            save_medal_shop(mhfdat_in=self.mhfdat_path, mhfdat_out=out_path, parsed=self.parsed)
            QMessageBox.information(self, "Saved", "Medal Shop data saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save Medal Shop:\n{e}")
