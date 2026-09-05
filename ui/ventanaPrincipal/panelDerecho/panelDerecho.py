from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QStackedWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

from ui.ventanaPrincipal.panelDerecho.configColumnas import ConfigColumnas
from ui.ventanaPrincipal.panelDerecho.filtros import Filtros
from ui.ventanaPrincipal.panelDerecho.formulas import Formulas
from ui.ventanaPrincipal.panelDerecho.detectarCabeceras import DetectarCabeceras


class PanelDerecho(QFrame):

    ANCHO_EXPANDIDO = 340
    ANCHO_COLAPSADO = 0
    ANCHO_MINIMO = 340
    ANCHO_MAXIMO = 800
    ZONA_ARRASTRE = 5

    def __init__(self, db_session=None):
        super().__init__()
        self.setObjectName("panelDerecho")
        self.db_session = db_session
        self.setFixedWidth(self.ANCHO_EXPANDIDO)
        self.hide()
        self.expandido = False
        self.redimensionando = False
        self.posicion_inicio_x = 0
        self.ancho_inicio = 0
        self.panel_activo = None
        self.info_actual = None
        self.ancho_expandido_actual = self.ANCHO_EXPANDIDO
        self.init_ui()

    def init_ui(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stacked widget para cambiar entre paneles
        self.stacked_widget = QStackedWidget()

        # Panel de mapeo de columnas
        scroll_mapeo = QScrollArea()
        scroll_mapeo.setWidgetResizable(True)
        scroll_mapeo.setFrameShape(QFrame.NoFrame)
        scroll_mapeo.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.config_columnas = ConfigColumnas()
        scroll_mapeo.setWidget(self.config_columnas)
        self.stacked_widget.addWidget(scroll_mapeo)

        # Panel de filtros
        scroll_filtros = QScrollArea()
        scroll_filtros.setWidgetResizable(True)
        scroll_filtros.setFrameShape(QFrame.NoFrame)
        scroll_filtros.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filtros = Filtros()
        scroll_filtros.setWidget(self.filtros)
        self.stacked_widget.addWidget(scroll_filtros)

        # Panel de formulas
        scroll_formulas = QScrollArea()
        scroll_formulas.setWidgetResizable(True)
        scroll_formulas.setFrameShape(QFrame.NoFrame)
        scroll_formulas.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.formulas = Formulas(db_session=self.db_session)
        scroll_formulas.setWidget(self.formulas)
        self.stacked_widget.addWidget(scroll_formulas)

        # Panel de detectar cabeceras
        scroll_detectar = QScrollArea()
        scroll_detectar.setWidgetResizable(True)
        scroll_detectar.setFrameShape(QFrame.NoFrame)
        scroll_detectar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.detectar_cabeceras = DetectarCabeceras(db_session=self.db_session)
        self.detectar_cabeceras.aliasesGuardados.connect(self._on_aliases_guardados)
        scroll_detectar.setWidget(self.detectar_cabeceras)
        self.stacked_widget.addWidget(scroll_detectar)

        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)

    def expandir_panel(self, panel_nombre):
        """Muestra el panel sin redimensionar las gráficas cuadro a cuadro."""
        if panel_nombre == "mapeo":
            self.stacked_widget.setCurrentIndex(0)
        elif panel_nombre == "filtros":
            self.stacked_widget.setCurrentIndex(1)
        elif panel_nombre == "formulas":
            self.stacked_widget.setCurrentIndex(2)
        elif panel_nombre == "detectar_cabeceras":
            self.stacked_widget.setCurrentIndex(3)

        self.panel_activo = panel_nombre
        if not self.expandido:
            self.expandido = True
            self.setFixedWidth(self.ancho_expandido_actual)
            self.show()

    def colapsar_panel(self):
        """Oculta el panel en una sola actualización de la interfaz."""
        if self.width() >= self.ANCHO_MINIMO:
            self.ancho_expandido_actual = self.width()
        self.expandido = False
        self.panel_activo = None
        self.hide()

    def toggle_panel(self):
        """Expande o colapsa el panel de forma inmediata."""
        if self.expandido:
            self.colapsar_panel()
        else:
            self.expandido = True
            self.setFixedWidth(self.ancho_expandido_actual)
            self.show()

    def animar_ancho(self, ancho_final):
        """Mantiene compatibilidad con llamadas anteriores, sin animación."""
        if ancho_final <= self.ANCHO_COLAPSADO:
            self.colapsar_panel()
            return
        self.ancho_expandido_actual = max(
            self.ANCHO_MINIMO, min(self.ANCHO_MAXIMO, int(ancho_final))
        )
        self.expandido = True
        self.setFixedWidth(self.ancho_expandido_actual)
        self.show()

    def actualizar_ancho(self, valor):
        """Actualiza el ancho solicitado sin generar una animación intermedia."""
        self.animar_ancho(int(valor))

    def mousePressEvent(self, event: QMouseEvent):
        """Detecta click en la zona de arrastre del borde izquierdo."""
        if event.pos().x() <= self.ZONA_ARRASTRE and self.expandido:
            self.redimensionando = True
            self.posicion_inicio_x = event.globalPos().x()
            self.ancho_inicio = self.width()
            self.setCursor(Qt.SizeHorCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Maneja el arrastre para redimensionar el panel."""
        if self.redimensionando:
            delta = self.posicion_inicio_x - event.globalPos().x()
            nuevo_ancho = max(self.ANCHO_MINIMO, min(self.ANCHO_MAXIMO, self.ancho_inicio + delta))
            self.setFixedWidth(nuevo_ancho)
            event.accept()
        else:
            if event.pos().x() <= self.ZONA_ARRASTRE and self.expandido:
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Finaliza el arrastre."""
        if self.redimensionando:
            self.ancho_expandido_actual = self.width()
        self.redimensionando = False
        self.setCursor(Qt.ArrowCursor)
        event.accept()

    def cargar_datos_csv(self, info):
        """Carga los datos detectados del CSV en el panel."""
        self.info_actual = info
        self.config_columnas.cargar_datos(info)
        self.filtros.cargar_datos(info)
        self.detectar_cabeceras.cargar_datos(info)

    def _on_aliases_guardados(self, secciones):
        """Guarda las secciones pendientes. La re-detección la maneja PanelIzquierdo."""
        if hasattr(self, 'detectar_cabeceras') and self.detectar_cabeceras is not None:
            self.detectar_cabeceras.secciones_pendientes = secciones
