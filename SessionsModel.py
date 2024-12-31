from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt

class SessionsModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.workspace = None
        self._columns = ['Name', 'File']

    def assign_workspace(self, workspace):
        self.workspace = workspace

    def reset(self, active, data, columns):
        assert(False)
        self._data = data
        self._checked = active
        self._columns = columns
        self.layoutChanged.emit()

    def get_columns(self):
        return self._columns

    def cell_value(self, row, column):
        return self.workspace.sessions_def[row][column + 1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
                return self.cell_value(index.row(), index.column())
            if index.column() == 0 and role == Qt.ItemDataRole.CheckStateRole:
                return Qt.CheckState.Checked if self.workspace.sessions_def[index.row()][0] else Qt.CheckState.Unchecked

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            self.workspace.sessions_def[index.row()][index.column() + 1] = value
            return True
        if role == Qt.ItemDataRole.CheckStateRole:
            self.workspace.sessions_def[index.row()][0] = value > 0
            return True

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._columns[section]
        return super().headerData(section, orientation, role)

    def rowCount(self, index=None):
        return len(self.workspace.sessions_def) if self.workspace else 0

    def columnCount(self, index=None):
        return (len(self.workspace.sessions_def[0]) - 1) if self.workspace else 0

    def flags(self, index):
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable
        else:
            return Qt.ItemFlag.ItemIsSelectable|Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsEditable
