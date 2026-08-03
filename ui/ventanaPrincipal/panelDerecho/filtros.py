from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from logica import paleta


class Filtros(QFrame):
    filtroSolicitado = Signal(object)
    restaurarSolicitado = Signal(object)

    def __init__(self):
        super().__init__()
        self.setObjectName("filtrosPanel")
        self.info_actual = {}
        self.frecuencia_detectada = None
        self.senales_disponibles = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        titulo = QLabel("Filtro de frecuencias")
        titulo.setObjectName("tituloPanel")
        subtitulo = QLabel("Configura qué parte de la señal querés conservar")
        subtitulo.setObjectName("subtituloPanel")
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)

        layout.addWidget(self._crear_seccion_destino())
        layout.addWidget(self._crear_seccion_configuracion())
        layout.addWidget(self._crear_seccion_resultado())
        layout.addStretch()
        self.setLayout(layout)

        self.tipo_filtro.currentIndexChanged.connect(self._actualizar_controles_tipo)
        self.senal_objetivo.currentIndexChanged.connect(self._actualizar_resumen)
        self.corte_unico.valueChanged.connect(self._actualizar_resumen)
        self.corte_inferior.valueChanged.connect(self._actualizar_resumen)
        self.corte_superior.valueChanged.connect(self._actualizar_resumen)
        self.orden.valueChanged.connect(self._actualizar_resumen)
        self.fs_control.valueChanged.connect(self._actualizar_limites_frecuencia)
        self.fs_control.valueChanged.connect(self._actualizar_resumen)
        self.btn_aplicar.clicked.connect(self._solicitar_filtro)
        self.btn_restaurar.clicked.connect(self._solicitar_restauracion)
        self._actualizar_controles_tipo()

    def _crear_seccion_destino(self):
        seccion = QFrame()
        seccion.setObjectName("seccionFiltro")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        titulo = QLabel("1. Elegí las señales")
        titulo.setObjectName("tituloSeccionMapeo")
        self.senal_objetivo = QComboBox()
        self.senal_objetivo.setObjectName("cmbSenalFiltro")
        self.senal_objetivo.addItem("Cargá un archivo CSV", None)
        self.senal_objetivo.setEnabled(False)

        ayuda = QLabel(
            "Podés aplicar una configuración a todas las señales visibles o "
            "trabajar con una señal por vez."
        )
        ayuda.setWordWrap(True)
        ayuda.setObjectName("lblDeteccion")

        layout.addWidget(titulo)
        layout.addWidget(self.senal_objetivo)
        layout.addWidget(ayuda)
        seccion.setLayout(layout)
        return seccion

    def _crear_seccion_configuracion(self):
        seccion = QFrame()
        seccion.setObjectName("seccionFiltro")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        titulo = QLabel("2. Definí qué conservar")
        titulo.setObjectName("tituloSeccionMapeo")
        titulo.setContentsMargins(10, 10, 10, 4)

        self.tipo_filtro = QComboBox()
        self.tipo_filtro.setObjectName("cmbFiltro")
        self.tipo_filtro.addItem("Pasa-bajos", "lowpass")
        self.tipo_filtro.addItem("Pasa-altos", "highpass")
        self.tipo_filtro.addItem("Pasa-banda", "bandpass")
        self.tipo_filtro.addItem("Rechazo banda", "bandstop")

        self.corte_unico = self._crear_control_frecuencia(20.0)
        self.corte_inferior = self._crear_control_frecuencia(30.0)
        self.corte_superior = self._crear_control_frecuencia(450.0)

        formulario = QFormLayout()
        formulario.setSpacing(5)
        formulario.setContentsMargins(8, 0, 8, 0)
        formulario.setLabelAlignment(Qt.AlignLeft)
        formulario.addRow("Modo:", self.tipo_filtro)

        self.lbl_corte_unico = QLabel("Límite:")
        self.lbl_corte_inferior = QLabel("Desde:")
        self.lbl_corte_superior = QLabel("Hasta:")
        formulario.addRow(self.lbl_corte_unico, self.corte_unico)
        formulario.addRow(self.lbl_corte_inferior, self.corte_inferior)
        formulario.addRow(self.lbl_corte_superior, self.corte_superior)

        self.lbl_orden = QLabel("Orden:")
        self.orden = QSpinBox()
        self.orden.setObjectName("spinFiltro")
        self.orden.setRange(1, 10)
        self.orden.setValue(4)
        formulario.addRow(self.lbl_orden, self.orden)

        self.lbl_fs = QLabel("Fs:")
        self.fs_control = self._crear_control_frecuencia(2000.0)
        self.fs_control.setDecimals(0)
        self.fs_control.setSingleStep(100)
        self.fs_control.setValue(2000)
        formulario.addRow(self.lbl_fs, self.fs_control)

        self.lbl_frecuencia = QLabel("Cargá un archivo para habilitar el filtro.")
        self.lbl_frecuencia.setWordWrap(True)
        self.lbl_frecuencia.setObjectName("lblFrecuenciaFiltro")
        self.lbl_frecuencia.setContentsMargins(10, 0, 10, 0)

        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setObjectName("resumenFiltro")
        self.lbl_resumen.setContentsMargins(10, 0, 10, 0)

        aclaracion = QLabel(
            "El cambio no es un corte vertical perfecto: el filtro atenúa "
            "gradualmente el contenido que queda fuera de lo elegido."
        )
        aclaracion.setWordWrap(True)
        aclaracion.setObjectName("lblDeteccion")
        aclaracion.setContentsMargins(10, 0, 10, 10)

        contenedor = QWidget()
        contenedor_layout = QVBoxLayout()
        contenedor_layout.setContentsMargins(0, 0, 0, 0)
        contenedor_layout.setSpacing(0)
        contenedor_layout.addWidget(titulo)
        contenedor_layout.addLayout(formulario)
        contenedor_layout.addWidget(self.lbl_frecuencia)
        contenedor_layout.addWidget(self.lbl_resumen)
        contenedor_layout.addWidget(aclaracion)
        contenedor_layout.addStretch()
        contenedor.setLayout(contenedor_layout)

        layout.addWidget(contenedor)
        seccion.setLayout(layout)
        return seccion

    def _crear_seccion_resultado(self):
        seccion = QFrame()
        seccion.setObjectName("seccionFiltro")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        titulo = QLabel("3. Compará el resultado")
        titulo.setObjectName("tituloSeccionMapeo")
        # La leyenda toma los colores reales de las curvas, así sigue al modo
        # daltónico en vez de nombrar un color que puede haber cambiado.
        self.lbl_leyenda_colores = QLabel()
        self.lbl_leyenda_colores.setObjectName("lblDeteccion")
        self.aplicar_paleta()
        leyenda = self.lbl_leyenda_colores

        botones = QHBoxLayout()
        self.btn_aplicar = QPushButton("Mostrar resultado")
        self.btn_aplicar.setObjectName("btnAplicarMapeo")
        self.btn_aplicar.setCursor(Qt.PointingHandCursor)
        self.btn_aplicar.setEnabled(False)
        self.btn_restaurar = QPushButton("Quitar filtro")
        self.btn_restaurar.setObjectName("btnResetMapeo")
        self.btn_restaurar.setCursor(Qt.PointingHandCursor)
        self.btn_restaurar.setEnabled(False)
        botones.addWidget(self.btn_aplicar, 1)
        botones.addWidget(self.btn_restaurar)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setWordWrap(True)
        self.lbl_estado.setObjectName("lblDeteccion")

        layout.addWidget(titulo)
        layout.addWidget(leyenda)
        layout.addLayout(botones)
        layout.addWidget(self.lbl_estado)
        seccion.setLayout(layout)
        return seccion

    @staticmethod
    def _crear_control_frecuencia(valor):
        control = QDoubleSpinBox()
        control.setObjectName("spinFiltro")
        control.setRange(0.01, 999_999.99)
        control.setDecimals(2)
        control.setSingleStep(1.0)
        control.setSuffix(" Hz")
        control.setValue(valor)
        control.setKeyboardTracking(False)
        return control

    def cargar_datos(self, info):
        self.info_actual = info or {}
        frecuencia_grafica = self.info_actual.get("frecuencia_grafica")
        if frecuencia_grafica:
            self.fs_control.blockSignals(True)
            self.fs_control.setValue(float(frecuencia_grafica))
            self.fs_control.blockSignals(False)
            self._actualizar_limites_frecuencia()
        else:
            self.lbl_frecuencia.setText(
                "El CSV no informa una frecuencia de muestreo. "
                "Ingresala manualmente."
            )
        self.lbl_estado.clear()
        self._actualizar_resumen()

    def cargar_senales(self, senales):
        seleccion_anterior = self.senal_objetivo.currentData()
        self.senales_disponibles = [
            senal for senal in (senales or []) if senal.get("visible", True)
        ]

        self.senal_objetivo.blockSignals(True)
        self.senal_objetivo.clear()
        if self.senales_disponibles:
            self.senal_objetivo.addItem("Todas las señales visibles", None)
            for senal in self.senales_disponibles:
                self.senal_objetivo.addItem(senal["nombre"], senal["columna"])

            indice_anterior = self.senal_objetivo.findData(seleccion_anterior)
            self.senal_objetivo.setCurrentIndex(max(0, indice_anterior))
            self.senal_objetivo.setEnabled(True)
        else:
            self.senal_objetivo.addItem("No hay señales visibles", None)
            self.senal_objetivo.setEnabled(False)
        self.senal_objetivo.blockSignals(False)
        self._actualizar_resumen()

    def _actualizar_limites_frecuencia(self, _valor=None):
        fs = self.fs_control.value()
        if fs <= 0:
            return

        nyquist = fs / 2
        margen = max(0.01, nyquist * 0.000001)
        limite = max(0.02, nyquist - margen)
        for control in (self.corte_unico, self.corte_inferior, self.corte_superior):
            control.setMaximum(limite)

        if self.corte_unico.value() >= limite:
            self.corte_unico.setValue(max(0.01, min(20.0, limite / 2)))

        inferior = min(30.0, limite * 0.25)
        superior = min(450.0, limite * 0.8)
        if superior <= inferior:
            inferior = max(0.01, limite * 0.25)
            superior = max(inferior + 0.01, limite * 0.75)
        self.corte_inferior.setValue(inferior)
        self.corte_superior.setValue(min(limite, superior))

        self.lbl_frecuencia.setText(
            f"Fs: {fs:g} Hz · Nyquist: {nyquist:g} Hz · "
            f"Límites &lt; {limite:g} Hz."
        )

    def _actualizar_controles_tipo(self, _indice=None):
        es_banda = self.tipo_filtro.currentData() in ("bandpass", "bandstop")
        self.lbl_corte_unico.setVisible(not es_banda)
        self.corte_unico.setVisible(not es_banda)
        self.lbl_corte_inferior.setVisible(es_banda)
        self.corte_inferior.setVisible(es_banda)
        self.lbl_corte_superior.setVisible(es_banda)
        self.corte_superior.setVisible(es_banda)
        self._actualizar_resumen()

    def _columnas_objetivo(self):
        columna = self.senal_objetivo.currentData()
        if columna:
            return [columna]
        return [senal["columna"] for senal in self.senales_disponibles]

    def _validar_configuracion(self):
        fs = self.fs_control.value()
        if fs <= 0:
            return False, "La frecuencia de muestreo debe ser mayor que cero."
        if not self._columnas_objetivo():
            return False, "No hay señales visibles para filtrar."

        limite = fs / 2
        tipo = self.tipo_filtro.currentData()
        if tipo in ("bandpass", "bandstop"):
            inferior = self.corte_inferior.value()
            superior = self.corte_superior.value()
            if inferior >= superior:
                return False, "El valor «Desde» debe ser menor que «Hasta»."
            if superior >= limite:
                return False, f"El valor «Hasta» debe ser menor que {limite:g} Hz."
        elif self.corte_unico.value() >= limite:
            return False, f"El límite debe ser menor que {limite:g} Hz."
        return True, ""

    def _actualizar_resumen(self, _valor=None):
        tipo = self.tipo_filtro.currentData()
        orden = self.orden.value()
        if tipo == "lowpass":
            texto = (
                "Se conservará principalmente el contenido por debajo de "
                f"{self.corte_unico.value():g} Hz (orden {orden})."
            )
        elif tipo == "highpass":
            texto = (
                "Se conservará principalmente el contenido por encima de "
                f"{self.corte_unico.value():g} Hz (orden {orden})."
            )
        elif tipo == "bandstop":
            texto = (
                "Se eliminará principalmente el contenido entre "
                f"{self.corte_inferior.value():g} y "
                f"{self.corte_superior.value():g} Hz (orden {orden})."
            )
        else:
            texto = (
                "Se conservará principalmente el contenido entre "
                f"{self.corte_inferior.value():g} y "
                f"{self.corte_superior.value():g} Hz (orden {orden})."
            )

        es_valida, error = self._validar_configuracion()
        self.lbl_resumen.setText(texto if es_valida else f"{texto}\n{error}")
        self.lbl_resumen.setProperty("valido", "true" if es_valida else "false")
        self.lbl_resumen.style().unpolish(self.lbl_resumen)
        self.lbl_resumen.style().polish(self.lbl_resumen)
        self.btn_aplicar.setEnabled(es_valida)
        self.btn_restaurar.setEnabled(bool(self._columnas_objetivo()))

    def _crear_configuracion(self):
        tipo = self.tipo_filtro.currentData()
        if tipo in ("bandpass", "bandstop"):
            frecuencias_corte = (
                self.corte_inferior.value(),
                self.corte_superior.value(),
            )
        else:
            frecuencias_corte = self.corte_unico.value()

        return {
            "frecuencia_muestreo": self.fs_control.value(),
            "tipo": tipo,
            "frecuencias_corte": frecuencias_corte,
            "orden": self.orden.value(),
            "columnas": self._columnas_objetivo(),
        }

    def _solicitar_filtro(self):
        es_valida, error = self._validar_configuracion()
        if not es_valida:
            self.actualizar_estado(False, error)
            return
        self.filtroSolicitado.emit(self._crear_configuracion())

    def _solicitar_restauracion(self):
        columnas = self._columnas_objetivo()
        if columnas:
            self.restaurarSolicitado.emit(columnas)

    def aplicar_paleta(self):
        """Actualiza la leyenda de colores con la paleta activa."""
        self.lbl_leyenda_colores.setText(
            f'<span style="color:{paleta.color_senal_original()}; font-weight:600;">'
            "▬ Original</span>"
            " &nbsp;&nbsp; "
            f'<span style="color:{paleta.color_senal_filtrada()}; font-weight:600;">'
            "▬ Filtrada</span>"
        )

    def actualizar_estado(self, exito, mensaje):
        # El símbolo acompaña al color: en modo daltónico el verde y el rojo
        # pueden verse casi iguales, el ✓/✕ no.
        color = "#66BB6A" if exito else "#EF5350"
        if paleta.modo_daltonico_activo():
            color = "#56B4E9" if exito else "#D55E00"
        simbolo = "✓" if exito else "✕"
        self.lbl_estado.setStyleSheet(f"color: {color};")
        self.lbl_estado.setText(f"{simbolo} {mensaje}" if mensaje else "")
