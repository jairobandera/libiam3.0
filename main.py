import sys

from PySide6.QtWidgets import QApplication

from ui.ventanaPrincipal.ventana_principal import VentanaPrincipal

app = QApplication(sys.argv)

with open(
    "utilidades/estilos.qss",
    "r",
    encoding="utf-8"
) as file:

    app.setStyleSheet(
        file.read()
    )

window = VentanaPrincipal()
window.showMaximized() #Inicia la ventana maximizada.

window.show()

sys.exit(app.exec())