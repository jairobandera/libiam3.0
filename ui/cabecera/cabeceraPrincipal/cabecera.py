from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QToolButton,
    QSizePolicy,

)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QPixmap

from logica import app_info
from ui.cabecera.cabeceraPrincipal.acerca_de import AcercaDeDialog
from ui.cabecera.cabeceraPrincipal.configuracion import ConfiguracionDialog


class Cabecera(QFrame):

    superposicionIntervalosCambiada = Signal(bool)
    noPreguntarSuperposicionCambiada = Signal(bool)
    guardarSolicitado = Signal()
    cargarSolicitado = Signal()
    exportarSolicitado = Signal()
    inicioSolicitado = Signal()
    # Cambió algún ajuste de accesibilidad; el área central relee el estado.
    accesibilidadCambiada = Signal()
    # Compatibilidad durante la migración: ver ``configuracion.py``.
    modoDaltonicoCambiado = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("topHeader")
        self.superposicion_intervalos = False
        self.no_preguntar_superposicion = False
        self.init_ui()

    def init_ui(self):

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 4, 20, 4)
        layout.setSpacing(10)
        self.layout_principal = layout

        import os

        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",".."))

        left_layout = QHBoxLayout()
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(0, 0, 0, 0)

        logo_path = os.path.join(BASE_DIR, "utilidades", "icons", "logo.png")
        logo = QLabel()
        self.logo = logo
        self.logo_path = logo_path
        logo.setPixmap(
            QPixmap(logo_path).scaled(
                60,
                60,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)

        titulo = QLabel(app_info.NOMBRE)
        self.titulo = titulo
        titulo.setObjectName("mainTitle")

        subtitulo = QLabel(app_info.LABORATORIO)
        self.subtitulo = subtitulo
        subtitulo.setObjectName("subTitle")
        subtitulo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        subtitulo.setToolTip(app_info.LABORATORIO)
        subtitulo.setAccessibleName(app_info.LABORATORIO)

        text_layout.addWidget(titulo)
        text_layout.addWidget(subtitulo)

        left_layout.addWidget(logo)
        left_layout.addLayout(text_layout)

        right_layout = QHBoxLayout()
        self.layout_botones = right_layout
        right_layout.setSpacing(12)
        right_layout.setAlignment(Qt.AlignVCenter)

        botones = [
            ("Inicio", "utilidades/icons/home.svg"),
            ("Guardar", "utilidades/icons/save.svg"),
            ("Cargar", "utilidades/icons/load.svg"),
            ("Exportar", "utilidades/icons/export.svg"),
            ("Configurar", "utilidades/icons/config.svg"),
            ("Acerca de", "utilidades/icons/help.svg"),
        ]

        self.botones = {}
        for texto, icono in botones:

            btn = QToolButton()
            btn.setText(texto)
            btn.setIcon(QIcon(os.path.join(BASE_DIR, icono)))
            btn.setIconSize(QSize(20, 20))
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setObjectName("toolbarButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setAccessibleName(texto)
            btn.setToolTip(texto)
            btn.setMinimumWidth(70)
            self.botones[texto] = btn

            if texto == "Inicio":
                btn.setToolTip("Volver al estado inicial.")
                btn.clicked.connect(self.inicioSolicitado.emit)
            elif texto == "Acerca de":
                btn.clicked.connect(self._mostrar_acerca_de)
            elif texto == "Configurar":
                btn.clicked.connect(self._mostrar_configuracion)
            elif texto == "Guardar":
                btn.clicked.connect(self.guardarSolicitado.emit)
            elif texto == "Cargar":
                btn.setToolTip("Abrir proyecto.")
                btn.clicked.connect(self.cargarSolicitado.emit)
            elif texto == "Exportar":
                btn.setToolTip("Exportar análisis.")
                btn.clicked.connect(self.exportarSolicitado.emit)

            right_layout.addWidget(btn)

        layout.addLayout(left_layout)
        layout.addStretch()
        layout.addLayout(right_layout)

        self.setLayout(layout)
        self.ajustar_modo(False, False)

    def ajustar_modo(self, compacto=False, muy_compacto=False):
        """Reduce la cabecera sin ocultar acciones en pantallas angostas."""
        compacto = bool(compacto)
        muy_compacto = bool(muy_compacto)
        margen = 6 if compacto else 20
        separacion = 4 if compacto else 10
        self.layout_principal.setContentsMargins(margen, 3, margen, 3)
        self.layout_principal.setSpacing(separacion)
        self.layout_botones.setSpacing(3 if compacto else 12)
        self.subtitulo.setText(
            app_info.LABORATORIO_CORTO if compacto else app_info.LABORATORIO
        )
        self.subtitulo.setVisible(True)

        tamano_logo = 36 if muy_compacto else 44 if compacto else 60
        self.logo.setPixmap(
            QPixmap(self.logo_path).scaled(
                tamano_logo,
                tamano_logo,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        for boton in self.botones.values():
            if compacto:
                boton.setToolButtonStyle(Qt.ToolButtonIconOnly)
                ancho = 38 if muy_compacto else 42
                boton.setMinimumWidth(ancho)
                boton.setMaximumWidth(ancho + 4)
                boton.setIconSize(QSize(19, 19))
            else:
                boton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
                boton.setMinimumWidth(70)
                boton.setMaximumWidth(16777215)
                boton.setIconSize(QSize(20, 20))

    def _mostrar_acerca_de(self):
        AcercaDeDialog(self.window()).exec()

    def _mostrar_configuracion(self):
        dialogo = ConfiguracionDialog(
            self.window(),
            superposicion=self.superposicion_intervalos,
            no_preguntar=self.no_preguntar_superposicion,
        )
        dialogo.superposicionCambiada.connect(self._on_superposicion_cambiada)
        dialogo.noPreguntarSuperposicionCambiada.connect(
            self._on_no_preguntar_cambiada
        )
        dialogo.accesibilidadCambiada.connect(self._on_accesibilidad_cambiada)
        # Compatibilidad durante la migración: el antiguo modo «daltónico» se
        # reenvía tal cual; el área central todavía lo escucha (etapa 5).
        dialogo.modoDaltonicoCambiado.connect(self.modoDaltonicoCambiado.emit)
        dialogo.exec()

    def _on_superposicion_cambiada(self, activo):
        self.superposicion_intervalos = bool(activo)
        self.superposicionIntervalosCambiada.emit(self.superposicion_intervalos)

    def _on_no_preguntar_cambiada(self, activo):
        self.no_preguntar_superposicion = bool(activo)
        self.noPreguntarSuperposicionCambiada.emit(self.no_preguntar_superposicion)

    def _on_accesibilidad_cambiada(self):
        self.accesibilidadCambiada.emit()
