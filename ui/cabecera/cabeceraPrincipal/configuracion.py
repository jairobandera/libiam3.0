from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from logica import accesibilidad, paleta, preferencias_graficas, proyecto
from logica.interfaz_adaptativa import configurar_geometria_persistente


class VistaPreviaColores(QFrame):
    """Muestra los dos trazos tal como se distinguirán sobre el fondo oscuro."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original = paleta.COLOR_ORIGINAL_PREDETERMINADO
        self._filtrada = paleta.COLOR_FILTRADA_PREDETERMINADO
        self.setMinimumHeight(72)
        self.setStyleSheet(
            "background-color: #1E1E1E; border: 1px solid #3E3E42; "
            "border-radius: 5px;"
        )

    def set_colores(self, original, filtrada):
        self._original = original
        self._filtrada = filtrada
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing, True)
        fin_linea = max(72, min(120, self.width() // 3))
        for y, color, texto, grosor in (
            (23, self._original, "Señal original", 2.0),
            (49, self._filtrada, "Señal filtrada", 3.0),
        ):
            pintor.setPen(QPen(QColor(color), grosor, Qt.SolidLine, Qt.RoundCap))
            pintor.drawLine(14, y, fin_linea, y)
            pintor.setPen(QColor("#E6E6E6"))
            pintor.drawText(fin_linea + 12, y + 5, texto)


class ConfiguracionDialog(QDialog):
    """Popup de configuración de la aplicación.

    Emite en vivo los cambios para que se apliquen apenas se marca cada opción,
    sin necesidad de cerrar el diálogo.
    """

    superposicionCambiada = Signal(bool)
    noPreguntarSuperposicionCambiada = Signal(bool)
    # Emitido cuando cambia cualquier ajuste de accesibilidad; el área central
    # relee el estado desde ``logica.accesibilidad`` y se repinta.
    accesibilidadCambiada = Signal()
    coloresGraficasCambiaron = Signal()
    # Compatibilidad durante la migración: el antiguo modo «daltónico» (paleta
    # rojo-verde) se seguía notificando con esta señal cuando corresponde.
    modoDaltonicoCambiado = Signal(bool)

    def __init__(
        self,
        parent=None,
        superposicion=False,
        no_preguntar=False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setModal(True)
        preferencias_graficas.cargar_colores()
        preferencias_graficas.cargar_modo_zoom()
        self._init_ui(superposicion, no_preguntar)
        configurar_geometria_persistente(
            self,
            "dialogos/configuracion/geometria",
            ideal=(540, 650),
            minimo=(380, 360),
            piso=(300, 240),
        )

    def _init_ui(self, superposicion, no_preguntar):
        contenido = QWidget()
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        titulo = QLabel("Configuración")
        titulo.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(titulo)

        # --- Sección: intervalos / recortes ---
        seccion = QFrame()
        seccion_layout = QVBoxLayout()
        seccion_layout.setContentsMargins(0, 0, 0, 0)
        seccion_layout.setSpacing(8)

        lbl_seccion = QLabel("Intervalos")
        lbl_seccion.setStyleSheet("font-weight: 600; color: #555555;")
        seccion_layout.addWidget(lbl_seccion)

        self.chk_superposicion = QCheckBox("Habilitar superposición de intervalos")
        self.chk_superposicion.setChecked(bool(superposicion))
        self.chk_superposicion.setToolTip("Permite intervalos superpuestos.")
        seccion_layout.addWidget(self.chk_superposicion)

        self.chk_no_preguntar = QCheckBox("No preguntar al superponer")
        self.chk_no_preguntar.setChecked(bool(no_preguntar))
        self.chk_no_preguntar.setToolTip(
            "Al superponer, no muestra el mensaje de confirmación."
        )
        # Sangría para indicar que depende de la opción anterior.
        self.chk_no_preguntar.setStyleSheet("margin-left: 22px;")
        seccion_layout.addWidget(self.chk_no_preguntar)

        seccion.setLayout(seccion_layout)
        layout.addWidget(seccion)

        # --- Sección: comportamiento del zoom ---
        seccion_zoom = QFrame()
        zoom_layout = QVBoxLayout()
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(6)

        lbl_zoom = QLabel("Zoom de las gráficas")
        lbl_zoom.setStyleSheet("font-weight: 600; color: #B0B0B0;")
        zoom_layout.addWidget(lbl_zoom)

        descripcion_zoom = QLabel(
            "Elegí qué ejes modifica la rueda del mouse. El zoom se centra "
            "en la posición del cursor."
        )
        descripcion_zoom.setWordWrap(True)
        descripcion_zoom.setStyleSheet("color: #9A9A9A; font-size: 11px;")
        zoom_layout.addWidget(descripcion_zoom)

        self.grupo_zoom = QButtonGroup(self)
        self.radio_zoom_x = QRadioButton("Solo horizontal (X)")
        self.radio_zoom_y = QRadioButton("Solo vertical (Y)")
        self.radio_zoom_xy = QRadioButton("Horizontal y vertical (X + Y)")
        opciones_zoom = (
            (self.radio_zoom_x, preferencias_graficas.MODO_ZOOM_X),
            (self.radio_zoom_y, preferencias_graficas.MODO_ZOOM_Y),
            (self.radio_zoom_xy, preferencias_graficas.MODO_ZOOM_XY),
        )
        modo_zoom = preferencias_graficas.modo_zoom_actual()
        for radio, modo in opciones_zoom:
            radio.setProperty("modoZoom", modo)
            radio.setAccessibleDescription(
                "Define los ejes que cambian al girar la rueda sobre una gráfica."
            )
            self.grupo_zoom.addButton(radio)
            zoom_layout.addWidget(radio)
            if modo == modo_zoom:
                radio.setChecked(True)

        nota_arrastre = QLabel(
            "El arrastre continúa desplazando la gráfica horizontalmente."
        )
        nota_arrastre.setWordWrap(True)
        nota_arrastre.setStyleSheet("color: #8A8A8A; font-size: 10px;")
        zoom_layout.addWidget(nota_arrastre)

        seccion_zoom.setLayout(zoom_layout)
        layout.addWidget(seccion_zoom)

        # --- Sección: colores de las curvas ---
        seccion_colores = QFrame()
        colores_layout = QVBoxLayout()
        colores_layout.setContentsMargins(0, 0, 0, 0)
        colores_layout.setSpacing(8)

        lbl_colores = QLabel("Colores de las gráficas")
        lbl_colores.setStyleSheet("font-weight: 600; color: #B0B0B0;")
        colores_layout.addWidget(lbl_colores)

        descripcion_colores = QLabel(
            "Elegí los colores de las líneas. Los cambios se aplican al instante "
            "y se conservan al volver a abrir ABS."
        )
        descripcion_colores.setWordWrap(True)
        descripcion_colores.setStyleSheet("color: #9A9A9A; font-size: 11px;")
        colores_layout.addWidget(descripcion_colores)

        self.vista_previa_colores = VistaPreviaColores()
        colores_layout.addWidget(self.vista_previa_colores)

        self.btn_color_original = QPushButton()
        self.btn_color_original.setObjectName("btnColorOriginal")
        self.btn_color_original.setCursor(Qt.PointingHandCursor)
        self.btn_color_original.setAccessibleName("Elegir color de la señal original")
        self.btn_color_original.setToolTip("Abrir el selector de color")
        fila_original = QHBoxLayout()
        fila_original.addWidget(QLabel("Señal original"))
        fila_original.addStretch()
        fila_original.addWidget(self.btn_color_original)
        colores_layout.addLayout(fila_original)

        self.btn_color_filtrada = QPushButton()
        self.btn_color_filtrada.setObjectName("btnColorFiltrada")
        self.btn_color_filtrada.setCursor(Qt.PointingHandCursor)
        self.btn_color_filtrada.setAccessibleName("Elegir color de la señal filtrada")
        self.btn_color_filtrada.setToolTip("Abrir el selector de color")
        fila_filtrada = QHBoxLayout()
        fila_filtrada.addWidget(QLabel("Señal filtrada"))
        fila_filtrada.addStretch()
        fila_filtrada.addWidget(self.btn_color_filtrada)
        colores_layout.addLayout(fila_filtrada)

        nota_accesible = QLabel(
            "El modo accesible utiliza su propia paleta mientras está activado."
        )
        nota_accesible.setWordWrap(True)
        nota_accesible.setStyleSheet("color: #8A8A8A; font-size: 10px;")
        colores_layout.addWidget(nota_accesible)

        fila_restaurar = QHBoxLayout()
        self.btn_restaurar_colores = QPushButton("Restaurar colores")
        self.btn_restaurar_colores.setObjectName("btnDialogoSecundario")
        self.btn_restaurar_colores.setCursor(Qt.PointingHandCursor)
        fila_restaurar.addWidget(self.btn_restaurar_colores)
        fila_restaurar.addStretch()
        colores_layout.addLayout(fila_restaurar)

        seccion_colores.setLayout(colores_layout)
        layout.addWidget(seccion_colores)
        self._actualizar_colores_ui()

        # --- Sección: accesibilidad ---
        seccion_accesibilidad = QFrame()
        accesibilidad_layout = QVBoxLayout()
        accesibilidad_layout.setContentsMargins(0, 0, 0, 0)
        accesibilidad_layout.setSpacing(8)

        lbl_accesibilidad = QLabel("Accesibilidad")
        lbl_accesibilidad.setStyleSheet("font-weight: 600; color: #555555;")
        accesibilidad_layout.addWidget(lbl_accesibilidad)

        # Solo el interruptor principal es visible hasta que se activa el modo.
        self.chk_accesible = QCheckBox("Activar modo accesible")
        self.chk_accesible.setChecked(accesibilidad.activo())
        accesibilidad_layout.addWidget(self.chk_accesible)

        # --- Tipo de visión cromática ---
        gpo_tipo = QFrame()
        gpo_tipo_layout = QVBoxLayout()
        gpo_tipo_layout.setContentsMargins(22, 0, 0, 0)
        gpo_tipo_layout.setSpacing(4)

        lbl_tipo = QLabel("Tipo de visión cromática")
        lbl_tipo.setStyleSheet("color: #8A8A8A; font-size: 11px;")
        gpo_tipo_layout.addWidget(lbl_tipo)

        self.grupo_vision = QButtonGroup(self)
        self.radio_rojo_verde = QRadioButton("Deficiencia rojo-verde")
        self.radio_azul_amarillo = QRadioButton("Deficiencia azul-amarillo")
        self.radio_completa = QRadioButton("Deficiencia completa")
        self.grupo_vision.addButton(self.radio_rojo_verde)
        self.grupo_vision.addButton(self.radio_azul_amarillo)
        self.grupo_vision.addButton(self.radio_completa)
        if accesibilidad.tipo_vision() == accesibilidad.TIPO_COMPLETO:
            self.radio_completa.setChecked(True)
        elif accesibilidad.tipo_vision() == accesibilidad.TIPO_AZUL_AMARILLO:
            self.radio_azul_amarillo.setChecked(True)
        else:
            self.radio_rojo_verde.setChecked(True)
        gpo_tipo_layout.addWidget(self.radio_rojo_verde)
        gpo_tipo_layout.addWidget(self.radio_azul_amarillo)
        gpo_tipo_layout.addWidget(self.radio_completa)

        gpo_tipo.setLayout(gpo_tipo_layout)
        gpo_tipo.setVisible(accesibilidad.activo())
        accesibilidad_layout.addWidget(gpo_tipo)

        # --- Opciones adicionales ---
        gpo_opciones = QFrame()
        gpo_opciones_layout = QVBoxLayout()
        gpo_opciones_layout.setContentsMargins(22, 0, 0, 0)
        gpo_opciones_layout.setSpacing(4)

        lbl_opciones = QLabel("Opciones adicionales")
        lbl_opciones.setStyleSheet("color: #8A8A8A; font-size: 11px;")
        gpo_opciones_layout.addWidget(lbl_opciones)

        self.chk_nombre = QCheckBox("Mostrar el nombre del color en el intervalo")
        self.chk_nombre.setChecked(accesibilidad.mostrar_nombre_color())
        gpo_opciones_layout.addWidget(self.chk_nombre)

        self.chk_estilos = QCheckBox("Utilizar estilos de línea diferenciados")
        self.chk_estilos.setChecked(accesibilidad.estilos_linea_activos())
        gpo_opciones_layout.addWidget(self.chk_estilos)

        self.chk_grosor = QCheckBox("Aumentar grosor de las líneas")
        self.chk_grosor.setChecked(accesibilidad.aumentar_grosor_activo())
        gpo_opciones_layout.addWidget(self.chk_grosor)

        gpo_opciones.setLayout(gpo_opciones_layout)
        gpo_opciones.setVisible(accesibilidad.activo())
        accesibilidad_layout.addWidget(gpo_opciones)

        self.gpo_tipo = gpo_tipo
        self.gpo_opciones = gpo_opciones

        seccion_accesibilidad.setLayout(accesibilidad_layout)
        layout.addWidget(seccion_accesibilidad)

        # --- Sección: mantenimiento de la carpeta «archivos» ---
        seccion_archivos = QFrame()
        archivos_layout = QVBoxLayout()
        archivos_layout.setContentsMargins(0, 0, 0, 0)
        archivos_layout.setSpacing(6)

        lbl_archivos = QLabel("Archivos guardados")
        lbl_archivos.setStyleSheet("font-weight: 600; color: #555555;")
        archivos_layout.addWidget(lbl_archivos)

        self.lbl_resumen_archivos = QLabel()
        self.lbl_resumen_archivos.setWordWrap(True)
        self.lbl_resumen_archivos.setStyleSheet(
            "color: #8A8A8A; font-size: 11px;"
        )
        archivos_layout.addWidget(self.lbl_resumen_archivos)

        fila_limpiar = QHBoxLayout()
        self.btn_limpiar = QPushButton("Limpiar archivos guardados…")
        self.btn_limpiar.setObjectName("btnDialogoSecundario")
        self.btn_limpiar.setCursor(Qt.PointingHandCursor)
        self.btn_limpiar.clicked.connect(self._abrir_limpiar_archivos)
        fila_limpiar.addWidget(self.btn_limpiar)
        fila_limpiar.addStretch()
        archivos_layout.addLayout(fila_limpiar)

        seccion_archivos.setLayout(archivos_layout)
        layout.addWidget(seccion_archivos)

        self._actualizar_resumen_archivos()

        layout.addStretch()

        botones = QHBoxLayout()
        botones.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        botones.addWidget(btn_cerrar)
        layout.addLayout(botones)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(contenido)
        principal = QVBoxLayout(self)
        principal.setContentsMargins(0, 0, 0, 0)
        principal.addWidget(scroll)

        self.chk_superposicion.toggled.connect(self._on_superposicion)
        self.chk_no_preguntar.toggled.connect(self.noPreguntarSuperposicionCambiada.emit)
        self.radio_zoom_x.toggled.connect(self._on_modo_zoom)
        self.radio_zoom_y.toggled.connect(self._on_modo_zoom)
        self.radio_zoom_xy.toggled.connect(self._on_modo_zoom)
        self.chk_accesible.toggled.connect(self._on_accesible)
        self.radio_rojo_verde.toggled.connect(self._on_tipo_vision)
        self.radio_azul_amarillo.toggled.connect(self._on_tipo_vision)
        self.chk_nombre.toggled.connect(self._on_nombre_color)
        self.chk_estilos.toggled.connect(self._on_estilos_linea)
        self.chk_grosor.toggled.connect(self._on_grosor_lineas)
        self.btn_color_original.clicked.connect(self._elegir_color_original)
        self.btn_color_filtrada.clicked.connect(self._elegir_color_filtrada)
        self.btn_restaurar_colores.clicked.connect(self._restaurar_colores)
        btn_cerrar.clicked.connect(self.accept)

        # Estado inicial coherente: "no preguntar" solo aplica si hay superposición.
        self._actualizar_no_preguntar_habilitado(self.chk_superposicion.isChecked())

    @staticmethod
    def _color_texto_para_fondo(color):
        valor = QColor(color)
        luminancia = (
            valor.red() * 299 + valor.green() * 587 + valor.blue() * 114
        ) / 1000
        return "#111111" if luminancia >= 150 else "#FFFFFF"

    def _estilizar_boton_color(self, boton, color):
        texto = self._color_texto_para_fondo(color)
        boton.setText(color)
        boton.setMinimumWidth(116)
        boton.setStyleSheet(
            "QPushButton {"
            f"background-color: {color}; color: {texto};"
            "border: 1px solid #6A6A6A; border-radius: 4px;"
            "padding: 6px 12px; font-weight: 600;"
            "}"
            "QPushButton:hover { border: 2px solid #FFFFFF; }"
            "QPushButton:focus { border: 2px solid #64B5F6; }"
        )

    def _actualizar_colores_ui(self):
        colores = paleta.colores_senales_configurados()
        self._estilizar_boton_color(
            self.btn_color_original,
            colores["senal_original"],
        )
        self._estilizar_boton_color(
            self.btn_color_filtrada,
            colores["senal_filtrada"],
        )
        self.vista_previa_colores.set_colores(
            colores["senal_original"],
            colores["senal_filtrada"],
        )
        self.btn_restaurar_colores.setEnabled(
            colores["senal_original"] != paleta.COLOR_ORIGINAL_PREDETERMINADO
            or colores["senal_filtrada"] != paleta.COLOR_FILTRADA_PREDETERMINADO
        )

    def _elegir_color(self, clave, titulo):
        colores = paleta.colores_senales_configurados()
        elegido = QColorDialog.getColor(QColor(colores[clave]), self, titulo)
        if not elegido.isValid():
            return
        colores[clave] = elegido.name(QColor.NameFormat.HexRgb).upper()
        preferencias_graficas.guardar_colores(
            colores["senal_original"],
            colores["senal_filtrada"],
        )
        self._actualizar_colores_ui()
        self.coloresGraficasCambiaron.emit()

    def _elegir_color_original(self):
        self._elegir_color("senal_original", "Color de la señal original")

    def _elegir_color_filtrada(self):
        self._elegir_color("senal_filtrada", "Color de la señal filtrada")

    def _restaurar_colores(self):
        anteriores = paleta.colores_senales_configurados()
        actuales = preferencias_graficas.restaurar_colores()
        self._actualizar_colores_ui()
        if actuales != anteriores:
            self.coloresGraficasCambiaron.emit()

    def _on_accesible(self, activo):
        # Al activar por primera vez hay que fijar un tipo de visión (por
        # defecto rojo-verde), o la paleta no tendría a qué modo pasarse.
        if activo and accesibilidad.tipo_vision() is None:
            accesibilidad.set_tipo_vision(self._tipo_vision_seleccionado())
        accesibilidad.set_activo(activo)
        self.gpo_tipo.setVisible(activo)
        self.gpo_opciones.setVisible(activo)
        self._emitir_accesibilidad()

    def _on_tipo_vision(self):
        accesibilidad.set_tipo_vision(self._tipo_vision_seleccionado())
        self._emitir_accesibilidad()

    def _on_nombre_color(self, activo):
        accesibilidad.set_mostrar_nombre_color(activo)
        self._emitir_accesibilidad()

    def _on_estilos_linea(self, activo):
        accesibilidad.set_estilos_linea(activo)
        self._emitir_accesibilidad()

    def _on_grosor_lineas(self, activo):
        accesibilidad.set_aumentar_grosor(activo)
        self._emitir_accesibilidad()

    def _tipo_vision_seleccionado(self):
        if self.radio_completa.isChecked():
            return accesibilidad.TIPO_COMPLETO
        if self.radio_azul_amarillo.isChecked():
            return accesibilidad.TIPO_AZUL_AMARILLO
        return accesibilidad.TIPO_ROJO_VERDE

    def _emitir_accesibilidad(self):
        self.accesibilidadCambiada.emit()
        # Compatibilidad durante la migración: el antiguo modo «daltónico» solo
        # sabía activar la paleta rojo-verde, así que la señal histórica solo se
        # reemite cuando el tipo elegido es ese (o el predeterminado). Con la
        # deficiencia azul-amarillo y la completa la nueva señal es la que manda.
        if accesibilidad.tipo_vision() in (None, accesibilidad.TIPO_ROJO_VERDE):
            self.modoDaltonicoCambiado.emit(accesibilidad.activo())

    def _on_superposicion(self, activo):
        self._actualizar_no_preguntar_habilitado(activo)
        self.superposicionCambiada.emit(activo)

    def _on_modo_zoom(self, marcado):
        if not marcado:
            return
        radio = self.sender()
        preferencias_graficas.guardar_modo_zoom(
            radio.property("modoZoom") if radio is not None else None
        )

    def _actualizar_no_preguntar_habilitado(self, superposicion_activa):
        self.chk_no_preguntar.setEnabled(superposicion_activa)

    def _actualizar_resumen_archivos(self):
        """Muestra cuánto ocupa hoy la carpeta «archivos»."""
        proyectos = proyecto.listar_proyectos()
        self.btn_limpiar.setEnabled(bool(proyectos))
        if not proyectos:
            self.lbl_resumen_archivos.setText("No hay proyectos guardados.")
            return

        total = proyecto.formatear_tamano(sum(p["tamano"] for p in proyectos))
        self.lbl_resumen_archivos.setText(
            f"{len(proyectos)} proyecto(s) · {total}"
        )

    def _abrir_limpiar_archivos(self):
        from ui.cabecera.cabeceraPrincipal.limpiarArchivos import (
            LimpiarArchivosDialog,
        )

        dialogo = LimpiarArchivosDialog(self)
        dialogo.exec()
        self._actualizar_resumen_archivos()
