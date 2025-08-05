# gui/browser_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QHBoxLayout, QFileDialog, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from backend.preservica_client import PreservicaClient
import pyPreservica as pyp
import xml.etree.ElementTree as ET
import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

class BrowserTab(QWidget):
    def __init__(self):
        super().__init__()
        self.client = PreservicaClient().client

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

        export_path, _ = QFileDialog.getSaveFileName(self, "Save Metadata", filter="Excel Files (*.xlsx)")
        if not export_path:
            return
        if not export_path.endswith(".xlsx"):
            export_path += ".xlsx"

        rows = []
        fieldnames = {"reference", "title", "type", "qdc_xml"}

        for item in selected_items:
            ref = item.data(0, Qt.ItemDataRole.UserRole)
            if not ref:
                continue

            # Try to load asset or folder
            try:
                entity = self.client.asset(ref)
                etype = "ASSET"
            except Exception:
                try:
                    entity = self.client.folder(ref)
                    etype = "FOLDER"
                except Exception:
                    continue  # skip invalid refs

            row = {
                "reference": entity.reference,
                "title": entity.title,
                "type": etype,
                "qdc_xml": ""
            }

            for url, schema in (entity.metadata or {}).items():
                if "dc" in schema.lower():
                    try:
                        xml = self.client.metadata(url).strip()
                        row["qdc_xml"] = xml
                        root = ET.fromstring(xml)
                        ns = {
                            "dc": "http://purl.org/dc/elements/1.1/",
                            "dcterms": "http://purl.org/dc/terms/"
                        }
                        counts = {}
                        for prefix in ns:
                            for elem in root.findall(f".//{{{ns[prefix]}}}*"):
                                tag = elem.tag.split("}")[-1]
                                value = (elem.text or "").strip()
                                if not value:
                                    continue
                                base = f"dc:{tag}"
                                count = counts.get(base, 0)
                                col = base if count == 0 else f"{base}.{count}"
                                row[col] = value
                                fieldnames.add(col)
                                counts[base] = count + 1
                    except ET.ParseError:
                        continue

            rows.append(row)

        # Write to Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Metadata"

        headers = sorted(fieldnames - {"reference", "title", "type"})
        final_headers = ["reference", "title", "type"] + headers
        ws.append(final_headers)

        for i, header in enumerate(final_headers, 1):
            col_letter = get_column_letter(i)
            ws[f"{col_letter}1"].font = Font(bold=True)

        for row_data in rows:
            row = [row_data.get(h, "") for h in final_headers]
            ws.append(row)

        wb.save(export_path)

        QMessageBox.information(self, "Export Complete", f"Metadata exported to:\n{export_path}")

    def move_selected_assets(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select one or more assets to move.")
            return

        destination_ref, ok = QInputDialog.getText(self, "Destination Folder", "Enter destination folder reference ID:")
        if not ok or not destination_ref.strip():
            return
        destination_ref = destination_ref.strip()

        # Validate destination folder
        try:
            destination_folder = self.client.folder(destination_ref)
        except Exception as e:
            QMessageBox.critical(self, "Invalid Destination", f"Could not find folder:\n{e}")
            return

        moved = 0
        skipped = []

        for item in selected_items:
            ref = item.data(0, Qt.ItemDataRole.UserRole)
            ref_type = item.data(0, Qt.ItemDataRole.UserRole + 1)

            if not ref or ref_type != "ASSET":
                skipped.append(ref)
                continue

            try:
                asset = self.client.asset(ref)
                self.client.move(asset, destination_folder)  # <-- Correct method
                moved += 1
            except Exception as e:
                skipped.append(ref)

        msg = f"Moved {moved} asset(s) to folder: {destination_folder.title} ({destination_folder.reference})"
        if skipped:
            msg += f"\n\nSkipped {len(skipped)} item(s) (likely not assets)."

        QMessageBox.information(self, "Move Complete", msg)
        self.tree.clearSelection()

