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


            self.status.emit("Collecting inventory metadata...")

            rows = []
            count = 0

            def extract_values(meta: dict, prefix: str):
                vals = []
                # keys like 'dc:title', 'dc:title.1', ... order by suffix
                i = 0
                while True:
                    key = f"{prefix}" if i == 0 else f"{prefix}.{i}"
                    if key in meta:
                        vals.append(meta.get(key, ""))
                        i += 1
                    else:
                        break
                return vals

            def extract_filenames(entity_ref, entity_obj):
                names = []
                # try direct attributes first
                fname = getattr(entity_obj, 'file_name', None) or getattr(entity_obj, 'filename', None)
                if fname:
                    names.append(fname)
                # then try bitstreams
                try:
                    bstreams = self.client.bitstreams_for_asset(entity_ref)
                    for bs in bstreams:
                        name = getattr(bs, 'filename', None) or getattr(bs, 'name', None)
                        if name and name not in names:
                            names.append(name)
                except Exception:
                    pass
                return names

            # helper to process an asset-like object and append to rows
            def process_asset(ref, entity):
                nonlocal count
                try:
                    qdc_xml, meta = fetch_current_metadata(self.client, ref)
                except Exception:
                    qdc_xml, meta = ('', {})

                dc_titles = extract_values(meta, 'dc:title')
                dcterms_titles = extract_values(meta, 'dcterms:title')
                dc_ids = extract_values(meta, 'dc:identifier')
                dcterms_ids = extract_values(meta, 'dcterms:identifier')
                filenames = extract_filenames(ref, entity)

                rows.append({
                    'reference': ref,
                    'dc_titles': dc_titles,
                    'dcterms_titles': dcterms_titles,
                    'dc_identifiers': dc_ids,
                    'dcterms_identifiers': dcterms_ids,
                    'filenames': filenames,
                    'title_attr': getattr(entity, 'title', '')
                })
                count += 1

            if asset_refs is not None:
                # determinate mode
                total_refs = len(asset_refs)
                for i, ref in enumerate(asset_refs, 1):
                    try:
                        try:
                            entity = self.client.asset(ref)
                        except Exception:
                            continue
                        process_asset(ref, entity)
                        self.progress.emit(int(i / total_refs * 100))
                    except Exception:
                        continue
            else:
                # indeterminate mode: traverse recursively
                def process_folder(ref):
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
                                process_asset(cr, child)
                                if count % 100 == 0:
                                    self.status.emit(f"Collected {count} items...")
                        except Exception:
                            continue

                process_folder(self.root_ref)

            # compute maximum counts for each group to build header
            max_dc_titles = max((len(r['dc_titles']) for r in rows), default=0)
            max_dcterms_titles = max((len(r['dcterms_titles']) for r in rows), default=0)
            max_dc_ids = max((len(r['dc_identifiers']) for r in rows), default=0)
            max_dcterms_ids = max((len(r['dcterms_identifiers']) for r in rows), default=0)
            max_fnames = max((len(r['filenames']) for r in rows), default=0)

            # build header
            header = ['reference']
            # include attribute title (fallback) and then dc/dcterms titles
            header.append('title')
            for i in range(max_dc_titles):
                header.append('dc:title' if i == 0 else f'dc:title.{i}')
            for i in range(max_dcterms_titles):
                header.append('dcterms:title' if i == 0 else f'dcterms:title.{i}')
            for i in range(max_dc_ids):
                header.append('dc:identifier' if i == 0 else f'dc:identifier.{i}')
            for i in range(max_dcterms_ids):
                header.append('dcterms:identifier' if i == 0 else f'dcterms:identifier.{i}')
            for i in range(max_fnames):
                header.append('filename' if i == 0 else f'filename.{i}')

            # write CSV
            self.status.emit('Writing CSV...')
            with open(self.out_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header)

                for r in rows:
                    row = [r['reference'], r.get('title_attr', '')]
                    # dc titles
                    for i in range(max_dc_titles):
                        row.append(r['dc_titles'][i] if i < len(r['dc_titles']) else '')
                    # dcterms titles
                    for i in range(max_dcterms_titles):
                        row.append(r['dcterms_titles'][i] if i < len(r['dcterms_titles']) else '')
                    # dc identifiers
                    for i in range(max_dc_ids):
                        row.append(r['dc_identifiers'][i] if i < len(r['dc_identifiers']) else '')
                    # dcterms identifiers
                    for i in range(max_dcterms_ids):
                        row.append(r['dcterms_identifiers'][i] if i < len(r['dcterms_identifiers']) else '')
                    # filenames
                    for i in range(max_fnames):
                        row.append(r['filenames'][i] if i < len(r['filenames']) else '')

                    writer.writerow(row)

            self.finished.emit(self.out_path)
            self.status.emit(f"Export complete: {count} items written to {self.out_path}")

        except Exception as e:
            self.status.emit(f"Export failed: {e}")
            self.finished.emit("")

    
    
    
    
    

    
