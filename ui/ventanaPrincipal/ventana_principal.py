from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from ui.cabecera.cabeceraPrincipal.cabecera import Cabecera
from ui.ventanaPrincipal.panelizquierdo import PanelIzquierdo


class VentanaPrincipal(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("LIBiAM 3.0")
        self.resize(1600, 900)

        self.init_ui()

    def init_ui(self):

        # Layout principal vertical
        layout = QVBoxLayout()

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Cabecera
        self.cabecera = Cabecera()
        layout.addWidget(self.cabecera)

        # Layout horizontal para el contenido (panel izquierdo + area central)
        layout_contenido = QHBoxLayout()
        layout_contenido.setContentsMargins(0, 0, 0, 0)
        layout_contenido.setSpacing(0)

        # Panel izquierdo
        self.panel_izquierdo = PanelIzquierdo()
        layout_contenido.addWidget(self.panel_izquierdo)

        # Area central vacia (por ahora)
        self.area_central = QWidget()
        self.area_central.setObjectName("areaCentral")
        layout_contenido.addWidget(self.area_central, 1)

        layout.addLayout(layout_contenido)

        self.setLayout(layout)
