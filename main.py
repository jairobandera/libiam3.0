import sys
import os

from PySide6.QtWidgets import QApplication

from ui.ventanaPrincipal.ventana_principal import VentanaPrincipal


app = QApplication(sys.argv)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

archivos_qss = [
    os.path.join(BASE_DIR, "utilidades", "estilos", "ventana.qss"),
    os.path.join(BASE_DIR, "utilidades", "estilos", "cabecera.qss"),
    os.path.join(BASE_DIR, "utilidades", "estilos", "panelizquierdo.qss"),
    os.path.join(BASE_DIR, "utilidades", "estilos", "panelderecho.qss"),
    os.path.join(BASE_DIR, "utilidades", "estilos", "barrabotones.qss"),
]

estilos = ""

for archivo in archivos_qss:
    with open(archivo, "r", encoding="utf-8") as f:
        estilos += f.read() + "\n"

app.setStyleSheet(estilos)

ventana = VentanaPrincipal()
ventana.showMaximized()

sys.exit(app.exec())
