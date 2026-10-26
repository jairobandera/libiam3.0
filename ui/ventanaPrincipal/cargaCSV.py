import os

from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from logica.lector_csv import leer_csv_rapido


class TrabajadorCargaCSV(QObject):
    progresoCambiado = Signal(int, str)
    cargaCompletada = Signal(object, object)
    cargaFallida = Signal(str)

    def __init__(self, ruta_archivo):
        super().__init__()
        self.ruta_archivo = ruta_archivo

    @Slot()
    def ejecutar(self):
        try:
            df, metadatos = leer_csv_rapido(
                self.ruta_archivo,
                self.progresoCambiado.emit,
            )
        except Exception as exc:
            self.cargaFallida.emit(str(exc))
            return
        self.cargaCompletada.emit(df, metadatos)


class CargaCSVDialog(QDialog):
    def __init__(self, ruta_archivo, parent=None):
        super().__init__(parent)
        self._activo = True
        self._porcentaje = 0
        self._tamano = self._formatear_tamano(ruta_archivo)

        self.setObjectName("dialogoCargaCSV")
        self.setWindowTitle("Cargando CSV")
        self.setModal(True)
        self.setFixedWidth(460)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self._crear_interfaz(os.path.basename(ruta_archivo))

    def _crear_interfaz(self, nombre_archivo):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        titulo = QLabel("Cargando archivo CSV")
        titulo.setObjectName("tituloCargaCSV")

        self.lbl_archivo = QLabel(nombre_archivo)
        self.lbl_archivo.setObjectName("archivoCargaCSV")
        self.lbl_archivo.setWordWrap(True)

        self.lbl_estado = QLabel("Preparando la carga…")
        self.lbl_estado.setObjectName("estadoCargaCSV")

        self.barra = QProgressBar()
        self.barra.setObjectName("progresoCargaCSV")
        self.barra.setRange(0, 100)
        self.barra.setValue(0)
        self.barra.setFormat("%p%")

        self.lbl_detalle = QLabel(self._tamano)
        self.lbl_detalle.setObjectName("detalleCargaCSV")

        layout.addWidget(titulo)
        layout.addWidget(self.lbl_archivo)
        layout.addSpacing(4)
        layout.addWidget(self.lbl_estado)
        layout.addWidget(self.barra)
        layout.addWidget(self.lbl_detalle)

    @staticmethod
    def _formatear_tamano(ruta_archivo):
        try:
            bytes_archivo = os.path.getsize(ruta_archivo)
        except OSError:
            return ""

        unidades = ("B", "KB", "MB", "GB")
        valor = float(bytes_archivo)
        unidad = unidades[0]
        for unidad in unidades:
            if valor < 1024 or unidad == unidades[-1]:
                break
            valor /= 1024
        decimales = 0 if unidad in ("B", "KB") else 1
        return f"{valor:.{decimales}f} {unidad}"

    @Slot(int, str)
    def actualizar(self, porcentaje, mensaje):
        self._porcentaje = max(self._porcentaje, min(100, int(porcentaje)))
        self.barra.setValue(self._porcentaje)
        self.lbl_estado.setText(mensaje)

    def mostrar_columnas_omitidas(self, cantidad):
        if cantidad:
            self.lbl_detalle.setText(
                f"{self._tamano} · {cantidad} canales omitidos"
            )

    def finalizar(self, exito=True):
        self._activo = False
        if exito:
            super().accept()
        else:
            super().reject()

    def reject(self):
        if not self._activo:
            super().reject()

    def closeEvent(self, event):
        if self._activo:
            event.ignore()
            return
        super().closeEvent(event)
