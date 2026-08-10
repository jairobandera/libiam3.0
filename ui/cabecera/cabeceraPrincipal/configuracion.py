from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from logica import accesibilidad, proyecto


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
        self.setMinimumWidth(440)
        self._init_ui(superposicion, no_preguntar)

    def _init_ui(self, superposicion, no_preguntar):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        titulo = QLabel("Configuración")
        titulo.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(titulo)

        # --- Sección: rangos / recortes ---
        seccion = QFrame()
        seccion_layout = QVBoxLayout()
        seccion_layout.setContentsMargins(0, 0, 0, 0)
        seccion_layout.setSpacing(8)

        lbl_seccion = QLabel("Rangos")
        lbl_seccion.setStyleSheet("font-weight: 600; color: #555555;")
        seccion_layout.addWidget(lbl_seccion)

        self.chk_superposicion = QCheckBox("Habilitar superposición de rangos")
        self.chk_superposicion.setChecked(bool(superposicion))
        self.chk_superposicion.setToolTip(
            "Permite crear un recorte que se apoya sobre otros ya existentes. "
            "Si está desactivado, el recorte se corre automáticamente al tramo libre."
        )
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
        self.chk_accesible.setToolTip(
            "Al activarlo aparecen las opciones de tipo de visión cromática y "
            "de refuerzo visual (colores, grosor y estilos de línea). "
            "Con el modo desactivado el software se comporta como siempre."
        )
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
        self.radio_rojo_verde.setToolTip(
            "Deuteranomalía, Protanomalía, Protanopia y Deuteranopia. "
            "Usa la paleta Okabe-Ito."
        )
        self.radio_azul_amarillo = QRadioButton("Deficiencia azul-amarillo")
        self.radio_azul_amarillo.setToolTip(
            "Tritanomalía y Tritanopia. Usa una paleta que separa por "
            "tonalidad y luminancia los pares que tienden a confundirse."
        )
        self.radio_completa = QRadioButton("Deficiencia completa")
        self.radio_completa.setToolTip(
            "Monocromacia o Acromatopsia. Usa una escala de grises "
            "ordenada por brillo."
        )
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

        self.chk_nombre = QCheckBox("Mostrar el nombre del color en el rango")
        self.chk_nombre.setChecked(accesibilidad.mostrar_nombre_color())
        self.chk_nombre.setToolTip(
            "Al pasar el cursor sobre un rango o subrango se muestra el "
            "nombre del color en el tooltip."
        )
        gpo_opciones_layout.addWidget(self.chk_nombre)

        self.chk_estilos = QCheckBox("Utilizar estilos de línea diferenciados")
        self.chk_estilos.setChecked(accesibilidad.estilos_linea_activos())
        self.chk_estilos.setToolTip(
            "Cada tipo de línea (original, filtrada, fórmula) usa un trazo "
            "distinto además del color."
        )
        gpo_opciones_layout.addWidget(self.chk_estilos)

        self.chk_grosor = QCheckBox("Aumentar grosor de las líneas")
        self.chk_grosor.setChecked(accesibilidad.aumentar_grosor_activo())
        self.chk_grosor.setToolTip(
            "Engrosa las señales y los rangos para que se distingan mejor."
        )
        gpo_opciones_layout.addWidget(self.chk_grosor)

        gpo_opciones.setLayout(gpo_opciones_layout)
        gpo_opciones.setVisible(accesibilidad.activo())
        accesibilidad_layout.addWidget(gpo_opciones)

        ayuda_accesible = QLabel(
            "Los cambios se aplican al instante sobre las gráficas ya abiertas. "
            "No modifican los datos ni los archivos guardados."
        )
        ayuda_accesible.setWordWrap(True)
        ayuda_accesible.setStyleSheet(
            "color: #8A8A8A; font-size: 11px; margin-left: 22px;"
        )
        accesibilidad_layout.addWidget(ayuda_accesible)

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
        self.btn_limpiar.setToolTip(
            "Elegir qué copias de CSV y anotaciones eliminar de la carpeta "
            "«archivos»."
        )
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

        self.setLayout(layout)

        self.chk_superposicion.toggled.connect(self._on_superposicion)
        self.chk_no_preguntar.toggled.connect(self.noPreguntarSuperposicionCambiada.emit)
        self.chk_accesible.toggled.connect(self._on_accesible)
        self.radio_rojo_verde.toggled.connect(self._on_tipo_vision)
        self.radio_azul_amarillo.toggled.connect(self._on_tipo_vision)
        self.chk_nombre.toggled.connect(self._on_nombre_color)
        self.chk_estilos.toggled.connect(self._on_estilos_linea)
        self.chk_grosor.toggled.connect(self._on_grosor_lineas)
        btn_cerrar.clicked.connect(self.accept)

        # Estado inicial coherente: "no preguntar" solo aplica si hay superposición.
        self._actualizar_no_preguntar_habilitado(self.chk_superposicion.isChecked())

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

    def _actualizar_no_preguntar_habilitado(self, superposicion_activa):
        self.chk_no_preguntar.setEnabled(superposicion_activa)

    def _actualizar_resumen_archivos(self):
        """Muestra cuánto ocupa hoy la carpeta «archivos»."""
        proyectos = proyecto.listar_proyectos()
        self.btn_limpiar.setEnabled(bool(proyectos))
        if not proyectos:
            self.lbl_resumen_archivos.setText(
                "La carpeta «archivos» está vacía."
            )
            return

        total = proyecto.formatear_tamano(sum(p["tamano"] for p in proyectos))
        self.lbl_resumen_archivos.setText(
            f"{len(proyectos)} proyecto(s) guardado(s) · {total} en la carpeta "
            "«archivos»."
        )

    def _abrir_limpiar_archivos(self):
        from ui.cabecera.cabeceraPrincipal.limpiarArchivos import (
            LimpiarArchivosDialog,
        )

        dialogo = LimpiarArchivosDialog(self)
        dialogo.exec()
        self._actualizar_resumen_archivos()
