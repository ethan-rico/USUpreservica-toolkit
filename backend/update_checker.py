import requests
from PyQt6.QtWidgets import QMessageBox

GITHUB_REPO = "ethan-rico/USUpreservica-toolkit"
CURRENT_VERSION = "v1.0.0"  # Replace with your actual version

def check_for_update():
    try:
        response = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
        if response.status_code == 200:
            latest = response.json().get("tag_name", "")
            if latest and latest != CURRENT_VERSION:
                QMessageBox.information(
                    None,
                    "Update Available",
                    f"A new version ({latest}) is available.\nVisit the GitHub releases page to download."
                )
    except Exception as e:
        print(f"Failed to check for update: {e}")
