from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ui.ventanaPrincipal.panelDerecho.panelCalculo import PanelCalculo


class VentanaRegion(QDialog):
    """Ventana que muestra el recorte de un rango para crear sub-rangos dentro.

    Reutiliza ``GraficaSenal`` en modo selección: dos clics sobre la gráfica
    proponen un sub-rango, que el área central valida y agrega. La sección de
    fórmulas de la derecha es el mismo ``PanelCalculo`` del panel principal, así
    el cálculo de sub-rangos comparte el mismo componente (y el mismo aspecto).
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
        self.resize(1180, 540)
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

        # Izquierda: encabezado + acción de sub-rangos + gráfica.
        caja_izquierda = QWidget()
        layout_izquierda = QVBoxLayout()
        layout_izquierda.setContentsMargins(0, 0, 0, 0)
        layout_izquierda.setSpacing(8)
        layout_izquierda.addWidget(encabezado)
        layout_izquierda.addLayout(fila_botones)

        self.grafica = GraficaSenal(
            titulo,
            unidad=unidad,
            etiqueta_x=etiqueta_x,
            columna=columna,
        )
        self.grafica.set_datos(x, y_original, y_filtrada)
        self.grafica.set_modo_seleccion_rango(False)
        self.grafica.rangoPropuesto.connect(self._on_rango_propuesto)
        layout_izquierda.addWidget(self.grafica, 1)
        caja_izquierda.setLayout(layout_izquierda)

        # Derecha: sección de cálculo reutilizada del panel principal. El
        # cálculo de sub-rangos llega luego via las señales del área central.
        self.panel_calculo = PanelCalculo()
        self.panel_calculo.setFixedWidth(300)
        # La fuente (filtrada/original) depende de si esta señal tiene filtro.
        self.panel_calculo.set_hay_filtro(y_filtrada is not None)

        separador = QSplitter(Qt.Horizontal)
        separador.addWidget(caja_izquierda)
        separador.addWidget(self.panel_calculo)
        separador.setSizes([840, 300])
        separador.setCollapsible(0, False)
        layout.addWidget(separador, 1)

        self.setLayout(layout)

    def _on_seleccion_toggled(self, activo):
        self.grafica.set_modo_seleccion_rango(activo)

    def _on_rango_propuesto(self, _grafica, desde, hasta):
        self.subRangoPropuesto.emit(int(desde), int(hasta))

    def mostrar_subrangos(self, subrangos):
        self.grafica.mostrar_rangos(subrangos)

    def formula_seleccionada(self):
        """Clave de la fórmula elegida en el panel de la derecha."""
        return self.panel_calculo.formula_seleccionada()

    def mostrar_resultados_formula(self, datos):
        """Vuelca en el panel los resultados calculados por el área central."""
        self.panel_calculo.mostrar_resultados(datos)

    def aplicar_paleta(self):
        """Repinta la gráfica al cambiar la accesibilidad (colores y estilos).

        La gráfica es un ``GraficaSenal``: todo el renderizado accesible
        (paleta, grosor, estilos y tooltips) se hereda de ``areaCentralGraficas``.
        """
        self.grafica.aplicar_paleta()
