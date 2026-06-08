from PySide6.QtWidgets import (
    QWidget, 
    QVBoxLayout
)

from ui.cabecera.cabeceraPrincipal.cabecera import Cabecera
from ui.cabecera.subCabecera.seleccionarRango import SeleccionarRango


class VentanaPrincipal(QWidget): 

    def __init__(self):

        super().__init__()

        self.setWindowTitle("LIBiAM 3.0")
        self.resize(1600, 900)

        self.init_ui()

    def init_ui(self):

        # Layout principal vertical
        layout = QVBoxLayout()

        # Sin márgenes externos
        layout.setContentsMargins(0, 0, 0, 0)

        # Sin separación entre cabecera y subcabecera
        layout.setSpacing(0)

        # CABECERA PRINCIPAL

        self.cabecera = Cabecera()
        layout.addWidget(self.cabecera)

        # SUBCABECERA

        self.subcabecera = SeleccionarRango()
        layout.addWidget(self.subcabecera)

        # ESPACIO PARA EL RESTO DEL PROGRAMA
      
        layout.addStretch()

        self.setLayout(layout)


#Explicacion 
#QWidget: La base de toda la ventana y controles  
#QVBoxLayout: Organizador vertical.
#class VentanaPrincipal(QWidget) --> Crea una clase llamada VentanaPrincipal que hereda de QWidget.
