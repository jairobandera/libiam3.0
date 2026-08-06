from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from logica import proyecto


class ConfiguracionDialog(QDialog):
    """Popup de configuración de la aplicación.

    Emite en vivo los cambios para que se apliquen apenas se marca cada opción,
    sin necesidad de cerrar el diálogo.
    """

    superposicionCambiada = Signal(bool)
    noPreguntarSuperposicionCambiada = Signal(bool)
    modoDaltonicoCambiado = Signal(bool)

    def __init__(
        self,
        parent=None,
        superposicion=False,
        no_preguntar=False,
        modo_daltonico=False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setModal(True)
        self.setMinimumWidth(440)
        self._init_ui(superposicion, no_preguntar, modo_daltonico)

    def _init_ui(self, superposicion, no_preguntar, modo_daltonico):
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
        accesibilidad_layout.setSpacing(4)

        lbl_accesibilidad = QLabel("Accesibilidad")
        lbl_accesibilidad.setStyleSheet("font-weight: 600; color: #555555;")
        accesibilidad_layout.addWidget(lbl_accesibilidad)

        self.chk_daltonico = QCheckBox("Paleta accesible para daltonismo")
        self.chk_daltonico.setChecked(bool(modo_daltonico))
        self.chk_daltonico.setToolTip(
            "Cambia los colores de las señales, los filtros y los rangos por la "
            "paleta Okabe-Ito, que se distingue con deuteranopía, protanopía y "
            "tritanopía. Al desactivarla vuelven los colores originales."
        )
        accesibilidad_layout.addWidget(self.chk_daltonico)

        ayuda_daltonico = QLabel(
            "Aplica al instante sobre las gráficas ya abiertas. "
            "No modifica los datos ni los archivos guardados."
        )
        ayuda_daltonico.setWordWrap(True)
        ayuda_daltonico.setStyleSheet(
            "color: #8A8A8A; font-size: 11px; margin-left: 22px;"
        )
        accesibilidad_layout.addWidget(ayuda_daltonico)

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
        self.chk_daltonico.toggled.connect(self.modoDaltonicoCambiado.emit)
        btn_cerrar.clicked.connect(self.accept)

        # Estado inicial coherente: "no preguntar" solo aplica si hay superposición.
        self._actualizar_no_preguntar_habilitado(self.chk_superposicion.isChecked())

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
