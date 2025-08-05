from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTreeWidget, QTreeWidgetItem, QMessageBox
)
from backend.preservica_client import PreservicaClient
import pyPreservica as pyp


class BrowserTab(QWidget):
    def __init__(self):
        super().__init__()
        self.client = PreservicaClient().client

        self.layout = QVBoxLayout(self)

        # Top input row
        input_layout = QHBoxLayout()
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("Enter folder reference ID to start")
        self.load_button = QPushButton("Load Folder")
        self.load_button.clicked.connect(self.load_root_folder)
        input_layout.addWidget(QLabel("Start Folder:"))
        input_layout.addWidget(self.ref_input)
        input_layout.addWidget(self.load_button)

        # Folder tree view
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Preservica Folders & Assets")
        self.tree.itemExpanded.connect(self.load_children)

        self.layout.addLayout(input_layout)
        self.layout.addWidget(self.tree)

    def load_root_folder(self):
        folder_ref = self.ref_input.text().strip()
        if not folder_ref:
            QMessageBox.warning(self, "Missing ID", "Please enter a folder reference ID.")
            return

        try:
            folder = self.client.folder(folder_ref)
            self.tree.clear()
            root_item = QTreeWidgetItem([folder.title])
            root_item.setData(0, 1, folder.reference)
            self.tree.addTopLevelItem(root_item)
            root_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load folder:\n{e}")

    def load_children(self, item):
        # Don’t reload if already loaded
        if item.childCount() > 0 and item.child(0).data(0, 1) != "DUMMY":
            return

        item.takeChildren()

        folder_ref = item.data(0, 1)
        try:
            children = self.client.children(folder_ref)
            for child in children.results:
                label = f"{child.title} (Asset)" if isinstance(child, pyp.Asset) else child.title
                child_item = QTreeWidgetItem([label])
                child_item.setData(0, 1, child.reference)
                item.addChild(child_item)

                if isinstance(child, pyp.Folder):
                    # Add dummy to show expandable arrow
                    dummy = QTreeWidgetItem(["Loading..."])
                    dummy.setData(0, 1, "DUMMY")
                    child_item.addChild(dummy)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load children:\n{e}")
