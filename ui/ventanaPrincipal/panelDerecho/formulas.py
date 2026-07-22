from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class Formulas(QFrame):
    """Selecciona qué rangos estarán disponibles para los cálculos."""

    eliminarRangosSolicitado = Signal(object)
    limpiarRangosSolicitado = Signal()
    seleccionRangosCambiada = Signal(object)

    def __init__(self):
        super().__init__()
        self.setObjectName("formulasPanel")
        self.checkboxes = {}
        self.rangos = []
        self.estados_seleccion = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        titulo = QLabel("Rangos para cálculos")
        titulo.setObjectName("tituloPanel")
        subtitulo = QLabel("Elegí todos, algunos, pares o impares")
        subtitulo.setObjectName("subtituloPanel")

        seleccion = QFrame()
        seleccion.setObjectName("seccionMapeo")
        seleccion_layout = QVBoxLayout()
        seleccion_layout.setContentsMargins(10, 10, 10, 10)
        seleccion_layout.setSpacing(8)

        ayuda = QLabel(
            "Los rangos pertenecen a la gráfica donde se marcan. Elegí una "
            "señal y seleccioná los que usarán las operaciones de cálculo."
        )
        ayuda.setWordWrap(True)
        ayuda.setObjectName("lblDeteccion")

        fila_senal = QHBoxLayout()
        fila_senal.addWidget(QLabel("Señal:"))
        self.cmb_senal = QComboBox()
        self.cmb_senal.setMinimumWidth(190)
        fila_senal.addWidget(self.cmb_senal, 1)

        accesos = QGridLayout()
        for indice, (texto, modo) in enumerate(
            (("Todos", "todos"), ("Pares", "pares"), ("Impares", "impares"), ("Ninguno", "ninguno"))
        ):
            boton = QPushButton(texto)
            boton.setObjectName("btnResetMapeo")
            boton.setCursor(Qt.PointingHandCursor)
            boton.clicked.connect(lambda _, valor=modo: self._seleccionar(valor))
            accesos.addWidget(boton, indice // 2, indice % 2)

        self.contenedor = QWidget()
        self.layout_rangos = QVBoxLayout()
        self.layout_rangos.setContentsMargins(0, 0, 0, 0)
        self.layout_rangos.setSpacing(6)
        self.contenedor.setLayout(self.layout_rangos)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(250)
        self.scroll.setWidget(self.contenedor)

        self.lbl_resumen = QLabel("No hay rangos marcados.")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setObjectName("lblDeteccion")
        self.lbl_error = QLabel("")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setStyleSheet("color: #EF5350;")

        botones = QHBoxLayout()
        self.btn_eliminar = QPushButton("Eliminar de esta señal")
        self.btn_eliminar.setObjectName("btnResetMapeo")
        self.btn_limpiar = QPushButton("Eliminar todos")
        self.btn_limpiar.setObjectName("btnResetMapeo")
        self.btn_limpiar.setToolTip("Elimina los rangos de todas las señales")
        botones.addWidget(self.btn_eliminar)
        botones.addWidget(self.btn_limpiar)

        seleccion_layout.addWidget(ayuda)
        seleccion_layout.addLayout(fila_senal)
        seleccion_layout.addLayout(accesos)
        seleccion_layout.addWidget(self.scroll)
        seleccion_layout.addWidget(self.lbl_resumen)
        seleccion_layout.addWidget(self.lbl_error)
        seleccion_layout.addLayout(botones)
        seleccion.setLayout(seleccion_layout)

        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addWidget(seleccion)
        layout.addStretch()
        self.setLayout(layout)

        self.btn_eliminar.clicked.connect(self._eliminar_seleccionados)
        self.btn_limpiar.clicked.connect(lambda: self.limpiarRangosSolicitado.emit())
        self.cmb_senal.currentIndexChanged.connect(self._renderizar_rangos_actuales)
        self._actualizar_botones()

    def cargar_rangos(self, rangos):
        self._guardar_estados_visibles()
        ids_anteriores = {self._id_rango(rango) for rango in self.rangos}
        self.rangos = list(rangos or [])
        rangos_nuevos = [
            rango
            for rango in self.rangos
            if self._id_rango(rango) not in ids_anteriores
        ]
        ids_validos = {self._id_rango(rango) for rango in self.rangos}
        self.estados_seleccion = {
            identificador: self.estados_seleccion.get(identificador, True)
            for identificador in ids_validos
        }

        columna_actual = (
            rangos_nuevos[-1].get("columna", "__global__")
            if rangos_nuevos
            else self.cmb_senal.currentData()
        )
        senales = []
        for rango in self.rangos:
            columna = rango.get("columna", "__global__")
            if columna not in {item[0] for item in senales}:
                senales.append((columna, rango.get("senal", str(columna))))

        self.cmb_senal.blockSignals(True)
        self.cmb_senal.clear()
        for columna, nombre in senales:
            self.cmb_senal.addItem(nombre, columna)
        if columna_actual is not None:
            indice = self.cmb_senal.findData(columna_actual)
            if indice >= 0:
                self.cmb_senal.setCurrentIndex(indice)
        self.cmb_senal.setEnabled(bool(senales))
        self.cmb_senal.blockSignals(False)
        self._renderizar_rangos_actuales()

    @staticmethod
    def _id_rango(rango):
        return rango.get("id", rango.get("numero"))

    def _guardar_estados_visibles(self):
        for identificador, checkbox in self.checkboxes.items():
            self.estados_seleccion[identificador] = checkbox.isChecked()

    def _renderizar_rangos_actuales(self):
        self._guardar_estados_visibles()
        self.checkboxes = {}
        while self.layout_rangos.count():
            item = self.layout_rangos.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        columna_actual = self.cmb_senal.currentData()
        rangos_visibles = [
            rango
            for rango in self.rangos
            if rango.get("columna", "__global__") == columna_actual
        ]

        if not rangos_visibles:
            texto = (
                "Todavía no se seleccionaron rangos en esta señal."
                if self.rangos
                else "Todavía no se seleccionaron rangos."
            )
            vacio = QLabel(texto)
            vacio.setObjectName("lblDeteccion")
            vacio.setAlignment(Qt.AlignCenter)
            self.layout_rangos.addWidget(vacio)

        for rango in rangos_visibles:
            numero = int(rango["numero"])
            identificador = self._id_rango(rango)
            fuente = " · datos filtrados" if rango.get("fuente") == "filtrada" else ""
            checkbox = QCheckBox(
                f"Rango {numero}: {int(rango['desde'])} – {int(rango['hasta'])}{fuente}"
            )
            checkbox.setChecked(self.estados_seleccion.get(identificador, True))
            checkbox.setStyleSheet(
                f"QCheckBox {{ color: {rango['color']}; font-weight: 600; }}"
            )
            checkbox.toggled.connect(
                lambda activo, ident=identificador: self._cambiar_estado(ident, activo)
            )
            self.checkboxes[identificador] = checkbox
            self.layout_rangos.addWidget(checkbox)

        self.layout_rangos.addStretch()
        self.lbl_error.clear()
        self._emitir_seleccion()
        self._actualizar_botones()

    def _seleccionar(self, modo):
        for identificador, checkbox in self.checkboxes.items():
            numero = next(
                int(rango["numero"])
                for rango in self.rangos
                if self._id_rango(rango) == identificador
            )
            if modo == "todos":
                activo = True
            elif modo == "pares":
                activo = numero % 2 == 0
            elif modo == "impares":
                activo = numero % 2 == 1
            else:
                activo = False
            checkbox.blockSignals(True)
            checkbox.setChecked(activo)
            checkbox.blockSignals(False)
            self.estados_seleccion[identificador] = activo
        self._emitir_seleccion()

    def obtener_rangos_seleccionados(self):
        return [
            identificador
            for identificador, activo in self.estados_seleccion.items()
            if activo
        ]

    def _obtener_visibles_seleccionados(self):
        return [
            identificador
            for identificador, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

    def _cambiar_estado(self, identificador, activo):
        self.estados_seleccion[identificador] = activo
        self._emitir_seleccion()

    def _emitir_seleccion(self):
        seleccionados = self.obtener_rangos_seleccionados()
        seleccionados_visibles = self._obtener_visibles_seleccionados()
        total = len(self.checkboxes)
        self.lbl_resumen.setText(
            f"{len(seleccionados_visibles)} de {total} rango(s) seleccionados en esta señal."
            if total
            else "No hay rangos marcados."
        )
        self.seleccionRangosCambiada.emit(seleccionados)
        self._actualizar_botones()

    def _eliminar_seleccionados(self):
        seleccionados = self._obtener_visibles_seleccionados()
        if seleccionados:
            self.eliminarRangosSolicitado.emit(seleccionados)

    def _actualizar_botones(self):
        self.btn_eliminar.setEnabled(bool(self._obtener_visibles_seleccionados()))
        self.btn_limpiar.setEnabled(bool(self.rangos))

    def mostrar_error_rango(self, mensaje):
        self.lbl_error.setStyleSheet("color: #EF5350;")
        self.lbl_error.setText(mensaje)

    def mostrar_aviso_rango(self, mensaje):
        self.lbl_error.setStyleSheet("color: #66BB6A;")
        self.lbl_error.setText(mensaje)
