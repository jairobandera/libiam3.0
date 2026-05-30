from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout
)

from ui.cabecera.cabeceraPrincipal.cabecera import Cabecera


class VentanaPrincipal(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("LIBiAM 3.0")
        self.resize(1600, 900)

        self.init_ui()

    def init_ui(self):

        layout = QVBoxLayout()

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Cabecera
        self.cabecera = Cabecera()
        layout.addWidget(self.cabecera)

        # Espacio vacío debajo
        layout.addStretch()

        self.setLayout(layout)