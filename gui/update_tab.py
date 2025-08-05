from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class UpdateTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Update Metadata tab coming soon!"))
        self.setLayout(layout)
