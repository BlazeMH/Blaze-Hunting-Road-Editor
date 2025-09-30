
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate, QSpinBox, QDoubleSpinBox
from PySide6.QtGui import QPainter
from .styles import app_stylesheet  # just to ensure module is imported when needed
# ---- import fallback so this module also works if run outside project root ----
try:
    from core.constants import MONSTERS  # normal import when run from project root
except Exception:  # pragma: no cover
    import sys, pathlib
    sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))  # add project root
    from core.constants import MONSTERS
# ----------------------------------------------------------------------------

# Cyan dropdown text for combo editors
DROPDOWN_STYLE = """
QComboBox { 
    color: cyan;
}
QComboBox QAbstractItemView { 
    color: cyan;
    background: rgba(5,20,45,0.92);
    selection-background-color: #2f6d9b;
    selection-color: cyan;
    outline: 0;
}
"""

# Cyan text for editors while editing (spinboxes / line edits)
EDITOR_TEXT_STYLE = """
QSpinBox, QDoubleSpinBox, QLineEdit {
    color: cyan;
}
"""

class FloorStatsModel(QAbstractTableModel):
    COLS = ["FloorNumber", "SpawnTableUsed", "Unk0", "PointMulti1", "PointMulti2", "FinalLoop"]
    def __init__(self, rows, parent=None):
        super().__init__(parent); self.rows = rows
    def rowCount(self, _=QModelIndex()): return len(self.rows)
    def columnCount(self, _=QModelIndex()): return len(self.COLS)
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole: return None
        return self.COLS[section] if orientation == Qt.Horizontal else section
    def flags(self, index):
        if not index.isValid(): return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        obj = self.rows[index.row()]; col = self.COLS[index.column()]
        val = getattr(obj, col)
        if role in (Qt.DisplayRole, Qt.EditRole): return val
        return None
    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid(): return False
        obj = self.rows[index.row()]; col = self.COLS[index.column()]
        try:
            if col in ("PointMulti1","PointMulti2"): value = float(value)
            else: value = int(value)
            setattr(obj, col, value)
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        except Exception:
            return False


class SpawnTableModel(QAbstractTableModel):
    COLS = ["FirstMonsterID","FirstMonsterVariant","SecondMonsterID","SecondMonsterVariant",
            "MonstersStatTable","MapZoneOverride","SpawnWeighting","AdditionalFlag"]
    def __init__(self, rows, parent=None):
        super().__init__(parent); self.rows = rows
    def rowCount(self, _=QModelIndex()): return len(self.rows)
    def columnCount(self, _=QModelIndex()): return len(self.COLS)
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole: return None
        if orientation == Qt.Horizontal:
            name = self.COLS[section]
            return "Bonus Spawns" if name == "MapZoneOverride" else name
        return section
    def flags(self, index):
        if not index.isValid(): return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        obj = self.rows[index.row()]; col = self.COLS[index.column()]
        val = getattr(obj, col)
        if role in (Qt.DisplayRole, Qt.EditRole):
            if col in ("FirstMonsterID","SecondMonsterID"):
                try: return MONSTERS[val]
                except Exception: return val
            return val
        return None
    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid(): return False
        obj = self.rows[index.row()]; col = self.COLS[index.column()]
        try:
            if col in ("FirstMonsterID","SecondMonsterID"):
                if isinstance(value, str):
                    value = MONSTERS.index(value) if not value.isdigit() else int(value)
            else:
                value = int(value)
            setattr(obj, col, value)
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        except Exception:
            return False


class MonsterDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        cb = QComboBox(parent)
        cb.addItems(MONSTERS)
        cb.setEditable(False)  # dropdown ONLY
        cb.setInsertPolicy(QComboBox.NoInsert)
        cb.setStyleSheet(DROPDOWN_STYLE)
        return cb
    def setEditorData(self, editor, index):
        current = index.model().data(index, Qt.EditRole)
        try:
            if isinstance(current, int):
                editor.setCurrentIndex(current if 0 <= current < len(MONSTERS) else 0)
            else:
                editor.setCurrentIndex(MONSTERS.index(str(current)))
        except Exception:
            editor.setCurrentIndex(0)
    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentIndex(), Qt.EditRole)


class IntDelegate(QStyledItemDelegate):
    def __init__(self, minimum=0, maximum=2**31-1, parent=None):
        super().__init__(parent); self.min = minimum; self.max = maximum
    def createEditor(self, parent, option, index):
        sb = QSpinBox(parent)
        sb.setRange(self.min, self.max)
        sb.setFrame(False)
        sb.setStyleSheet(EDITOR_TEXT_STYLE)
        return sb
    def setEditorData(self, editor, index):
        try: editor.setValue(int(index.model().data(index, Qt.EditRole)))
        except Exception: editor.setValue(self.min)
    def setModelData(self, editor, model, index):
        model.setData(index, editor.value(), Qt.EditRole)


class FloatDelegate(QStyledItemDelegate):
    def __init__(self, minimum=-1e9, maximum=1e9, step=0.1, decimals=3, parent=None):
        super().__init__(parent); self.min=minimum; self.max=maximum; self.step=step; self.decimals=decimals
    def createEditor(self, parent, option, index):
        dsb = QDoubleSpinBox(parent)
        dsb.setRange(self.min, self.max)
        dsb.setDecimals(self.decimals)
        dsb.setSingleStep(self.step)
        dsb.setFrame(False)
        dsb.setStyleSheet(EDITOR_TEXT_STYLE)
        return dsb
    def setEditorData(self, editor, index):
        try: editor.setValue(float(index.model().data(index, Qt.EditRole)))
        except Exception: editor.setValue(0.0)
    def setModelData(self, editor, model, index):
        model.setData(index, editor.value(), Qt.EditRole)


class EnumDelegate(QStyledItemDelegate):
    def __init__(self, items, parent=None):
        super().__init__(parent); self.items = items
    def createEditor(self, parent, option, index):
        cb = QComboBox(parent)
        for label, _ in self.items:
            cb.addItem(label)
        cb.setEditable(False)
        cb.setInsertPolicy(QComboBox.NoInsert)
        cb.setStyleSheet(DROPDOWN_STYLE)
        return cb
    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.EditRole)
        try:
            v = int(val) if not isinstance(val, int) else val
            for i, (_, item_v) in enumerate(self.items):
                if v == item_v:
                    editor.setCurrentIndex(i)
                    return
        except Exception:
            pass
        editor.setCurrentIndex(0)
    def setModelData(self, editor, model, index):
        i = editor.currentIndex()
        value = self.items[i][1] if 0 <= i < len(self.items) else self.items[0][1]
        model.setData(index, value, Qt.EditRole)
