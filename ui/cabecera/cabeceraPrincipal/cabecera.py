from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QToolButton,
    QSizePolicy,

)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon

from logica import app_info
from ui.cabecera.cabeceraPrincipal.acerca_de import AcercaDeDialog
from ui.cabecera.cabeceraPrincipal.configuracion import ConfiguracionDialog


class Cabecera(QFrame): #Componenete visual reautilizable, es la barra superior en si

    superposicionRangosCambiada = Signal(bool)
    noPreguntarSuperposicionCambiada = Signal(bool)
    guardarSolicitado = Signal()
    cargarSolicitado = Signal()
    # Cambió algún ajuste de accesibilidad; el área central relee el estado.
    accesibilidadCambiada = Signal()
    # Compatibilidad durante la migración: ver ``configuracion.py``.
    modoDaltonicoCambiado = Signal(bool)

    def __init__(self): #Constructor
        super().__init__()
        self.setObjectName("topHeader")
        # Configuración de sesión (no se persiste).
        self.superposicion_rangos = False
        self.no_preguntar_superposicion = False
        self.init_ui()

    def init_ui(self):

        layout = QHBoxLayout() #Todo se organiza en una fila (IZquierda - Derecha)
        layout.setContentsMargins(20, 4, 20, 4)  #Margenes internos del layout
        layout.setSpacing(10)

        # IZQUIERDA (LOGO + TEXTO)
        from PySide6.QtGui import QPixmap
        import os

        
        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..",".."))

        left_layout = QHBoxLayout() #Logo y texto
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # LOGO
        logo = QLabel()
        logo_path = os.path.join(BASE_DIR, "utilidades", "icons", "logo.png") #Ruta del logo.

        logo = QLabel() #Carga la imagen del logo.
        logo.setPixmap(QPixmap(logo_path).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)) #Ajusta el tamaño.

        text_layout = QVBoxLayout() #Titulo y subtitulo
        text_layout.setSpacing(0)

        titulo = QLabel(app_info.NOMBRE)
        titulo.setObjectName("mainTitle")

        subtitulo = QLabel(
            "Laboratorio de Investigación en Biomecánica y Análisis de Movimiento"
        )
        subtitulo.setObjectName("subTitle")

        text_layout.addWidget(titulo) 
        text_layout.addWidget(subtitulo)

        left_layout.addWidget(logo)
        left_layout.addLayout(text_layout)

        right_layout = QHBoxLayout() #Botones a la derecha, se organizan en una fila.
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

        for texto, icono in botones: #Genera botones dinamicamente.

            btn = QToolButton()
            btn.setText(texto)
            btn.setIcon(QIcon(os.path.join(BASE_DIR, icono))) #Carga el icono del botón.
            btn.setIconSize(QSize(20, 20))  #Tamaño del icono.
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon) #Icono y texto.
            btn.setObjectName("toolbarButton")
            btn.setCursor(Qt.PointingHandCursor)

            btn.setMinimumWidth(70) #Evita que el texto se corte.

            if texto == "Acerca de":
                btn.clicked.connect(self._mostrar_acerca_de)
            elif texto == "Configurar":
                btn.clicked.connect(self._mostrar_configuracion)
            elif texto == "Guardar":
                btn.clicked.connect(self.guardarSolicitado.emit)
            elif texto == "Cargar":
                btn.setToolTip(
                    "Abrir un proyecto guardado en la carpeta «archivos» "
                    "con sus rangos y notas."
                )
                btn.clicked.connect(self.cargarSolicitado.emit)

            right_layout.addWidget(btn)

        layout.addLayout(left_layout)
        layout.addStretch()
        layout.addLayout(right_layout)

        self.setLayout(layout)

    def _mostrar_acerca_de(self):
        AcercaDeDialog(self.window()).exec()

    def _mostrar_configuracion(self):
        dialogo = ConfiguracionDialog(
            self.window(),
            superposicion=self.superposicion_rangos,
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
        self.superposicion_rangos = bool(activo)
        self.superposicionRangosCambiada.emit(self.superposicion_rangos)

    def _on_no_preguntar_cambiada(self, activo):
        self.no_preguntar_superposicion = bool(activo)
        self.noPreguntarSuperposicionCambiada.emit(self.no_preguntar_superposicion)

    def _on_accesibilidad_cambiada(self):
        self.accesibilidadCambiada.emit()
