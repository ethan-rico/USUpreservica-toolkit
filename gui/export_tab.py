# gui/export_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFileDialog, QInputDialog, QLabel, QProgressBar
)
from backend.preservica_client import PreservicaClient
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import xml.etree.ElementTree as ET
import csv
import pyPreservica as pyp
from backend.export_utils import export_to_xlsx  # Adjust import as needed

class ExportWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)

    def __init__(self, start_ref, export_path):
        super().__init__()
        self.client = PreservicaClient().client
        self.start_ref = start_ref.strip()
        self.export_path = export_path

    def run(self):
        start_folder = self.client.folder(self.start_ref)

        all_assets = list(filter(
            lambda e: "ASSET" in str(e.entity_type).upper(),
            self.client.descendants(start_folder)
        ))

        total = len(all_assets)
        rows = []
        fieldnames = {"reference", "title", "type", "qdc_xml"}

        for i, asset_ref in enumerate(all_assets):
            asset = self.client.asset(asset_ref.reference)
            row = {
                "reference": asset.reference,
                "title": asset.title,
                "type": "ASSET",
                "qdc_xml": ""
            }

            meta_map = asset.metadata or {}

            # Find first metadata block that includes "dc"
            qdc_url = next((u for u, s in meta_map.items() if "dc" in s.lower()), None)

            if qdc_url:
                try:
                    xml_text = self.client.metadata(qdc_url)
                    row["qdc_xml"] = xml_text.strip()

                    root = ET.fromstring(xml_text)
                    ns = {
                        "dc": "http://purl.org/dc/elements/1.1/",
                        "dcterms": "http://purl.org/dc/terms/"
                    }

                    counts = {}
                    for prefix in ns:
                        for elem in root.findall(f".//{{{ns[prefix]}}}*"):
                            tag = elem.tag.split("}")[-1]
                            base_col = f"dc:{tag}"
                            val = (elem.text or "").strip()

                            if val:
                                count = counts.get(base_col, 0)
                                col = base_col if count == 0 else f"{base_col}.{count}"
                                row[col] = val  # <- Use value exactly as-is from XML
                                fieldnames.add(col)
                                counts[base_col] = count + 1

                except ET.ParseError:
                    pass

            rows.append(row)
            self.progress.emit(int((i + 1) / total * 100))

        export_to_xlsx(self.export_path, rows, sorted(fieldnames))

        self.finished.emit(self.export_path)


class ExportTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label = QLabel("Export metadata from a folder or asset to Excel.")
        self.layout.addWidget(self.label)

        self.export_button = QPushButton("Export Metadata to .xlsx")
        self.export_button.clicked.connect(self.start_export)
        self.layout.addWidget(self.export_button)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.layout.addWidget(self.progress)

    def start_export(self):
        # Ask user for reference ID and destination
        ref_id, ok = QInputDialog.getText(self, "Start Folder or Asset Reference", "Enter reference ID:")
        if not ok or not ref_id:
            return

        ref_id = ref_id.strip()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Excel File",
            filter="Excel files (*.xlsx)"
        )
        if not path:
            return

        # Ensure correct extension
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.worker = ExportWorker(ref_id, path)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self.on_export_finished)
        self.worker.start()

    def on_export_finished(self, filepath):
        self.progress.setVisible(False)
        self.label.setText(f"Exported metadata to: {filepath}")
