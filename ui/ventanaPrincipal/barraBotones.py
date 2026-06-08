from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QPushButton,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
import os


class BarraBotones(QFrame):
    """Barra vertical de botones en el borde derecho de la ventana."""

    def __init__(self, panel_derecho):
        super().__init__()
        self.setObjectName("barraBotones")
        self.setFixedWidth(80)
        self.panel_derecho = panel_derecho

        # Rutas de los iconos SVG
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "utilidades", "icons"))
        self.icon_expandir = QIcon(os.path.join(base_dir, "panel_toggle_expandir.svg"))
        self.icon_colapsar = QIcon(os.path.join(base_dir, "panel_toggle_colapsar.svg"))

        self.panel_activo = None

        self.init_ui()

    def init_ui(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 12, 6, 12)
        layout.setSpacing(12)

        # Boton toggle Mapeo de Columnas
        self.btn_mapeo = QPushButton()
        self.btn_mapeo.setObjectName("btnToggleMapeo")
        self.btn_mapeo.setFixedSize(70, 35)
        self.btn_mapeo.setIcon(self.icon_expandir)
        self.btn_mapeo.setIconSize(QSize(20, 20))
        self.btn_mapeo.setCursor(Qt.PointingHandCursor)
        self.btn_mapeo.setProperty("activo", "false")
        self.btn_mapeo.clicked.connect(lambda: self.toggle_panel("mapeo"))

        # Boton toggle Filtros
        self.btn_filtros = QPushButton()
        self.btn_filtros.setObjectName("btnToggleFiltros")
        self.btn_filtros.setFixedSize(70, 35)
        self.btn_filtros.setIcon(self.icon_expandir)
        self.btn_filtros.setIconSize(QSize(20, 20))
        self.btn_filtros.setCursor(Qt.PointingHandCursor)
        self.btn_filtros.setProperty("activo", "false")
        self.btn_filtros.clicked.connect(lambda: self.toggle_panel("filtros"))

        # Boton toggle Formulas
        self.btn_formulas = QPushButton()
        self.btn_formulas.setObjectName("btnToggleFormulas")
        self.btn_formulas.setFixedSize(70, 35)
        self.btn_formulas.setIcon(self.icon_expandir)
        self.btn_formulas.setIconSize(QSize(20, 20))
        self.btn_formulas.setCursor(Qt.PointingHandCursor)
        self.btn_formulas.setProperty("activo", "false")
        self.btn_formulas.clicked.connect(lambda: self.toggle_panel("formulas"))

        layout.addWidget(self.btn_mapeo)
        layout.addWidget(self.btn_filtros)
        layout.addWidget(self.btn_formulas)
        layout.addStretch()

        self.setLayout(layout)

    def toggle_panel(self, panel_nombre):
        if self.panel_activo == panel_nombre:
            self.panel_derecho.colapsar_panel()
            self.actualizar_icono(panel_nombre, False)
            self.establecer_activo(panel_nombre, False)
            self.panel_activo = None
        else:
            if self.panel_activo:
                self.actualizar_icono(self.panel_activo, False)
                self.establecer_activo(self.panel_activo, False)
            self.panel_derecho.expandir_panel(panel_nombre)
            self.actualizar_icono(panel_nombre, True)
            self.establecer_activo(panel_nombre, True)
            self.panel_activo = panel_nombre

    def actualizar_icono(self, panel_nombre, expandido):
        if panel_nombre == "mapeo":
            self.btn_mapeo.setIcon(self.icon_colapsar if expandido else self.icon_expandir)
        elif panel_nombre == "filtros":
            self.btn_filtros.setIcon(self.icon_colapsar if expandido else self.icon_expandir)
        elif panel_nombre == "formulas":
            self.btn_formulas.setIcon(self.icon_colapsar if expandido else self.icon_expandir)

    def establecer_activo(self, panel_nombre, activo):
        valor = "true" if activo else "false"
        if panel_nombre == "mapeo":
            self.btn_mapeo.setProperty("activo", valor)
            self.btn_mapeo.style().unpolish(self.btn_mapeo)
            self.btn_mapeo.style().polish(self.btn_mapeo)
        elif panel_nombre == "filtros":
            self.btn_filtros.setProperty("activo", valor)
            self.btn_filtros.style().unpolish(self.btn_filtros)
            self.btn_filtros.style().polish(self.btn_filtros)
        elif panel_nombre == "formulas":
            self.btn_formulas.setProperty("activo", valor)
            self.btn_formulas.style().unpolish(self.btn_formulas)
            self.btn_formulas.style().polish(self.btn_formulas)
