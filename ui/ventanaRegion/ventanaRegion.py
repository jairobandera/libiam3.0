from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from logica import formulas as formulas_logica
from ui.ventanaPrincipal.panelDerecho.panelCalculo import PanelCalculo


class VentanaRegion(QDialog):
    """Ventana que muestra el recorte de un intervalo para crear sub-intervalos dentro.

    Reutiliza ``GraficaSenal`` en modo selección: dos clics sobre la gráfica
    proponen un sub-intervalo, que el área central valida y agrega. La sección de
    fórmulas de la derecha es el mismo ``PanelCalculo`` del panel principal, así
    el cálculo de sub-intervalos comparte el mismo componente (y el mismo aspecto).
    """

    subIntervaloPropuesto = Signal(int, int)

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
        permitir_gestion_formulas=False,
    ):
        super().__init__(parent)
        self.formulas_activas = {}
        self._calculos_formulas = {}
        self._seleccion_subintervalos = {}
        self.setWindowTitle(titulo or "Sub-intervalos")
        self.setModal(False)
        self.resize(1180, 540)
        self.setStyleSheet("QDialog { background-color: #1E1E1E; }")
        self._init_ui(
            titulo,
            etiqueta_x,
            unidad,
            x,
            y_original,
            y_filtrada,
            columna,
            permitir_gestion_formulas,
        )

    def _init_ui(
        self,
        titulo,
        etiqueta_x,
        unidad,
        x,
        y_original,
        y_filtrada,
        columna,
        permitir_gestion_formulas,
    ):
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

        # Botón para activar la selección de sub-intervalos (igual que en la principal).
        fila_botones = QHBoxLayout()
        self.btn_seleccionar = QPushButton("Seleccionar sub-intervalo")
        self.btn_seleccionar.setObjectName("btnSeleccionarIntervalo")
        self.btn_seleccionar.setCursor(Qt.PointingHandCursor)
        self.btn_seleccionar.setCheckable(True)
        self.btn_seleccionar.toggled.connect(self._on_seleccion_toggled)
        fila_botones.addWidget(self.btn_seleccionar)
        fila_botones.addStretch()

        # Izquierda: encabezado + acción de sub-intervalos + gráfica.
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
        self.grafica.set_modo_seleccion_intervalo(False)
        self.grafica.intervaloPropuesto.connect(self._on_intervalo_propuesto)
        layout_izquierda.addWidget(self.grafica, 1)
        caja_izquierda.setLayout(layout_izquierda)

        # Derecha: selección de sub-intervalos y cálculo reutilizado del principal.
        panel_derecho = QWidget()
        layout_derecho = QVBoxLayout()
        layout_derecho.setContentsMargins(0, 0, 0, 0)
        layout_derecho.setSpacing(8)
        layout_derecho.addWidget(self._crear_selector_subintervalos())

        self.panel_calculo = PanelCalculo(
            permitir_gestion=permitir_gestion_formulas
        )
        self.panel_calculo.setMinimumWidth(286)
        # La fuente (filtrada/original) depende de si esta señal tiene filtro.
        self.panel_calculo.set_hay_filtro(y_filtrada is not None)
        layout_derecho.addWidget(self.panel_calculo)
        layout_derecho.addStretch()
        panel_derecho.setLayout(layout_derecho)

        scroll_derecho = QScrollArea()
        scroll_derecho.setWidgetResizable(True)
        scroll_derecho.setFrameShape(QFrame.NoFrame)
        scroll_derecho.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_derecho.setMinimumWidth(310)
        scroll_derecho.setWidget(panel_derecho)

        separador = QSplitter(Qt.Horizontal)
        separador.addWidget(caja_izquierda)
        separador.addWidget(scroll_derecho)
        separador.setSizes([840, 320])
        separador.setCollapsible(0, False)
        layout.addWidget(separador, 1)

        self.setLayout(layout)

    def _crear_selector_subintervalos(self):
        bloque = QFrame()
        bloque.setObjectName("seccionFormulas")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        titulo = QLabel("Sub-intervalos para calcular")
        titulo.setObjectName("tituloSeccionMapeo")
        layout.addWidget(titulo)

        fila = QHBoxLayout()
        btn_todos = QPushButton("Todos")
        btn_todos.setObjectName("btnResetMapeo")
        btn_todos.clicked.connect(lambda: self._marcar_subintervalos(True))
        btn_ninguno = QPushButton("Ninguno")
        btn_ninguno.setObjectName("btnResetMapeo")
        btn_ninguno.clicked.connect(lambda: self._marcar_subintervalos(False))
        fila.addWidget(btn_todos)
        fila.addWidget(btn_ninguno)
        layout.addLayout(fila)

        self.lista_subintervalos = QListWidget()
        self.lista_subintervalos.setMaximumHeight(118)
        self.lista_subintervalos.setStyleSheet(
            "QListWidget { background:#252526; color:#E8E8E8; "
            "border:1px solid #3E3E42; border-radius:4px; }"
        )
        layout.addWidget(self.lista_subintervalos)
        bloque.setLayout(layout)
        return bloque

    def _on_seleccion_toggled(self, activo):
        self.grafica.set_modo_seleccion_intervalo(activo)

    def _on_intervalo_propuesto(self, _grafica, desde, hasta):
        self.subIntervaloPropuesto.emit(int(desde), int(hasta))

    def mostrar_subintervalos(self, subintervalos):
        subintervalos = list(subintervalos or [])
        self._guardar_seleccion_subintervalos()
        self.grafica.mostrar_intervalos(subintervalos)
        self.lista_subintervalos.clear()
        ids_validos = []
        for subintervalo in subintervalos:
            numero = int(getattr(subintervalo, "numero", 0))
            identificador = self._id_subintervalo(numero)
            ids_validos.append(identificador)
            nombre = getattr(subintervalo, "nombre", "") or f"Sub-intervalo {numero}"
            desde = int(getattr(subintervalo, "desde", 0))
            hasta = int(getattr(subintervalo, "hasta", 0))
            item = QListWidgetItem(f"{nombre}: {desde}–{hasta}")
            item.setData(Qt.UserRole, identificador)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            activo = self._seleccion_subintervalos.get(identificador, True)
            item.setCheckState(Qt.Checked if activo else Qt.Unchecked)
            self.lista_subintervalos.addItem(item)
        self._seleccion_subintervalos = {
            identificador: self._seleccion_subintervalos.get(identificador, True)
            for identificador in ids_validos
        }

    def _id_subintervalo(self, numero):
        columna, numero_padre = self.clave_subgestor
        return f"{columna}::{int(numero_padre)}::sub::{int(numero)}"

    def _guardar_seleccion_subintervalos(self):
        if not hasattr(self, "lista_subintervalos"):
            return
        for indice in range(self.lista_subintervalos.count()):
            item = self.lista_subintervalos.item(indice)
            self._seleccion_subintervalos[item.data(Qt.UserRole)] = (
                item.checkState() == Qt.Checked
            )

    def _marcar_subintervalos(self, activo):
        estado = Qt.Checked if activo else Qt.Unchecked
        for indice in range(self.lista_subintervalos.count()):
            self.lista_subintervalos.item(indice).setCheckState(estado)
        self._guardar_seleccion_subintervalos()

    def subintervalos_seleccionados(self):
        self._guardar_seleccion_subintervalos()
        return [
            identificador
            for identificador, activo in self._seleccion_subintervalos.items()
            if activo
        ]

    def formula_seleccionada(self):
        """Clave de la fórmula elegida en el panel de la derecha."""
        return self.panel_calculo.formula_seleccionada()

    def mostrar_resultados_formula(self, datos):
        """Vuelca en el panel los resultados calculados por el área central."""
        self.panel_calculo.mostrar_resultados(datos)

    def registrar_calculo_formula(self, aplicaciones, clave, calculo):
        """Conserva y redibuja todas las fórmulas aplicadas a sub-intervalos."""
        self._calculos_formulas[clave] = calculo
        calculos = {
            activa: self._calculos_formulas[activa]
            for activa in aplicaciones
            if activa in self._calculos_formulas
        }
        self.establecer_calculos_formulas(aplicaciones, calculos)

    def establecer_calculos_formulas(self, aplicaciones, calculos):
        self.formulas_activas = dict(aplicaciones)
        self._calculos_formulas = dict(calculos)
        por_grafica = formulas_logica.preparar_curvas_formulas_por_grafica(
            self._calculos_formulas,
            self.formulas_activas,
        )
        self.grafica.set_curvas_formulas(
            por_grafica.get(self.grafica.columna, [])
        )
        for clave in reversed(self.formulas_activas):
            calculo = self._calculos_formulas.get(clave)
            if calculo is not None:
                self.mostrar_resultados_formula(calculo["datos_panel"])
                return
        self.panel_calculo.limpiar_resultados()

    def quitar_formulas_aplicadas(self):
        self.formulas_activas = {}
        self._calculos_formulas = {}
        self.grafica.limpiar_curva_formula()
        self.panel_calculo.limpiar_resultados()

    def aplicar_paleta(self):
        """Repinta la gráfica al cambiar la accesibilidad (colores y estilos).

        La gráfica es un ``GraficaSenal``: todo el renderizado accesible
        (paleta, grosor, estilos y tooltips) se hereda de ``areaCentralGraficas``.
        """
        self.grafica.aplicar_paleta()
