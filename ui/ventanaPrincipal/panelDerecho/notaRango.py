from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class NotaDialog(QDialog):
    """Editor de una nota breve para un rango o sub-rango, con contador."""

    MAX = 1000

    def __init__(self, parent=None, nombre="", nota=""):
        super().__init__(parent)
        self.setWindowTitle("Nota del rango")
        self.setModal(True)
        self.setMinimumWidth(420)
        self._init_ui(nombre, nota)

    def _init_ui(self, nombre, nota):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        titulo = QLabel(f"Nota para «{nombre}»")
        titulo.setStyleSheet("font-weight: 600;")
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        ayuda = QLabel(
            "Escribí una breve descripción o recordatorio de lo que pasa en "
            "este rango."
        )
        ayuda.setWordWrap(True)
        ayuda.setStyleSheet("color: #B0B0B0;")
        layout.addWidget(ayuda)

        self.editor = QPlainTextEdit()
        self.editor.setPlainText(nota or "")
        self.editor.setMinimumHeight(120)
        layout.addWidget(self.editor)

        self.lbl_contador = QLabel()
        self.lbl_contador.setAlignment(Qt.AlignRight)
        self.lbl_contador.setStyleSheet("color: #8A8A8A;")
        layout.addWidget(self.lbl_contador)

        botones = QHBoxLayout()
        botones.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_guardar = QPushButton("Guardar")
        btn_guardar.setDefault(True)
        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_guardar)
        layout.addLayout(botones)

        self.setLayout(layout)

        self.editor.textChanged.connect(self._on_text_changed)
        btn_cancelar.clicked.connect(self.reject)
        btn_guardar.clicked.connect(self.accept)
        self._on_text_changed()

    def _on_text_changed(self):
        texto = self.editor.toPlainText()
        if len(texto) > self.MAX:
            self.editor.blockSignals(True)
            self.editor.setPlainText(texto[: self.MAX])
            self.editor.moveCursor(QTextCursor.End)
            self.editor.blockSignals(False)
            texto = self.editor.toPlainText()
        self.lbl_contador.setText(f"{len(texto)}/{self.MAX}")

    def texto(self):
        return self.editor.toPlainText().strip()
