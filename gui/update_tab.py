import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from backend.preservica_client import PreservicaClient
from backend.metadata_diff import parse_csv, generate_diffs
from backend.metadata_updater import update_asset_metadata
import traceback


class UpdateWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int)
    cancelled = pyqtSignal()

    def __init__(self, client, diffs):
        super().__init__()
        self.client = client
        self.diffs = diffs
        self._cancel = False

    def run(self):
        total = len(self.diffs)
        updated = 0
        failed = 0

        for i, diff in enumerate(self.diffs, 1):
            if self._cancel:
                self.cancelled.emit()
                return

            try:
                res = update_asset_metadata(self.client, diff["reference"], diff["csv_row"])
                print(f"Update result for {diff['reference']}: {res}")
                updated += 1
            except Exception as e:
                failed += 1
                print(f"Update failed for {diff['reference']}: {e}")
                traceback.print_exc()

            self.progress.emit(int(i / total * 100))

        self.finished.emit(updated)

    def cancel(self):
        self._cancel = True


class UpdateTab(QWidget):
    preview_ready = pyqtSignal(list)

    def __init__(self, client):
        super().__init__()
        self.client = client
        self.diffs = []
        self.file_path = None
        self.csv_rows = []
        self.worker = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.status_label = QLabel("Load a CSV or Excel file to update metadata.")
        self.layout.addWidget(self.status_label)

        self.load_button = QPushButton("Load Metadata File")
        self.load_button.clicked.connect(self.load_file)
        self.layout.addWidget(self.load_button)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Reference", "Field", "New Value"])
        self.layout.addWidget(self.table)

        self.update_button = QPushButton("Update Metadata")
        self.update_button.setEnabled(False)
        self.update_button.clicked.connect(self.update_metadata)
        self.layout.addWidget(self.update_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_update)
        self.layout.addWidget(self.cancel_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.layout.addWidget(self.progress_bar)

        self.preview_ready.connect(self.show_preview)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Metadata File",
            filter="Metadata Files (*.csv *.xlsx);;CSV Files (*.csv);;Excel Files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            rows = parse_csv(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to parse file:\n{e}")
            return

        self.file_path = file_path
        self.csv_rows = rows
        self.preview_diffs(rows[:10])  # Only preview first 10

    def preview_diffs(self, preview_rows):
        self.status_label.setText("Checking for metadata differences...")

        def run_preview():
            partial_diffs = generate_diffs(self.client, preview_rows)
            changed = [d for d in partial_diffs if d["changes"]]
            self.preview_ready.emit(changed)

        thread = threading.Thread(target=run_preview)
        thread.start()

    def show_preview(self, changed):
        if not changed:
            QMessageBox.information(self, "No Changes", "No metadata differences found.")
            self.table.setRowCount(0)
            self.update_button.setEnabled(False)
            self.status_label.setText("No metadata differences found.")
            return

        self.populate_preview_table(changed)
        self.update_button.setEnabled(True)
        self.status_label.setText("Previewing changes. Click update to apply to all items.")

    def populate_preview_table(self, preview_diffs):
        self.table.setRowCount(0)
        rows = []
        for diff in preview_diffs:
            ref = diff["reference"]
            for field, (_, new_val) in diff["changes"].items():
                rows.append((ref, field, new_val))

        self.table.setRowCount(len(rows))
        for row_idx, (ref, field, val) in enumerate(rows):
            self.table.setItem(row_idx, 0, QTableWidgetItem(ref))
            self.table.setItem(row_idx, 1, QTableWidgetItem(field))
            self.table.setItem(row_idx, 2, QTableWidgetItem(val))

    def update_metadata(self):
        if not self.csv_rows:
            return

        self.status_label.setText("Processing all changes...")
        self.update_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.table.setRowCount(0)
        self.progress_bar.setValue(0)

        def full_diff():
            all_diffs = generate_diffs(self.client, self.csv_rows)
            changed = [d for d in all_diffs if d["changes"]]
            self.run_update_worker(changed)

        threading.Thread(target=full_diff).start()

    def run_update_worker(self, diffs):
        self.worker = UpdateWorker(self.client, diffs)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.update_complete)
        self.worker.cancelled.connect(self.update_cancelled)
        self.worker.start()

    def cancel_update(self):
        if self.worker:
            self.worker.cancel()
            self.status_label.setText("Cancelling update...")

    def update_complete(self, updated_count):
        self.status_label.setText(f"Metadata update complete. {updated_count} items updated.")
        self.progress_bar.setValue(100)
        self.cancel_button.setEnabled(False)

    def update_cancelled(self):
        self.status_label.setText("Update cancelled by user.")
        self.cancel_button.setEnabled(False)
        self.progress_bar.setValue(0)
