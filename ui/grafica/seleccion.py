import pyqtgraph as pg

from PySide6.QtCore import Qt


class SelectorRegion:

    def __init__(self, parent):

        self.parent = parent

        self.modo_seleccion = False

        self.x1 = None
        self.x2 = None

        self.region_item = None

        self.callback = None

        self.plot_seleccionado = None

    # =====================================================
    # CALLBACK
    # =====================================================

    def set_callback(self, callback):

        self.callback = callback

    # =====================================================
    # ACTIVAR
    # =====================================================

    def activar(self):

        self.modo_seleccion = True

        self.x1 = None
        self.x2 = None

        self.plot_seleccionado = None

        self.parent.setCursor(Qt.CrossCursor)

    # =====================================================
    # OBTENER PLOT
    # =====================================================

    def obtener_plot_desde_mouse(self, event, plots):

        scene_pos = self.parent.graphics.mapToScene(
            event.position().toPoint()
        )

        for nombre, plot in plots.items():

            rect = plot.sceneBoundingRect()

            if rect.contains(scene_pos):

                return nombre, plot

        return None, None

    # =====================================================
    # OBTENER X
    # =====================================================

    def obtener_x(self, event, plot):

        scene_pos = self.parent.graphics.mapToScene(
            event.position().toPoint()
        )

        vb = plot.vb

        punto = vb.mapSceneToView(scene_pos)

        return punto.x()

    # =====================================================
    # CLICK
    # =====================================================

    def mouse_press(self, event, plots):

        if (
            not self.modo_seleccion
            or event.button() != Qt.LeftButton
            or not plots
        ):
            return

        # ============================================
        # DETECTAR PLOT SELECCIONADO
        # ============================================

        nombre_plot, plot = self.obtener_plot_desde_mouse(
            event,
            plots
        )

        if plot is None:
            return

        # ============================================
        # GUARDAR PLOT
        # ============================================

        self.plot_seleccionado = nombre_plot

        x = self.obtener_x(event, plot)

        # ============================================
        # PRIMER CLICK
        # ============================================

        if self.x1 is None:

            self.x1 = x

            if self.region_item:

                plot.removeItem(
                    self.region_item
                )

            self.region_item = pg.LinearRegionItem(
                values=[x, x],
                orientation="vertical",
                movable=False
            )

            plot.addItem(
                self.region_item
            )

            return

        # ============================================
        # SEGUNDO CLICK
        # ============================================

        self.x2 = x

        inicio = min(self.x1, self.x2)
        fin = max(self.x1, self.x2)

        self.region_item.setRegion([
            inicio,
            fin
        ])

        self.modo_seleccion = False

        self.parent.setCursor(
            Qt.ArrowCursor
        )

        if self.callback:

            self.callback(
                inicio,
                fin,
                self.plot_seleccionado
            )