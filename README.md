# USU Preservica Metadata Toolkit

A desktop application for managing, exporting, and updating metadata in the USU Preservica system.

This tool was built to simplify bulk metadata workflows using Preservica's API, with a user-friendly interface that includes features like:

- Exporting metadata to Excel
- Updating metadata from Excel files
- Moving assets between folders
- Authentication with caching
- Version checking for easy updates

---

## Getting Started

Follow these instructions to get up and running on your Windows or Mac computer.

### Step 1: Download the App

Go to the latest release here:

[**Latest Version on GitHub**](https://github.com/ethan-rico/USUpreservica-toolkit/releases/latest)

- Download the file named: `USUpreservicaToolkit.exe` (Windows) or `.app` (Mac — coming soon)
- Save it somewhere on your computer (e.g., Desktop or Documents)

### Step 2: Run the App

- **Double-click** the downloaded file to launch it
- On first launch, you might see a security warning — click **"More info" → "Run anyway"** if prompted

### Step 3: Log In to Preservica

- You’ll be asked to enter your Preservica:
  - **username**
  - **Password**
  - **Tenant**
  - **Server**
- If you use **two-factor authentication (2FA)**, enter your 2FA secret key as well
- Your login will be saved securely on your device so you don’t have to enter it every time

---

## Checking for Updates

This app checks for updates automatically using GitHub.

If a new version is available, you’ll see a message on launch telling you to download the latest version.

---

## 🛠 Features

| Tab          | Description                                                                 |
|--------------|-----------------------------------------------------------------------------|
| **Browser**  | Browse and select assets/folders from Preservica                            |
| **Export**   | Export selected asset metadata (or by folder reference) to `.xlsx` format   |
| **Update**   | Load an updated `.xlsx` to preview and push metadata changes to Preservica |
| **Move**     | Move assets to a new folder by providing their references                   |

---

## Logging Out

To remove your saved credentials:

1. Click **File → Log Out**
2. The app will forget your login and prompt you again next time

---

## Support

If you run into issues or have questions, contact **Ethan Rico** or file an issue on GitHub.

---

## 📦 Tech Stack

- [Python](https://www.python.org/)
- [PyQt6](https://pypi.org/project/PyQt6/)
- [pyPreservica](https://github.com/adamretter/pyPreservica)
- [OpenPyXL](https://openpyxl.readthedocs.io/en/stable/)

---

## Updating / Getting the Latest Version (for coworkers)

There are two common ways to get the latest version of this toolkit:

- Use the prebuilt binary from the GitHub Releases page (recommended for non-developers).
- Use the source code from this repository (recommended for developers or if you want the latest commits).

If you already have a local clone of this repository, you do NOT need to delete and re-download the whole repo — a simple `git pull` will bring you up to date.

Below are step-by-step instructions for both workflows.

1) Quick (non-developer) — Download the latest release executable

- Go to the Releases page: https://github.com/ethan-rico/USUpreservica-toolkit/releases
- Download `USUpreservicaToolkit.exe` for Windows and run it. This is the easiest option for most users.

2) Developer / Source workflow — Clone & pull the repo (Windows `cmd.exe` examples)

- Clone the repo (first time):

```cmd
git clone https://github.com/ethan-rico/USUpreservica-toolkit.git
cd USUpreservica-toolkit
```

- Update an existing clone (pull latest changes):

```cmd
cd \path\to\USUpreservica-toolkit
git checkout main
git pull origin main
```

- Create and activate a virtual environment, install dependencies, and run the app:

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Notes:
- If your coworkers downloaded a single prebuilt `.exe` from Releases, they should download the new `.exe` for the latest version — they don't need to clone the repo for that.
- If they used a git clone, `git pull` keeps their working copy up to date. Deleting and re-downloading is not necessary unless they prefer a fresh clone.

3) Pushing changes to GitHub (for the repo owner / maintainers)

If you have local changes you want on GitHub, commit and push them from your clone (Windows `cmd.exe`):

```cmd
cd \path\to\USUpreservica-toolkit
git status
git add -A
git commit -m "Describe the change: add README update and metadata fixes"
git push origin main
```

If you prefer a GUI, GitHub Desktop or other git clients work too.

4) Creating a Release (optional)

- Creating a release is a good idea if you want coworkers to download a single `.exe` file. You can create a Release on GitHub (Repository → Releases → Draft a new release), upload the built `.exe`, and publish it.

5) Troubleshooting / Preview panel note

- If the Browser Preview panel doesn't render a thumbnail for certain assets (TIFF/PDF), use the **Open** action in the preview to view the full asset externally.
- If coworkers run into issues after a `git pull`, ask them to run `python -m pip install -r requirements.txt` to pick up any new dependencies.

If you'd like, I can:
- prepare a release draft and upload an `.exe` (if you provide the build), or
- create a small `tools/` script that prints the outgoing metadata XML for a single test asset (dry-run) so you can validate payloads before pushing.

