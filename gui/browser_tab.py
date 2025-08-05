# gui/browser_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QHBoxLayout, QFileDialog, QInputDialog, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt
from backend.preservica_client import PreservicaClient
import pyPreservica as pyp
import xml.etree.ElementTree as ET
import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

class BrowserTab(QWidget):
    def __init__(self, export_tab, move_tab, client):
        super().__init__()
        self.export_tab = export_tab
        self.move_tab = move_tab
        self.client = client

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Preservica Folders and Assets")
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.itemExpanded.connect(self.load_children)
        self.layout.addWidget(self.tree)

        # Action buttons
        button_layout = QHBoxLayout()
        self.export_button = QPushButton("Export Metadata for Selected")
        self.export_button.clicked.connect(self.export_metadata_from_selection)
        self.layout.addWidget(self.export_button)

        self.move_button = QPushButton("Move Assets")
        self.move_button.clicked.connect(self.move_selected_assets)
        self.layout.addWidget(self.move_button)

        self.layout.addLayout(button_layout)

        # Load starting folder
        self.ask_for_starting_folder()

        # Load status bar when moving
        self.status_bar = QStatusBar()
        self.layout.addWidget(self.status_bar)

    def ask_for_starting_folder(self):
        ref_id, ok = QInputDialog.getText(self, "Start Folder", "Enter folder reference ID:")
        if ok and ref_id.strip():
            self.load_folder(ref_id.strip())

    def load_folder(self, ref_id):
        try:
            folder = self.client.folder(ref_id)
            item = QTreeWidgetItem([folder.title or "Untitled Folder"])
            item.setData(0, Qt.ItemDataRole.UserRole, folder.reference)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, "FOLDER")
            item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            self.tree.addTopLevelItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load folder: {e}")

    def load_children(self, item):
        # Prevent reloading
        if item.childCount() > 0 and item.child(0).data(0, Qt.ItemDataRole.UserRole):
            return

        item.takeChildren()
        ref_id = item.data(0, Qt.ItemDataRole.UserRole)

        try:
            children = self.client.children(ref_id)
            for child in children.results:
                label = f"{child.title or 'Untitled'}"
                child_item = QTreeWidgetItem([label])
                child_item.setData(0, Qt.ItemDataRole.UserRole, child.reference)
                if isinstance(child, pyp.Folder):
                    child_item.setData(0, Qt.ItemDataRole.UserRole + 1, "FOLDER")
                    child_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                else:
                    child_item.setData(0, Qt.ItemDataRole.UserRole + 1, "ASSET")
                item.addChild(child_item)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load children: {e}")

    def get_selected_items(self):
        selected = self.tree.selectedItems()
        refs = []
        for item in selected:
            ref_id = item.data(0, Qt.ItemDataRole.UserRole)
            ref_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if ref_id:
                refs.append((ref_id, ref_type))
        return refs

    def export_metadata_from_selection(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select one or more items to export.")
            return

        refs = []
        for item in selected_items:
            ref = item.data(0, Qt.ItemDataRole.UserRole)
            if ref:
                refs.append(ref)

        # Ask for export path
        export_path, _ = QFileDialog.getSaveFileName(self, "Save Metadata", filter="Excel Files (*.xlsx)")
        if not export_path:
            return
        if not export_path.endswith(".xlsx"):
            export_path += ".xlsx"

        # Start the export via ExportTab
        self.export_tab.start_export_with_refs(refs, export_path)



    def move_selected_assets(self):
        selected_refs = [
            item.data(0, Qt.ItemDataRole.UserRole)
            for item in self.tree.selectedItems()
            if item.data(0, Qt.ItemDataRole.UserRole)
        ]

        if not selected_refs:
            QMessageBox.warning(self, "No Selection", "Please select one or more assets or folders to move.")
            return

        destination_ref, ok = QInputDialog.getText(self, "Destination Folder", "Enter destination folder reference ID:")
        if not ok or not destination_ref.strip():
            return

        destination_ref = destination_ref.strip()

        # Switch to Move tab and start move
        self.parentWidget().parentWidget().setCurrentIndex(2)  # index of Move tab in QTabWidget
        self.move_tab.move_items(selected_refs, destination_ref)


        def set_tabs(self, export_tab, move_tab):
            self.export_tab = export_tab
            self.move_tab = move_tab
