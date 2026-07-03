from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QPushButton,
    QScrollArea,
    QWidget,
)
from PySide6.QtCore import Qt, Signal

from logica.mapeo_columnas import MapeoColumnas


class ConfigColumnas(QFrame):
    mapeoAplicado = Signal(object)

    def __init__(self):
        super().__init__()
        self.setObjectName("configColumnas")
        self.mapeo = MapeoColumnas()
        self.init_ui()

    def init_ui(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Titulo
        self.lbl_titulo = QLabel("Configuracion de Columnas")
        self.lbl_titulo.setObjectName("tituloPanel")

        self.lbl_subtitulo = QLabel("Mapeo de variables del CSV")
        self.lbl_subtitulo.setObjectName("subtituloPanel")

        # Seccion de deteccion
        self.seccion_deteccion = self.crear_seccion_deteccion()
        layout.addWidget(self.seccion_deteccion)

        # Seccion de mapeo
        self.seccion_mapeo = self.crear_seccion_mapeo()
        layout.addWidget(self.seccion_mapeo)

        # Seccion de columnas del CSV
        self.seccion_columnas = self.crear_seccion_columnas()
        layout.addWidget(self.seccion_columnas)

        # Espacio vacio al final
        layout.addStretch()

        self.setLayout(layout)

    def crear_seccion_deteccion(self):

        frame = QFrame()
        frame.setObjectName("seccionDeteccion")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Indicador de deteccion
        self.lbl_deteccion = QLabel("")
        self.lbl_deteccion.setObjectName("lblDeteccion")
        self.lbl_deteccion.setWordWrap(True)

        # Boton re-detectar
        self.btn_redetectar = QPushButton("Re-detectar Columnas")
        self.btn_redetectar.setObjectName("btnRedetectar")
        self.btn_redetectar.setCursor(Qt.PointingHandCursor)
        self.btn_redetectar.clicked.connect(self.re_detectar)

        layout.addWidget(self.lbl_deteccion)
        layout.addWidget(self.btn_redetectar)

        frame.setLayout(layout)
        return frame

    def crear_seccion_mapeo(self):

        frame = QFrame()
        frame.setObjectName("seccionMapeo")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Titulo de seccion
        lbl_titulo_mapeo = QLabel("Mapeo de Variables")
        lbl_titulo_mapeo.setObjectName("tituloSeccionMapeo")

        # Dropdown tipo de dato
        layout_tipo = QHBoxLayout()
        layout_tipo.setSpacing(8)

        lbl_tipo = QLabel("Tipo de dato:")
        lbl_tipo.setObjectName("lblTipoDato")

        self.cmb_tipo_dato = QComboBox()
        self.cmb_tipo_dato.setObjectName("cmbTipoDato")
        self.cmb_tipo_dato.addItem("Todos")
        self.cmb_tipo_dato.currentTextChanged.connect(self.filtrar_por_tipo)

        layout_tipo.addWidget(lbl_tipo)
        layout_tipo.addWidget(self.cmb_tipo_dato, 1)

        # Contenedor de filas de mapeo
        self.contenedor_filas = QWidget()
        self.layout_filas = QVBoxLayout()
        self.layout_filas.setContentsMargins(0, 0, 0, 0)
        self.layout_filas.setSpacing(6)
        self.contenedor_filas.setLayout(self.layout_filas)

        # Scroll para las filas
        self.scroll_filas = QScrollArea()
        self.scroll_filas.setWidget(self.contenedor_filas)
        self.scroll_filas.setWidgetResizable(True)
        self.scroll_filas.setFrameShape(QFrame.NoFrame)
        self.scroll_filas.setFixedHeight(500)
        self.scroll_filas.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Botones de accion
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(8)

        self.btn_aplicar = QPushButton("Aplicar Mapeo")
        self.btn_aplicar.setObjectName("btnAplicarMapeo")
        self.btn_aplicar.setCursor(Qt.PointingHandCursor)
        self.btn_aplicar.clicked.connect(self.aplicar_mapeo)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setObjectName("btnResetMapeo")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self.resetear_mapeo)

        layout_botones.addWidget(self.btn_aplicar, 1)
        layout_botones.addWidget(self.btn_reset, 1)

        layout.addWidget(lbl_titulo_mapeo)
        layout.addLayout(layout_tipo)
        layout.addWidget(self.scroll_filas)
        layout.addLayout(layout_botones)

        frame.setLayout(layout)
        return frame

    def crear_seccion_columnas(self):

        frame = QFrame()
        frame.setObjectName("seccionColumnasCSV")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        lbl_titulo = QLabel("Columnas en el CSV")
        lbl_titulo.setObjectName("tituloSeccionMapeo")

        self.lbl_columnas = QLabel("")
        self.lbl_columnas.setObjectName("lblColumnasCSV")
        self.lbl_columnas.setWordWrap(True)

        layout.addWidget(lbl_titulo)
        layout.addWidget(self.lbl_columnas)

        frame.setLayout(layout)
        return frame

    def cargar_datos(self, info):
        """Carga los datos detectados del CSV en la UI."""
        deteccion = info.get("deteccion", {})
        columnas = info.get("columnas_csv", [])

        # Inicializar el mapeo
        self.mapeo.inicializar(deteccion, columnas)

        # Actualizar indicador de deteccion
        tipos = self.mapeo.obtener_tipos_detectados()
        if tipos:
            self.lbl_deteccion.setText(
                f"Se detectaron automaticamente: {', '.join(tipos)}"
            )
            self.lbl_deteccion.setObjectName("lblDeteccionOk")
        else:
            self.lbl_deteccion.setText(
                "No se pudieron detectar columnas automaticamente. Usa el panel Detectar Cabeceras."
            )
            self.lbl_deteccion.setObjectName("lblDeteccionWarn")

        # Actualizar dropdown de tipo de dato
        self.cmb_tipo_dato.clear()
        self.cmb_tipo_dato.addItem("Todos")
        tipos_graficables = [t for t in tipos if t not in ("Frame", "Tiempo")]
        for tipo in tipos_graficables:
            self.cmb_tipo_dato.addItem(tipo)

        # Actualizar lista de columnas
        self.lbl_columnas.setText(
            f"{len(columnas)} columnas: {', '.join(columnas)}"
        )

        # Generar filas de mapeo
        self.generar_filas_mapeo("Todos")

    def generar_filas_mapeo(self, tipo_filtro):
        """Genera las filas de mapeo con checkbox y nombre."""
        # Limpiar filas existentes
        while self.layout_filas.count():
            hijo = self.layout_filas.takeAt(0)
            if hijo.widget():
                hijo.widget().deleteLater()

        tipos = self.mapeo.obtener_tipos_detectados()

        for tipo in tipos:
            ejes = self.mapeo.obtener_ejes_para_tipo(tipo)

            for eje, columna_auto in ejes.items():
                fila = self.crear_fila_mapeo(tipo, eje, columna_auto)
                fila.tipo_dato = tipo
                self.layout_filas.addWidget(fila)

        # Aplicar filtro visual
        self._aplicar_filtro_visual(tipo_filtro)

    def _aplicar_filtro_visual(self, tipo_filtro):
        """Muestra u oculta filas segun el tipo seleccionado."""
        for i in range(self.layout_filas.count()):
            hijo = self.layout_filas.itemAt(i)
            if hijo and hijo.widget():
                frame = hijo.widget()
                tipo_fila = getattr(frame, "tipo_dato", "")
                if tipo_filtro == "Todos" or tipo_fila == tipo_filtro:
                    frame.setVisible(True)
                else:
                    frame.setVisible(False)

    def filtrar_por_tipo(self, tipo):
        """Filtra las filas de mapeo segun el tipo de dato seleccionado."""
        self._aplicar_filtro_visual(tipo)

    def _toggle_eje(self, tipo, eje, activo):
        """Activa/desactiva un eje internamente. Solo se aplica al presionar 'Aplicar Mapeo'."""
        print(f"[DEBUG] _toggle_eje: tipo={tipo}, eje={eje}, activo={activo}")
        self.mapeo.toggle_eje(tipo, eje, activo)

    def crear_fila_mapeo(self, tipo, eje, columna_auto):
        """Crea una fila de mapeo con checkbox y label."""
        frame = QFrame()
        frame.setObjectName("filaMapeo")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Checkbox para activar/desactivar el eje
        checkbox = QCheckBox()
        checkbox.setObjectName(f"chk_{tipo}_{eje}")
        checkbox.setChecked(self.mapeo.es_eje_activo(tipo, eje))
        checkbox.toggled.connect(
            lambda checked, t=tipo, e=eje: self._toggle_eje(t, e, checked)
        )

        # Label del eje
        label_eje = QLabel(self.formatear_nombre_eje(tipo, eje))
        label_eje.setObjectName("lblEje")
        label_eje.setMinimumWidth(80)

        # Label del nombre de columna
        label_columna = QLabel(columna_auto if columna_auto else "---")
        label_columna.setObjectName("lblColumnaCSV")

        layout.addWidget(checkbox)
        layout.addWidget(label_eje)
        layout.addWidget(label_columna, 1)

        frame.setLayout(layout)
        return frame

    def formatear_nombre_eje(self, tipo, eje):
        """Formatea el nombre del eje para mostrarlo en la UI."""
        ejes_nombres = {
            "eje_x": "X",
            "eje_y": "Y",
            "eje_z": "Z",
        }
        nombre_eje = ejes_nombres.get(eje, eje)
        return f"{tipo}{nombre_eje}"

    def re_detectar(self):
        """Re-ejecuta la deteccion automatica."""
        self.generar_filas_mapeo(self.cmb_tipo_dato.currentText())

    def aplicar_mapeo(self):
        """Guarda la configuracion actual del mapeo completo."""
        print("[DEBUG] aplicar_mapeo: Boton presionado")
        mapeo_completo = self.mapeo.obtener_mapeo_completo()
        tipo_filtro = self.cmb_tipo_dato.currentText()
        print(f"[DEBUG] aplicar_mapeo: tipo_filtro={tipo_filtro}")

        if tipo_filtro != "Todos":
            mapeo_completo = {
                tipo: ejes for tipo, ejes in mapeo_completo.items()
                if tipo == tipo_filtro
            }

        print(f"[DEBUG] aplicar_mapeo: mapeo_emitido={mapeo_completo}")
        self.mapeoAplicado.emit(mapeo_completo)
        print("[DEBUG] aplicar_mapeo: señal emitida")

    def resetear_mapeo(self):
        """Vuelve a la deteccion automatica."""
        self.mapeo.resetear_mapeo()
        self.generar_filas_mapeo(self.cmb_tipo_dato.currentText())
