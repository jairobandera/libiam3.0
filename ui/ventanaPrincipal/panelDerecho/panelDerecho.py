from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QStackedWidget,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QMouseEvent

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
        self.setFixedWidth(self.ANCHO_COLAPSADO)
        self.expandido = False
        self.redimensionando = False
        self.posicion_inicio_x = 0
        self.ancho_inicio = 0
        self.panel_activo = None
        self.info_actual = None
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
        self.filtros = Filtros()
        self.stacked_widget.addWidget(self.filtros)

        # Panel de formulas
        self.formulas = Formulas()
        self.stacked_widget.addWidget(self.formulas)

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
        """Expande el panel y muestra el contenido correspondiente."""
        if panel_nombre == "mapeo":
            self.stacked_widget.setCurrentIndex(0)
        elif panel_nombre == "filtros":
            self.stacked_widget.setCurrentIndex(1)
        elif panel_nombre == "formulas":
            self.stacked_widget.setCurrentIndex(2)
        elif panel_nombre == "detectar_cabeceras":
            self.stacked_widget.setCurrentIndex(3)

        self.panel_activo = panel_nombre
        self.expandido = True
        self.animar_ancho(self.ANCHO_EXPANDIDO)

    def colapsar_panel(self):
        """Colapsa el panel."""
        self.expandido = False
        self.panel_activo = None
        self.animar_ancho(self.ANCHO_COLAPSADO)

    def toggle_panel(self):
        """Expande o colapsa el panel con animacion."""
        self.expandido = not self.expandido

        if self.expandido:
            self.animar_ancho(self.ANCHO_EXPANDIDO)
        else:
            self.animar_ancho(self.ANCHO_COLAPSADO)

    def animar_ancho(self, ancho_final):
        """Anima el cambio de ancho del panel."""
        self.animacion = QPropertyAnimation(self, b"minimumWidth")
        self.animacion.setDuration(250)
        self.animacion.setStartValue(self.width())
        self.animacion.setEndValue(ancho_final)
        self.animacion.setEasingCurve(QEasingCurve.InOutCubic)
        self.animacion.valueChanged.connect(self.actualizar_ancho)
        self.animacion.finished.connect(lambda: self.setFixedWidth(ancho_final))
        self.animacion.start()

    def actualizar_ancho(self, valor):
        """Actualiza el ancho durante la animacion."""
        self.setFixedWidth(int(valor))

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
        self.redimensionando = False
        self.setCursor(Qt.ArrowCursor)
        event.accept()

    def cargar_datos_csv(self, info):
        """Carga los datos detectados del CSV en el panel."""
        self.info_actual = info
        self.config_columnas.cargar_datos(info)
        self.detectar_cabeceras.cargar_datos(info)

    def _on_aliases_guardados(self, secciones):
        """Guarda las secciones pendientes. La re-detección la maneja PanelIzquierdo."""
        print(f"[DEBUG] PanelDerecho._on_aliases_guardados: secciones={secciones}")
        if hasattr(self, 'detectar_cabeceras') and self.detectar_cabeceras is not None:
            self.detectar_cabeceras.secciones_pendientes = secciones
