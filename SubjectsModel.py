from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt
import csv

class SubjectsModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._data = []
        self._checked = []
        self._columns = []

    def reset(self, active, data, columns):
        self._data = data
        self._checked = active
        self._columns = columns
        self.layoutChanged.emit()

    def get_columns(self):
        return self._columns

    def cell_value(self, row, column):
        return self._data[row][column]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
                value = self.cell_value(index.row(), index.column())
                return value
            if index.column() == 0 and role == Qt.ItemDataRole.CheckStateRole:
                return Qt.CheckState.Checked if self._checked[index.row()] else Qt.CheckState.Unchecked

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            self._data[index.row()][index.column()] = value
            return True
        if role == Qt.ItemDataRole.CheckStateRole:
            self._checked[index.row()] = value
            return True

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._columns[section]
        return super().headerData(section, orientation, role)

    def rowCount(self, index=None):
        return len(self._data)

    def columnCount(self, index=None):
        return len(self._data[0]) if self._data else 0

    def flags(self, index):
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable
        else:
            return Qt.ItemFlag.ItemIsSelectable|Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsEditable

    def get_active_subjs(self):
        return [line[0] for k, line in enumerate(self._data) if self._checked[k]]

    def get_active_rows(self):
        return [(line[0], line) for k, line in enumerate(self._data) if self._checked[k]]

    def save_into(self, dst):
        with open(dst, 'w') as writer:
            writer.write('active')
            for col in range(self.columnCount()):
                writer.write('\t')
                writer.write(self._columns[col])
            writer.write('\n')
            for row in range(self.rowCount()):
                writer.write('1' if self._checked[row] else '0')
                for col in range(self.columnCount()):
                    writer.write('\t')
                    writer.write(self.cell_value(row, col))
                writer.write('\n')

def load_tsv_subjects(src, first_line_caption = True):
    with open(src) as reader:
        data = []
        for line in csv.reader(reader, delimiter='\t'):
            data.append(line)
        if first_line_caption:
            columns = data[0]
            data = data[1:]
        else:
            columns = [str(k) for k in range(len(data[0]))]

        if columns[0] == 'active':
            columns.pop(0)
            active = []
            for line in data:
                active.append(int(line.pop(0)))
        else:
            active = [True for _ in data]

        return active, data, columns
