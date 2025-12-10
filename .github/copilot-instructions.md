This repository is a small PyQt6 desktop toolkit for interacting with a Preservica backend.

Use these instructions to help an AI coding agent be immediately productive working on the codebase.

**Big Picture**
- **App entry**: `main.py` — launches a PyQt6 `QApplication`, runs `authenticate_user()` (from `backend/login_manager.py`) and opens `gui/main_window.py`.
- **Layers**: `gui/` (UI tabs), `backend/` (API wrappers, metadata helpers), `logic/` (export logic). The `pyPreservica` library (wrapped by `backend/preservica_client.py`) is the API client.
- **Primary data flow**: GUI triggers export/preview/update flows → `backend/metadata_diff.py` parses/export metadata and computes diffs → `backend/metadata_updater.py` builds QDC XML and calls `pyPreservica` to add/update metadata blocks on entities.

**Critical files & functions (quick map)**
- `backend/preservica_client.py` — singleton-like wrapper; use `PreservicaClient()` or `EntityAPI` returned by `authenticate_user()` in `main.py`.
- `logic/operations.py::export_metadata_to_excel` and `gui/export_tab.py::ExportWorker.run` — collect metadata keys dynamically into a `fieldnames` set. The export writes headers like `dc:creator`, `dc:creator.1`.
- `backend/metadata_diff.py`:
  - `parse_csv(file_path)` — reads `.csv` or `.xlsx` into a list of dict rows (pandas used for xlsx).
  - `parse_qdc_xml(xml_text)` — turns QDC XML into keys like `dc:title`, `dc:subject.1`, etc.
  - `generate_diffs(client, csv_rows)` — compares CSV rows to current metadata and returns per-row diffs.
- `backend/metadata_updater.py`::`update_asset_metadata(client, reference, updated_metadata)` — core place to add/update element values and to add a metadata block when missing.
- `gui/update_tab.py::UpdateTab` — loads CSV/xlsx, previews first 10 rows, then runs updates via `UpdateWorker` (QThread).

**Project-specific patterns & conventions**
- Metadata keys exported/imported use the `dc:` prefix and numeric suffixes for repeated fields: `dc:identifier`, `dc:identifier.1`, `dc:identifier.2`.
- Exports build a dynamic header set (`fieldnames`), so adding a new metadata key on export will produce a new column automatically.
- The re-upload pipeline expects metadata CSV headers that match `dc:...` keys (compare step filters keys by `dc:` in `compare_metadata`).
- Credentials are stored at `~/.preservica_toolkit_credentials.json` by the login dialog logic.

**Concrete guidance for the two requested features**
- Enable adding brand-new metadata columns (not just editing existing keys):
  - Look at `backend/metadata_diff.py::compare_metadata` — it currently only cares about keys starting with `dc:` but will treat presence/absence as change; ensure it treats missing existing keys as an "addition" (it already reports when csv value != existing). If code currently skips adding entirely new schema blocks, change `backend/metadata_updater.py::update_asset_metadata` to:
    - Accept keys with `dc:` and create new `dc` elements when they don't exist (group by base key and append elements for each `dc:tag` and its `.N` variants). The function already groups and adds elements — if adding fails, make sure the code calls `client.add_metadata(entity, schema_url, updated_xml)` when no existing QDC block exists.
    - For non-dc/custom schema fields, prefer the header format `schemaURL::elementName` (example: `http://example.org/schema::customField`) and implement parsing in `parse_csv`/`generate_diffs` and `update_asset_metadata` to add (or update) a separate metadata block at `schemaURL`.
  - Files to modify: `backend/metadata_diff.py` (parsing + compare rules), `backend/metadata_updater.py` (create/add blocks and elements). Use `NAMESPACES` in `metadata_diff.py` as reference for mapping prefixes.

- Add a Preview pane in the GUI (File-Explorer style):
  - UI files: update `gui/browser_tab.py` (the tree view) to host a side panel; or create a new widget `gui/preview_panel.py` and embed it in `gui/main_window.py` next to the `QTreeWidget`.
  - Behavior: on tree selection change, call `client.asset(ref)` (or `client.folder(ref)`) and display: title, reference id, type, key metadata fields (first N `dc:` fields), and the `qdc_xml`. Optionally render an image/thumbnail if the `pyPreservica` asset exposes a rendition URL.
  - Concrete widgets: use `QSplitter` or a horizontal `QHBoxLayout` with the tree on the left and a `QVBoxLayout` preview card on the right. Add actions in `gui/browser_tab.py` to connect `tree.itemSelectionChanged` to the preview update function.

**Developer workflows & commands**
- Install deps and run the app (Windows `cmd.exe`):
```cmd
python -m pip install -r requirements.txt
python main.py
```
- There are no automated tests in the repo; run the app and exercise UI flows manually. There is a PyInstaller spec `USUpeservicaToolkit.spec` if you want to build a bundled exe.

**Examples & snippets (where to look)**
- Export header generation: `logic/operations.py::export_metadata_to_excel` — it adds keys to `fieldnames` as it sees elements.
- Import parsing: `backend/metadata_diff.py::parse_csv` returns dicts keyed by column headers; ensure headers are preserved verbatim when re-uploading.
- Update application: `backend/metadata_updater.py::update_asset_metadata` — adjust this function to create missing elements or metadata blocks.

If anything in this summary is unclear or you want the AI agent to implement the metadata-add or preview panel changes now, tell me which feature to start with and whether you prefer the preview added into `BrowserTab` or as a separate dockable widget in `MainWindow`.
