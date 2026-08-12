import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from logica.config_db import init_db, get_session
from ui.ventanaPrincipal.ventana_principal import VentanaPrincipal


app = QApplication(sys.argv)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ícono único de la aplicación: Qt lo propaga a la ventana principal, a todos
# los diálogos/ventanas top-level que no definan uno propio y a los
# QMessageBox/QInputDialog. Ruta robusta basada en la ubicación de este archivo,
# para que el programa funcione aunque se mueva a otra PC.
app.setWindowIcon(
    QIcon(os.path.join(BASE_DIR, "utilidades", "icons", "logo.ico"))
)

engine = init_db()
db_session = get_session(engine)

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

ventana = VentanaPrincipal(db_session=db_session)
ventana.showMaximized()

sys.exit(app.exec())
