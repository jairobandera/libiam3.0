from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class VentanaRegion(QDialog):
    """Ventana que muestra el recorte de un rango para crear sub-rangos dentro.

    Reutiliza ``GraficaSenal`` en modo selección: dos clics sobre la gráfica
    proponen un sub-rango, que el área central valida y agrega.
    """

    subRangoPropuesto = Signal(int, int)

    def __init__(
        self,
        parent=None,
        titulo="",
        etiqueta_x="Frame",
        unidad=None,
        x=None,
        y_original=None,
        y_filtrada=None,
        columna=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(titulo or "Sub-rangos")
        self.setModal(False)
        self.resize(900, 520)
        self.setStyleSheet("QDialog { background-color: #1E1E1E; }")
        self._init_ui(titulo, etiqueta_x, unidad, x, y_original, y_filtrada, columna)

    def _init_ui(self, titulo, etiqueta_x, unidad, x, y_original, y_filtrada, columna):
        # Import local para evitar el ciclo con areaCentralGraficas.
        from ui.ventanaPrincipal.areaCentralGraficas import GraficaSenal

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        encabezado = QLabel(titulo)
        encabezado.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #FFFFFF;"
        )
        encabezado.setWordWrap(True)
        layout.addWidget(encabezado)

        # Botón para activar la selección de sub-rangos (igual que en la principal).
        fila_botones = QHBoxLayout()
        self.btn_seleccionar = QPushButton("Seleccionar sub-rango")
        self.btn_seleccionar.setObjectName("btnSeleccionarRango")
        self.btn_seleccionar.setCursor(Qt.PointingHandCursor)
        self.btn_seleccionar.setCheckable(True)
        self.btn_seleccionar.toggled.connect(self._on_seleccion_toggled)
        fila_botones.addWidget(self.btn_seleccionar)
        fila_botones.addStretch()
        layout.addLayout(fila_botones)

        self.grafica = GraficaSenal(
            titulo,
            unidad=unidad,
            etiqueta_x=etiqueta_x,
            columna=columna,
        )
        self.grafica.set_datos(x, y_original, y_filtrada)
        self.grafica.set_modo_seleccion_rango(False)
        self.grafica.rangoPropuesto.connect(self._on_rango_propuesto)
        layout.addWidget(self.grafica, 1)

        self.setLayout(layout)

    def _on_seleccion_toggled(self, activo):
        self.grafica.set_modo_seleccion_rango(activo)

    def _on_rango_propuesto(self, _grafica, desde, hasta):
        self.subRangoPropuesto.emit(int(desde), int(hasta))

    def mostrar_subrangos(self, subrangos):
        self.grafica.mostrar_rangos(subrangos)

    def aplicar_paleta(self):
        """Repinta la gráfica cuando cambia la paleta (modo daltónico)."""
        self.grafica.aplicar_paleta()
