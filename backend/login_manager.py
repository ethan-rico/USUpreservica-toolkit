import os
import json
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QMessageBox
from pyPreservica import EntityAPI

CREDENTIALS_FILE = Path.home() / ".preservica_toolkit_credentials.json"


def save_credentials(data):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(data, f)


def load_credentials():
    if CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    return None


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login to Preservica")

        layout = QVBoxLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(QLabel("Username:"))
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Password or Shared Secret")
        layout.addWidget(QLabel("Password / Shared Secret:"))
        layout.addWidget(self.password_input)

        self.tenant_input = QLineEdit()
        self.tenant_input.setPlaceholderText("e.g. USU")
        layout.addWidget(QLabel("Tenant ID:"))
        layout.addWidget(self.tenant_input)

        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("e.g. us.preservica.com")
        layout.addWidget(QLabel("Server:"))
        layout.addWidget(self.server_input)

        self.shared_secret_checkbox = QCheckBox("Use Shared Secret")
        layout.addWidget(self.shared_secret_checkbox)

        self.twofa_input = QLineEdit()
        self.twofa_input.setPlaceholderText("Optional 2FA token")
        layout.addWidget(QLabel("2FA Token (if required):"))
        layout.addWidget(self.twofa_input)

        self.remember_me = QCheckBox("Remember Me")
        layout.addWidget(self.remember_me)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.accept)
        layout.addWidget(self.login_button)

        self.setLayout(layout)

    def get_login_data(self):
        return {
            "username": self.username_input.text().strip(),
            "password": self.password_input.text().strip(),
            "tenant": self.tenant_input.text().strip(),
            "server": self.server_input.text().strip(),
            "use_shared_secret": self.shared_secret_checkbox.isChecked(),
            "two_fa_secret_key": self.twofa_input.text().strip(),
            "remember": self.remember_me.isChecked()
        }


def authenticate_user():
    creds = load_credentials()
    if creds:
        try:
            return EntityAPI(**creds)
        except Exception:
            QMessageBox.warning(None, "Login Failed", "Stored credentials are invalid. Please re-enter them.")

    dialog = LoginDialog()
    if dialog.exec():
        data = dialog.get_login_data()

        try:
            client = EntityAPI(
                username=data["username"],
                password=data["password"],
                tenant=data["tenant"],
                server=data["server"],
                use_shared_secret=data["use_shared_secret"],
                two_fa_secret_key=data["two_fa_secret_key"] or None
            )

            if data["remember"]:
                save_credentials({
                    "username": data["username"],
                    "password": data["password"],
                    "tenant": data["tenant"],
                    "server": data["server"],
                    "use_shared_secret": data["use_shared_secret"],
                    "two_fa_secret_key": data["two_fa_secret_key"] or None
                })

            return client

        except Exception as e:
            QMessageBox.critical(None, "Login Error", f"Could not log in: {e}")
            return None

    return None
