# gui/move_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QInputDialog, QMessageBox,
    QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from backend.preservica_client import PreservicaClient
import pyPreservica as pyp

class MoveWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(self, client, source_ref, dest_ref):
        super().__init__()
        self.client = client
        self.source_ref = source_ref
        self.dest_ref = dest_ref

    def run(self):
        try:
            source_folder = self.client.folder(self.source_ref)
            dest_folder = self.client.folder(self.dest_ref)
        except Exception as e:
            self.failed.emit(f"Invalid folder: {e}")
            return

        try:
            all_assets = list(filter(
                lambda child: isinstance(child, pyp.Asset),
                self.client.descendants(source_folder)
            ))
        except Exception as e:
            self.failed.emit(f"Failed to load descendants: {e}")
            return

        total = len(all_assets)
        moved = 0

        for i, asset in enumerate(all_assets):
            try:
                self.client.move(asset, dest_folder)
                moved += 1
            except Exception as e:
                print(f"[WARN] Failed to move asset {asset.reference}: {e}")
            self.progress.emit(i + 1)

        self.finished.emit(moved)

class MoveTab(QWidget):
    def __init__(self):
        super().__init__()
        self.client = PreservicaClient().client

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.info_label = QLabel("Click the button below to move all assets from one folder to another.")
        self.layout.addWidget(self.info_label)

        self.move_button = QPushButton("Move Assets Between Folders")
        self.move_button.clicked.connect(self.move_assets)
        self.layout.addWidget(self.move_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setVisible(False)
        self.layout.addWidget(self.status_label)

    def move_assets(self):
        source_ref, ok1 = QInputDialog.getText(self, "Source Folder", "Enter source folder reference ID:")
        if not ok1 or not source_ref.strip():
            return
        dest_ref, ok2 = QInputDialog.getText(self, "Destination Folder", "Enter destination folder reference ID:")
        if not ok2 or not dest_ref.strip():
            return

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Starting move...")
        self.status_label.setVisible(True)
        self.move_button.setEnabled(False)

        self.worker = MoveWorker(self.client, source_ref.strip(), dest_ref.strip())
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.on_move_complete)
        self.worker.failed.connect(self.on_move_failed)
        self.worker.start()

    def on_move_complete(self, count):
        self.status_label.setText(f"Move complete: {count} asset(s) moved.")
        self.move_button.setEnabled(True)
        self.progress_bar.setVisible(False)

    def on_move_failed(self, error):
        QMessageBox.critical(self, "Move Failed", error)
        self.status_label.setText("Move failed.")
        self.move_button.setEnabled(True)
        self.progress_bar.setVisible(False)
