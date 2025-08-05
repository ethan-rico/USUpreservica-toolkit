from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout

class MoveTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Move Assets tab coming soon!"))
        self.setLayout(layout)
