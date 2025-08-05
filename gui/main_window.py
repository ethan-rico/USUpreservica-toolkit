from PyQt6.QtWidgets import QMainWindow, QTabWidget
from gui.browser_tab import BrowserTab
from gui.export_tab import ExportTab
from gui.update_tab import UpdateTab
from gui.move_tab import MoveTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Preservica Toolkit")
        self.resize(1000, 700)

        tabs = QTabWidget()
        tabs.addTab(BrowserTab(), "Folder Browser")
        tabs.addTab(ExportTab(), "Export Metadata")
        tabs.addTab(UpdateTab(), "Update Metadata")
        tabs.addTab(MoveTab(), "Move Assets")

        self.setCentralWidget(tabs)
