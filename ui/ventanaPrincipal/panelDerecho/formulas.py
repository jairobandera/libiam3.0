from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt


class Formulas(QFrame):

    def __init__(self):
        super().__init__()
        self.setObjectName("formulasPanel")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        frame = QFrame()
        frame.setObjectName("seccionMapeo")

        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(10, 10, 10, 10)
        frame_layout.setSpacing(10)
        frame_layout.setAlignment(Qt.AlignCenter)

        label = QLabel("En construcción")
        label.setAlignment(Qt.AlignCenter)
        label.setObjectName("tituloSeccionMapeo")
        label.setStyleSheet("font-size: 16px;")

        frame_layout.addWidget(label)
        frame.setLayout(frame_layout)

        layout.addWidget(frame)

        # Espacio para igualar altura con el panel de mapeo
        spacer = QWidget()
        spacer.setFixedHeight(500)
        layout.addWidget(spacer)

        layout.addStretch()
        self.setLayout(layout)
