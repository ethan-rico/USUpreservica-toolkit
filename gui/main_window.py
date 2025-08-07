from PyQt6.QtWidgets import QMainWindow, QTabWidget, QMenuBar, QMenu
from PyQt6.QtGui import QAction
from backend.preservica_client import PreservicaClient, logout_user
from gui.browser_tab import BrowserTab
from gui.export_tab import ExportTab
from gui.update_tab import UpdateTab
from gui.move_tab import MoveTab

class MainWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()

        self.export_tab = ExportTab(client)
        self.move_tab = MoveTab(client)
        self.browser_tab = BrowserTab(self.export_tab, self.move_tab, client)
        self.update_tab = UpdateTab(client)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.browser_tab, "Browser")
        self.tabs.addTab(self.export_tab, "Export")
        self.tabs.addTab(self.move_tab, "Move")
        self.tabs.addTab(self.update_tab, "Update")

        self.setCentralWidget(self.tabs)
        # Menu Bar
        menu_bar = self.menuBar()
        account_menu = menu_bar.addMenu("Account")

        logout_action = QAction("Log Out", self)
        logout_action.triggered.connect(logout_user)
        account_menu.addAction(logout_action)

        self.setWindowTitle("Preservica Toolkit")
        self.resize(1200, 800)

        # self.showMaximized()  # Uncomment this if you want it maximized on launch