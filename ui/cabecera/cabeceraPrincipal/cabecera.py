from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QToolButton,
    QSizePolicy,

)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon


class Cabecera(QFrame): #Componenete visual reautilizable, es la barra superior en si

    def __init__(self): #Constructor
        super().__init__()
        self.setObjectName("topHeader")
        self.init_ui()

    def init_ui(self):

        layout = QHBoxLayout() #Todo se organiza en una fila (IZquierda - Derecha)
        layout.setContentsMargins(20, 4, 20, 4)  #Margenes internos del layout
        layout.setSpacing(10)

        # IZQUIERDA (LOGO + TEXTO)
        from PySide6.QtGui import QPixmap
        import os

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) #Permite encontrar /icons correctamente.

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

        titulo = QLabel("LIBiAM 3.0")
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
            ("Proyecto", "utilidades/icons/home.svg"),
            ("Guardar", "utilidades/icons/save.svg"),
            ("Exportar", "utilidades/icons/export.svg"),
            ("Ayuda", "utilidades/icons/help.svg"),
        ]

        for texto, icono in botones: #Genera botones dinamicamente.

            btn = QToolButton()
            btn.setText(texto)
            btn.setIcon(QIcon(icono)) #Carga el icono del botón.
            btn.setIconSize(QSize(20, 20))  #Tamaño del icono.
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon) #Icono y texto.
            btn.setObjectName("toolbarButton")
            btn.setCursor(Qt.PointingHandCursor)

            btn.setMinimumWidth(70) #Evita que el texto se corte.

            right_layout.addWidget(btn)

        layout.addLayout(left_layout)
        layout.addStretch()
        layout.addLayout(right_layout)

        self.setLayout(layout)