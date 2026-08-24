"""Diálogo para abrir un proyecto guardado en la carpeta «archivos».

Deliberadamente **no** es un explorador de archivos: no se puede navegar a otra
ruta ni escribir una. Solo lista los CSV que guardó el botón «Guardar», que son
los únicos que pueden traer intervalos y notas asociados.
"""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from logica import proyecto


class CargarProyectoDialog(QDialog):
    """Selector de proyectos guardados. Devuelve el proyecto elegido."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cargar proyecto")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setObjectName("dialogoCargar")
        self.proyectos = proyecto.listar_proyectos()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        titulo = QLabel("Cargar proyecto")
        titulo.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(titulo)

        subtitulo = QLabel(
            "Proyectos guardados en la carpeta «archivos». "
            "Al abrirlos se restauran sus intervalos, sub-intervalos y notas."
        )
        subtitulo.setObjectName("dialogoCargarAyuda")
        subtitulo.setWordWrap(True)
        layout.addWidget(subtitulo)

        self.lista = QListWidget()
        self.lista.setObjectName("listaProyectos")
        self.lista.setMinimumHeight(220)
        self.lista.itemDoubleClicked.connect(self._on_doble_click)
        self.lista.currentItemChanged.connect(self._actualizar_detalle)
        layout.addWidget(self.lista, 1)

        self.lbl_detalle = QLabel("")
        self.lbl_detalle.setObjectName("dialogoCargarDetalle")
        self.lbl_detalle.setWordWrap(True)
        layout.addWidget(self.lbl_detalle)

        botones = QHBoxLayout()
        botones.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnDialogoSecundario")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)

        self.btn_abrir = QPushButton("Abrir")
        self.btn_abrir.setObjectName("btnDialogoPrimario")
        self.btn_abrir.setCursor(Qt.PointingHandCursor)
        self.btn_abrir.setDefault(True)
        self.btn_abrir.clicked.connect(self.accept)

        botones.addWidget(btn_cancelar)
        botones.addWidget(self.btn_abrir)
        layout.addLayout(botones)

        self.setLayout(layout)
        self._poblar_lista()

    def _poblar_lista(self):
        self.lista.clear()

        if not self.proyectos:
            item = QListWidgetItem(
                "Todavía no hay proyectos guardados.\n"
                "Usá «Guardar» para crear el primero."
            )
            item.setFlags(Qt.NoItemFlags)
            self.lista.addItem(item)
            self.btn_abrir.setEnabled(False)
            self.lbl_detalle.setText("")
            return

        for datos in self.proyectos:
            item = QListWidgetItem(datos["nombre"])
            item.setData(Qt.UserRole, datos)
            item.setToolTip(datos["archivo"])
            self.lista.addItem(item)

        self.lista.setCurrentRow(0)

    def _actualizar_detalle(self, actual, _anterior=None):
        datos = actual.data(Qt.UserRole) if actual is not None else None
        if not datos:
            self.lbl_detalle.setText("")
            return

        partes = []
        if datos["modificado"]:
            fecha = datetime.fromtimestamp(datos["modificado"])
            partes.append(f"Guardado el {fecha.strftime('%d/%m/%Y a las %H:%M')}")

        if datos["tiene_anotaciones"]:
            cantidad = len(proyecto.leer_anotaciones(datos["ruta_anotaciones"]))
            if cantidad:
                partes.append(f"{cantidad} intervalo(s)/sub-intervalo(s) con sus notas")
            else:
                partes.append("Sin intervalos guardados")
        else:
            partes.append("Sin archivo de anotaciones")

        self.lbl_detalle.setText(" · ".join(partes))

    def _on_doble_click(self, item):
        if item.data(Qt.UserRole):
            self.accept()

    def proyecto_seleccionado(self):
        """Datos del proyecto elegido, o ``None`` si no hay ninguno."""
        item = self.lista.currentItem()
        return item.data(Qt.UserRole) if item is not None else None
