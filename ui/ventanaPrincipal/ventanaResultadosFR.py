"""Ventana independiente para mostrar resultados de Fuerza Resultante.

Recibe directamente los resultados y las muestras calculadas por el área
central: dibuja la curva real de FR (una por intervalo temporal completo) en su
propia gráfica y ofrece lectura por cursor (frame y valor) reutilizando el
mecanismo de cajas de ``GraficaSenal``.
"""
from __future__ import annotations

import pyqtgraph as pg

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from logica import paleta
from logica.formulas import concatenar_curva, picos_de_resultados
from ui.ventanaPrincipal.panelDerecho.panelCalculo import PanelCalculo


class VentanaResultadosFR(QDialog):
    def __init__(
        self,
        parent=None,
        titulo="Fuerza resultante",
        resultados_panel=None,
        segmentos=None,
        unidad="N",
        nombre_senal="Fuerza resultante",
    ):
        super().__init__(parent)
        self.setWindowTitle(titulo or "Fuerza resultante")
        self.setModal(False)
        self.resize(1100, 560)
        self.setStyleSheet("QDialog { background-color: #1E1E1E; }")
        self.resultados_panel = dict(resultados_panel or {})
        self.segmentos = list(segmentos or [])
        self.unidad = unidad or "N"
        self.nombre_senal = nombre_senal or "Fuerza resultante"
        self.grafica = None
        self._init_ui()

    def _init_ui(self):
        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(12, 12, 12, 12)
        layout_principal.setSpacing(8)

        encabezado = QLabel("Fuerza resultante - Resultados por intervalo temporal")
        encabezado.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #FFFFFF;"
        )
        encabezado.setWordWrap(True)
        layout_principal.addWidget(encabezado)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._crear_panel_grafica())
        splitter.addWidget(self._crear_panel_resultados())
        splitter.setSizes([720, 340])
        splitter.setCollapsible(0, False)
        layout_principal.addWidget(splitter, 1)

        self.setLayout(layout_principal)

    def _crear_panel_grafica(self):
        contenedor = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        from ui.ventanaPrincipal.areaCentralGraficas import GraficaSenal

        grafica = GraficaSenal(
            self.nombre_senal,
            unidad=self.unidad,
            etiqueta_x="Frame",
            columna="FR",
        )
        self.grafica = grafica
        self._dibujar_segmentos(grafica)
        layout.addWidget(grafica, 1)
        contenedor.setLayout(layout)
        return contenedor

    def _pares_validos(self):
        """(resultado, (x, y)) por intervalo, conservando la correspondencia."""
        resultados = self.resultados_panel.get("resultados") or []
        return [
            (resultado, segmento)
            for resultado, segmento in zip(resultados, self.segmentos)
            if segmento
            and segmento[0] is not None
            and segmento[1] is not None
            and len(segmento[0])
        ]

    def _dibujar_segmentos(self, grafica):
        pares = self._pares_validos()
        if not pares:
            return

        # La señal base es la propia curva de FR (frames reales): da el
        # autointervalo y sirve de referencia atenuada bajo los colores.
        curva = concatenar_curva([segmento for _r, segmento in pares])
        grafica.set_datos(curva["x"], curva["y"])
        grafica.leyenda.removeItem(grafica.curva_original)
        grafica.curva_original.setPen(pg.mkPen((140, 140, 140, 70)))

        curvas = []
        for indice, (resultado, (x_seg, y_seg)) in enumerate(pares, start=1):
            nombre = resultado.get("nombre") or f"Intervalo {indice}"
            desde = resultado.get("desde")
            hasta = resultado.get("hasta")
            picos = picos_de_resultados([resultado])
            for pico in picos:
                pico.update(
                    {
                        "formula": nombre,
                        "unidad": self.unidad,
                        "etiqueta": f"Frame {desde}–{hasta}",
                    }
                )
            curvas.append(
                {
                    "clave": f"fr::{indice}",
                    "x": x_seg,
                    "y": y_seg,
                    "nombre": nombre,
                    "unidad": self.unidad,
                    "picos": picos,
                    "color": paleta.color_intervalo(indice),
                }
            )

        grafica.set_curvas_formulas(curvas)
        grafica.enableAutoRange(axis="y", enable=True)
        grafica.autoRange()

    def _crear_panel_resultados(self):
        panel_derecho = QWidget()
        layout_derecho = QVBoxLayout()
        layout_derecho.setContentsMargins(0, 0, 0, 0)
        layout_derecho.setSpacing(6)

        self.panel_calculo = PanelCalculo(permitir_gestion=False)
        self.panel_calculo.mostrar_resultados(self.resultados_panel)
        # Esta ventana muestra resultados ya calculados: no recalcula nada. Los
        # botones Aplicar/Quitar del panel no aplican aquí (y recalcular FR exige
        # revalidar las tres componentes), así que se ocultan en vez de dejarlos
        # activos sin acción; los combos solo se desactivan para no simular edición.
        self.panel_calculo.btn_aplicar_formula.hide()
        self.panel_calculo.btn_quitar_formula.hide()
        self.panel_calculo.cmb_fuente.setEnabled(False)
        self.panel_calculo.cmb_formula.setEnabled(False)
        layout_derecho.addWidget(self.panel_calculo)
        layout_derecho.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(320)
        scroll.setWidget(panel_derecho)
        return scroll
