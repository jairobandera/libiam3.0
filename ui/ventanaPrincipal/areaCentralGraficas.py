import math
import re

import numpy as np
import pandas as pd
import pyqtgraph as pg

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from logica.filtros_senales import (
    ErrorConfiguracionFiltro,
    aplicar_butterworth,
)
from logica.rangos import GestorRangos, RangoSuperpuestoError


class EjeDecimal(pg.AxisItem):
    """Eje sin factores como ``×1e-06``; muestra el valor decimal real."""

    def tickStrings(self, values, scale, spacing):
        if self.logMode:
            return self.logTickStrings(values, scale, spacing)

        paso = abs(float(spacing) * float(scale))
        if not math.isfinite(paso) or paso <= 0:
            decimales = 6
        else:
            decimales = max(0, min(12, math.ceil(-math.log10(paso))))

        limite_cero = 0.5 * (10 ** -decimales) if decimales else 0.5
        textos = []
        for valor in values:
            escalado = float(valor) * float(scale)
            if abs(escalado) < limite_cero:
                escalado = 0.0
            textos.append(f"{escalado:.{decimales}f}")
        return textos


class ViewBoxZoom(pg.ViewBox):
    """ViewBox con zoom horizontal centrado en la posición del cursor."""

    def wheelEvent(self, ev, axis=None):
        delta = ev.delta() if hasattr(ev, "delta") else ev.angleDelta().y()
        factor = 0.85 if delta > 0 else 1.15
        centro = self.mapSceneToView(ev.scenePos())
        self.scaleBy(x=factor, y=1.0, center=centro)
        ev.accept()


class GraficaSenal(pg.PlotWidget):
    """Gráfica que propone rangos enteros; el área central los valida."""

    rangoPropuesto = Signal(object, int, int)

    def __init__(
        self,
        nombre_senal,
        unidad=None,
        etiqueta_x="Frame",
        columna=None,
        parent=None,
    ):
        eje_izquierdo = EjeDecimal(orientation="left")
        eje_izquierdo.enableAutoSIPrefix(False)
        super().__init__(
            parent=parent,
            viewBox=ViewBoxZoom(),
            axisItems={"left": eje_izquierdo},
        )
        self.nombre_senal = nombre_senal
        self.columna = columna
        self.unidad = unidad
        self.x = None
        self.y = None
        self.y_original = None
        self.y_filtrada = None
        self.modo_seleccion_rango = False
        self.x_inicio = None
        self.linea_inicio = None
        self.linea_preview = None
        self.region_preview = None
        self.regiones_rangos = {}

        self.setMinimumHeight(210)
        self.setBackground("#1E1E1E")
        self.setTitle(nombre_senal, color="#FFFFFF", size="11pt")
        self.setLabel("bottom", etiqueta_x)
        self.setLabel("left", unidad or "Sin unidad")
        self.getAxis("left").enableAutoSIPrefix(False)
        self.getAxis("left").setStyle(
            tickTextWidth=82,
            autoExpandTextSpace=True,
            autoReduceTextSpace=False,
        )
        self.getAxis("left").setWidth(100)
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setMouseEnabled(x=True, y=False)
        self.getViewBox().setMenuEnabled(False)
        self.plotItem.setDownsampling(auto=True, mode="peak")
        self.plotItem.setClipToView(True)
        self.leyenda = self.addLegend(offset=(-10, 10))
        self.leyenda.hide()
        self.scene().sigMouseClicked.connect(self._manejar_click)
        self.scene().sigMouseMoved.connect(self._manejar_mouse_movido)

    def set_datos(self, x, y_original, y_filtrada=None):
        self.x = np.asarray(x, dtype=float)
        self.y_original = np.asarray(y_original, dtype=float)
        self.y_filtrada = (
            np.asarray(y_filtrada, dtype=float)
            if y_filtrada is not None
            else None
        )
        self.y = self.y_filtrada if self.y_filtrada is not None else self.y_original
        self.clear()
        self.linea_inicio = None
        self.linea_preview = None
        self.region_preview = None
        self.regiones_rangos = {}
        self.x_inicio = None

        color_original = pg.mkColor("#4FC3F7")
        if self.y_filtrada is not None:
            color_original.setAlpha(165)
        self.plot(
            self.x,
            self.y_original,
            pen=pg.mkPen(color_original, width=1.2),
            name="Original",
        )
        if self.y_filtrada is not None:
            self.plot(
                self.x,
                self.y_filtrada,
                pen=pg.mkPen("#FFB300", width=2.2),
                name="Filtrada",
            )
            self.leyenda.show()
        else:
            self.leyenda.hide()
        self.enableAutoRange(axis="y", enable=True)
        self.autoRange()

    def set_modo_seleccion_rango(self, activo):
        self.modo_seleccion_rango = activo
        self.setCursor(Qt.CrossCursor if activo else Qt.ArrowCursor)
        if not activo:
            self._cancelar_propuesta()

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
        if self.x is None or len(self.x) == 0:
            return

        x_click = self._normalizar_x_click(float(view_box.mapSceneToView(event.scenePos()).x()))
        if self.x_inicio is None:
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

        x_inicio, x_fin = self.x_inicio, x_click
        self._cancelar_propuesta()
        if x_inicio != x_fin:
            self.rangoPropuesto.emit(self, x_inicio, x_fin)
        event.accept()

    @staticmethod
    def _redondear_entero(valor):
        # round() usa redondeo bancario para .5; aquí se necesita el entero
        # más cercano de forma intuitiva para seleccionar frames.
        return int(math.floor(valor + 0.5)) if valor >= 0 else int(math.ceil(valor - 0.5))

    def _normalizar_x_click(self, x_click):
        x_finito = self.x[np.isfinite(self.x)] if self.x is not None else np.array([])
        if len(x_finito) == 0:
            return self._redondear_entero(x_click)

        x_min = self._redondear_entero(float(np.min(x_finito)))
        x_max = self._redondear_entero(float(np.max(x_finito)))
        return max(x_min, min(x_max, self._redondear_entero(x_click)))

    def _mostrar_preview(self, x_inicio, x_fin, x_actual):
        if self.region_preview is None:
            self.region_preview = pg.LinearRegionItem(
                values=[x_inicio, x_fin], movable=False, brush=(255, 183, 77, 45)
            )
            self.region_preview.setZValue(-20)
            for linea in self.region_preview.lines:
                linea.setPen(pg.mkPen("#FFB74D", width=1))
            self.addItem(self.region_preview)
        else:
            self.region_preview.setRegion([x_inicio, x_fin])

        if self.linea_preview is None:
            self.linea_preview = pg.InfiniteLine(
                pos=x_actual,
                angle=90,
                movable=False,
                pen=pg.mkPen("#FFB74D", width=1.5, style=Qt.DashLine),
            )
            self.addItem(self.linea_preview)
        else:
            self.linea_preview.setPos(x_actual)

    def _cancelar_propuesta(self):
        self.x_inicio = None
        if self.linea_inicio is not None:
            self.removeItem(self.linea_inicio)
            self.linea_inicio = None
        if self.linea_preview is not None:
            self.removeItem(self.linea_preview)
            self.linea_preview = None
        if self.region_preview is not None:
            self.removeItem(self.region_preview)
            self.region_preview = None

    def mostrar_rangos(self, rangos):
        for region in self.regiones_rangos.values():
            self.removeItem(region)
        self.regiones_rangos = {}

        for rango in rangos:
            color = pg.mkColor(rango.color)
            color_brush = pg.mkColor(rango.color)
            color_brush.setAlpha(55)
            region = pg.LinearRegionItem(
                values=[rango.desde, rango.hasta], movable=False, brush=color_brush
            )
            region.setZValue(-10)
            for linea in region.lines:
                linea.setPen(pg.mkPen(color, width=2))
            self.addItem(region)
            self.regiones_rangos[rango.numero] = region

    def proponer_rango(self, x_inicio, x_fin):
        if self.x is None or len(self.x) == 0:
            return
        x_inicio = self._normalizar_x_click(float(x_inicio))
        x_fin = self._normalizar_x_click(float(x_fin))
        if x_inicio != x_fin:
            self.rangoPropuesto.emit(self, x_inicio, x_fin)


class AreaCentralGraficas(QFrame):
    rangosCambiados = Signal(object)
    rangoRechazado = Signal(str)
    rangoAjustado = Signal(str)
    filtroEstadoCambiado = Signal(bool, str)
    senalesDisponiblesCambiaron = Signal(object)

    def __init__(self):
        super().__init__()
        self.setObjectName("areaCentralGraficas")
        self.nombre_archivo = None
        self.df_original = None
        self.df_grafica_original = None
        self.df_grafica = None
        self.columna_x = None
        self.mapeo_actual = None
        self.modo_seleccion_rango = False
        self.graficas = []
        self.graficas_por_columna = {}
        self.unidades = {}
        self.frecuencia_grafica = None
        self.gestores_rangos = {}
        self.columnas_filtradas = set()
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
        self.lbl_estado = QLabel("Carga un archivo .CSV para visualizar las señales")
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
        preparado, self.columna_x = self._preparar_dataframe(df)
        self.df_grafica_original = preparado.copy()
        self.df_grafica = preparado.copy()
        self.mapeo_actual = self._mapeo_desde_info(info)
        self.unidades = dict((info or {}).get("unidades", df.attrs.get("unidades", {})))
        self.frecuencia_grafica = (info or {}).get("frecuencia_grafica")
        self.gestores_rangos = {}
        self.columnas_filtradas = set()
        self.rangosCambiados.emit([])
        self._crear_graficas()
        self._actualizar_visibilidad()

    def actualizar_mapeo(self, mapeo):
        self.mapeo_actual = mapeo
        columnas_nuevas = set(self._obtener_todas_columnas_mapeo())
        if not columnas_nuevas.issubset(self.graficas_por_columna):
            self._crear_graficas()
        self._actualizar_visibilidad()

    def set_modo_seleccion_rango(self, activo):
        self.modo_seleccion_rango = activo
        for grafica in self.graficas:
            grafica.set_modo_seleccion_rango(activo)

    @staticmethod
    def _normalizar_identificador(valor):
        return re.sub(r"[^a-z0-9]+", "", str(valor).lower())

    def _preparar_dataframe(self, df):
        df_preparado = df.copy()
        df_preparado.attrs.update(df.attrs)
        for columna in df_preparado.columns:
            if not pd.api.types.is_numeric_dtype(df_preparado[columna]):
                df_preparado[columna] = pd.to_numeric(df_preparado[columna], errors="coerce")

        frame_col = self._buscar_columna(df_preparado, "frame")
        subframe_col = self._buscar_columna(df_preparado, "subframe", "sub frame", "sub_frame")

        if frame_col and subframe_col:
            columnas_numericas = list(df_preparado.select_dtypes(include=[np.number]).columns)
            columnas_promedio = [
                columna
                for columna in columnas_numericas
                if columna not in {frame_col, subframe_col}
            ]
            if columnas_promedio:
                agrupado = df_preparado.groupby(frame_col, as_index=False, sort=False)[
                    columnas_promedio
                ].mean()
                agrupado.attrs.update(df.attrs)
                return agrupado, frame_col

        if frame_col:
            return df_preparado, frame_col

        tiempo_col = self._buscar_columna(df_preparado, "time", "time_s", "tiempo")
        if tiempo_col:
            return df_preparado, tiempo_col

        df_preparado["Indice"] = np.arange(len(df_preparado), dtype=float)
        return df_preparado, "Indice"

    def _buscar_columna(self, df, *nombres):
        nombres_normalizados = {self._normalizar_identificador(nombre) for nombre in nombres}
        for columna in df.columns:
            if self._normalizar_identificador(columna) in nombres_normalizados:
                return columna
        return None

    def _mapeo_desde_info(self, info):
        deteccion = info.get("deteccion", {}) if info else {}
        mapeo = deteccion.get("mapeo", {})
        resultado = {}
        for tipo, ejes in mapeo.items():
            if not isinstance(ejes, dict):
                continue
            resultado[tipo] = {
                eje: {"columna": columna, "activo": True}
                for eje, columna in ejes.items()
            }
        return resultado

    def _obtener_todas_columnas_mapeo(self):
        columnas = []
        if self.mapeo_actual:
            for ejes in self.mapeo_actual.values():
                if not isinstance(ejes, dict):
                    continue
                for config in ejes.values():
                    columna = config.get("columna") if isinstance(config, dict) else config
                    if columna and columna not in columnas:
                        columnas.append(columna)
        return [
            columna
            for columna in columnas
            if self.df_grafica is not None
            and columna in self.df_grafica.columns
            and columna != self.columna_x
            and self._es_numerica(columna)
        ]

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
                        columna, activo = config, True
                    if activo and columna and columna not in columnas:
                        columnas.append(columna)
            return [
                columna
                for columna in columnas
                if columna in self.df_grafica.columns
                and columna != self.columna_x
                and self._es_numerica(columna)
            ]

        return [
            columna
            for columna in self.df_grafica.select_dtypes(include=[np.number]).columns
            if columna != self.columna_x
            and self._normalizar_identificador(columna) != "subframe"
        ]

    def _es_numerica(self, columna):
        return pd.api.types.is_numeric_dtype(self.df_grafica[columna])

    def _obtener_labels_columnas(self):
        labels = {}
        if self.mapeo_actual:
            for tipo, ejes in self.mapeo_actual.items():
                if not isinstance(ejes, dict):
                    continue
                for eje, config in ejes.items():
                    columna = config.get("columna") if isinstance(config, dict) else config
                    if not columna:
                        continue
                    eje_str = eje.replace("eje_", "").upper() if eje != "ninguno" else ""
                    labels[columna] = f"{tipo} {eje_str}".strip()
        return labels

    def _crear_graficas(self):
        self._limpiar_graficas()
        if self.df_grafica is None or self.columna_x not in self.df_grafica.columns:
            self._mostrar_placeholder("No hay datos disponibles para graficar.")
            return

        columnas = self._obtener_todas_columnas_mapeo() or self._obtener_columnas_a_graficar()
        if not columnas:
            self._mostrar_placeholder("No se encontraron columnas numéricas para graficar.")
            return

        self.stack.setCurrentWidget(self.scroll)
        labels = self._obtener_labels_columnas()
        x = self.df_grafica_original[self.columna_x].to_numpy(dtype=float)
        for columna in columnas:
            y_original = self.df_grafica_original[columna].to_numpy(dtype=float)
            mascara = np.isfinite(x) & np.isfinite(y_original)
            if not mascara.any():
                continue

            y_filtrada = None
            if columna in self.columnas_filtradas:
                y_filtrada = self.df_grafica[columna].to_numpy(dtype=float)

            label = labels.get(columna)
            titulo = f"{label} - {columna}" if label else str(columna)
            grafica = GraficaSenal(
                titulo,
                unidad=self.unidades.get(columna),
                etiqueta_x=str(self.columna_x),
                columna=columna,
            )
            grafica.set_datos(
                x[mascara],
                y_original[mascara],
                y_filtrada[mascara] if y_filtrada is not None else None,
            )
            grafica.set_modo_seleccion_rango(self.modo_seleccion_rango)
            grafica.rangoPropuesto.connect(self._registrar_rango)
            gestor = self.gestores_rangos.setdefault(columna, GestorRangos())
            grafica.mostrar_rangos(gestor.listar())
            self.layout_graficas.addWidget(grafica)
            self.graficas.append(grafica)
            self.graficas_por_columna[columna] = grafica

        self.layout_graficas.addStretch()

    def _actualizar_visibilidad(self):
        if not self.graficas_por_columna:
            self.senalesDisponiblesCambiaron.emit([])
            return
        columnas_activas = set(self._obtener_columnas_a_graficar())
        hay_visibles = False
        for columna, grafica in self.graficas_por_columna.items():
            visible = columna in columnas_activas
            grafica.setVisible(visible)
            hay_visibles = hay_visibles or visible
        if hay_visibles:
            self.stack.setCurrentWidget(self.scroll)
        else:
            self._mostrar_placeholder("No hay columnas activas para graficar.")
        self._emitir_senales_disponibles(columnas_activas)

    def _emitir_senales_disponibles(self, columnas_activas=None):
        if columnas_activas is None:
            columnas_activas = set(self._obtener_columnas_a_graficar())
        self.senalesDisponiblesCambiaron.emit(
            [
                {
                    "columna": columna,
                    "nombre": grafica.nombre_senal,
                    "visible": columna in columnas_activas,
                }
                for columna, grafica in self.graficas_por_columna.items()
            ]
        )

    def _actualizar_datos_graficas(self):
        if self.df_grafica is None:
            return
        x = self.df_grafica_original[self.columna_x].to_numpy(dtype=float)
        for columna, grafica in self.graficas_por_columna.items():
            y_original = self.df_grafica_original[columna].to_numpy(dtype=float)
            mascara = np.isfinite(x) & np.isfinite(y_original)
            y_filtrada = (
                self.df_grafica[columna].to_numpy(dtype=float)
                if columna in self.columnas_filtradas
                else None
            )
            grafica.set_datos(
                x[mascara],
                y_original[mascara],
                y_filtrada[mascara] if y_filtrada is not None else None,
            )
            grafica.set_modo_seleccion_rango(self.modo_seleccion_rango)
            gestor = self.gestores_rangos.setdefault(columna, GestorRangos())
            grafica.mostrar_rangos(gestor.listar())

    def _registrar_rango(self, grafica, desde, hasta):
        columna = grafica.columna
        gestor = self.gestores_rangos.setdefault(columna, GestorRangos())
        try:
            rango, fue_ajustado = gestor.agregar_ajustado(desde, hasta)
        except (RangoSuperpuestoError, ValueError) as exc:
            mensaje = f"{grafica.nombre_senal}: {exc}"
            self.rangoRechazado.emit(mensaje)
            QToolTip.showText(QCursor.pos(), mensaje, grafica)
            return

        grafica.mostrar_rangos(gestor.listar())
        self._emitir_rangos()
        if fue_ajustado:
            mensaje = (
                f"El rango se ajustó automáticamente a "
                f"{rango.desde}–{rango.hasta} para no superponerse."
            )
            self.rangoAjustado.emit(mensaje)
            QToolTip.showText(QCursor.pos(), mensaje, grafica)

    @staticmethod
    def _id_rango(columna, numero):
        return f"{columna}::{int(numero)}"

    def _rangos_para_panel(self):
        resultado = []
        for columna, grafica in self.graficas_por_columna.items():
            gestor = self.gestores_rangos.get(columna)
            if gestor is None:
                continue
            for rango in gestor.listar():
                datos = rango.como_dict()
                datos.update(
                    {
                        "id": self._id_rango(columna, rango.numero),
                        "columna": columna,
                        "senal": grafica.nombre_senal,
                        "fuente": (
                            "filtrada"
                            if columna in self.columnas_filtradas
                            else "original"
                        ),
                    }
                )
                resultado.append(datos)
        return resultado

    def _emitir_rangos(self):
        self.rangosCambiados.emit(self._rangos_para_panel())

    def eliminar_rangos(self, identificadores):
        por_columna = {}
        for identificador in identificadores or []:
            if isinstance(identificador, str) and "::" in identificador:
                columna, numero = identificador.rsplit("::", 1)
                por_columna.setdefault(columna, []).append(int(numero))
            elif len(self.gestores_rangos) == 1:
                columna = next(iter(self.gestores_rangos))
                por_columna.setdefault(columna, []).append(int(identificador))

        for columna, numeros in por_columna.items():
            gestor = self.gestores_rangos.get(columna)
            if gestor is None:
                continue
            gestor.eliminar(numeros)
            grafica = self.graficas_por_columna.get(columna)
            if grafica is not None:
                grafica.mostrar_rangos(gestor.listar())
        self._emitir_rangos()

    def limpiar_rangos(self):
        for columna, gestor in self.gestores_rangos.items():
            gestor.limpiar()
            grafica = self.graficas_por_columna.get(columna)
            if grafica is not None:
                grafica.mostrar_rangos([])
        self.rangosCambiados.emit([])

    def seleccionar_rango_manual(self, categoria, senal, desde, hasta):
        grafica = None
        if self.mapeo_actual and categoria in self.mapeo_actual:
            eje = f"eje_{senal[-1].lower()}" if senal else ""
            config = self.mapeo_actual[categoria].get(eje)
            if isinstance(config, dict):
                grafica = self.graficas_por_columna.get(config.get("columna"))
        if grafica is None and self.graficas:
            grafica = self.graficas[0]
        if grafica is not None:
            grafica.proponer_rango(desde, hasta)

    def obtener_datos_rango(self, columna, desde, hasta):
        """Devuelve los datos activos para cálculos (filtrados si están visibles)."""
        if self.df_grafica is None or columna not in self.df_grafica.columns:
            return pd.DataFrame()
        desde, hasta = sorted((int(desde), int(hasta)))
        eje_x = self.df_grafica[self.columna_x]
        mascara = eje_x.between(desde, hasta, inclusive="both")
        return self.df_grafica.loc[mascara, [self.columna_x, columna]].copy()

    def aplicar_filtro(self, configuracion):
        if self.df_grafica_original is None:
            self.filtroEstadoCambiado.emit(False, "Primero cargá un archivo CSV.")
            return

        frecuencia = float(configuracion.get("frecuencia_muestreo") or 0)
        tipo = str(configuracion.get("tipo") or "lowpass")
        frecuencias_corte = configuracion.get(
            "frecuencias_corte",
            configuracion.get("frecuencia_corte"),
        )
        orden = int(configuracion.get("orden") or 4)
        columnas_solicitadas = configuracion.get("columnas")
        if columnas_solicitadas is None:
            columnas_solicitadas = self._obtener_columnas_a_graficar()
        columnas = [
            columna
            for columna in columnas_solicitadas
            if columna in self.graficas_por_columna
            and columna in self.df_grafica_original.columns
        ]
        resultado = (
            self.df_grafica.copy()
            if self.df_grafica is not None
            else self.df_grafica_original.copy()
        )

        if not columnas:
            self.filtroEstadoCambiado.emit(False, "No hay señales seleccionadas para filtrar.")
            return

        try:
            for columna in columnas:
                resultado[columna] = aplicar_butterworth(
                    self.df_grafica_original[columna].to_numpy(dtype=float),
                    frecuencia,
                    tipo,
                    frecuencias_corte,
                    orden,
                )
        except ErrorConfiguracionFiltro as exc:
            self.filtroEstadoCambiado.emit(False, str(exc))
            return

        self.df_grafica = resultado
        self.columnas_filtradas.update(columnas)
        self._actualizar_datos_graficas()
        self._emitir_rangos()
        descripcion = self._describir_filtro(tipo, frecuencias_corte)
        cantidad = len(columnas)
        destino = "una señal" if cantidad == 1 else f"{cantidad} señales"
        self.filtroEstadoCambiado.emit(
            True,
            f"Se aplicó {descripcion} a {destino}. La curva original sigue visible.",
        )

    @staticmethod
    def _describir_filtro(tipo, frecuencias_corte):
        if tipo == "highpass":
            return f"un filtro por encima de {float(frecuencias_corte):g} Hz"
        if tipo == "bandpass":
            inferior, superior = frecuencias_corte
            return f"un filtro entre {float(inferior):g} y {float(superior):g} Hz"
        return f"un filtro por debajo de {float(frecuencias_corte):g} Hz"

    def restaurar_datos_originales(self, columnas=None):
        if self.df_grafica_original is None:
            self.filtroEstadoCambiado.emit(False, "No hay datos cargados.")
            return

        columnas_objetivo = set(columnas or self.columnas_filtradas)
        columnas_a_restaurar = columnas_objetivo & self.columnas_filtradas
        if not columnas_a_restaurar:
            self.filtroEstadoCambiado.emit(
                True,
                "Las señales seleccionadas ya muestran únicamente los datos originales.",
            )
            return

        for columna in columnas_a_restaurar:
            self.df_grafica[columna] = self.df_grafica_original[columna]
        self.columnas_filtradas.difference_update(columnas_a_restaurar)
        self._actualizar_datos_graficas()
        self._emitir_rangos()
        cantidad = len(columnas_a_restaurar)
        destino = "la señal seleccionada" if cantidad == 1 else f"{cantidad} señales"
        self.filtroEstadoCambiado.emit(True, f"Se quitó el filtro de {destino}.")

    def _limpiar_graficas(self):
        self.graficas = []
        self.graficas_por_columna = {}
        while self.layout_graficas.count():
            item = self.layout_graficas.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _mostrar_placeholder(self, texto):
        self.lbl_estado.setText(texto)
        self.stack.setCurrentWidget(self.placeholder)
