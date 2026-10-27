"""Ventana independiente para los resultados de fuerza resultante."""

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
from logica.interfaz_adaptativa import (
    configurar_geometria_persistente,
    guardar_geometria,
)
from ui.ventanaPrincipal.panelDerecho.panelCalculo import PanelCalculo


class VentanaResultadosFR(QDialog):
    CLAVE_GEOMETRIA = "ventana_fuerza_resultante/geometria"
    CLAVE_DIVISION = "ventana_fuerza_resultante/division"

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
        self.setStyleSheet("QDialog { background-color: #1E1E1E; }")
        self.resultados_panel = dict(resultados_panel or {})
        self.segmentos = list(segmentos or [])
        self.unidad = unidad or "N"
        self.nombre_senal = nombre_senal or "Fuerza resultante"
        self.grafica = None
        self._init_ui()

        _, self._ajustes = configurar_geometria_persistente(
            self,
            self.CLAVE_GEOMETRIA,
            ideal=(1100, 600),
            minimo=(700, 430),
            piso=(580, 360),
        )
        division = self._ajustes.value(self.CLAVE_DIVISION)
        if division:
            self.separador.restoreState(division)

    def _init_ui(self):
        layout_principal = QVBoxLayout()
        layout_principal.setContentsMargins(12, 12, 12, 12)
        layout_principal.setSpacing(8)

        encabezado = QLabel(
            "Fuerza resultante · resultados por intervalo temporal"
        )
        encabezado.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #FFFFFF;"
        )
        encabezado.setWordWrap(True)
        layout_principal.addWidget(encabezado)

        self.separador = QSplitter(Qt.Horizontal)
        self.separador.addWidget(self._crear_panel_grafica())
        self.separador.addWidget(self._crear_panel_resultados())
        self.separador.setSizes([720, 340])
        self.separador.setCollapsible(0, False)
        self.separador.setCollapsible(1, False)
        self.separador.setHandleWidth(6)
        layout_principal.addWidget(self.separador, 1)
        self.setLayout(layout_principal)

    def _crear_panel_grafica(self):
        contenedor = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        from ui.ventanaPrincipal.areaCentralGraficas import GraficaSenal

        self.grafica = GraficaSenal(
            self.nombre_senal,
            unidad=self.unidad,
            etiqueta_x="Frame",
            columna="FR",
        )
        self._dibujar_segmentos()
        layout.addWidget(self.grafica, 1)
        contenedor.setLayout(layout)
        return contenedor

    def _pares_validos(self):
        resultados = self.resultados_panel.get("resultados") or []
        return [
            (resultado, segmento)
            for resultado, segmento in zip(resultados, self.segmentos)
            if segmento
            and segmento[0] is not None
            and segmento[1] is not None
            and len(segmento[0])
        ]

    def _dibujar_segmentos(self):
        pares = self._pares_validos()
        if not pares:
            return

        curva = concatenar_curva([segmento for _resultado, segmento in pares])
        self.grafica.set_datos(curva["x"], curva["y"])
        self.grafica.leyenda.removeItem(self.grafica.curva_original)
        self.grafica.curva_original.setPen(pg.mkPen((140, 140, 140, 75)))

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
                    "indice_color": indice,
                    "color": paleta.color_intervalo(indice),
                    "compartir_eje": True,
                }
            )

        self.grafica.set_curvas_formulas(curvas)
        self.grafica.enableAutoRange(axis="y", enable=True)
        self.grafica.autoRange()

    def _crear_panel_resultados(self):
        panel_derecho = QFrame()
        panel_derecho.setObjectName("formulasPanel")
        layout_derecho = QVBoxLayout()
        layout_derecho.setContentsMargins(10, 10, 10, 10)
        layout_derecho.setSpacing(6)

        self.panel_calculo = PanelCalculo(permitir_gestion=False)
        self.panel_calculo.set_formula("fuerza_resultante")
        self.panel_calculo.mostrar_resultados(self.resultados_panel)
        self.panel_calculo.btn_aplicar_formula.hide()
        self.panel_calculo.btn_quitar_formula.hide()
        self.panel_calculo.cmb_fuente.setEnabled(False)
        self.panel_calculo.cmb_formula.setEnabled(False)
        layout_derecho.addWidget(self.panel_calculo)
        layout_derecho.addStretch()
        panel_derecho.setLayout(layout_derecho)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(280)
        scroll.setWidget(panel_derecho)
        return scroll

    def aplicar_paleta(self):
        if self.grafica is not None:
            self.grafica.aplicar_paleta()
            if self.grafica.curva_original is not None:
                self.grafica.curva_original.setPen(
                    pg.mkPen((140, 140, 140, 75))
                )

    def closeEvent(self, event):
        self.guardar_geometria()
        super().closeEvent(event)

    def guardar_geometria(self):
        self._ajustes.setValue(self.CLAVE_DIVISION, self.separador.saveState())
        self._ajustes.sync()
        guardar_geometria(self)
