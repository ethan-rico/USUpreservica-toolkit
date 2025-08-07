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

