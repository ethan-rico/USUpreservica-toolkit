# USU Preservica Metadata Toolkit

A desktop application for managing, exporting, and updating metadata in the USU Preservica system.

This repo provides a PyQt6 desktop client that wraps `pyPreservica` to support common bulk metadata workflows:

- Export metadata to Excel (.xlsx)
- Export full inventory to CSV (recursive folder traversal)
- Update metadata from Excel uploads
- Move assets between folders
- Login caching for convenience

---

## Quick start (non-developers)

1. Download the latest release from the repository Releases page and run the `USUpreservicaToolkit.exe` (Windows).
2. On first launch, enter your Preservica credentials (username, password, tenant, server). Optionally provide a 2FA secret key.
3. Use the UI tabs (`Browser`, `Export`, `Inventory`, `Move`, `Update`) to perform tasks.

Notes for non-developers:
- The prebuilt `.exe` is the recommended way for non-technical users.
- If thumbnails don't render for certain assets (PDF/TIFF), use the **Open** action in the preview to view externally.

---

## Inventory feature (new)

Use the **Inventory** tab to export a full inventory CSV for a folder and all its subfolders.

- Enter the parent folder reference ID (e.g. `REF-12345`).
- Click **Export Inventory** and choose a save location for the CSV.
- The CSV columns are: `reference`, `dc:title`, `dcterms:identifier`, `dc:identifier`, `filename`.

Behavior notes:
- The worker will attempt to compute a total asset count (uses `client.descendants`) and show a determinate progress bar when possible; otherwise a streaming mode with periodic status updates is used.
- `filename` is best-effort: first tries `file_name` or `filename` attributes on the asset, then inspects bitstreams for a candidate name.

If you want a one-off inventory without the GUI, ask me and I can add a small CLI script under `tools/`.

---

## Developer / IT guide

Project layout (important files):

- `main.py` — Application entrypoint; creates `PreservicaClient()` and opens the `MainWindow`.
- `gui/` — PyQt6 tabs and widgets: `browser_tab.py`, `export_tab.py`, `inventory_tab.py`, `update_tab.py`, `move_tab.py`, `main_window.py`.
- `backend/` — API and metadata helpers:
  - `preservica_client.py` — wrapper around `pyPreservica.EntityAPI` and credential caching.
  - `metadata_diff.py` — CSV parsing and QDC XML parsing; used to compute diffs.
  - `metadata_updater.py` — builds QDC / custom-schema XML and calls `client.add_metadata` / `update_metadata`.
  - `metadata_utils.py` and `export_utils.py` — helpers used across flows.
- `logic/` — export and higher-level operations (e.g., building headers for Excel export).

Key runtime details:

- Credentials are saved to: `%USERPROFILE%\\.preservica_toolkit_credentials.json` (Windows path). Remove this file or use the app **Log Out** action to clear cached credentials.
- The app uses `pyPreservica` for all API calls; many helper functions expect `Entity` objects rather than raw references for some operations.
- Metadata blocks are written as namespaced XML. QDC blocks include an `xsi:schemaLocation` pairing the DC namespace with the QDC XSD to improve server validation acceptance.

Dependencies and running from source (Windows examples):

```cmd
git clone <repo>
cd USUpreservica-toolkit
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

Building a Windows executable (pyinstaller):

- There are two spec files in the repo: `USUpeservicaToolkit.spec` and `USUpreservica-toolkit2.1.spec` (pick the one you use for packaging).
- Typical steps (run from project root):

```cmd
pip install pyinstaller
pyinstaller --clean --noconfirm USUpreservicaToolkit.spec
```

After building, upload the built `.exe` to GitHub Releases for non-technical users.

---

## Testing & Troubleshooting

- If you encounter errors after a `git pull`, reinstall dependencies:

```cmd
python -m pip install -r requirements.txt
```

- To debug metadata issues, use `backend/metadata_diff.py::parse_qdc_xml` and `backend/metadata_updater.py::build_qdc_xml` to inspect how QDC/custom blocks are built.

- If the GUI crashes while exporting inventory, run `python main.py` from a console to see traceback output; ensure the current user has network access to the Preservica server and that credentials are valid.

---

## Support & Next steps I can help with

- Prepare a GitHub Release and upload a built `.exe` for non-technical coworkers.
- Add a small CLI `tools/inventory_cli.py` to run the inventory export from the command line for automation.
- Add PDF page-count or large-file handling to the preview (requires `pdf2image` and system `poppler`).

If you'd like me to prepare any of the above (release, CLI tool, packaging), tell me which and I will proceed.


