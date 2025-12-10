# gui/browser_tab.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QHBoxLayout, QFileDialog, QInputDialog, QStatusBar, QMessageBox,
    QSplitter, QLabel, QTextEdit, QTableWidget, QTableWidgetItem, QApplication
)
from PyQt6.QtCore import Qt
from backend.preservica_client import PreservicaClient
from backend.metadata_diff import fetch_current_metadata
import pyPreservica as pyp
import xml.etree.ElementTree as ET
import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
import requests
import threading
from PyQt6.QtGui import QPixmap
import io
import os
import webbrowser

class BrowserTab(QWidget):
    def __init__(self, export_tab, move_tab, client):
        super().__init__()
        self.export_tab = export_tab
        self.move_tab = move_tab
        self.client = client

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Splitter: tree on left, preview panel on right
        self.splitter = QSplitter()

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Preservica Folders and Assets")
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.itemExpanded.connect(self.load_children)
        self.tree.itemSelectionChanged.connect(self.on_selection_changed)
        self.splitter.addWidget(self.tree)

        # Preview panel
        self.preview_widget = QWidget()
        pv_layout = QVBoxLayout()
        self.preview_widget.setLayout(pv_layout)
        self.current_preview_url = None

        # Header labels
        self.preview_title = QLabel("Title: ")
        pv_layout.addWidget(self.preview_title)

        self.preview_ref = QLabel("Reference: ")
        pv_layout.addWidget(self.preview_ref)

        self.preview_type = QLabel("Type: ")
        pv_layout.addWidget(self.preview_type)

        # Thumbnail + metadata table area
        thumb_meta_layout = QHBoxLayout()

        # Thumbnail placeholder
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(200, 150)
        self.thumbnail_label.setStyleSheet("border: 1px solid #ccc; background: #fff;")
        thumb_meta_layout.addWidget(self.thumbnail_label)

        # Metadata table (two columns: field, value)
        self.meta_table = QTableWidget()
        self.meta_table.setColumnCount(2)
        self.meta_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.meta_table.horizontalHeader().setStretchLastSection(True)
        thumb_meta_layout.addWidget(self.meta_table)

        pv_layout.addLayout(thumb_meta_layout)

        # Raw XML area
        pv_layout.addWidget(QLabel("Raw QDC XML:"))
        self.preview_xml = QTextEdit()
        self.preview_xml.setReadOnly(True)
        self.preview_xml.setMinimumHeight(150)
        pv_layout.addWidget(self.preview_xml)

        # Action buttons: Refresh preview, Copy XML
        actions_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._refresh_current_preview)
        actions_layout.addWidget(self.refresh_button)

        self.copy_xml_button = QPushButton("Copy XML")
        self.copy_xml_button.clicked.connect(self._copy_xml_to_clipboard)
        actions_layout.addWidget(self.copy_xml_button)

        self.open_button = QPushButton("Open File")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_current_url)
        actions_layout.addWidget(self.open_button)

        pv_layout.addLayout(actions_layout)

        self.splitter.addWidget(self.preview_widget)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)

        self.layout.addWidget(self.splitter)

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

    def on_selection_changed(self):
        selected = self.tree.selectedItems()
        if not selected:
            self.preview_title.setText("Title: ")
            self.preview_ref.setText("Reference: ")
            self.preview_type.setText("Type: ")
            # clear table and xml and thumbnail
            self.meta_table.setRowCount(0)
            self.preview_xml.clear()
            self.thumbnail_label.clear()
            try:
                self.open_button.setEnabled(False)
            except Exception:
                pass
            self.current_preview_url = None
            return

        # preview the first selected item
        item = selected[0]
        ref = item.data(0, Qt.ItemDataRole.UserRole)
        if not ref:
            return

        try:
            try:
                entity = self.client.asset(ref)
                etype = 'ASSET'
            except Exception:
                entity = self.client.folder(ref)
                etype = 'FOLDER'

            qdc_xml, meta_dict = fetch_current_metadata(self.client, ref)

            self.preview_title.setText(f"Title: {getattr(entity, 'title', '')}")
            self.preview_ref.setText(f"Reference: {ref}")
            self.preview_type.setText(f"Type: {etype}")

            # Populate metadata table with sorted keys
            keys = sorted(meta_dict.keys())
            self.meta_table.setRowCount(len(keys))
            for row_idx, k in enumerate(keys):
                key_item = QTableWidgetItem(k)
                val_item = QTableWidgetItem(meta_dict[k])
                self.meta_table.setItem(row_idx, 0, key_item)
                self.meta_table.setItem(row_idx, 1, val_item)

            self.preview_xml.setPlainText(qdc_xml or "")

            # Attempt to fetch a thumbnail/rendition if available
            self.thumbnail_label.setPixmap(QPixmap())
            # Try common attributes on the entity for an image URL
            thumb_url = None
            # pyPreservica may expose rendition URLs in different attributes; attempt several names
            for attr in ("thumbnail_url", "thumbnail", "rendition_url", "representative_url", "representations"):
                try:
                    v = getattr(entity, attr, None)
                    if isinstance(v, str) and v.startswith("http"):
                        thumb_url = v
                        break
                    # If representations is a dict or list, attempt to extract a URL
                    if isinstance(v, dict):
                        # pick first URL-like value
                        for vv in v.values():
                            if isinstance(vv, str) and vv.startswith("http"):
                                thumb_url = vv
                                break
                        if thumb_url:
                            break
                    if isinstance(v, (list, tuple)) and v:
                        for vv in v:
                            if isinstance(vv, str) and vv.startswith("http"):
                                thumb_url = vv
                                break
                        if thumb_url:
                            break
                except Exception:
                    continue

            if thumb_url:
                # fetch in background
                threading.Thread(target=self._fetch_and_set_thumbnail, args=(thumb_url,)).start()

        except Exception as e:
            # show error in XML area and clear meta table
            self.meta_table.setRowCount(0)
            self.preview_xml.setPlainText(f"Error loading preview: {e}")
            try:
                self.open_button.setEnabled(False)
            except Exception:
                pass

    def _fetch_and_set_thumbnail(self, url):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return
            img_data = resp.content

            lower = url.lower()
            # PDF handling: can't render easily — enable open button and show placeholder
            if lower.endswith('.pdf'):
                def set_pdf_placeholder():
                    self.thumbnail_label.setText('PDF (open)')
                    self.open_button.setEnabled(True)
                    self.current_preview_url = url
                QTimer.singleShot(0, set_pdf_placeholder)
                return

            # Try to load image data (including TIFF). If loading fails, enable open button.
            pix = QPixmap()
            loaded = pix.loadFromData(img_data)
            if not loaded or pix.isNull():
                # failed to load image; provide open button
                def set_failed():
                    self.thumbnail_label.setText('Preview not available; open file')
                    self.open_button.setEnabled(True)
                    self.current_preview_url = url
                QTimer.singleShot(0, set_failed)
                return

            # scale to label size preserving aspect
            scaled = pix.scaled(self.thumbnail_label.width(), self.thumbnail_label.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            def set_pix():
                self.thumbnail_label.setPixmap(scaled)
                self.open_button.setEnabled(False)
                self.current_preview_url = None
            QTimer.singleShot(0, set_pix)
        except Exception:
            try:
                QTimer.singleShot(0, lambda: self.thumbnail_label.setText('Preview failed'))
            except Exception:
                pass

    def _open_current_url(self):
        if not getattr(self, 'current_preview_url', None):
            return
        try:
            webbrowser.open(self.current_preview_url)
        except Exception:
            QMessageBox.warning(self, 'Open Failed', 'Could not open the file URL externally.')

    def _copy_xml_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.preview_xml.toPlainText())

    def _refresh_current_preview(self):
        # re-run selection handler to refresh data
        self.on_selection_changed()

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

        except Exception as e:
            # show error in XML area and clear meta table
            self.meta_table.setRowCount(0)
            self.preview_xml.setPlainText(f"Error loading preview: {e}")
            try:
                self.open_button.setEnabled(False)
            except Exception:
                pass

    def _fetch_and_set_thumbnail(self, url):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return
            img_data = resp.content

            lower = url.lower()
            # PDF handling: can't render easily — enable open button and show placeholder
            if lower.endswith('.pdf'):
                def set_pdf_placeholder():
                    self.thumbnail_label.setText('PDF (open)')
                    self.open_button.setEnabled(True)
                    self.current_preview_url = url
                QTimer.singleShot(0, set_pdf_placeholder)
                return

            # Prefer using Pillow to open image data (better TIFF support). Fallback to QPixmap.loadFromData.
            pix = QPixmap()
            loaded = False
            try:
                image = Image.open(io.BytesIO(img_data))
                # If multi-frame (e.g., multi-page TIFF), use first frame
                try:
                    if getattr(image, 'n_frames', 1) > 1:
                        image.seek(0)
                except Exception:
                    pass

                # Convert to RGBA/RGB for consistent Qt loading
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA")

                out = io.BytesIO()
                image.save(out, format="PNG")
                png_data = out.getvalue()
                loaded = pix.loadFromData(png_data)
            except Exception:
                # Pillow failed; try QPixmap directly
                try:
                    loaded = pix.loadFromData(img_data)
                except Exception:
                    loaded = False

            if not loaded or pix.isNull():
                # failed to load image; provide open button
                def set_failed():
                    self.thumbnail_label.setText('Preview not available; open file')
                    self.open_button.setEnabled(True)
                    self.current_preview_url = url
                QTimer.singleShot(0, set_failed)
                return

            # scale to label size preserving aspect
            scaled = pix.scaled(self.thumbnail_label.width(), self.thumbnail_label.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            def set_pix():
                self.thumbnail_label.setPixmap(scaled)
                self.open_button.setEnabled(False)
                self.current_preview_url = None
            QTimer.singleShot(0, set_pix)
        except Exception:
            try:
                QTimer.singleShot(0, lambda: self.thumbnail_label.setText('Preview failed'))
            except Exception:
                pass

    def _set_thumbnail_from_bytes(self, img_bytes, enable_open=False, url=None):
        """Set the thumbnail label from raw image bytes (uses Pillow for consistency)."""
        try:
            pix = QPixmap()
            loaded = False
            try:
                image = Image.open(io.BytesIO(img_bytes))
                try:
                    if getattr(image, 'n_frames', 1) > 1:
                        image.seek(0)
                except Exception:
                    pass
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGBA")
                out = io.BytesIO()
                image.save(out, format="PNG")
                png_data = out.getvalue()
                loaded = pix.loadFromData(png_data)
            except Exception:
                try:
                    loaded = pix.loadFromData(img_bytes)
                except Exception:
                    loaded = False

            if not loaded or pix.isNull():
                QTimer.singleShot(0, lambda: self.thumbnail_label.setText('Preview not available; open file'))
                QTimer.singleShot(0, lambda: self.open_button.setEnabled(bool(enable_open)))
                if url:
                    self.current_preview_url = url
                return

            scaled = pix.scaled(self.thumbnail_label.width(), self.thumbnail_label.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            def set_pix():
                self.thumbnail_label.setPixmap(scaled)
                self.open_button.setEnabled(False)
                self.current_preview_url = None
            QTimer.singleShot(0, set_pix)
        except Exception:
            QTimer.singleShot(0, lambda: self.thumbnail_label.setText('Preview failed'))

    def _open_current_url(self):
        if not getattr(self, 'current_preview_url', None):
            return
        try:
            webbrowser.open(self.current_preview_url)
        except Exception:
            QMessageBox.warning(self, 'Open Failed', 'Could not open the file URL externally.')

    def _copy_xml_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.preview_xml.toPlainText())

    def _refresh_current_preview(self):
        # re-run selection handler to refresh data
        self.on_selection_changed()

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
