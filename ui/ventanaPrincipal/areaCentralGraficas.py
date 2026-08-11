import math
import re

import numpy as np
import pandas as pd
import pyqtgraph as pg

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame,
    QInputDialog,
    QLabel,
    QMessageBox,
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
from logica import accesibilidad, formulas, paleta
from logica.formulas import ErrorFormula
from logica.rangos import GestorRangos, RangoSuperpuestoError


# Vocabulario compartido con los rangos (ver ``_rangos_para_panel``) para decir
# sobre qué serie se trabajó.
FUENTE_ORIGINAL = "original"
FUENTE_FILTRADA = "filtrada"
# Una fórmula entre señales puede tomar unas filtradas y otras no.
FUENTE_MIXTA = "mixta"


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
    rangoDobleClick = Signal(object, int)

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
        self.etiqueta_x = etiqueta_x
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
        self.rangos_actuales = []
        self.curva_original = None
        self.curva_filtrada = None
        self.curva_formula = None
        self.x_formula = None
        self.y_formula = None
        self.picos_formula = []
        self.info_formula = None
        self.marcador_pico = None
        self.caja_valor = None
        self._vista_items = None
        self._formula_en_eje_derecho = False

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

        # ViewBox propio para la curva de fórmula: se usa solo cuando su unidad
        # no coincide con la de la señal (ej. BW sobre newtons), porque si no
        # una curva quedaría aplastada contra el piso de la otra.
        self.vb_formula = pg.ViewBox()
        self.plotItem.scene().addItem(self.vb_formula)
        self.plotItem.getAxis("right").linkToView(self.vb_formula)
        self.vb_formula.setXLink(self.plotItem.vb)
        # Sin esto la curva de fórmula se dibuja por detrás de la original.
        self.vb_formula.setZValue(self.plotItem.vb.zValue() + 1)
        self.plotItem.vb.sigResized.connect(self._sincronizar_eje_formula)
        self.plotItem.showAxis("right", False)

        self.scene().sigMouseClicked.connect(self._manejar_click)
        self.scene().sigMouseMoved.connect(self._manejar_mouse_movido)

    def _sincronizar_eje_formula(self):
        """Mantiene el ViewBox de la fórmula pegado al principal al redimensionar."""
        self.vb_formula.setGeometry(self.plotItem.vb.sceneBoundingRect())
        self.vb_formula.linkedViewChanged(self.plotItem.vb, self.vb_formula.XAxis)

    def set_datos(self, x, y_original, y_filtrada=None):
        self.x = np.asarray(x, dtype=float)
        self.y_original = np.asarray(y_original, dtype=float)
        self.y_filtrada = (
            np.asarray(y_filtrada, dtype=float)
            if y_filtrada is not None
            else None
        )
        self.y = self.y_filtrada if self.y_filtrada is not None else self.y_original
        # La curva de fórmula vive en otro ViewBox: clear() no la alcanza.
        self.limpiar_curva_formula()
        self.clear()
        self.linea_inicio = None
        self.linea_preview = None
        self.region_preview = None
        self.regiones_rangos = {}
        self.rangos_actuales = []
        self.x_inicio = None

        self.curva_original = self.plot(
            self.x,
            self.y_original,
            pen=pg.mkPen(self._pen_original()),
            name="Original",
        )
        self.curva_filtrada = None
        if self.y_filtrada is not None:
            self.curva_filtrada = self.plot(
                self.x,
                self.y_filtrada,
                pen=pg.mkPen(self._pen_filtrada()),
                name="Filtrada",
            )
            self.leyenda.show()
        else:
            self.leyenda.hide()
        self.enableAutoRange(axis="y", enable=True)
        self.autoRange()

    def _pen_original(self):
        """Lápiz de la señal original; se atenúa si hay una curva filtrada encima.

        Color, grosor y estilo salen de las paletas/opciones activas: con el
        modo accesible desactivado se obtiene exactamente el trazo actual.
        """
        color = pg.mkColor(paleta.color_senal_original())
        if self.y_filtrada is not None:
            color.setAlpha(165)
        return pg.mkPen(
            color,
            width=accesibilidad.grosor_senal(accesibilidad.TIPO_LINEA_ORIGINAL),
            style=self._estilo_linea(accesibilidad.TIPO_LINEA_ORIGINAL),
        )

    def _pen_filtrada(self):
        return pg.mkPen(
            paleta.color_senal_filtrada(),
            width=accesibilidad.grosor_senal(accesibilidad.TIPO_LINEA_FILTRADA),
            style=self._estilo_linea(accesibilidad.TIPO_LINEA_FILTRADA),
        )

    def _pen_formula(self):
        return pg.mkPen(
            paleta.color_senal_formula(),
            width=accesibilidad.grosor_senal(accesibilidad.TIPO_LINEA_FORMULA),
            style=self._estilo_linea(accesibilidad.TIPO_LINEA_FORMULA),
        )

    @staticmethod
    def _estilo_linea(tipo_linea):
        """Traduce el estilo simbólico de accesibilidad al enum de Qt."""
        estilos = {
            accesibilidad.ESTILO_SOLIDA: Qt.SolidLine,
            accesibilidad.ESTILO_DISCONTINUA: Qt.DashLine,
            accesibilidad.ESTILO_PUNTEADA: Qt.DotLine,
        }
        return estilos.get(
            accesibilidad.estilo_linea(tipo_linea), Qt.SolidLine
        )

    def aplicar_paleta(self):
        """Repinta curvas y rangos con la paleta activa, sin perder el zoom."""
        if self.curva_original is not None:
            self.curva_original.setPen(self._pen_original())
        if self.curva_filtrada is not None:
            self.curva_filtrada.setPen(self._pen_filtrada())
        if self.curva_formula is not None:
            color = paleta.color_senal_formula()
            self.curva_formula.setPen(self._pen_formula())
            if self.marcador_pico is not None:
                self.marcador_pico.setBrush(pg.mkBrush(color))
            if self.caja_valor is not None:
                self.caja_valor.border = pg.mkPen(color, width=1)
            self.plotItem.getAxis("right").setPen(pg.mkPen(color))
            self.plotItem.getAxis("right").setTextPen(pg.mkPen(color))
        if self.rangos_actuales:
            self.mostrar_rangos(self.rangos_actuales)

    def set_curva_formula(self, x, y, nombre, unidad=None, picos=None):
        """Superpone la curva calculada sobre esta señal.

        ``x`` e ``y`` pueden traer NaN intercalados para separar tramos: así
        una sola curva dibuja varios rangos sin unirlos con un trazo que no
        existe. ``picos`` lleva un punto por rango, cada uno con su resumen.
        """
        self.limpiar_curva_formula()
        if y is None or x is None:
            return

        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if len(y) != len(x) or not np.isfinite(y).any():
            return

        self.x_formula = x
        self.y_formula = y
        self.picos_formula = list(picos or [])
        self.info_formula = {"nombre": nombre, "unidad": unidad}

        color = paleta.color_senal_formula()
        unidad_formula = (unidad or "").strip()
        self._formula_en_eje_derecho = self._necesita_eje_propio(y, unidad_formula)

        etiqueta = f"{nombre} ({unidad_formula})" if unidad_formula else nombre
        self.curva_formula = pg.PlotDataItem(
            x, y, pen=self._pen_formula(), name=etiqueta, connect="finite"
        )
        # Siempre por encima de la original y de la filtrada.
        self.curva_formula.setZValue(10)

        if self._formula_en_eje_derecho:
            self.vb_formula.addItem(self.curva_formula)
            eje = self.plotItem.getAxis("right")
            eje.setLabel(etiqueta)
            eje.setPen(pg.mkPen(color))
            eje.setTextPen(pg.mkPen(color))
            eje.enableAutoSIPrefix(False)
            self.plotItem.showAxis("right", True)
            self._sincronizar_eje_formula()
            # Solo en Y: autoRange() tocaría también la X y, como este ViewBox
            # está X-linkeado al principal, arrastraría la vista de la señal al
            # tramo de los rangos y la desincronizaría de las demás gráficas.
            self.vb_formula.enableAutoRange(axis="y", enable=True)
            # La leyenda vive en el plot principal: se agrega la entrada a mano.
            self.leyenda.addItem(self.curva_formula, etiqueta)
        else:
            self.addItem(self.curva_formula)
            # Comparten eje: hay que reencuadrar en Y o la curva nueva puede
            # quedar fuera de la vista (|F| ronda los 800 N y Fx los ±100 N).
            self.enableAutoRange(axis="y", enable=True)

        self._crear_marcador_pico(color)
        self.leyenda.show()

    # Si al compartir eje una de las dos curvas ocupara menos que esta fracción
    # del alto del gráfico, se considera aplastada y va a su propio eje.
    FRACCION_MINIMA_EJE_COMPARTIDO = 0.35

    def _necesita_eje_propio(self, y, unidad_formula):
        """Decide si la curva de fórmula necesita su propio eje Y.

        Mirar solo la unidad no alcanza: |F| y Fx están los dos en newtons,
        pero van de 387 a 1145 N y de −3 a 125 N. Compartir eje deja la señal
        original (y la filtrada) aplastadas contra el piso, así que también se
        comparan las escalas.
        """
        unidad_senal = (self.unidad or "").strip()
        if unidad_formula and unidad_formula != unidad_senal:
            return True

        rango_senal = self._rango_finito(self.y_original, self.y_filtrada)
        rango_formula = self._rango_finito(y)
        if rango_senal is None or rango_formula is None:
            return False

        alto_combinado = max(rango_senal[1], rango_formula[1]) - min(
            rango_senal[0], rango_formula[0]
        )
        if alto_combinado <= 0:
            return False

        return any(
            (maximo - minimo) / alto_combinado < self.FRACCION_MINIMA_EJE_COMPARTIDO
            for minimo, maximo in (rango_senal, rango_formula)
        )

    @staticmethod
    def _rango_finito(*series):
        """(mínimo, máximo) de todas las series juntas, ignorando NaN."""
        extremos = []
        for serie in series:
            if serie is None:
                continue
            arreglo = np.asarray(serie, dtype=float)
            finitos = arreglo[np.isfinite(arreglo)]
            if finitos.size:
                extremos.append((float(finitos.min()), float(finitos.max())))
        if not extremos:
            return None
        return min(e[0] for e in extremos), max(e[1] for e in extremos)

    def _crear_marcador_pico(self, color):
        """Un punto sobre el máximo de cada rango, con su caja de valor oculta."""
        if not self.picos_formula:
            return

        # Se guarda el ViewBox usado: hay que sacarlos del mismo lugar donde se
        # pusieron, o quedan colgados en la gráfica para siempre.
        self._vista_items = self._vista_formula()

        self.marcador_pico = pg.ScatterPlotItem(
            [pico["x"] for pico in self.picos_formula],
            [pico["y"] for pico in self.picos_formula],
            size=11,
            brush=pg.mkBrush(color),
            pen=pg.mkPen("#1E1E1E", width=1.5),
            symbol="o",
        )
        self.marcador_pico.setZValue(20)
        # ignoreBounds: ni el punto ni la caja deben estirar el autorango.
        self._vista_items.addItem(self.marcador_pico, ignoreBounds=True)

        self.caja_valor = pg.TextItem(
            border=pg.mkPen(color, width=1),
            fill=pg.mkBrush(30, 30, 30, 235),
        )
        self.caja_valor.setZValue(30)
        self.caja_valor.hide()
        self._vista_items.addItem(self.caja_valor, ignoreBounds=True)

    def _vista_formula(self):
        return self.vb_formula if self._formula_en_eje_derecho else self.plotItem.vb

    def limpiar_curva_formula(self):
        """Saca la curva de fórmula y todo lo que la acompaña.

        Cada elemento se quita del mismo contenedor donde se agregó: la curva
        del plot (o del ViewBox derecho) y el punto y la caja del ViewBox que
        guardó ``_crear_marcador_pico``. Mezclarlos deja ítems colgados.
        """
        if self.curva_formula is not None:
            if self._formula_en_eje_derecho:
                self.vb_formula.removeItem(self.curva_formula)
            else:
                self.removeItem(self.curva_formula)
            self.leyenda.removeItem(self.curva_formula)

        if self._vista_items is not None:
            for item in (self.marcador_pico, self.caja_valor):
                if item is not None:
                    self._vista_items.removeItem(item)

        tenia_eje_propio = self._formula_en_eje_derecho

        self.curva_formula = None
        self.marcador_pico = None
        self.caja_valor = None
        self.x_formula = None
        self.y_formula = None
        self.picos_formula = []
        self.info_formula = None
        self._vista_items = None
        self._formula_en_eje_derecho = False
        self.plotItem.showAxis("right", False)

        # Si la curva compartía eje, el rango quedó estirado por ella: se
        # reencuadra para que la señal vuelva a ocupar toda la altura.
        if not tenia_eje_propio:
            self.enableAutoRange(axis="y", enable=True)

        if self.y_filtrada is None:
            self.leyenda.hide()

    def set_modo_seleccion_rango(self, activo):
        self.modo_seleccion_rango = activo
        self.setCursor(Qt.CrossCursor if activo else Qt.ArrowCursor)
        if not activo:
            self._cancelar_propuesta()

    # Radio en píxeles alrededor del pico / de la curva para que aparezca la caja.
    RADIO_HOVER_PICO = 16
    RADIO_HOVER_CURVA = 12

    def _manejar_mouse_movido(self, posicion):
        self._actualizar_caja_valor(posicion)

        if not self.modo_seleccion_rango or self.x_inicio is None:
            return

        view_box = self.plotItem.vb
        if not view_box.sceneBoundingRect().contains(posicion):
            return

        x_actual = self._normalizar_x_click(float(view_box.mapSceneToView(posicion).x()))
        x_inicio = min(self.x_inicio, x_actual)
        x_fin = max(self.x_inicio, x_actual)
        self._mostrar_preview(x_inicio, x_fin, x_actual)

    def _actualizar_caja_valor(self, posicion):
        """Muestra la caja de valor solo mientras el mouse está sobre la curva.

        Primero se prueba el pico (tiene un radio más generoso porque es el dato
        que más se busca) y después el resto de la curva. Al alejarse, se
        esconde.
        """
        if self.caja_valor is None or self.y_formula is None:
            return

        vista = self._vista_items or self._vista_formula()
        if not self.plotItem.vb.sceneBoundingRect().contains(posicion):
            self.caja_valor.hide()
            return

        # Primero los picos: tienen un radio más generoso porque son el dato
        # que más se busca, y cada uno trae el resumen de su rango.
        for pico in self.picos_formula:
            distancia = self._distancia_en_pixeles(
                vista, posicion, pico["x"], pico["y"]
            )
            if distancia is not None and distancia <= self.RADIO_HOVER_PICO:
                self._mostrar_caja_valor(pico["x"], pico["y"], pico, es_pico=True)
                return

        # Fuera de los picos: el punto de la curva más cercano en X.
        x_vista = float(vista.mapSceneToView(posicion).x())
        indice = self._indice_mas_cercano(x_vista)
        if indice is None:
            self.caja_valor.hide()
            return

        x_punto = float(self.x_formula[indice])
        y_punto = float(self.y_formula[indice])
        if not math.isfinite(y_punto):
            self.caja_valor.hide()
            return

        distancia = self._distancia_en_pixeles(vista, posicion, x_punto, y_punto)
        if distancia is not None and distancia <= self.RADIO_HOVER_CURVA:
            self._mostrar_caja_valor(
                x_punto, y_punto, self._pico_que_contiene(x_punto), es_pico=False
            )
        else:
            self.caja_valor.hide()

    def _pico_que_contiene(self, x):
        """El rango al que pertenece ese punto, para mostrar sus valores."""
        if not self.picos_formula:
            return None
        return min(self.picos_formula, key=lambda pico: abs(pico["x"] - x))

    def _indice_mas_cercano(self, x_vista):
        if self.x_formula is None or len(self.x_formula) == 0:
            return None
        diferencias = np.abs(self.x_formula - x_vista)
        if not np.isfinite(diferencias).any():
            return None
        return int(np.nanargmin(diferencias))

    @staticmethod
    def _distancia_en_pixeles(vista, posicion, x, y):
        """Distancia en pantalla entre el cursor y un punto en coordenadas de datos."""
        if not math.isfinite(x) or not math.isfinite(y):
            return None
        punto = vista.mapViewToScene(QPointF(x, y))
        return math.hypot(punto.x() - posicion.x(), punto.y() - posicion.y())

    def _mostrar_caja_valor(self, x, y, pico, es_pico):
        """Caja con el resumen del rango al que pertenece ese punto."""
        info = self.info_formula
        unidad = (info.get("unidad") or "").strip()
        nombre = info.get("nombre") or "Fórmula"
        if pico and pico.get("etiqueta"):
            nombre = f"{nombre} · {pico['etiqueta']}"
        datos = (pico or {}).get("resumen") or {}
        color = paleta.color_senal_formula()
        sufijo = f" {unidad}" if unidad else ""

        def fila(etiqueta, valor, destacada=False):
            if valor is None:
                return ""
            texto = f"{formulas.formatear_valor(valor)}{sufijo}"
            if destacada:
                texto = f"<b>{texto}</b>"
            return (
                f'<tr><td style="color:#B0B0B0; padding-right:8px;">{etiqueta}</td>'
                f'<td style="color:#FFFFFF;" align="right">{texto}</td></tr>'
            )

        filas = ""
        if not es_pico:
            # En un punto cualquiera de la curva, primero el valor de ahí.
            filas += fila(f"{self.etiqueta_x} {x:g}", y, destacada=True)

        pico = datos.get("pico")
        etiqueta_pico = "Pico"
        if datos.get("x_pico") is not None:
            etiqueta_pico = f"Pico ({self.etiqueta_x} {datos['x_pico']:g})"
        filas += fila(etiqueta_pico, pico, destacada=es_pico)
        filas += fila("Mínimo", datos.get("minimo"))
        filas += fila("Media", datos.get("media"))
        filas += fila("RMS", datos.get("rms"))

        self.caja_valor.setHtml(
            f'<div style="font-size:9pt;">'
            f'<div style="color:{color};"><b>{nombre}</b></div>'
            f'<table cellspacing="0">{filas}</table></div>'
        )
        self.caja_valor.setAnchor(self._anclaje_caja(y))
        self.caja_valor.setPos(x, y)
        self.caja_valor.show()

    # Anclajes de la caja: debajo del punto (preferido) y encima.
    ANCLA_DEBAJO = (0.5, -0.2)
    ANCLA_ENCIMA = (0.5, 1.2)

    def _anclaje_caja(self, y):
        """Ubica la caja del lado donde entra, prefiriendo debajo del punto.

        No alcanza con mirar si el punto está alto o bajo: la caja cambia de
        alto según cuántas estadísticas tenga, así que se compara su altura
        real contra el espacio libre a cada lado. Se llama después de
        ``setHtml`` para que ``boundingRect`` ya esté actualizado.
        """
        vista = self._vista_items or self._vista_formula()
        y_min, y_max = vista.viewRange()[1]
        if y_max <= y_min:
            return self.ANCLA_DEBAJO

        # La caja se dibuja en píxeles: hay que pasarla a unidades de dato.
        alto_pixel = vista.viewPixelSize()[1]
        alto_caja = self.caja_valor.boundingRect().height() * alto_pixel
        espacio_abajo = y - y_min
        espacio_arriba = y_max - y

        if espacio_abajo >= alto_caja:
            return self.ANCLA_DEBAJO
        if espacio_arriba >= alto_caja:
            return self.ANCLA_ENCIMA
        # No entra de ningún lado: se elige el que menos la recorta.
        return (
            self.ANCLA_DEBAJO
            if espacio_abajo >= espacio_arriba
            else self.ANCLA_ENCIMA
        )

    def _manejar_click(self, event):
        if event.button() != Qt.LeftButton:
            return

        view_box = self.plotItem.vb
        if not view_box.sceneBoundingRect().contains(event.scenePos()):
            return
        if self.x is None or len(self.x) == 0:
            return

        x_click = self._normalizar_x_click(float(view_box.mapSceneToView(event.scenePos()).x()))

        # Doble click sobre un rango existente: abre la ventana de sub-rangos.
        if event.double():
            numero = self._rango_en_x(x_click)
            if numero is not None:
                self._cancelar_propuesta()
                self.rangoDobleClick.emit(self, numero)
                event.accept()
            return

        if not self.modo_seleccion_rango:
            return

        if self.x_inicio is None:
            self.x_inicio = x_click
            self.linea_inicio = pg.InfiniteLine(
                pos=x_click,
                angle=90,
                movable=False,
                pen=pg.mkPen(paleta.color_seleccion(), width=2),
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
        color_seleccion = pg.mkColor(paleta.color_seleccion())
        if self.region_preview is None:
            brocha = pg.mkColor(color_seleccion)
            brocha.setAlpha(45)
            self.region_preview = pg.LinearRegionItem(
                values=[x_inicio, x_fin], movable=False, brush=brocha
            )
            self.region_preview.setZValue(-20)
            for linea in self.region_preview.lines:
                linea.setPen(pg.mkPen(color_seleccion, width=1))
            self.addItem(self.region_preview)
        else:
            self.region_preview.setRegion([x_inicio, x_fin])

        if self.linea_preview is None:
            self.linea_preview = pg.InfiniteLine(
                pos=x_actual,
                angle=90,
                movable=False,
                pen=pg.mkPen(color_seleccion, width=1.5, style=Qt.DashLine),
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

    def _rango_en_x(self, x_click):
        """Devuelve el número del rango cuyo intervalo contiene x, o None."""
        for rango in self.rangos_actuales:
            if rango.desde <= x_click <= rango.hasta:
                return rango.numero
        return None

    def mostrar_rangos(self, rangos):
        for region in self.regiones_rangos.values():
            self.removeItem(region)
        self.regiones_rangos = {}
        self.rangos_actuales = list(rangos)

        # Nombre del color en el tooltip del rango: solo con el modo accesible
        # activo y la opción «mostrar el nombre del color» marcada. Desactivado,
        # los rangos no llevan tooltip (igual que hoy).
        mostrar_nombre = (
            accesibilidad.activo() and accesibilidad.mostrar_nombre_color()
        )

        for rango in rangos:
            color = pg.mkColor(rango.color)
            color_brush = pg.mkColor(rango.color)
            color_brush.setAlpha(55)
            region = pg.LinearRegionItem(
                values=[rango.desde, rango.hasta], movable=False, brush=color_brush
            )
            region.setZValue(-10)
            for linea in region.lines:
                linea.setPen(
                    pg.mkPen(
                        color,
                        width=accesibilidad.grosor_rango(),
                    )
                )
            if mostrar_nombre:
                region.setToolTip(
                    f"{rango.nombre} · Color: {paleta.nombre_color(rango.color)}"
                )
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
    formulaEstadoCambiado = Signal(bool, str)
    resultadosFormulaCambiaron = Signal(object)
    # True cuando alguna señal visible tiene filtro: habilita elegir la fuente.
    fuenteDatosCambiada = Signal(bool)

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
        self.subgestores = {}
        self.notas = {}
        self._ventanas_region = []
        self.columnas_filtradas = set()
        self.aplicar_corte_todas = False
        self.superposicion_habilitada = False
        self.no_preguntar_superposicion = False
        self.formula_activa = None
        self.masa_sujeto = None
        self.gravedad = 9.8
        # Descripción legible del filtro puesto en cada columna, para poder
        # decir sobre qué datos se calculó cada resultado.
        self.filtros_por_columna = {}
        # Sobre qué serie calculan las fórmulas: "filtrada" usa la filtrada
        # cuando existe; "original" fuerza la señal cruda aunque haya filtro.
        self.fuente_calculo = FUENTE_FILTRADA
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
        self.subgestores = {}
        self.notas = {}
        self.columnas_filtradas = set()
        self.filtros_por_columna = {}
        self.formula_activa = None
        self.rangosCambiados.emit([])
        self.resultadosFormulaCambiaron.emit(None)
        self.fuenteDatosCambiada.emit(False)
        self._crear_graficas()
        self._actualizar_visibilidad()

    def actualizar_mapeo(self, mapeo):
        self.mapeo_actual = mapeo
        columnas_ordenadas = self._obtener_todas_columnas_mapeo()
        orden_actual = [grafica.columna for grafica in self.graficas]
        # Reconstruir si aparecen columnas nuevas o si cambió el orden pedido.
        if columnas_ordenadas != orden_actual:
            self._crear_graficas()
        self._actualizar_visibilidad()

    def set_frecuencia_grafica(self, frecuencia):
        """Actualiza la frecuencia efectiva elegida en el panel de filtros."""
        try:
            frecuencia = float(frecuencia)
        except (TypeError, ValueError):
            frecuencia = 0.0
        nueva_frecuencia = frecuencia if frecuencia > 0 else None
        if nueva_frecuencia == self.frecuencia_grafica:
            return
        self.frecuencia_grafica = nueva_frecuencia
        if self.formula_activa:
            self.aplicar_formula(self.formula_activa, avisar=False)

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

    def _entradas_mapeo_ordenadas(self):
        """Devuelve (columna, activo) del mapeo respetando el orden pedido.

        Cada configuración puede traer un campo ``orden`` (entero) definido por
        el usuario al arrastrar las filas en «Aplicar Mapeo». Cuando no existe,
        se conserva el orden de inserción del diccionario (comportamiento previo).
        """
        entradas = []
        indice = 0
        for ejes in self.mapeo_actual.values():
            if not isinstance(ejes, dict):
                continue
            for config in ejes.values():
                if isinstance(config, dict):
                    columna = config.get("columna")
                    activo = config.get("activo", True)
                    orden = config.get("orden")
                else:
                    columna, activo, orden = config, True, None
                clave_orden = orden if orden is not None else float("inf")
                entradas.append((clave_orden, indice, columna, activo))
                indice += 1

        entradas.sort(key=lambda entrada: (entrada[0], entrada[1]))
        return [(columna, activo) for _, _, columna, activo in entradas]

    def _obtener_todas_columnas_mapeo(self):
        columnas = []
        if self.mapeo_actual:
            for columna, _activo in self._entradas_mapeo_ordenadas():
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
        if self.mapeo_actual:
            columnas = []
            for columna, activo in self._entradas_mapeo_ordenadas():
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
            grafica.rangoDobleClick.connect(self._abrir_ventana_subrango)
            gestor = self.gestores_rangos.setdefault(columna, GestorRangos())
            grafica.mostrar_rangos(gestor.listar())

            self.layout_graficas.addWidget(grafica)
            self.graficas.append(grafica)
            self.graficas_por_columna[columna] = grafica

        self.layout_graficas.addStretch()

        # Las gráficas se rehicieron desde cero: si había una fórmula puesta,
        # se vuelve a aplicar sobre las nuevas curvas.
        if self.formula_activa:
            self.aplicar_formula(self.formula_activa, avisar=False)

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

        # set_datos() rehace las curvas, así que la fórmula se vuelve a poner
        # (y se recalcula sobre los datos filtrados, que es lo que se espera).
        if self.formula_activa:
            self.aplicar_formula(self.formula_activa, avisar=False)

    def set_aplicar_corte_todas(self, activo):
        """Define si el próximo recorte se aplica a todas las gráficas visibles."""
        self.aplicar_corte_todas = bool(activo)

    def set_superposicion_habilitada(self, activo):
        """Permite crear recortes superpuestos en lugar de ajustarlos al tramo libre."""
        self.superposicion_habilitada = bool(activo)

    def set_modo_daltonico(self, activo):
        """Compatibilidad: activa la paleta rojo-verde (modo antiguo) y repinta.

        El modo accesible nuevo ya no pasa por aquí: ``accesibilidad``
        sincroniza la paleta y luego se llama a ``aplicar_accesibilidad``.
        """
        if not paleta.set_modo_daltonico(activo):
            return
        self._repintar_accesibilidad()

    def aplicar_accesibilidad(self):
        """Repinta las gráficas con la paleta ya sincronizada por accesibilidad.

        La paleta activa ya quedó actualizada por ``logica.accesibilidad``
        cuando el usuario tocó la configuración; aquí solo se vuelve a pintar
        con los colores vigentes. El resto de las opciones de renderizado
        (grosor, estilos y tooltips) se aplican dentro de ``aplicar_paleta``.
        """
        self._repintar_accesibilidad()

    def _repintar_accesibilidad(self):
        """Reasigna los colores y repinta gráficas y ventanas de sub-rangos.

        Los colores dependen solo del número de rango, así que volver al modo
        estándar devuelve exactamente los colores anteriores.
        """
        for gestor in self.gestores_rangos.values():
            gestor.recolorear()
        for subgestor in self.subgestores.values():
            subgestor.recolorear()

        for columna, grafica in self.graficas_por_columna.items():
            gestor = self.gestores_rangos.get(columna)
            if gestor is not None:
                grafica.rangos_actuales = gestor.listar()
            grafica.aplicar_paleta()

        # Las ventanas de sub-rangos abiertas también se repintan.
        self._ventanas_region = [v for v in self._ventanas_region if v.isVisible()]
        for ventana in self._ventanas_region:
            subgestor = self.subgestores.get(getattr(ventana, "clave_subgestor", None))
            if subgestor is not None:
                ventana.mostrar_subrangos(subgestor.listar())
            ventana.aplicar_paleta()

        self._emitir_rangos()

    def set_no_preguntar_superposicion(self, activo):
        """Si está activo, no pide confirmación al crear un recorte superpuesto."""
        self.no_preguntar_superposicion = bool(activo)

    def _confirmar_superposicion(self, parent, desde, hasta):
        """Pregunta si se desea crear un recorte que se superpone a otro."""
        respuesta = QMessageBox.question(
            parent,
            "Superposición de rangos",
            f"El recorte {desde}–{hasta} se superpone con al menos un rango "
            "existente.\n\n¿Deseás crearlo igualmente?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return respuesta == QMessageBox.Yes

    def _graficas_visibles(self):
        """Devuelve [(columna, grafica)] de las señales actualmente visibles.

        Se cruza el mapeo (qué tipos de dato están activos en «Config. de
        columnas») con el estado real del widget: si el usuario dejó a la vista
        solo Fuerza, las fórmulas tienen que aplicarse solo a esas gráficas.
        Se usa ``isHidden()`` y no ``isVisible()`` porque este último da False
        para todas cuando el panel contenedor está colapsado.
        """
        activas = set(self._obtener_columnas_a_graficar())
        return [
            (columna, self.graficas_por_columna[columna])
            for columna in self._obtener_columnas_a_graficar()
            if columna in self.graficas_por_columna
            and columna in activas
            and not self.graficas_por_columna[columna].isHidden()
        ]

    def _registrar_rango(self, grafica, desde, hasta):
        if self.aplicar_corte_todas:
            self._registrar_rango_en_todas(grafica, desde, hasta)
        else:
            self._registrar_rango_individual(grafica, desde, hasta)

    def _registrar_rango_individual(self, grafica, desde, hasta):
        columna = grafica.columna
        gestor = self.gestores_rangos.setdefault(columna, GestorRangos())
        nombre, ok = QInputDialog.getText(
            grafica,
            "Nombre del rango",
            f"Nombre para el rango {desde}–{hasta} (opcional):",
        )
        if not ok:
            return
        nombre = nombre.strip()
        if nombre:
            existentes = [r.nombre for r in gestor.listar() if r.nombre]
            if nombre in existentes:
                QMessageBox.warning(
                    grafica,
                    "Nombre repetido",
                    f"Ya existe un rango con el nombre «{nombre}».",
                )
                return

        # Modo con superposición habilitada: se crea el recorte tal cual, pidiendo
        # confirmación si pisa a otro (salvo que se haya desactivado el aviso).
        if self.superposicion_habilitada:
            if gestor.hay_superposicion(desde, hasta):
                if not self.no_preguntar_superposicion and not self._confirmar_superposicion(
                    grafica, desde, hasta
                ):
                    return
            try:
                gestor.agregar(desde, hasta, nombre, permitir_superposicion=True)
            except ValueError as exc:
                mensaje = f"{grafica.nombre_senal}: {exc}"
                self.rangoRechazado.emit(mensaje)
                QToolTip.showText(QCursor.pos(), mensaje, grafica)
                return
            grafica.mostrar_rangos(gestor.listar())
            self._emitir_rangos()
            return

        # Modo por defecto: el recorte se corre automáticamente al tramo libre.
        try:
            rango, fue_ajustado = gestor.agregar_ajustado(desde, hasta, nombre)
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

    def _registrar_rango_en_todas(self, grafica_origen, desde, hasta):
        """Aplica el mismo recorte a todas las señales visibles.

        Pide el nombre una sola vez y lo agrega al gestor de cada gráfica
        visible. Cada señal se maneja de forma independiente: si en alguna se
        superpone o el nombre ya existe, se omite esa señal y se continúa con el
        resto. Todos los recortes creados aparecen en el recuadro y en el
        selector de señales del panel.
        """
        objetivos = self._graficas_visibles()
        if not objetivos:
            return

        nombre, ok = QInputDialog.getText(
            grafica_origen,
            "Nombre del rango",
            f"Nombre para el rango {desde}–{hasta} en todas las señales "
            "visibles (opcional):",
        )
        if not ok:
            return
        nombre = nombre.strip()

        # Modo con superposición habilitada: se pregunta una sola vez si alguna
        # señal visible se superpone, y luego se crea el recorte tal cual en todas.
        if self.superposicion_habilitada:
            alguna_solapa = any(
                self.gestores_rangos.setdefault(columna, GestorRangos()).hay_superposicion(
                    desde, hasta
                )
                for columna, _ in objetivos
            )
            if alguna_solapa and not self.no_preguntar_superposicion:
                if not self._confirmar_superposicion(grafica_origen, desde, hasta):
                    return

            agregados = 0
            omitidos = []
            for columna, grafica in objetivos:
                gestor = self.gestores_rangos.setdefault(columna, GestorRangos())
                if nombre and nombre in [r.nombre for r in gestor.listar() if r.nombre]:
                    omitidos.append(grafica.nombre_senal)
                    continue
                try:
                    gestor.agregar(desde, hasta, nombre, permitir_superposicion=True)
                except ValueError:
                    omitidos.append(grafica.nombre_senal)
                    continue
                grafica.mostrar_rangos(gestor.listar())
                agregados += 1

            if agregados:
                self._emitir_rangos()

            partes = []
            if agregados:
                partes.append(f"Recorte agregado a {agregados} señal(es) visible(s).")
            if omitidos:
                partes.append(f"No se pudo agregar en: {', '.join(omitidos)}.")
            if partes:
                mensaje = " ".join(partes)
                (self.rangoAjustado if agregados else self.rangoRechazado).emit(mensaje)
                QToolTip.showText(QCursor.pos(), mensaje, grafica_origen)
            return

        # Modo por defecto: cada recorte se corre automáticamente al tramo libre.
        agregados = 0
        ajustados = 0
        omitidos = []
        for columna, grafica in objetivos:
            gestor = self.gestores_rangos.setdefault(columna, GestorRangos())
            if nombre:
                existentes = [r.nombre for r in gestor.listar() if r.nombre]
                if nombre in existentes:
                    omitidos.append(grafica.nombre_senal)
                    continue
            try:
                _rango, fue_ajustado = gestor.agregar_ajustado(desde, hasta, nombre)
            except (RangoSuperpuestoError, ValueError):
                omitidos.append(grafica.nombre_senal)
                continue
            grafica.mostrar_rangos(gestor.listar())
            agregados += 1
            if fue_ajustado:
                ajustados += 1

        if agregados:
            self._emitir_rangos()

        partes = []
        if agregados:
            partes.append(f"Recorte agregado a {agregados} señal(es) visible(s).")
        if ajustados:
            partes.append(f"{ajustados} se ajustaron para no superponerse.")
        if omitidos:
            partes.append(f"No se pudo agregar en: {', '.join(omitidos)}.")

        if partes:
            mensaje = " ".join(partes)
            if agregados:
                self.rangoAjustado.emit(mensaje)
            else:
                self.rangoRechazado.emit(mensaje)
            QToolTip.showText(QCursor.pos(), mensaje, grafica_origen)

    @staticmethod
    def _id_rango(columna, numero):
        return f"{columna}::{int(numero)}"

    @staticmethod
    def _id_subrango(columna, numero_padre, numero_sub):
        return f"{columna}::{int(numero_padre)}::sub::{int(numero_sub)}"

    def _abrir_ventana_subrango(self, grafica, numero):
        """Abre una ventana con el recorte del rango para crear sub-rangos."""
        columna = grafica.columna
        gestor = self.gestores_rangos.get(columna)
        if gestor is None or self.df_grafica_original is None:
            return
        rango = next((r for r in gestor.listar() if r.numero == numero), None)
        if rango is None:
            return

        x = self.df_grafica_original[self.columna_x].to_numpy(dtype=float)
        y_original = self.df_grafica_original[columna].to_numpy(dtype=float)
        mascara = (
            (x >= rango.desde)
            & (x <= rango.hasta)
            & np.isfinite(x)
            & np.isfinite(y_original)
        )
        if not mascara.any():
            return

        y_filtrada = None
        if columna in self.columnas_filtradas:
            y_filtrada = self.df_grafica[columna].to_numpy(dtype=float)[mascara]

        from ui.ventanaRegion.ventanaRegion import VentanaRegion

        titulo = f"{grafica.nombre_senal} · {rango.nombre} ({rango.desde}–{rango.hasta})"
        ventana = VentanaRegion(
            self.window(),
            titulo=titulo,
            etiqueta_x=str(self.columna_x),
            unidad=self.unidades.get(columna),
            x=x[mascara],
            y_original=y_original[mascara],
            y_filtrada=y_filtrada,
            columna=columna,
        )
        subgestor = self.subgestores.setdefault((columna, numero), GestorRangos("Sub-rango"))
        # Deja rastro del subgestor para poder repintarla si cambia la paleta.
        ventana.clave_subgestor = (columna, numero)
        ventana.mostrar_subrangos(subgestor.listar())
        ventana.subRangoPropuesto.connect(
            lambda desde, hasta, c=columna, n=numero, v=ventana: self._registrar_subrango(
                c, n, desde, hasta, v
            )
        )
        # La sección de fórmulas de la ventana comparte el mismo panel que el
        # principal: el cálculo de sub-rangos corre con el mismo motor
        # ``_calcular_por_intervalos`` y los resultados vuelven a esa ventana.
        ventana.panel_calculo.calcularSolicitado.connect(
            lambda v=ventana: self._calcular_subrangos(v)
        )
        ventana.panel_calculo.quitarFormulaSolicitado.connect(
            lambda v=ventana: self._quitar_formula_subrangos(v)
        )
        ventana.panel_calculo.fuenteCalculoCambiada.connect(self.set_fuente_calculo)
        ventana.panel_calculo.set_fuente(self.fuente_calculo)
        # Guardar referencia para que la ventana no se destruya y limpiar cerradas.
        self._ventanas_region = [v for v in self._ventanas_region if v.isVisible()]
        self._ventanas_region.append(ventana)
        ventana.show()

    def _calcular_subrangos(self, ventana):
        """Calcula la fórmula elegida sobre los sub-rangos del rango abierto.

        Usa el mismo ``_calcular_por_intervalos`` que los rangos del panel
        principal; la única diferencia es el destino: la curva va en la gráfica
        de esta ventana y los resultados en su panel de fórmulas.
        """
        if self.df_grafica_original is None:
            ventana.panel_calculo.actualizar_estado(
                False, "Primero cargá un archivo CSV."
            )
            return

        clave = ventana.formula_seleccionada() or formulas.formula_predeterminada()
        if not formulas.hay_formula(clave):
            ventana.panel_calculo.actualizar_estado(
                False, f"Fórmula «{clave}» desconocida."
            )
            return
        desc = formulas.descripcion_formula(clave)

        columna, numero_padre = ventana.clave_subgestor
        padre_id = self._id_rango(columna, numero_padre)
        intervalos = [
            rango
            for rango in self._rangos_para_panel()
            if rango.get("padre") == padre_id
        ]
        if not intervalos:
            ventana.panel_calculo.actualizar_estado(
                False,
                "Creá al menos un sub-rango para poder calcular "
                f"{formulas.nombre_con_articulo(desc)}.",
            )
            return

        try:
            columna_origen, resultados, tramos, advertencias, _ = (
                self._calcular_por_intervalos(clave, intervalos)
            )
        except ErrorFormula as exc:
            ventana.panel_calculo.actualizar_estado(False, str(exc))
            return

        if not resultados:
            ventana.panel_calculo.actualizar_estado(
                False, "Los sub-rangos no tienen datos válidos para calcular "
                f"{formulas.nombre_con_articulo(desc)}."
            )
            return

        ventana.grafica.set_curva_formula(
            tramos["x"], tramos["y"], desc["nombre"],
            desc["unidad"], picos=tramos["picos"],
        )
        fuente, detalle = self._procedencia([columna_origen])
        grafica_origen = self.graficas_por_columna.get(columna_origen)
        ventana.mostrar_resultados_formula(
            {
                "clave": clave,
                "nombre": desc["nombre"],
                "expresion": desc["expresion"],
                "unidad": desc["unidad"],
                "senal": (
                    grafica_origen.nombre_senal if grafica_origen else columna_origen
                ),
                "fuente": fuente,
                "detalle_filtro": detalle,
                "resultados": resultados,
                "advertencias": advertencias,
            }
        )
        cantidad = len(resultados)
        destino = "un sub-rango" if cantidad == 1 else f"{cantidad} sub-rangos"
        ventana.panel_calculo.actualizar_estado(
            True,
                f"Se calculó {formulas.nombre_con_articulo(desc)} en {destino}.",
        )

    def _quitar_formula_subrangos(self, ventana):
        """Saca la curva de la ventana de sub-rangos y limpia sus resultados."""
        ventana.grafica.limpiar_curva_formula()
        ventana.panel_calculo.limpiar_resultados()

    def _registrar_subrango(self, columna, numero_padre, desde, hasta, ventana):
        """Agrega un sub-rango respetando la configuración de superposición."""
        subgestor = self.subgestores.setdefault((columna, numero_padre), GestorRangos("Sub-rango"))

        if self.superposicion_habilitada:
            if subgestor.hay_superposicion(desde, hasta):
                if not self.no_preguntar_superposicion and not self._confirmar_superposicion(
                    ventana, desde, hasta
                ):
                    return
            try:
                subgestor.agregar(desde, hasta, "", permitir_superposicion=True)
            except ValueError as exc:
                self.rangoRechazado.emit(str(exc))
                QToolTip.showText(QCursor.pos(), str(exc), ventana)
                return
        else:
            try:
                _sub, fue_ajustado = subgestor.agregar_ajustado(desde, hasta, "")
            except (RangoSuperpuestoError, ValueError) as exc:
                self.rangoRechazado.emit(str(exc))
                QToolTip.showText(QCursor.pos(), str(exc), ventana)
                return
            if fue_ajustado:
                mensaje = "El sub-rango se ajustó automáticamente a un tramo libre."
                self.rangoAjustado.emit(mensaje)
                QToolTip.showText(QCursor.pos(), mensaje, ventana)

        ventana.mostrar_subrangos(subgestor.listar())
        self._emitir_rangos()

    def _rangos_para_panel(self):
        resultado = []
        for columna, grafica in self.graficas_por_columna.items():
            gestor = self.gestores_rangos.get(columna)
            if gestor is None:
                continue
            fuente = "filtrada" if columna in self.columnas_filtradas else "original"
            for rango in gestor.listar():
                padre_id = self._id_rango(columna, rango.numero)
                datos = rango.como_dict()
                datos.update(
                    {
                        "id": padre_id,
                        "columna": columna,
                        "senal": grafica.nombre_senal,
                        "fuente": fuente,
                        "es_subrango": False,
                        "padre": None,
                        "nota": self.notas.get(padre_id, ""),
                    }
                )
                resultado.append(datos)

                # Sub-rangos de este rango, inmediatamente debajo.
                subgestor = self.subgestores.get((columna, rango.numero))
                if subgestor is None:
                    continue
                for sub in subgestor.listar():
                    sub_datos = sub.como_dict()
                    sub_id = self._id_subrango(columna, rango.numero, sub.numero)
                    sub_datos.update(
                        {
                            "id": sub_id,
                            "columna": columna,
                            "senal": grafica.nombre_senal,
                            "fuente": fuente,
                            "es_subrango": True,
                            "padre": padre_id,
                            "nota": self.notas.get(sub_id, ""),
                        }
                    )
                    resultado.append(sub_datos)
        return resultado

    def set_nota(self, identificador, texto):
        """Guarda (o borra) la nota asociada a un rango o sub-rango."""
        texto = (texto or "").strip()
        if texto:
            self.notas[identificador] = texto
        else:
            self.notas.pop(identificador, None)
        self._emitir_rangos()

    def exportar_anotaciones(self):
        """Devuelve las filas de rangos, sub-rangos y notas para guardar."""
        filas = []
        for rango in self._rangos_para_panel():
            filas.append(
                {
                    "tipo": "subrango" if rango["es_subrango"] else "rango",
                    "senal": rango["senal"],
                    "columna": rango["columna"],
                    "numero": rango["numero"],
                    "padre": rango["padre"] or "",
                    "desde": rango["desde"],
                    "hasta": rango["hasta"],
                    # Los nombres automáticos se recalculan según la posición
                    # horizontal. Se guarda vacío para no convertirlos en un
                    # nombre personalizado al volver a abrir el proyecto.
                    "nombre": (
                        rango["nombre"] if rango.get("nombre_personalizado") else ""
                    ),
                    "nota": rango.get("nota", ""),
                    "fuente": rango.get("fuente", ""),
                }
            )
        return filas

    def importar_anotaciones(self, filas):
        """Restaura rangos, sub-rangos y notas de un proyecto guardado.

        Reemplaza lo que hubiera cargado. Las filas cuya columna no está
        graficada en el archivo actual se descartan; devuelve
        ``(restaurados, descartados)`` para poder avisarle al usuario.
        """
        self.gestores_rangos = {}
        self.subgestores = {}
        self.notas = {}

        restaurados = 0
        descartados = 0

        # Primero los rangos padre: un sub-rango sin su padre no tiene sentido.
        for fila in sorted(filas or [], key=lambda f: f["tipo"] != "rango"):
            columna = fila["columna"]
            if columna not in self.graficas_por_columna:
                descartados += 1
                continue

            try:
                if fila["tipo"] == "rango":
                    gestor = self.gestores_rangos.setdefault(columna, GestorRangos())
                    gestor.restaurar(
                        fila["numero"], fila["desde"], fila["hasta"], fila["nombre"]
                    )
                    identificador = self._id_rango(columna, fila["numero"])
                else:
                    numero_padre = self._numero_padre(fila["padre"])
                    if numero_padre is None:
                        descartados += 1
                        continue
                    gestor_padre = self.gestores_rangos.get(columna)
                    if gestor_padre is None or not any(
                        rango.numero == numero_padre for rango in gestor_padre.listar()
                    ):
                        descartados += 1
                        continue
                    subgestor = self.subgestores.setdefault(
                        (columna, numero_padre), GestorRangos("Sub-rango")
                    )
                    subgestor.restaurar(
                        fila["numero"], fila["desde"], fila["hasta"], fila["nombre"]
                    )
                    identificador = self._id_subrango(
                        columna, numero_padre, fila["numero"]
                    )
            except ValueError:
                descartados += 1
                continue

            if fila.get("nota"):
                self.notas[identificador] = fila["nota"]
            restaurados += 1

        for columna, gestor in self.gestores_rangos.items():
            grafica = self.graficas_por_columna.get(columna)
            if grafica is not None:
                grafica.mostrar_rangos(gestor.listar())

        self._emitir_rangos()
        return restaurados, descartados

    @staticmethod
    def _numero_padre(padre):
        """Extrae el número de rango padre del identificador ``columna::numero``."""
        if not padre or "::" not in str(padre):
            return None
        try:
            return int(str(padre).rsplit("::", 1)[1])
        except ValueError:
            return None

    def _emitir_rangos(self):
        self.rangosCambiados.emit(self._rangos_para_panel())

    def eliminar_rangos(self, identificadores):
        por_columna = {}
        subs_por_clave = {}
        for identificador in identificadores or []:
            if isinstance(identificador, str) and "::sub::" in identificador:
                base, num_sub = identificador.rsplit("::sub::", 1)
                columna, num_padre = base.rsplit("::", 1)
                subs_por_clave.setdefault((columna, int(num_padre)), []).append(int(num_sub))
            elif isinstance(identificador, str) and "::" in identificador:
                columna, numero = identificador.rsplit("::", 1)
                por_columna.setdefault(columna, []).append(int(numero))
            elif len(self.gestores_rangos) == 1:
                columna = next(iter(self.gestores_rangos))
                por_columna.setdefault(columna, []).append(int(identificador))

        # Eliminar sub-rangos indicados.
        for (columna, num_padre), numeros in subs_por_clave.items():
            subgestor = self.subgestores.get((columna, num_padre))
            if subgestor is not None:
                subgestor.eliminar(numeros)
            for num_sub in numeros:
                self.notas.pop(self._id_subrango(columna, num_padre, num_sub), None)

        # Eliminar rangos (y arrastrar sus sub-rangos y notas).
        for columna, numeros in por_columna.items():
            gestor = self.gestores_rangos.get(columna)
            if gestor is None:
                continue
            gestor.eliminar(numeros)
            for numero in numeros:
                subgestor = self.subgestores.pop((columna, numero), None)
                if subgestor is not None:
                    for sub in subgestor.listar():
                        self.notas.pop(self._id_subrango(columna, numero, sub.numero), None)
                self.notas.pop(self._id_rango(columna, numero), None)
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
        self.subgestores = {}
        self.notas = {}
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

    def set_variables_sujeto(self, variables):
        """Recibe masa y gravedad del panel izquierdo para las fórmulas."""
        variables = variables or {}
        self.masa_sujeto = variables.get("masa")
        self.gravedad = variables.get("gravedad") or self.gravedad
        # Si hay una fórmula que depende de la masa, se recalcula sola.
        if self.formula_activa:
            self.aplicar_formula(self.formula_activa, avisar=False)

    def _fuente_de_columna(self, columna):
        """Sobre qué serie se calcula esta columna, de verdad.

        Es lo aplicado, no lo pedido: si se eligió «filtrada» pero la señal no
        tiene filtro puesto, la respuesta sigue siendo «original».
        """
        usa_filtrada = (
            self.fuente_calculo == FUENTE_FILTRADA
            and columna in self.columnas_filtradas
            and self.df_grafica is not None
        )
        return FUENTE_FILTRADA if usa_filtrada else FUENTE_ORIGINAL

    def _datos_columna(self, columna):
        """Datos de una columna según la fuente de cálculo elegida."""
        origen = (
            self.df_grafica
            if self._fuente_de_columna(columna) == FUENTE_FILTRADA
            else self.df_grafica_original
        )
        if origen is None or columna not in origen.columns:
            return None
        return origen[columna].to_numpy(dtype=float)

    def hay_filtro_en_visibles(self):
        """Indica si alguna señal visible tiene filtro puesto."""
        return any(
            columna in self.columnas_filtradas
            for columna, _grafica in self._graficas_visibles()
        )

    def set_fuente_calculo(self, valor):
        """Elige si las fórmulas trabajan sobre la señal filtrada o la original."""
        valor = FUENTE_ORIGINAL if valor == FUENTE_ORIGINAL else FUENTE_FILTRADA
        if valor == self.fuente_calculo:
            return
        self.fuente_calculo = valor
        if self.formula_activa:
            self.aplicar_formula(self.formula_activa, avisar=False)

    def _rangos_seleccionados(self, identificadores):
        """Convierte los IDs marcados en el panel en intervalos de frames.

        Se aceptan rangos de cualquier señal visible: todos comparten el eje de
        frames, que es lo único que hace falta para recortar la fórmula. Los
        sub-rangos quedan fuera: se calculan en la ventana que se abre con doble
        clic sobre su rango.
        """
        intervalos = []
        for identificador in identificadores or []:
            datos = self._buscar_rango(identificador)
            if datos is None or datos.get("es_subrango"):
                continue
            grafica = self.graficas_por_columna.get(datos["columna"])
            if grafica is None or grafica.isHidden():
                continue
            intervalos.append(datos)

        # Sin duplicados: dos señales pueden tener el mismo tramo marcado y la
        # fórmula se calcularía dos veces exactamente igual.
        vistos = set()
        unicos = []
        for datos in sorted(intervalos, key=lambda d: (d["desde"], d["hasta"])):
            clave = (datos["desde"], datos["hasta"])
            if clave not in vistos:
                vistos.add(clave)
                unicos.append(datos)
        return unicos

    def _buscar_rango(self, identificador):
        """Datos de un rango o sub-rango a partir de su identificador."""
        for rango in self._rangos_para_panel():
            if rango["id"] == identificador:
                return rango
        return None

    def _columna_vertical(self):
        """Columna mapeada como Fuerza Z, que es sobre la que se calcula."""
        entradas = (self.mapeo_actual or {}).get("Fuerza")
        if isinstance(entradas, dict):
            config = entradas.get("eje_z")
            columna = config.get("columna") if isinstance(config, dict) else config
            if columna in self.graficas_por_columna:
                return columna
        return None

    def _columna_de_rol(self, rol):
        """Columna que aporta un rol de señal, según el mapeo de columnas.

        El rol (Fz, Fx, Mz, Cx, ...) se traduce a ``(tipo, eje)`` con la tabla
        normativa ``logica.formulas.ROLES`` y se busca en ``mapeo_actual``.
        Así cualquier señal del mapeo es usable sin casos por nombre.
        """
        pareja = formulas.ROLES.get(rol)
        if pareja is None:
            return None
        tipo, eje = pareja
        entradas = (self.mapeo_actual or {}).get(tipo)
        if not isinstance(entradas, dict):
            return None
        config = entradas.get(eje)
        columna = config.get("columna") if isinstance(config, dict) else config
        if columna in self.graficas_por_columna:
            return columna
        return None

    def _roles_disponibles(self):
        """Roles de señal resolubles con los datos cargados (los 9)."""
        return {
            rol for rol in formulas.ROLES if self._columna_de_rol(rol) is not None
        }

    def aplicar_formula(self, configuracion=None, avisar=True):
        """Calcula una fórmula sobre cada rango seleccionado.

        Cada resultado se dibuja **únicamente en la gráfica que posee el rango**
        que lo originó: se agrupan por columna propietaria y cada gráfica recibe
        solo su tramo de curva y sus picos. El motor (``_calcular_por_intervalos``)
        es compartido con los sub-rangos y lo alimenta el registro ``FORMULAS``,
        así cualquier fórmula existe una sola vez en ambos lugares.
        """
        if self.df_grafica_original is None:
            self.formulaEstadoCambiado.emit(False, "Primero cargá un archivo CSV.")
            return

        configuracion = dict(configuracion or {})
        seleccionados = configuracion.get("rangos") or []
        clave = configuracion.get("clave") or formulas.formula_predeterminada()
        if not formulas.hay_formula(clave):
            self.formulaEstadoCambiado.emit(False, f"Fórmula «{clave}» desconocida.")
            return
        desc = formulas.descripcion_formula(clave)

        rangos = self._rangos_seleccionados(seleccionados)
        if not rangos:
            self.formulaEstadoCambiado.emit(
                False,
                "Marcá al menos un rango en una gráfica visible para calcular "
                f"{formulas.nombre_con_articulo(desc)}.",
            )
            return

        try:
            columna, resultados, tramos, advertencias, segmentos = (
                self._calcular_por_intervalos(clave, rangos)
            )
        except ErrorFormula as exc:
            self.formulaEstadoCambiado.emit(False, str(exc))
            return

        if not resultados:
            self.formulaEstadoCambiado.emit(
                False,
                "Los rangos marcados no tienen datos válidos para calcular "
                f"{formulas.nombre_con_articulo(desc)}.",
            )
            return

        self.formula_activa = configuracion

        # Cada resultado se dibuja únicamente en la gráfica que posee su rango.
        # El ``id`` de cada resultado mapea al rango que lo originó y ese rango
        # conoce su ``columna``: se agrupan los segmentos REALES de cada tramo
        # (no se re-filtra la curva combinada por frames, que mezclaría puntos
        # de otros rangos solapados) y cada gráfica dibuja solo los suyos.
        columna_por_id = {rango.get("id"): rango.get("columna") for rango in rangos}
        por_grafica = {}
        for res, seg in zip(resultados, segmentos):
            propietario = columna_por_id.get(res.get("id"))
            grupo = por_grafica.setdefault(
                propietario, {"resultados": [], "segmentos": []}
            )
            grupo["resultados"].append(res)
            grupo["segmentos"].append(seg)

        # Se limpian todas las curvas y se redibuja el tramo de cada gráfica
        # que posea al menos un rango seleccionado.
        for grafica in self.graficas_por_columna.values():
            grafica.limpiar_curva_formula()
        for columna_owner, grupo in por_grafica.items():
            grafica = self.graficas_por_columna.get(columna_owner)
            if grafica is None or grafica.isHidden():
                # Se calcula igual (no bloquea): solo no se dibuja.
                continue
            curva_owner = formulas.concatenar_curva(grupo["segmentos"])
            grafica.set_curva_formula(
                curva_owner["x"], curva_owner["y"], desc["nombre"],
                desc["unidad"], picos=formulas.picos_de_resultados(grupo["resultados"]),
            )

        fuentes = [rango["columna"] for rango in rangos]
        fuente, detalle = self._procedencia(fuentes)
        self.resultadosFormulaCambiaron.emit(
            {
                "clave": clave,
                "nombre": desc["nombre"],
                "expresion": desc["expresion"],
                "unidad": desc["unidad"],
                # Los resultados pertenecen a varias señales: sin senal única.
                "senal": "",
                "fuente": fuente,
                "detalle_filtro": detalle,
                "resultados": resultados,
                "advertencias": advertencias,
            }
        )
        if avisar:
            cantidad = len(resultados)
            destino = "un rango" if cantidad == 1 else f"{cantidad} rangos"
            self.formulaEstadoCambiado.emit(
                True,
                f"Se calculó {formulas.nombre_con_articulo(desc)} en {destino}.",
            )

    def _calcular_por_intervalos(self, clave, intervalos):
        """Motor compartido: resuelve roles, valida y aplica la fórmula.

        Lo usan tanto los rangos (ventana principal) como los sub-rangos
        (ventana de detalle). Dentro de ``logica.formulas`` viven:
        - ``resolver_roles``: elige los roles (obligatorios + opcionales) y
          produce las advertencias no bloqueantes.
        - ``validar_formula``: errores bloqueantes (roles/variables que faltan).
        - ``computar_formula``: recorte por intervalo, cálculo y resumen.

        Devuelve ``(columna_salida, resultados, curva, advertencias,
        segmentos)``. ``segmentos`` son los ``(x, y)`` reales de cada intervalo
        (alineados con ``resultados``), para que el panel de rangos dibuje cada
        gráfica solo con sus propios tramos.
        """
        desc = formulas.descripcion_formula(clave)

        # Restricción declarada por la propia fórmula (``rangos_en_rol``): los
        # rangos deben pertenecer a una señal concreta (p. ej. Potencia -> Fz).
        # No es una regla general: solo aplica a la fórmula que la declara.
        restriccion = desc.get("rangos_en_rol")
        if restriccion:
            columna_permitida = self._columna_de_rol(restriccion.get("rol"))
            mensaje = restriccion.get("mensaje")
            for intervalo in intervalos or []:
                if (
                    columna_permitida is None
                    or intervalo.get("columna") != columna_permitida
                ):
                    raise ErrorFormula(mensaje)

        disponibles = self._roles_disponibles()
        roles_a_usar, eleccion, advertencias = formulas.resolver_roles(
            clave, disponibles
        )
        if not roles_a_usar:
            raise ErrorFormula(
                f"No hay señales disponibles para calcular "
                f"{formulas.nombre_con_articulo(desc)}."
            )

        contexto = {
            "masa": self.masa_sujeto,
            "gravedad": self.gravedad,
            "frecuencia": self.frecuencia_grafica,
        }
        motivo = formulas.validar_formula(clave, contexto, disponibles)
        if motivo:
            raise ErrorFormula(motivo)

        roles = {}
        x_total = self.df_grafica_original[self.columna_x].to_numpy(dtype=float)
        for rol in roles_a_usar:
            columna = self._columna_de_rol(rol)
            if columna is None:
                raise ErrorFormula(f"No se pudo resolver la señal {rol}.")
            datos = self._datos_columna(columna)
            if datos is None:
                raise ErrorFormula(f"No se pudo leer la señal {rol}.")
            roles[rol] = datos

        resultados, segmentos = formulas.computar_formula(
            clave, roles, x_total, contexto, intervalos, eleccion
        )
        curva = formulas.concatenar_curva(segmentos)
        curva["picos"] = formulas.picos_de_resultados(resultados)

        # Rol de salida: el declarado si está en uso, si no el primero usado.
        salida = desc.get("salida_rol")
        if salida not in roles and roles_a_usar:
            salida = roles_a_usar[0]
        columna_salida = self._columna_de_rol(salida) if salida else None
        return columna_salida, resultados, curva, advertencias, segmentos

    def _procedencia(self, columnas_origen):
        """(fuente, detalle) de los datos que entraron en el cálculo."""
        fuentes = [self._fuente_de_columna(columna) for columna in columnas_origen]
        if not fuentes:
            return FUENTE_ORIGINAL, ""

        if all(fuente == FUENTE_FILTRADA for fuente in fuentes):
            detalles = {
                self.filtros_por_columna.get(columna, "")
                for columna in columnas_origen
            }
            detalle = detalles.pop() if len(detalles) == 1 else "filtros distintos"
            return FUENTE_FILTRADA, detalle
        if all(fuente == FUENTE_ORIGINAL for fuente in fuentes):
            return FUENTE_ORIGINAL, ""
        return FUENTE_MIXTA, "algunas señales filtradas y otras no"

    def potencia_disponible(self):
        """Si están los datos mínimos para poder calcular potencia."""
        return bool(
            self.masa_sujeto and self.frecuencia_grafica and self._columna_vertical()
        )

    def quitar_formula(self):
        """Saca la curva de la fórmula de todas las gráficas."""
        self.formula_activa = None
        for grafica in self.graficas_por_columna.values():
            grafica.limpiar_curva_formula()
        self.resultadosFormulaCambiaron.emit(None)
        self.formulaEstadoCambiado.emit(True, "Se quitó la curva de la fórmula.")


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
        descripcion = self._describir_filtro(tipo, frecuencias_corte)
        # Se recuerda por columna: se pueden filtrar señales distintas con
        # cortes distintos, y cada resultado tiene que poder decir cuál usó.
        for columna in columnas:
            self.filtros_por_columna[columna] = descripcion
        self._actualizar_datos_graficas()
        self._emitir_rangos()
        self.fuenteDatosCambiada.emit(self.hay_filtro_en_visibles())
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
            self.filtros_por_columna.pop(columna, None)
        self.columnas_filtradas.difference_update(columnas_a_restaurar)
        self._actualizar_datos_graficas()
        self._emitir_rangos()
        self.fuenteDatosCambiada.emit(self.hay_filtro_en_visibles())
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
