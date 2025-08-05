from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class ExportTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Export Metadata tab coming soon!"))
        self.setLayout(layout)
