import os
import json
import pyPreservica as pyp
from backend.login_manager import LoginDialog
from PyQt6.QtWidgets import QApplication
import sys
import subprocess

CREDENTIALS_FILE = os.path.expanduser("~/.preservica_toolkit_credentials.json")

class PreservicaClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            credentials = cls._load_credentials()
            try:
                cls._instance.client = cls._login_with(credentials)
            except Exception:
                print("⚠️ Cached login failed — prompting user...")
                credentials = cls._prompt_user_login()
                cls._instance.client = cls._login_with(credentials)
                cls._save_credentials(credentials)

        return cls._instance

    @staticmethod
    def _login_with(credentials):
        return pyp.EntityAPI(
            username=credentials["username"],
            password=credentials["password"],
            tenant=credentials["tenant"],
            server=credentials["server"],
            two_fa_secret_key=credentials.get("twoFactorToken")
        )

    @staticmethod
    def _load_credentials():
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, "r") as f:
                return json.load(f)
        else:
            return {}

    @staticmethod
    def _save_credentials(credentials):
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(credentials, f)

    @staticmethod
    def _prompt_user_login():
        app = QApplication.instance() or QApplication(sys.argv)
        dialog = LoginDialog()
        if dialog.exec():
            return dialog.get_credentials()
        else:
            sys.exit("Login canceled by user.")
    
def logout_user():
    """
    Clears the saved credentials to force login on next run.
    """
    try:
        if os.path.exists(CREDENTIALS_FILE):
            os.remove(CREDENTIALS_FILE)
            print("✅ Logged out and removed saved credentials.")
        else:
            print("⚠️ No credential file found to delete.")
    except Exception as e:
        print(f"⚠️ Error during logout: {e}")