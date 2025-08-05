# gui/move_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QProgressBar,
    QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from backend.preservica_client import PreservicaClient
import pyPreservica as pyp
import time

class MoveWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int)

    def __init__(self, client, source_ref, destination_ref):
        super().__init__()
        self.client = client
        self.source_ref = source_ref
        self.destination_ref = destination_ref

    def run(self):
        try:
            source_folder = self.client.folder(self.source_ref)
            destination_folder = self.client.folder(self.destination_ref)
        except Exception as e:
            self.finished.emit(0, 0)
            return

        moved = 0
        skipped = 0
        assets = []

        # Get all children recursively
        try:
            descendants = self.client.descendants(source_folder)
            assets = [a for a in descendants if isinstance(a, pyp.Asset)]
        except Exception:
            self.finished.emit(0, 0)
            return

        total = len(assets)

        for i, asset in enumerate(assets, 1):
            try:
                self.client.move(asset, destination_folder)
                moved += 1
            except Exception:
                skipped += 1
            self.progress.emit(int((i / total) * 100))
            time.sleep(0.05)  # slight delay for smoother UI feedback

        self.finished.emit(moved, skipped)

class MoveSelectionWorker(QThread):
        progress = pyqtSignal(int)
        finished = pyqtSignal(int, int)

        def __init__(self, client, refs, destination_ref):
            super().__init__()
            self.client = client
            self.refs = refs
            self.destination_ref = destination_ref

        def run(self):
            try:
                destination_folder = self.client.folder(self.destination_ref)
            except Exception:
                self.finished.emit(0, len(self.refs))
                return

            total = len(self.refs)
            moved = 0
            skipped = 0

            for i, ref in enumerate(self.refs, 1):
                try:
                    entity = self.client.asset(ref)  # Try as asset
                except Exception:
                    try:
                        entity = self.client.folder(ref)  # Try as folder
                    except Exception:
                        skipped += 1
                        self.progress.emit(int((i / total) * 100))
                        continue

                try:
                    self.client.move(entity, destination_folder)
                    moved += 1
                except Exception:
                    skipped += 1

                self.progress.emit(int((i / total) * 100))

            self.finished.emit(moved, skipped)

class MoveTab(QWidget):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.info_label = QLabel("Move all assets from one folder to another.")
        self.layout.addWidget(self.info_label)

        self.move_button = QPushButton("Move Assets Between Folders")
        self.move_button.clicked.connect(self.handle_move)
        self.layout.addWidget(self.move_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)

    def handle_move(self):
        src_ref, ok1 = QInputDialog.getText(self, "Source Folder", "Enter the source folder reference ID:")
        if not ok1 or not src_ref.strip():
            return

        dst_ref, ok2 = QInputDialog.getText(self, "Destination Folder", "Enter the destination folder reference ID:")
        if not ok2 or not dst_ref.strip():
            return

        self.progress_bar.setValue(0)
        self.worker = MoveWorker(self.client, src_ref.strip(), dst_ref.strip())
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.show_results)
        self.worker.start()

    def show_results(self, moved, skipped):
        msg = f"Moved {moved} asset(s)."
        if skipped > 0:
            msg += f"\nSkipped {skipped} item(s)."
        QMessageBox.information(self, "Move Complete", msg)
    
    def move_items(self, ref_list, destination_ref):
        self.progress_bar.setValue(0)
        self.ref_list = ref_list
        self.destination_ref = destination_ref

        self.worker = MoveSelectionWorker(self.client, ref_list, destination_ref)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.show_results)
        self.worker.start()

