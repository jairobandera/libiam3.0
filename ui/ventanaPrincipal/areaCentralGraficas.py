import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class ViewBoxZoom(pg.ViewBox):
    """ViewBox con zoom horizontal centrado en la posicion del cursor."""

    def wheelEvent(self, ev, axis=None):
        delta = ev.delta() if hasattr(ev, "delta") else ev.angleDelta().y()
        factor = 0.85 if delta > 0 else 1.15
        centro = self.mapSceneToView(ev.scenePos())
        self.scaleBy(x=factor, y=1.0, center=centro)
        ev.accept()


class GraficaSenal(pg.PlotWidget):
    rangoSeleccionado = Signal(object, str, object, object, float, float)

    def __init__(self, nombre_senal, parent=None):
        super().__init__(parent=parent, viewBox=ViewBoxZoom())
        self.nombre_senal = nombre_senal
        self.x = None
        self.y = None
        self.modo_seleccion_rango = False
        self.x_inicio = None
        self.linea_inicio = None
        self.linea_preview = None
        self.region_preview = None
        self.region_rango = None

        self.setMinimumHeight(210)
        self.setBackground("#1E1E1E")
        self.setTitle(nombre_senal, color="#FFFFFF", size="11pt")
        self.setLabel("bottom", "Frame")
        self.setLabel("left", nombre_senal)
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setMouseEnabled(x=True, y=False)
        self.getViewBox().setMenuEnabled(False)
        self.scene().sigMouseClicked.connect(self._manejar_click)
        self.scene().sigMouseMoved.connect(self._manejar_mouse_movido)

    def set_datos(self, x, y):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.clear()
        self.linea_inicio = None
        self.linea_preview = None
        self.region_preview = None
        self.region_rango = None
        self.x_inicio = None

        self.plot(self.x, self.y, pen=pg.mkPen("#4FC3F7", width=1.5))
        self.enableAutoRange(axis="y", enable=True)
        self.autoRange()

    def set_modo_seleccion_rango(self, activo):
        self.modo_seleccion_rango = activo
        self.setCursor(Qt.CrossCursor if activo else Qt.ArrowCursor)
        if not activo:
            self.x_inicio = None
            self._limpiar_preview()
            if self.linea_inicio is not None:
                self.removeItem(self.linea_inicio)
                self.linea_inicio = None

    def _manejar_mouse_movido(self, posicion):
        if not self.modo_seleccion_rango or self.x_inicio is None:
            return

        view_box = self.plotItem.vb
        if not view_box.sceneBoundingRect().contains(posicion):
            return

        x_actual = self._normalizar_x_click(float(view_box.mapSceneToView(posicion).x()))
        x_inicio = min(self.x_inicio, x_actual)
        x_fin = max(self.x_inicio, x_actual)
        self._mostrar_preview(x_inicio, x_fin, x_actual)

    def _manejar_click(self, event):
        if not self.modo_seleccion_rango or event.button() != Qt.LeftButton:
            return

        view_box = self.plotItem.vb
        if not view_box.sceneBoundingRect().contains(event.scenePos()):
            return

        x_click = self._normalizar_x_click(float(view_box.mapSceneToView(event.scenePos()).x()))
        if self.x is None or len(self.x) == 0:
            return

        if self.x_inicio is None:
            self._limpiar_rango()
            self.x_inicio = x_click
            self.linea_inicio = pg.InfiniteLine(
                pos=x_click,
                angle=90,
                movable=False,
                pen=pg.mkPen("#FFB74D", width=2),
            )
            self.addItem(self.linea_inicio)
            event.accept()
            return

        x_fin = x_click
        x_inicio = min(self.x_inicio, x_fin)
        x_fin = max(self.x_inicio, x_fin)
        self.x_inicio = None
        self._limpiar_preview()

        if x_inicio == x_fin:
            event.accept()
            return

        self._mostrar_rango(x_inicio, x_fin)
        self.rangoSeleccionado.emit(self, self.nombre_senal, self.x, self.y, x_inicio, x_fin)
        event.accept()

    def _normalizar_x_click(self, x_click):
        x_finito = self.x[np.isfinite(self.x)] if self.x is not None else np.array([])
        if len(x_finito) == 0:
            return x_click

        x_min = float(np.min(x_finito))
        if x_click < x_min:
            return x_min

        x_max = float(np.max(x_finito))
        if x_click > x_max:
            return x_max

        return x_click

    def _mostrar_rango(self, x_inicio, x_fin):
        self._limpiar_rango()
        self.region_rango = pg.LinearRegionItem(
            values=[x_inicio, x_fin],
            movable=False,
            brush=(25, 118, 210, 90),
        )
        self.region_rango.setZValue(-10)
        for linea in self.region_rango.lines:
            linea.setPen(pg.mkPen("#FFB74D", width=2))
        self.addItem(self.region_rango)

    def _mostrar_preview(self, x_inicio, x_fin, x_actual):
        if self.region_preview is None:
            self.region_preview = pg.LinearRegionItem(
                values=[x_inicio, x_fin],
                movable=False,
                brush=(25, 118, 210, 45),
            )
            self.region_preview.setZValue(-20)
            for linea in self.region_preview.lines:
                linea.setPen(pg.mkPen("#64B5F6", width=1))
            self.addItem(self.region_preview)
        else:
            self.region_preview.setRegion([x_inicio, x_fin])

        if self.linea_preview is None:
            self.linea_preview = pg.InfiniteLine(
                pos=x_actual,
                angle=90,
                movable=False,
                pen=pg.mkPen("#64B5F6", width=1.5, style=Qt.DashLine),
            )
            self.addItem(self.linea_preview)
        else:
            self.linea_preview.setPos(x_actual)

    def _limpiar_preview(self):
        if self.linea_preview is not None:
            self.removeItem(self.linea_preview)
            self.linea_preview = None
        if self.region_preview is not None:
            self.removeItem(self.region_preview)
            self.region_preview = None

    def limpiar_seleccion_rango(self):
        self.x_inicio = None
        self._limpiar_preview()
        self._limpiar_rango()

    def _limpiar_rango(self):
        if self.linea_inicio is not None:
            self.removeItem(self.linea_inicio)
            self.linea_inicio = None
        self._limpiar_preview()
        if self.region_rango is not None:
            self.removeItem(self.region_rango)
            self.region_rango = None


class VentanaRangoModal(QDialog):
    def __init__(self, nombre_senal, x, y, x_inicio, x_fin, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{nombre_senal} | Frame {x_inicio:.2f} - {x_fin:.2f}")
        self.setModal(True)
        self.resize(900, 520)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        titulo = QLabel(f"{nombre_senal} | Rango seleccionado")
        titulo.setStyleSheet("font-size: 15px; font-weight: 600; color: #FFFFFF;")
        layout.addWidget(titulo)

        x_rango, y_rango = self._recortar_rango(x, y, x_inicio, x_fin)

        grafica = pg.PlotWidget(viewBox=ViewBoxZoom())
        grafica.setBackground("#1E1E1E")
        grafica.setLabel("bottom", "Frame")
        grafica.setLabel("left", nombre_senal)
        grafica.showGrid(x=True, y=True, alpha=0.25)
        grafica.setMouseEnabled(x=True, y=False)
        grafica.getViewBox().setMenuEnabled(False)

        if len(x_rango) > 0:
            grafica.plot(x_rango, y_rango, pen=pg.mkPen("#4FC3F7", width=1.8))
            grafica.autoRange()
            grafica.setXRange(x_inicio, x_fin, padding=0)
            self._marcar_limites(grafica, x_inicio, x_fin)

        layout.addWidget(grafica, 1)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

        self.setLayout(layout)

    def _recortar_rango(self, x, y, x_inicio, x_fin):
        mascara_finita = np.isfinite(x) & np.isfinite(y)
        x = x[mascara_finita]
        y = y[mascara_finita]

        if len(x) == 0:
            return x, y

        orden = np.argsort(x)
        x = x[orden]
        y = y[orden]

        mascara = (x >= x_inicio) & (x <= x_fin)
        x_rango = x[mascara]
        y_rango = y[mascara]

        puntos_x = []
        puntos_y = []
        x_min = float(x[0])
        x_max = float(x[-1])

        if x_min <= x_inicio <= x_max and not np.any(np.isclose(x_rango, x_inicio)):
            puntos_x.append(x_inicio)
            puntos_y.append(float(np.interp(x_inicio, x, y)))

        puntos_x.extend(x_rango.tolist())
        puntos_y.extend(y_rango.tolist())

        if x_min <= x_fin <= x_max and not np.any(np.isclose(x_rango, x_fin)):
            puntos_x.append(x_fin)
            puntos_y.append(float(np.interp(x_fin, x, y)))

        if not puntos_x:
            return np.array([]), np.array([])

        orden_rango = np.argsort(puntos_x)
        return np.asarray(puntos_x)[orden_rango], np.asarray(puntos_y)[orden_rango]

    def _marcar_limites(self, grafica, x_inicio, x_fin):
        region = pg.LinearRegionItem(
            values=[x_inicio, x_fin],
            movable=False,
            brush=(25, 118, 210, 45),
        )
        region.setZValue(-10)
        for linea in region.lines:
            linea.setPen(pg.mkPen("#FFB74D", width=2))
        grafica.addItem(region)


class AreaCentralGraficas(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("areaCentralGraficas")
        self.nombre_archivo = None
        self.df_original = None
        self.df_grafica = None
        self.columna_x = None
        self.mapeo_actual = None
        self.modo_seleccion_rango = False
        self.graficas = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        self.stack = QStackedWidget()

        self.placeholder = QWidget()
        layout_placeholder = QVBoxLayout()
        layout_placeholder.setContentsMargins(0, 0, 0, 0)
        layout_placeholder.addStretch()

        self.lbl_estado = QLabel("Carga un archivo .CSV para visualizar las senales")
        self.lbl_estado.setObjectName("estadoGraficas")
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        self.lbl_estado.setStyleSheet("color: #B0B0B0; font-size: 15px;")
        layout_placeholder.addWidget(self.lbl_estado)
        layout_placeholder.addStretch()
        self.placeholder.setLayout(layout_placeholder)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.contenedor = QWidget()
        self.layout_graficas = QVBoxLayout()
        self.layout_graficas.setContentsMargins(0, 0, 0, 0)
        self.layout_graficas.setSpacing(12)
        self.contenedor.setLayout(self.layout_graficas)
        self.scroll.setWidget(self.contenedor)

        self.stack.addWidget(self.placeholder)
        self.stack.addWidget(self.scroll)

        layout.addWidget(self.stack, 1)
        self.setLayout(layout)

    def cargar_dataframe(self, nombre_archivo, df, info):
        self.nombre_archivo = nombre_archivo
        self.df_original = df
        self.df_grafica, self.columna_x = self._preparar_dataframe(df)
        self.mapeo_actual = self._mapeo_desde_info(info)
        self._graficar()

    def actualizar_mapeo(self, mapeo):
        self.mapeo_actual = mapeo
        if self.df_grafica is not None:
            self._graficar()

    def set_modo_seleccion_rango(self, activo):
        self.modo_seleccion_rango = activo
        for grafica in self.graficas:
            grafica.set_modo_seleccion_rango(activo)

    def _preparar_dataframe(self, df):
        frame_col = self._buscar_columna(df, "frame")
        subframe_col = self._buscar_columna(df, "subframe", "sub_frame")

        if frame_col and subframe_col:
            columnas_numericas = list(df.select_dtypes(include=[np.number]).columns)
            columnas_promedio = [col for col in columnas_numericas if col != frame_col]
            if columnas_promedio:
                return df.groupby(frame_col, as_index=False)[columnas_promedio].mean(), frame_col

        if frame_col:
            return df.copy(), frame_col

        tiempo_col = self._buscar_columna(df, "time", "time_s", "tiempo")
        if tiempo_col:
            return df.copy(), tiempo_col

        df_indice = df.copy()
        df_indice["Indice"] = np.arange(len(df_indice), dtype=float)
        return df_indice, "Indice"

    def _buscar_columna(self, df, *nombres):
        nombres_normalizados = {nombre.lower().strip() for nombre in nombres}
        for columna in df.columns:
            if str(columna).lower().strip() in nombres_normalizados:
                return columna
        return None

    def _mapeo_desde_info(self, info):
        deteccion = info.get("deteccion", {}) if info else {}
        mapeo = deteccion.get("mapeo", {})
        resultado = {}

        for tipo, ejes in mapeo.items():
            if not isinstance(ejes, dict):
                continue
            resultado[tipo] = {}
            for eje, columna in ejes.items():
                resultado[tipo][eje] = {"columna": columna, "activo": True}

        return resultado

    def _obtener_columnas_a_graficar(self):
        columnas = []

        if self.mapeo_actual:
            for ejes in self.mapeo_actual.values():
                if not isinstance(ejes, dict):
                    continue
                for config in ejes.values():
                    if isinstance(config, dict):
                        columna = config.get("columna")
                        activo = config.get("activo", True)
                    else:
                        columna = config
                        activo = True
                    if activo and columna and columna not in columnas:
                        columnas.append(columna)

        columnas_validas = [
            col for col in columnas
            if col in self.df_grafica.columns and col != self.columna_x and self._es_numerica(col)
        ]

        if columnas_validas:
            return columnas_validas

        columnas_numericas = [
            col for col in self.df_grafica.select_dtypes(include=[np.number]).columns
            if col != self.columna_x and str(col).lower().strip() not in {"subframe", "sub_frame"}
        ]
        return columnas_numericas

    def _es_numerica(self, columna):
        return np.issubdtype(self.df_grafica[columna].dtype, np.number)

    def _graficar(self):
        self._limpiar_graficas()

        if self.df_grafica is None or self.columna_x not in self.df_grafica.columns:
            self._mostrar_placeholder("No hay datos disponibles para graficar.")
            return

        columnas = self._obtener_columnas_a_graficar()
        if not columnas:
            self._mostrar_placeholder("No se encontraron columnas numericas para graficar.")
            return

        self.stack.setCurrentWidget(self.scroll)

        x = self.df_grafica[self.columna_x].to_numpy(dtype=float)
        for columna in columnas:
            y = self.df_grafica[columna].to_numpy(dtype=float)
            mascara = np.isfinite(x) & np.isfinite(y)
            if not mascara.any():
                continue

            grafica = GraficaSenal(str(columna))
            grafica.set_datos(x[mascara], y[mascara])
            grafica.set_modo_seleccion_rango(self.modo_seleccion_rango)
            grafica.rangoSeleccionado.connect(self._abrir_rango_modal)
            self.layout_graficas.addWidget(grafica)
            self.graficas.append(grafica)

        self.layout_graficas.addStretch()

    def _limpiar_graficas(self):
        self.graficas = []
        while self.layout_graficas.count():
            item = self.layout_graficas.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _mostrar_placeholder(self, texto):
        self.lbl_estado.setText(texto)
        self.stack.setCurrentWidget(self.placeholder)

    def _abrir_rango_modal(self, grafica_senal, nombre_senal, x, y, x_inicio, x_fin):
        ventana = VentanaRangoModal(nombre_senal, x, y, x_inicio, x_fin, self)
        ventana.exec()
        grafica_senal.limpiar_seleccion_rango()
