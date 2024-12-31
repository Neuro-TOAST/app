import sys
import neon
import threading
import time
import json
import os.path as path
import argparse
from queue import Queue
from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QTabWidget, QLineEdit, QLabel
from PyQt6.QtWidgets import QComboBox, QStackedLayout, QMessageBox, QPlainTextEdit, QCheckBox, QFormLayout, QFileDialog
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPalette, QColor
from PyQt6 import QtWebEngineWidgets
from PyQt6 import QtCore, QtWidgets
import SessionsModel
import SubjectsModel
import Workspace
import pipeline

'''pip install PyQt6-WebEngine'''

class IdGenerator:
    def __init__(self):
        self.last = 0

    def id(self):
        self.last += 1
        return self.last

id_generator = IdGenerator()
menu_items = {}

class TreeModelItem(QTreeWidgetItem):
    def __init__(self, *a, item_id, config_item, **b):
        super(QTreeWidgetItem, self).__init__(*a, **b)
        self.id = item_id
        self.config_item = config_item
        self.config_item.tree_item = self


def inner_build_level(model_parent, dst_parent):
    level = []
    for model_child in model_parent.get_children():
        item = TreeModelItem([model_child.get_label()], item_id=id_generator.id(), config_item=model_child)
        menu_items[item.id] = item
        level.append(item)
        if dst_parent is not None:
            dst_parent.addChild(item)
        inner_build_level(model_child, item)
    return level

def create_tree_widget(window):
    tree = QTreeWidget()
    # tree.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
    tree.setColumnCount(3)
    tree.setHeaderLabels(['Parameter', 'Value', 'Run'])
    tree.header().resizeSection(0, 150)
    tree.header().resizeSection(1, 60)
    tree.header().resizeSection(2, 25)

    top_level = inner_build_level(global_pipeline, None)
    tree.insertTopLevelItems(0, top_level)
    tree.expandAll()

    for item in menu_items.values():
        if item.config_item.is_runnable():
            button = QtWidgets.QPushButton('Run')
            tree.setItemWidget(item, 2, button)
            button.clicked.connect((lambda _item, _button: lambda: window.clicked_run(_item, _button))(item, button))
    return tree

def set_tree_value(id_, value):
    if id_:
        if value != 'Select' and value:  # workaround, z neznameho duvodu se mi chybne prepisoval combobox
            menu_items[id_].config_item.set_value(value)

class MainWindow(QMainWindow):

    def open_workspace(self, workspace_file):
        if not path.isfile(workspace_file):
            error('Workspace file not found', f'Workspace file {workspace_file} was not found.')
        self.workspace_file = workspace_file
        self.update_title()
        self.workspace = Workspace.Workspace(self.workspace_file)
        self.sessions_model.assign_workspace = self.workspace
        if self.workspace.startup_subjects:
            self.subjects_model.reset(*SubjectsModel.load_tsv_subjects(self.workspace.startup_subjects, True))
        self.startup_pipeline_edit.setText(self.workspace.startup_pipeline)
        self.startup_subjects_edit.setText(self.workspace.startup_subjects)
        self.workdir_edit.setText(self.workspace.workdir)
        self.load_workspace_config()
        self.html_content.load(QUrl.fromLocalFile(self.workspace.src_jsapp_dir + '/intro.html'))  # TODO: pri otevreni noveho wrk resetovat
        # self.html_content.show()

    def __init__(self, workspace_file):
        super().__init__()

        self.signals_queue = Queue()
        self.into_thread_queue = Queue()

        self.selected_item_id = None

        self.create_menu_bar()
        self.create_pipeline_menu()

        menu = QVBoxLayout()
        menu.addWidget(self.tabs)
        menu.addLayout(self.create_settings_values())

        self.content_container = QTabWidget()
        self.content_container.setTabPosition(QTabWidget.TabPosition.North)

        self.content_console = QPlainTextEdit()
        # self.content_console.setReadOnly(True)

        self.html_content = QtWebEngineWidgets.QWebEngineView()

        # tabulka Subjects
        self.subjects_model = SubjectsModel.SubjectsModel()
        self.subjects_table = QtWidgets.QTableView()
        self.subjects_table.setModel(self.subjects_model)
        # self.subjects_table.resizeColumnsToContents()
        self.subjects_table.horizontalHeader().setStretchLastSection(True)

        def wrap_with_widget(ly):
            wd = QWidget()
            wd.setLayout(ly)
            return wd

        self.create_workspace_tab()

        self.content_container.addTab(wrap_with_widget(self.workspace_tab), 'Workspace')
        self.content_container.addTab(self.subjects_table, 'Subjects')
        self.content_container.addTab(self.content_console, 'Console')
        self.content_container.addTab(self.html_content, 'Result')

        layout = QHBoxLayout()
        layout.addLayout(menu, 1)
        layout.addWidget(self.content_container, 10)

        widget = QWidget()
        widget.setLayout(layout)
        self.setMinimumSize(QSize(800, 600))
        self.setCentralWidget(widget)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.process_signal)
        self.timer.start()

        # self.open_workspace('e:/Runtime/2024_07_01/BOND/bond01.workspace.json')
        self.open_workspace(workspace_file)

    def update_title(self):
        self.setWindowTitle('TOAST - ' + self.workspace_file)

    def create_workspace_tab(self):
        self.startup_pipeline_edit = QLineEdit(self)
        self.startup_subjects_edit = QLineEdit(self)
        self.workdir_edit = QLineEdit(self)

        self.startup_pipeline_edit.textEdited.connect(self.startup_pipeline_edited)
        self.startup_subjects_edit.textEdited.connect(self.startup_subjects_edited)
        self.workdir_edit.textEdited.connect(self.workdir_edited)

        form1 = QFormLayout()
        form1.addRow('Startup Pipeline:', self.startup_pipeline_edit)
        form1.addRow('Startup Subjects:', self.startup_subjects_edit)
        form1.addRow('Workdir:', self.workdir_edit)

        self.sessions_table = QtWidgets.QTableView()
        self.sessions_model = SessionsModel.SessionsModel()
        self.sessions_table.setModel(self.sessions_model)
        self.sessions_table.horizontalHeader().setStretchLastSection(True)

        self.workspace_tab = QVBoxLayout()
        self.workspace_tab.addLayout(form1)
        self.workspace_tab.addWidget(self.sessions_table)

    def startup_pipeline_edited(self):
        self.workspace.startup_pipeline = self.startup_pipeline_edit.text()

    def startup_subjects_edited(self):
        self.workspace.startup_subjects = self.startup_subjects_edit.text()

    def workdir_edited(self):
        self.workspace.workdir = self.workdir_edit.text()

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        menu_workspace = menu_bar.addMenu('Workspace')
        action_workspace_open = menu_workspace.addAction('Open')
        action_workspace_open.triggered.connect(self.menu_workspace_open)
        action_workspace_save = menu_workspace.addAction('Save')
        action_workspace_save.triggered.connect(self.menu_workspace_save)
        action_workspace_save_as = menu_workspace.addAction('Save As')
        action_workspace_save_as.triggered.connect(self.menu_workspace_save_as)
        menu_config = menu_bar.addMenu('Config')
        action_menu_new = menu_config.addAction('New')
        action_menu_open = menu_config.addAction('Open')
        action_menu_open.triggered.connect(self.menu_config_open)
        action_menu_save = menu_config.addAction('Save')
        action_menu_save.triggered.connect(self.menu_config_save)
        action_menu_save_as = menu_config.addAction('Save As')
        menu_subjects = menu_bar.addMenu('Subjects')
        menu_subjects.addAction('New')
        action_subjects_open = menu_subjects.addAction('Open')
        action_subjects_open.triggered.connect(self.menu_subjects_open)
        menu_subjects.addAction('Save')
        action_subjects_save_as = menu_subjects.addAction('Save As')
        action_subjects_save_as.triggered.connect(self.menu_subjects_save_as)
        menu_analysis = menu_bar.addMenu('Analysis')
        action_analysis_run = menu_analysis.addAction('Run')
        action_analysis_run.triggered.connect(self.menu_run)

    def create_pipeline_menu(self):
        tree = create_tree_widget(self)
        tree.itemClicked.connect(self.onItemClicked)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.addTab(tree, 'Pipeline')
        # self.tabs.addTab(None, 'Variables')

        self.tabs.setFixedWidth(300)
        self.tabs.setFixedHeight(600)

    def create_settings_values(self):

        # label = QLabel('Value:')
        # label.setBuddy(self._test_value)
        # label.move(10, 320)
        # self._test_value.move(70, 320)

        # readonly
        proxy_readonly = QtWidgets.QWidget()
        label = QLabel('Item is not editable', proxy_readonly)

        # numeric
        proxy_num = QtWidgets.QWidget()
        layout_num = QVBoxLayout(proxy_num)
        self._test_value = QLineEdit()
        layout_num.addWidget(self._test_value)
        button = QPushButton('Save')
        button.clicked.connect(self.save_button_clicked)
        layout_num.addWidget(button)

        # combo
        proxy_combo = QtWidgets.QWidget()
        layout_combo = QVBoxLayout(proxy_combo)
        self.value_combo = QComboBox(proxy_combo)
        self.value_combo.currentTextChanged.connect(self.combo_changed)
        layout_combo.addWidget(self.value_combo)

        self.value_container = QStackedLayout()
        self.value_container.addWidget(proxy_readonly)
        self.value_container.addWidget(proxy_num)
        self.value_container.addWidget(proxy_combo)
        self.value_container.setCurrentIndex(0)

        # container = QWidget()
        # container.setLayout(layout)
        return self.value_container

    def onItemClicked(self, it, col):
        # TODO: focus na edit
        # self._test_value.setText(it.text(col))
        self.selected_item_id = it.id
        if it.config_item.type.value_type == 'readonly':
            self.value_container.setCurrentIndex(0)
            if it.config_item.runnable:
                it.config_item.runnable.show_html(self)
        elif it.config_item.type.value_type == 'number':
            self._test_value.setText(str(it.config_item.value) if it.config_item.value is not None else '')
            self.value_container.setCurrentIndex(1)
        elif it.config_item.type.value_type == 'text':
            self._test_value.setText(it.config_item.value if it.config_item.value is not None else '')
            self.value_container.setCurrentIndex(1)
        elif it.config_item.type.value_type == 'combo':
            self.value_combo.clear()
            for k, option in enumerate(it.config_item.type.options):
                self.value_combo.addItem(option)
                if it.config_item.value == option:
                    self.value_combo.setCurrentIndex(k)
            self.value_container.setCurrentIndex(2)

    def save_button_clicked(self):
        text = self._test_value.text()
        set_tree_value(self.selected_item_id, text)

    def combo_changed(self, text):
        set_tree_value(self.selected_item_id, text)

    def menu_config_save(self):
        def process_level(model_parent):
            level = {}
            for model_child in model_parent.get_children():
                if model_child.get_children():
                    level[model_child.get_label()] = process_level(model_child)
                else:
                    level[model_child.get_label()] = model_child.value
            return level

        values = process_level(global_pipeline)
        print(values)
        print(neon.encode(values))

    def open_pipeline(self, params):
        def find_value(_params, config_item):
            curr = config_item
            keys = []
            while curr.parent is not None:  # zamerne nedojdu az na parenta, ten je jen virtualni
                keys.append(curr.get_id())
                curr = curr.parent
            keys.reverse()
            p = _params
            for key in keys:
                p = p[key]
            return p

        def process_level(model_parent, params):
            for model_child in model_parent.get_children():
                if model_child.get_children():
                    process_level(model_child, params)
                else:
                    model_child.set_value(find_value(params, model_child))

        process_level(global_pipeline, params)

    def menu_config_open(self):
        raise ValueError('Open new config is not supported now.')
        self.open_pipeline(params)

    def load_workspace_config(self):
        '''Vola se pri otevreni workspace, otevira pipeline, pokud je definovana ve workspace.'''
        if self.workspace.startup_pipeline:
            if path.isfile(self.workspace.startup_pipeline):
                with open(self.workspace.startup_pipeline) as reader:
                    params = json.load(reader)
                self.open_pipeline(params)
            else:
                error('Config file not found', f'Config file {self.workspace.startup_pipeline} was not found.')

    def menu_subjects_open(self):
        src = 'w:/Data/Balkan/MR/participants.tsv'
        self.subjects_model.reset(*load_tsv_subjects(src, True))

    def menu_subjects_save_as(self):
        dst = 'e:/Runtime/2024_01_01/toast_participant.tsv'
        self.subjects_model.save_into(dst)

    def menu_workspace_open(self):
        selected_file = QFileDialog.getOpenFileName(self, 'Open', '', 'Workspace (*.workspace.json)')
        print(selected_file)
        # self.workspace.save(self.workspace_file)

    def menu_workspace_save(self):
        self.workspace.save(self.workspace_file)

    def menu_workspace_save_as(self):
        selected_file = QFileDialog.getSaveFileName(self, 'Save As', 'workspace1.workspace.json', 'Workspace (*.workspace.json)')
        if selected_file[0]:
            self.workspace.save(selected_file[0])
            self.workspace_file = selected_file[0]
            self.update_title()

    def print(self, message):
        self.content_console.insertPlainText(message + '\n')
        scrollbar = self.content_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def setTabsIndex(self, index):
        self.content_container.setCurrentIndex(index)

    def ui_open_page(self, address):
        self.html_content.load(QUrl.fromLocalFile(address))
        self.html_content.show()

    def process_signal(self):
        while not self.signals_queue.empty():
            method, message = self.signals_queue.get()
            if method == 'print':
                self.print(message)
            elif method == 'setTabsIndex':
                self.setTabsIndex(message)
            elif method == 'ui_open_page':
                self.ui_open_page(message)
            else:
                raise Exception(f'Unknown signal {method}')

    def complete_config(self):
        return {item.get_id(): item.get_params() for item in global_pipeline.children}

    def run_step(self, menu_step, button=None):
        params = menu_step.get_params()
        inst = menu_step.runnable(self)

        def inner_fce():
            if button is not None:
                button.setText('Runnig')
            while not self.into_thread_queue.empty():
                self.into_thread_queue.get()
            inst.exec(self.complete_config(), self.subjects_model)
            if button is not None:
                button.setText('Run')
            self.thread_finished()

        thread = threading.Thread(target=inner_fce)
        thread.start()
        self.content_container.setCurrentIndex(2)

    def clicked_run(self, item, button):
        '''Spusti analyzu pri kliku na step v levem menu'''
        print(item.config_item.get_label())
        self.run_step(item.config_item, button=button)

    def menu_run(self):
        '''Spusti analyzu z horniho menu'''
        if self.selected_item_id is None:
            error('No step is selected', '')
        elif not menu_items[self.selected_item_id].config_item.is_runnable():
            label = menu_items[self.selected_item_id].config_item.get_label()
            error(f'Selected step \'{label}\' is not runnable.', '')
        else:
            menu_step = menu_items[self.selected_item_id].config_item
            self.run_step(menu_step)

    def thread_finished(self):
        print('Thread finished')

def error(title, message):
    msg = QMessageBox()
    msg.setText(title)
    msg.setInformativeText(message)
    msg.setWindowTitle('Error')
    msg.exec()


global_pipeline = pipeline.define_pipeline()

parser = argparse.ArgumentParser(description='Toast arguments')
parser.add_argument('workspace')
args = parser.parse_args()

app = QApplication(sys.argv)
window = MainWindow(args.workspace)
window.setGeometry(100, 100, 1200, 800)
window.show()

app.exec()
