from backend.update_checker import check_for_update
import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
from backend.login_manager import authenticate_user

app = QApplication(sys.argv)

client = authenticate_user()
if not client:
    sys.exit(0)

window = MainWindow(client)
window.show()
check_for_update()
sys.exit(app.exec())
