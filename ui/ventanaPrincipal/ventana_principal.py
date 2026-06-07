from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from ui.cabecera.cabeceraPrincipal.cabecera import Cabecera
from ui.ventanaPrincipal.areaCentralGraficas import AreaCentralGraficas
from ui.ventanaPrincipal.panelizquierdo import PanelIzquierdo
from ui.ventanaPrincipal.panelDerecho.panelDerecho import PanelDerecho
from ui.ventanaPrincipal.barraBotones import BarraBotones


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

        # Layout horizontal para el contenido
        layout_contenido = QHBoxLayout()
        layout_contenido.setContentsMargins(0, 0, 0, 0)
        layout_contenido.setSpacing(0)

        # Panel izquierdo
        self.panel_izquierdo = PanelIzquierdo()
        layout_contenido.addWidget(self.panel_izquierdo)

        # Area central de graficas
        self.area_central = AreaCentralGraficas()
        layout_contenido.addWidget(self.area_central, 1)

        # Panel derecho (colapsable)
        self.panel_derecho = PanelDerecho()
        layout_contenido.addWidget(self.panel_derecho)

        # Barra de botones derecha
        self.barra_botones = BarraBotones(self.panel_derecho)
        layout_contenido.addWidget(self.barra_botones)

        layout.addLayout(layout_contenido)

        self.setLayout(layout)

        # Conectar panel izquierdo con panel derecho
        self.panel_izquierdo.panel_derecho_ref = self.panel_derecho

        # Conectar carga de datos y seleccion de rango con las graficas
        self.panel_izquierdo.archivoCargado.connect(self.area_central.cargar_dataframe)
        self.panel_izquierdo.archivoSeleccionado.connect(self.area_central.cargar_dataframe)
        self.panel_izquierdo.modoSeleccionRangoCambiado.connect(
            self.area_central.set_modo_seleccion_rango
        )
        self.panel_derecho.config_columnas.mapeoAplicado.connect(
            self.area_central.actualizar_mapeo
        )
