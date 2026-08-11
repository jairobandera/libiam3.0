from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QAbstractScrollArea,
    QAbstractItemView,
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

        # Ayuda sobre el reordenamiento por arrastre
        lbl_ayuda_orden = QLabel("Arrastrá las variables para definir el orden de las gráficas.")
        lbl_ayuda_orden.setObjectName("lblAyudaOrden")
        lbl_ayuda_orden.setWordWrap(True)

        # Lista de filas de mapeo reordenable por drag & drop
        self.lista_filas = QListWidget()
        self.lista_filas.setObjectName("listaMapeo")
        self.lista_filas.setDragDropMode(QAbstractItemView.InternalMove)
        self.lista_filas.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lista_filas.setFocusPolicy(Qt.NoFocus)
        # Todos los renglones tienen la misma altura. Qt puede reutilizar ese
        # cálculo al mostrar el panel en vez de medir cada item al abrirlo.
        self.lista_filas.setUniformItemSizes(True)
        self.lista_filas.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.lista_filas.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.lista_filas.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored
        )
        self.lista_filas.setFixedHeight(220)
        self.lista_filas.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lista_filas.setSpacing(2)
        self.lista_filas.itemChanged.connect(self._on_item_cambiado)

        # Boton de accion
        layout_botones = QHBoxLayout()
        layout_botones.setSpacing(8)

        self.btn_aplicar = QPushButton("Aplicar Mapeo")
        self.btn_aplicar.setObjectName("btnAplicarMapeo")
        self.btn_aplicar.setCursor(Qt.PointingHandCursor)
        self.btn_aplicar.clicked.connect(self.aplicar_mapeo)

        layout_botones.addWidget(self.btn_aplicar, 1)

        layout.addWidget(lbl_titulo_mapeo)
        layout.addLayout(layout_tipo)
        layout.addWidget(lbl_ayuda_orden)
        layout.addWidget(self.lista_filas)
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
        """Genera las filas de mapeo como items nativos reordenables.

        Se usan items nativos (texto + checkbox del propio item) en lugar de
        widgets incrustados porque el reordenamiento por arrastre (InternalMove)
        preserva los datos del item pero descartaría los widgets de setItemWidget.
        """
        # Evitar que la carga inicial de checkboxes dispare itemChanged.
        self.lista_filas.blockSignals(True)
        self.lista_filas.setUpdatesEnabled(False)
        self.lista_filas.clear()

        tipos = self.mapeo.obtener_tipos_detectados()

        for tipo in tipos:
            ejes = self.mapeo.obtener_ejes_para_tipo(tipo)

            for eje, columna_auto in ejes.items():
                nombre = self.formatear_nombre_eje(tipo, eje)
                columna = columna_auto if columna_auto else "---"
                texto = f"☰   {nombre}   ·   {columna}"
                item = QListWidgetItem(texto)
                item.setToolTip(texto)
                item.setData(Qt.UserRole, (tipo, eje))
                # Arrastrable pero sin aceptar drop "dentro"; solo se reordena.
                item.setFlags(
                    (item.flags() | Qt.ItemIsDragEnabled | Qt.ItemIsUserCheckable)
                    & ~Qt.ItemIsDropEnabled
                )
                item.setCheckState(
                    Qt.Checked if self.mapeo.es_eje_activo(tipo, eje) else Qt.Unchecked
                )
                self.lista_filas.addItem(item)

        self.lista_filas.blockSignals(False)
        self.lista_filas.setUpdatesEnabled(True)

        # No se pinta un bloque fijo de 500 px cuando hay pocas variables. La
        # lista crece hasta un límite y usa su propio scroll si hiciera falta.
        if self.lista_filas.count():
            alto_fila = max(30, self.lista_filas.sizeHintForRow(0))
            alto_lista = min(380, max(150, alto_fila * self.lista_filas.count() + 8))
        else:
            alto_lista = 150
        self.lista_filas.setFixedHeight(alto_lista)

        # Aplicar filtro visual
        self._aplicar_filtro_visual(tipo_filtro)

    def _on_item_cambiado(self, item):
        """Refleja el cambio de checkbox del item en el modelo de mapeo."""
        datos = item.data(Qt.UserRole)
        if not datos:
            return
        tipo, eje = datos
        activo = item.checkState() == Qt.Checked
        self._toggle_eje(tipo, eje, activo)

    def _aplicar_filtro_visual(self, tipo_filtro):
        """Muestra u oculta filas segun el tipo seleccionado."""
        for i in range(self.lista_filas.count()):
            item = self.lista_filas.item(i)
            datos = item.data(Qt.UserRole) or ("", "")
            tipo_fila = datos[0]
            item.setHidden(tipo_filtro != "Todos" and tipo_fila != tipo_filtro)

    def filtrar_por_tipo(self, tipo):
        """Filtra las filas de mapeo segun el tipo de dato seleccionado."""
        self._aplicar_filtro_visual(tipo)

    def _toggle_eje(self, tipo, eje, activo):
        """Activa/desactiva un eje internamente. Solo se aplica al presionar 'Aplicar Mapeo'."""
        print(f"[DEBUG] _toggle_eje: tipo={tipo}, eje={eje}, activo={activo}")
        self.mapeo.toggle_eje(tipo, eje, activo)

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

        # Asignar el orden segun la disposicion visual de las filas (drag & drop).
        # Ese orden lo respeta el area central para ordenar las graficas.
        orden = 0
        for i in range(self.lista_filas.count()):
            item = self.lista_filas.item(i)
            datos = item.data(Qt.UserRole)
            if not datos:
                continue
            tipo, eje = datos
            ejes = mapeo_completo.get(tipo)
            if isinstance(ejes, dict) and isinstance(ejes.get(eje), dict):
                ejes[eje]["orden"] = orden
                orden += 1

        if tipo_filtro != "Todos":
            mapeo_completo = {
                tipo: ejes for tipo, ejes in mapeo_completo.items()
                if tipo == tipo_filtro
            }

        print(f"[DEBUG] aplicar_mapeo: mapeo_emitido={mapeo_completo}")
        self.mapeoAplicado.emit(mapeo_completo)
        print("[DEBUG] aplicar_mapeo: señal emitida")
