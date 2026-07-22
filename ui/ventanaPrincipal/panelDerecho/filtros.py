from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


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
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        titulo = QLabel("2. Definí qué conservar")
        titulo.setObjectName("tituloSeccionMapeo")

        self.tipo_filtro = QComboBox()
        self.tipo_filtro.setObjectName("cmbFiltro")
        self.tipo_filtro.addItem("Menores al límite (pasa-bajos)", "lowpass")
        self.tipo_filtro.addItem("Mayores al límite (pasa-altos)", "highpass")
        self.tipo_filtro.addItem("Entre dos límites (pasa-banda)", "bandpass")

        self.corte_unico = self._crear_control_frecuencia(20.0)
        self.corte_inferior = self._crear_control_frecuencia(30.0)
        self.corte_superior = self._crear_control_frecuencia(450.0)

        formulario = QFormLayout()
        formulario.setSpacing(8)
        formulario.addRow("Modo:", self.tipo_filtro)

        self.lbl_corte_unico = QLabel("Límite:")
        self.lbl_corte_inferior = QLabel("Desde:")
        self.lbl_corte_superior = QLabel("Hasta:")
        formulario.addRow(self.lbl_corte_unico, self.corte_unico)
        formulario.addRow(self.lbl_corte_inferior, self.corte_inferior)
        formulario.addRow(self.lbl_corte_superior, self.corte_superior)

        self.lbl_frecuencia = QLabel("Cargá un archivo para habilitar el filtro.")
        self.lbl_frecuencia.setWordWrap(True)
        self.lbl_frecuencia.setObjectName("lblFrecuenciaFiltro")

        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setObjectName("resumenFiltro")

        aclaracion = QLabel(
            "El cambio no es un corte vertical perfecto: el filtro atenúa "
            "gradualmente el contenido que queda fuera de lo elegido."
        )
        aclaracion.setWordWrap(True)
        aclaracion.setObjectName("lblDeteccion")

        layout.addWidget(titulo)
        layout.addLayout(formulario)
        layout.addWidget(self.lbl_frecuencia)
        layout.addWidget(self.lbl_resumen)
        layout.addWidget(aclaracion)
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
        leyenda = QLabel(
            '<span style="color:#4FC3F7; font-weight:600;">Azul: original</span>'
            ' &nbsp;&nbsp; '
            '<span style="color:#FFB300; font-weight:600;">Naranja: filtrada</span>'
        )
        leyenda.setObjectName("lblDeteccion")

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
            self.frecuencia_detectada = float(frecuencia_grafica)
            self._actualizar_limites_frecuencia()
            limite = self.frecuencia_detectada / 2
            self.lbl_frecuencia.setText(
                f"Frecuencia disponible: {self.frecuencia_detectada:g} Hz. "
                f"Los límites deben ser menores que {limite:g} Hz."
            )
        else:
            self.frecuencia_detectada = None
            self.lbl_frecuencia.setText(
                "El CSV no informa una frecuencia de muestreo, por lo que no "
                "se puede calcular el filtro de forma segura."
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

    def _actualizar_limites_frecuencia(self):
        if not self.frecuencia_detectada:
            return

        nyquist = self.frecuencia_detectada / 2
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

    def _actualizar_controles_tipo(self, _indice=None):
        es_banda = self.tipo_filtro.currentData() == "bandpass"
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
        if not self.frecuencia_detectada:
            return False, "Falta la frecuencia de muestreo."
        if not self._columnas_objetivo():
            return False, "No hay señales visibles para filtrar."

        limite = self.frecuencia_detectada / 2
        tipo = self.tipo_filtro.currentData()
        if tipo == "bandpass":
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
        if tipo == "lowpass":
            texto = (
                "Se conservará principalmente el contenido por debajo de "
                f"{self.corte_unico.value():g} Hz."
            )
        elif tipo == "highpass":
            texto = (
                "Se conservará principalmente el contenido por encima de "
                f"{self.corte_unico.value():g} Hz."
            )
        else:
            texto = (
                "Se conservará principalmente el contenido entre "
                f"{self.corte_inferior.value():g} y "
                f"{self.corte_superior.value():g} Hz."
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
        if tipo == "bandpass":
            frecuencias_corte = (
                self.corte_inferior.value(),
                self.corte_superior.value(),
            )
        else:
            frecuencias_corte = self.corte_unico.value()

        return {
            "frecuencia_muestreo": self.frecuencia_detectada,
            "tipo": tipo,
            "frecuencias_corte": frecuencias_corte,
            "orden": 4,
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

    def actualizar_estado(self, exito, mensaje):
        color = "#66BB6A" if exito else "#EF5350"
        self.lbl_estado.setStyleSheet(f"color: {color};")
        self.lbl_estado.setText(mensaje)
