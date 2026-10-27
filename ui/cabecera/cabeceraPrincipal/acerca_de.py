from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from logica import app_info
from logica.interfaz_adaptativa import configurar_geometria_persistente


class AcercaDeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Acerca de {app_info.NOMBRE}")
        self.setModal(True)
        self._init_ui()
        configurar_geometria_persistente(
            self,
            "dialogos/acerca_de/geometria",
            ideal=(760, 620),
            minimo=(480, 380),
            piso=(300, 260),
        )

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        contenido = QWidget()
        contenido_layout = QVBoxLayout()
        contenido_layout.setContentsMargins(20, 20, 20, 16)
        contenido_layout.setSpacing(12)

        titulo = QLabel(app_info.NOMBRE)
        titulo.setStyleSheet("font-size: 22px; font-weight: 700;")
        nombre_completo = QLabel(
            f"{app_info.NOMBRE_COMPLETO}<br>"
            f"<span style='color:#8F8F8F'>{app_info.NOMBRE_COMPLETO_ES}</span>"
        )
        nombre_completo.setStyleSheet("font-size: 14px; color: #B0B0B0;")
        nombre_completo.setWordWrap(True)

        informacion = QLabel(
            f"<b>Versión:</b> {app_info.VERSION} "
            f"({app_info.ALCANCE_VERSION})<br><br>"
            f"<b>Autoría:</b> {app_info.AUTORIA}<br>"
            f"<b>Tutores:</b> {app_info.TUTORIA}<br>"
            f"<b>Institución:</b> {app_info.INSTITUCION}<br>"
            f"<b>Laboratorio:</b> {app_info.LABORATORIO}<br><br>"
            f"{app_info.DESCRIPCION}"
        )
        informacion.setWordWrap(True)
        informacion.setTextInteractionFlags(Qt.TextSelectableByMouse)

        lbl_referencia = QLabel("Referencia sugerida")
        lbl_referencia.setStyleSheet("font-weight: 600;")
        self.txt_referencia = QPlainTextEdit(app_info.REFERENCIA)
        self.txt_referencia.setReadOnly(True)
        self.txt_referencia.setMinimumHeight(150)
        self.txt_referencia.setMaximumHeight(190)

        contenido_layout.addWidget(titulo)
        contenido_layout.addWidget(nombre_completo)
        contenido_layout.addWidget(informacion)
        contenido_layout.addWidget(lbl_referencia)
        contenido_layout.addWidget(self.txt_referencia)
        contenido_layout.addStretch()
        contenido.setLayout(contenido_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(contenido)

        pie = QFrame()
        botones = QHBoxLayout()
        botones.setContentsMargins(20, 12, 20, 16)
        botones.addStretch()
        self.btn_copiar = QPushButton("Copiar referencia")
        btn_cerrar = QPushButton("Cerrar")
        botones.addWidget(self.btn_copiar)
        botones.addWidget(btn_cerrar)
        pie.setLayout(botones)

        layout.addWidget(scroll, 1)
        layout.addWidget(pie)
        self.setLayout(layout)

        self.btn_copiar.clicked.connect(self._copiar_referencia)
        btn_cerrar.clicked.connect(self.accept)

    def _copiar_referencia(self):
        QGuiApplication.clipboard().setText(app_info.REFERENCIA)
        self.btn_copiar.setText("Referencia copiada")
