import pyqtgraph as pg

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QSizePolicy
)

from PySide6.QtCore import Qt

from utilidades.colores import COLORES

# IMPORTS MODULARES
from .utils import separar_señales, normalizar
from .plot_manager import limpiar, crear_plots
from .seleccion import SelectorRegion


# =========================================================
# CONFIG GLOBAL
# =========================================================

pg.setConfigOption("background", "w")
pg.setConfigOption("foreground", "k")


class Grafica(QWidget):

    def __init__(self):

        super().__init__()

        # =====================================================
        # LAYOUT
        # =====================================================

        layout = QVBoxLayout()

        self.graphics = pg.GraphicsLayoutWidget()

        # SCROLL
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.graphics)

        layout.addWidget(self.scroll)

        self.setLayout(layout)

        self.graphics.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # =====================================================
        # PLOTS DINÁMICOS
        # =====================================================

        self.plots = {}

        self.df = None
        # =====================================================
        # SELECTOR (NUEVO)
        # =====================================================

        self.selector = SelectorRegion(self)

    # =========================================================
    # CALLBACK
    # =========================================================

    def set_callback_region(self, callback):
        self.selector.set_callback(callback)

    # =========================================================
    # ACTIVAR SELECCIÓN
    # =========================================================

    def activar_seleccion(self):
        self.selector.activar()

    # =========================================================
    # LIMPIAR
    # =========================================================

    def limpiar(self):
        limpiar(self.graphics)
        self.plots = {}

    # =========================================================
    # OBTENER RANGO DEL DF
    # =========================================================

    def obtener_rango_df(self, inicio, fin):

        if self.df is None:
            return None

        columnas = self.df.columns.tolist()

        tiempo = self.df[columnas[0]]

        df_filtrado = self.df[
            (tiempo >= inicio)
            &
            (tiempo <= fin)
        ]

        return df_filtrado

    # =========================================================
    # GRAFICAR
    # =========================================================

    def graficar(self, df, señales_visibles):
        self.df = df

        señales_visibles = separar_señales(señales_visibles)

        self.limpiar()

        # USO DEL PLOT MANAGER
        self.plots = crear_plots(self.graphics, señales_visibles)

        columnas = df.columns.tolist()
        x = df[columnas[0]].to_numpy()

        for categoria, señales in señales_visibles.items():

            if categoria not in self.plots:
                continue

            plot = self.plots[categoria]

            for señal in señales:

                if señal not in df.columns:
                    continue

                y = normalizar(df[señal]).to_numpy()

                color = COLORES.get(señal, (0, 0, 0))

                pen = pg.mkPen(color=color, width=2)

                plot.plot(x, y, pen=pen, name=señal)

            plot.enableAutoRange()

    # =========================================================
    # MOUSE EVENTS (USANDO SELECTOR)
    # =========================================================

    def mousePressEvent(self, event):
        self.selector.mouse_press(event, self.plots)
        super().mousePressEvent(event)
