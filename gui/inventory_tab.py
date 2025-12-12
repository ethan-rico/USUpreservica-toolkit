from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import csv
from backend.preservica_client import PreservicaClient
from backend.metadata_diff import fetch_current_metadata
import pyPreservica as pyp


class InventoryTab(QWidget):
    """Export a full inventory (recursive) of a Preservica folder to CSV."""

    def __init__(self, client):
        super().__init__()
        self.client = client

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.instructions = QLabel("Enter parent folder reference and click Export. Exports a CSV of all items under the folder (recursive).")
        self.instructions.setWordWrap(True)
        self.layout.addWidget(self.instructions)

        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("Enter folder reference ID (e.g. REF-12345)")
        self.layout.addWidget(self.ref_input)

        self.export_button = QPushButton("Export Inventory")
        self.export_button.clicked.connect(self.start_export)
        self.layout.addWidget(self.export_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.layout.addWidget(self.status_label)

        self.worker = None

    def start_export(self):
        ref = self.ref_input.text().strip()
        if not ref:
            QMessageBox.warning(self, "Missing Reference", "Please enter a parent folder reference ID.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save Inventory", filter="CSV Files (*.csv)")
        if not path:
            return
        if not path.lower().endswith('.csv'):
            path += '.csv'

        self.export_button.setEnabled(False)
        self.status_label.setText("Preparing export...")
        self.progress_bar.setValue(0)

        self.worker = InventoryWorker(self.client, ref, path)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.status.connect(self._update_status)
        self.worker.start()

    def _on_progress(self, pct: int):
        try:
            self.progress_bar.setValue(pct)
        except Exception:
            pass

    def _on_finished(self, path: str):
        try:
            if path:
                QMessageBox.information(self, "Export Complete", f"Inventory exported to:\n{path}")
                self.status_label.setText("Export complete")
                self.progress_bar.setValue(100)
            else:
                QMessageBox.warning(self, "Export", "Export finished with errors or no output.")
        finally:
            try:
                self.export_button.setEnabled(True)
            except Exception:
                pass

    def _update_status(self, text: str):
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.status_label.setText(text))
        except Exception:
            try:
                self.status_label.setText(text)
            except Exception:
                pass

    
class InventoryWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, client, root_ref, out_path):
        super().__init__()
        self.client = client
        self.root_ref = root_ref
        self.out_path = out_path

    def run(self):
        try:
            # Attempt to count assets first using descendants (fast path)
            total = None
            asset_refs = None
            try:
                folder = self.client.folder(self.root_ref)
                descendants = list(self.client.descendants(folder))
                asset_refs = [e.reference for e in descendants if isinstance(e, pyp.Asset)]
                total = len(asset_refs)
            except Exception:
                # Couldn't use descendants; we'll stream recursively without a known total
                total = None

            self.status.emit("Writing CSV...")
            with open(self.out_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['reference', 'dc:title', 'dcterms:identifier', 'dc:identifier', 'filename'])

                count = 0

                if asset_refs is not None:
                    # Determinate mode
                    for i, ref in enumerate(asset_refs, 1):
                        try:
                            try:
                                entity = self.client.asset(ref)
                            except Exception:
                                # skip if not asset
                                continue

                            qdc_xml, meta = fetch_current_metadata(self.client, ref)

                            dcterms_id = ''
                            dc_id = ''
                            for k, v in meta.items():
                                if k.startswith('dcterms:identifier') and not dcterms_id:
                                    dcterms_id = v
                                if k.startswith('dc:identifier') and not dc_id:
                                    dc_id = v

                            filename = getattr(entity, 'file_name', '') or getattr(entity, 'filename', '') or ''
                            if not filename:
                                try:
                                    bstreams = self.client.bitstreams_for_asset(ref)
                                    for bs in bstreams:
                                        name = getattr(bs, 'filename', None) or getattr(bs, 'name', None)
                                        if name:
                                            filename = name
                                            break
                                except Exception:
                                    pass

                            writer.writerow([ref, getattr(entity, 'title', ''), dcterms_id, dc_id, filename])
                            count += 1
                            self.progress.emit(int(i / total * 100))
                        except Exception:
                            continue

                else:
                    # Indeterminate mode: traverse children recursively and emit no percentage
                    def process_folder(ref):
                        nonlocal count
                        try:
                            children = self.client.children(ref)
                        except Exception:
                            return

                        for child in getattr(children, 'results', []) or []:
                            try:
                                if isinstance(child, pyp.Folder):
                                    process_folder(child.reference)
                                else:
                                    cr = child.reference
                                    try:
                                        qdc_xml, meta = fetch_current_metadata(self.client, cr)
                                    except Exception:
                                        qdc_xml, meta = ('', {})

                                    dcterms_id = ''
                                    dc_id = ''
                                    for k, v in meta.items():
                                        if k.startswith('dcterms:identifier') and not dcterms_id:
                                            dcterms_id = v
                                        if k.startswith('dc:identifier') and not dc_id:
                                            dc_id = v

                                    filename = getattr(child, 'file_name', '') or getattr(child, 'filename', '') or ''
                                    if not filename:
                                        try:
                                            bstreams = self.client.bitstreams_for_asset(cr)
                                            for bs in bstreams:
                                                name = getattr(bs, 'filename', None) or getattr(bs, 'name', None)
                                                if name:
                                                    filename = name
                                                    break
                                        except Exception:
                                            pass

                                    writer.writerow([cr, getattr(child, 'title', ''), dcterms_id, dc_id, filename])
                                    count += 1
                                    if count % 100 == 0:
                                        self.status.emit(f"Exported {count} items...")
                            except Exception:
                                continue

                    process_folder(self.root_ref)

            self.finished.emit(self.out_path)
            self.status.emit(f"Export complete: {count} items written to {self.out_path}")

        except Exception as e:
            self.status.emit(f"Export failed: {e}")
            self.finished.emit("")

    
    
    
    
    

    
