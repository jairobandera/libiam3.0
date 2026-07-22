from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from logica import app_info


class AcercaDeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Acerca de {app_info.NOMBRE}")
        self.setModal(True)
        self.setMinimumWidth(620)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        titulo = QLabel(app_info.NOMBRE)
        titulo.setStyleSheet("font-size: 22px; font-weight: 700;")
        nombre_completo = QLabel(app_info.NOMBRE_COMPLETO)
        nombre_completo.setStyleSheet("font-size: 14px; color: #B0B0B0;")

        informacion = QLabel(
            f"<b>Versión:</b> {app_info.VERSION}<br>"
            f"<b>Año:</b> {app_info.ANIO}<br>"
            f"<b>Autoría:</b> {app_info.AUTORIA}<br>"
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
        self.txt_referencia.setMaximumHeight(90)

        botones = QHBoxLayout()
        botones.addStretch()
        self.btn_copiar = QPushButton("Copiar referencia")
        btn_cerrar = QPushButton("Cerrar")
        botones.addWidget(self.btn_copiar)
        botones.addWidget(btn_cerrar)

        layout.addWidget(titulo)
        layout.addWidget(nombre_completo)
        layout.addWidget(informacion)
        layout.addWidget(lbl_referencia)
        layout.addWidget(self.txt_referencia)
        layout.addLayout(botones)
        self.setLayout(layout)

        self.btn_copiar.clicked.connect(self._copiar_referencia)
        btn_cerrar.clicked.connect(self.accept)

    def _copiar_referencia(self):
        QGuiApplication.clipboard().setText(app_info.REFERENCIA)
        self.btn_copiar.setText("Referencia copiada")
