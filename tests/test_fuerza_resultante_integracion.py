"""Pruebas de integración de Fuerza Resultante (Fases 2, 3 y 4).

Cubren la agrupación temporal exclusiva de la fórmula, el selector de señal
«Todas las señales visibles» y la apertura de la ventana independiente de
resultados, todo sin desplegar la interfaz (QT_QPA_PLATFORM=offscreen).
"""
from __future__ import annotations

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover - entorno sin Qt
    raise unittest.SkipTest("PySide6 no disponible")

from PySide6.QtCore import QPointF

from logica import formulas as formulas_logica
from logica.intervalos import GestorIntervalos
from ui.ventanaPrincipal.areaCentralGraficas import AreaCentralGraficas

APLICACION = QApplication.instance() or QApplication([])


def _dataframe_fuerzas(n_frames=40, semilla: tuple | None = None):
    import pandas as pd

    frames = np.arange(1, n_frames + 1)
    if semilla is None:
        fx = np.sin(frames / 6.0) * 50 + 40
        fy = np.cos(frames / 5.0) * 40 + 30
        fz = np.full(n_frames, 700.0) + (frames % 7) * 3.0
    else:
        fx, fy, fz = semilla
    return pd.DataFrame({"Frame": frames, "Fx": fx, "Fy": fy, "Fz": fz})


def _mapeo_fuerzas():
    return {
        "Fuerza": {"eje_x": "Fx", "eje_y": "Fy", "eje_z": "Fz"},
    }


def _cargar_area(df, mapeo=None, nombre="prueba.csv"):
    area = AreaCentralGraficas()
    area.setWindowTitle("prueba")
    info = {"unidades": {"Fx": "N", "Fy": "N", "Fz": "N"}}
    area.cargar_dataframe(nombre, df, info)
    area.mapeo_actual = _mapeo_fuerzas() if mapeo is None else mapeo
    return area


def _marcar(area, columna, desde, hasta, permitir_superposicion=False):
    gestor = area.gestores_intervalos.get(columna)
    if gestor is None:
        gestor = GestorIntervalos()
        area.gestores_intervalos[columna] = gestor
    if permitir_superposicion:
        intervalo = gestor.agregar(desde, hasta, permitir_superposicion=True)
    else:
        intervalo, _fue_ajustado = gestor.agregar_ajustado(desde, hasta)
    return f"{columna}::{intervalo.numero}"


class TestAgrupacionTemporalFR(unittest.TestCase):
    """Fase 2: FR agrupa por bloque temporal, el resto de fórmulas no."""

    def setUp(self):
        self.area = _cargar_area(_dataframe_fuerzas())

    def tearDown(self):
        self.area = None

    def _seleccionar_fuerzas(self, desde, hasta):
        return [
            _marcar(self.area, col, desde, hasta)
            for col in ("Fx", "Fy", "Fz")
        ]

    def test_tres_intervalos_de_un_mismo_bloque_producen_un_solo_resultado(self):
        ids = self._seleccionar_fuerzas(10, 30)
        calculo = self.area._calculos_formulas
        self.assertTrue(
            self.area.aplicar_formula(
                {"clave": "fuerza_resultante", "intervalos": ids}
            )
        )
        datos = self.area._calculos_formulas["fuerza_resultante"]["datos_panel"]
        self.assertEqual(len(datos["resultados"]), 1)

    def test_dos_bloques_temporales_distintos_producen_dos_resultados(self):
        ids = [
            _marcar(self.area, "Fx", 5, 10),
            _marcar(self.area, "Fy", 5, 10),
            _marcar(self.area, "Fz", 5, 10),
            _marcar(self.area, "Fx", 25, 30),
            _marcar(self.area, "Fy", 25, 30),
            _marcar(self.area, "Fz", 25, 30),
        ]
        self.assertTrue(
            self.area.aplicar_formula(
                {"clave": "fuerza_resultante", "intervalos": ids}
            )
        )
        datos = self.area._calculos_formulas["fuerza_resultante"]["datos_panel"]
        self.assertEqual(len(datos["resultados"]), 2)

    def test_el_resultado_solo_depende_del_bloque_temporal(self):
        # Intervalos con límites idénticos pero creados en otro orden deben
        # agruparse igual; los del mismo bloque comparten rango (desde, hasta).
        ids_a = self._seleccionar_fuerzas(10, 30)
        ids_b = [
            _marcar(self.area, col, 10, 30, permitir_superposicion=True)
            for col in ("Fx", "Fy", "Fz")
        ]
        self.assertTrue(
            self.area.aplicar_formula(
                {"clave": "fuerza_resultante", "intervalos": [*ids_a, *ids_b]}
            )
        )
        datos = self.area._calculos_formulas["fuerza_resultante"]["datos_panel"]
        self.assertEqual(len(datos["resultados"]), 1)

    def test_falta_componente_rechaza_el_calculo(self):
        ids = self._seleccionar_fuerzas(10, 30)
        self.area.mapeo_actual = {"Fuerza": {"eje_x": "Fx", "eje_y": "Fy"}}
        mensajes = []
        self.area.formulaEstadoCambiado.connect(
            lambda ok, msg: mensajes.append((ok, msg))
        )
        self.assertFalse(
            self.area.aplicar_formula(
                {"clave": "fuerza_resultante", "intervalos": ids},
                avisar=True,
                actualizar_vista=False,
            )
        )
        self.assertTrue(mensajes)
        self.assertFalse(mensajes[-1][0])


class TestVentanaResultadosFR(unittest.TestCase):
    """Fase 4: al aplicar FR se abre la ventana y no se duplica en el panel."""

    def setUp(self):
        self.area = _cargar_area(_dataframe_fuerzas())
        self.panel_recibidos = []
        self.area.resultadosFormulaCambiaron.connect(self.panel_recibidos.append)
        self.panel_recibidos.clear()

    def tearDown(self):
        self.area = None

    def _ids_de_bloque(self, desde, hasta):
        return [
            _marcar(self.area, col, desde, hasta)
            for col in ("Fx", "Fy", "Fz")
        ]

    def test_aplicar_abre_una_ventana_con_los_resultados(self):
        self.area.aplicar_formula(
            {"clave": "fuerza_resultante", "intervalos": self._ids_de_bloque(10, 30)}
        )
        ventanas = getattr(self.area, "_ventanas_resultados_fr", [])
        self.assertEqual(len(ventanas), 1)
        ventana = ventanas[-1]
        self.assertEqual(len(ventana.segmentos), 1)
        self.assertEqual(len(ventana.resultados_panel.get("resultados", [])), 1)
        self.assertIsNotNone(ventana.panel_calculo)

    def test_el_mismo_resultado_no_se_emite_al_panel_derecho(self):
        self.area.aplicar_formula(
            {"clave": "fuerza_resultante", "intervalos": self._ids_de_bloque(10, 30)}
        )
        self.assertEqual(self.panel_recibidos, [])

    def test_una_ventana_reune_el_bloque_temporal_completo(self):
        ids = [
            _marcar(self.area, "Fx", 5, 10),
            _marcar(self.area, "Fy", 5, 10),
            _marcar(self.area, "Fz", 5, 10),
            _marcar(self.area, "Fx", 25, 30),
            _marcar(self.area, "Fy", 25, 30),
            _marcar(self.area, "Fz", 25, 30),
        ]
        self.area.aplicar_formula(
            {"clave": "fuerza_resultante", "intervalos": ids}
        )
        ventanas = getattr(self.area, "_ventanas_resultados_fr", [])
        self.assertEqual(len(ventanas), 1)
        ventana = ventanas[-1]
        self.assertEqual(len(ventana.segmentos), 2)
        self.assertEqual(len(ventana.resultados_panel.get("resultados", [])), 2)

    def test_las_demas_formulas_siguen_emitiendo_al_panel(self):
        self.area.set_variables_sujeto({"masa": 70.0, "gravedad": 9.8})
        # La aceleración se calcula sobre Fz: sus intervalos van en esa señal.
        self.assertTrue(
            self.area.aplicar_formula(
                {
                    "clave": "aceleracion",
                    "intervalos": [_marcar(self.area, "Fz", 10, 30)],
                }
            )
        )
        # La aceleración sí se muestra en el panel derecho (no abre ventana).
        self.assertTrue(any(d is not None for d in self.panel_recibidos))


class TestSelectorTodasLasSenales(unittest.TestCase):
    """Fase 3: el combo de señal elige entre «Todas» y cada señal visible."""

    def setUp(self):
        from ui.ventanaPrincipal.panelDerecho.formulas import Formulas

        self.panel = Formulas()

    def tearDown(self):
        self.panel = None

    def _senales(self, visibles=True):
        return [
            {"nombre": "Fuerza X", "columna": "Fx", "visible": visibles},
            {"nombre": "Fuerza Y", "columna": "Fy", "visible": visibles},
            {"nombre": "Fuerza Z", "columna": "Fz", "visible": visibles},
        ]

    def test_carga_con_la_opcion_todas_por_defecto(self):
        self.panel.cargar_senales(self._senales())
        combo = self.panel.cmb_senal
        self.assertEqual(combo.count(), 4)
        self.assertIsNone(combo.currentData())
        self.assertEqual(combo.itemText(0), "Todas las señales visibles")

    def test_preserva_la_seleccion_al_actualizar(self):
        self.panel.cargar_senales(self._senales())
        self.panel.cmb_senal.setCurrentIndex(
            self.panel.cmb_senal.findData("Fy")
        )
        self.panel.cargar_senales(self._senales())
        self.assertEqual(self.panel.cmb_senal.currentData(), "Fy")

    def test_sin_senales_muestra_mensaje_y_no_selecciona(self):
        self.panel.cargar_senales(self._senales(visibles=False))
        self.assertEqual(self.panel.cmb_senal.count(), 1)
        self.assertIsNone(self.panel.cmb_senal.currentData())

    def test_todas_muestra_todos_los_intervalos_padre(self):
        self.panel.cargar_senales(self._senales())
        self.panel.cargar_intervalos(
            [
                {"id": "Fx::1", "columna": "Fx", "senal": "Fuerza X",
                 "numero": 1, "desde": 10, "hasta": 30, "color": "#4FC3F7",
                 "es_subintervalo": False},
                {"id": "Fy::1", "columna": "Fy", "senal": "Fuerza Y",
                 "numero": 1, "desde": 10, "hasta": 30, "color": "#81C784",
                 "es_subintervalo": False},
                {"id": "Fx::1::sub::1", "columna": "Fx", "padre": "Fx::1",
                 "numero": 1, "desde": 12, "hasta": 20, "color": "#E57373",
                 "es_subintervalo": True},
            ]
        )
        self.panel.cmb_senal.setCurrentIndex(0)  # «Todas»
        self.panel._renderizar_intervalos_actuales()
        self.assertIn("Fx::1", self.panel.checkboxes)
        self.assertIn("Fy::1", self.panel.checkboxes)
        # El sub-intervalo se lista anidado bajo su padre, no como intervalo suelto.
        self.assertIn("Fx::1::sub::1", self.panel.checkboxes)

    def test_senal_elegida_solo_muestra_sus_intervalos(self):
        self.panel.cargar_senales(self._senales())
        self.panel.cargar_intervalos(
            [
                {"id": "Fx::1", "columna": "Fx", "senal": "Fuerza X",
                 "numero": 1, "desde": 10, "hasta": 30, "color": "#4FC3F7",
                 "es_subintervalo": False},
                {"id": "Fy::1", "columna": "Fy", "senal": "Fuerza Y",
                 "numero": 1, "desde": 10, "hasta": 30, "color": "#81C784",
                 "es_subintervalo": False},
            ]
        )
        self.panel.cmb_senal.setCurrentIndex(
            self.panel.cmb_senal.findData("Fx")
        )
        self.panel._renderizar_intervalos_actuales()
        self.assertIn("Fx::1", self.panel.checkboxes)
        self.assertNotIn("Fy::1", self.panel.checkboxes)


class TestValidacionComponentesUI(unittest.TestCase):
    """Fase 2/6: la FR solo se calcula con Fx, Fy y Fz en los mismos límites."""

    def setUp(self):
        self.area = _cargar_area(_dataframe_fuerzas())
        self.area.setWindowTitle("prueba")
        self.mensajes = []
        self.area.formulaEstadoCambiado.connect(
            lambda ok, msg: self.mensajes.append((ok, msg))
        )

    def tearDown(self):
        self.area = None

    def _aplicar(self, ids):
        return self.area.aplicar_formula(
            {"clave": "fuerza_resultante", "intervalos": ids}
        )

    def test_solo_fx_se_rechaza(self):
        self.assertFalse(self._aplicar([_marcar(self.area, "Fx", 10, 30)]))

    def test_solo_fy_se_rechaza(self):
        self.assertFalse(self._aplicar([_marcar(self.area, "Fy", 10, 30)]))

    def test_solo_fz_se_rechaza(self):
        self.assertFalse(self._aplicar([_marcar(self.area, "Fz", 10, 30)]))

    def test_fx_y_fy_se_rechaza(self):
        self.assertFalse(
            self._aplicar(
                [_marcar(self.area, "Fx", 10, 30), _marcar(self.area, "Fy", 10, 30)]
            )
        )

    def test_fx_y_fz_se_rechaza(self):
        self.assertFalse(
            self._aplicar(
                [_marcar(self.area, "Fx", 10, 30), _marcar(self.area, "Fz", 10, 30)]
            )
        )

    def test_fy_y_fz_se_rechaza(self):
        self.assertFalse(
            self._aplicar(
                [_marcar(self.area, "Fy", 10, 30), _marcar(self.area, "Fz", 10, 30)]
            )
        )

    def test_limites_distintos_se_rechaza_y_explica(self):
        ok = self._aplicar(
            [
                _marcar(self.area, "Fx", 10, 20),
                _marcar(self.area, "Fy", 10, 20),
                _marcar(self.area, "Fz", 30, 40),
            ]
        )
        self.assertFalse(ok)
        self.assertTrue(self.mensajes)
        self.assertFalse(self.mensajes[-1][0])

    def test_las_tres_con_los_mismos_limites_calculan_una(self):
        ok = self._aplicar(
            [
                _marcar(self.area, "Fx", 10, 30),
                _marcar(self.area, "Fy", 10, 30),
                _marcar(self.area, "Fz", 10, 30),
            ]
        )
        self.assertTrue(ok)
        datos = self.area._calculos_formulas["fuerza_resultante"]["datos_panel"]
        self.assertEqual(len(datos["resultados"]), 1)

    def test_rechazo_no_abre_ventana(self):
        self._aplicar([_marcar(self.area, "Fx", 10, 30)])
        self.assertEqual(getattr(self.area, "_ventanas_resultados_fr", []), [])


class TestAislamientoVentanaFR(unittest.TestCase):
    """Fases 3/4/5/6: curva solo en la ventana y lectura por cursor."""

    def setUp(self):
        self.area = _cargar_area(_dataframe_fuerzas())
        self.area.setWindowTitle("prueba")

    def tearDown(self):
        self.area = None

    def _ids_de_bloque(self, desde, hasta):
        return [
            _marcar(self.area, col, desde, hasta)
            for col in ("Fx", "Fy", "Fz")
        ]

    def _aplicar_fr(self, desde=10, hasta=30):
        self.area.aplicar_formula(
            {"clave": "fuerza_resultante", "intervalos": self._ids_de_bloque(desde, hasta)}
        )

    def test_la_curva_fr_no_se_dibuja_en_ninguna_grafica_original(self):
        self._aplicar_fr()
        for columna, grafica in self.area.graficas_por_columna.items():
            self.assertEqual(
                len(grafica._curvas_formula_dibujadas),
                0,
                f"FR no debe dibujarse en la gráfica de {columna}",
            )

    def test_aplicar_fr_no_altera_los_datos_ni_las_selecciones(self):
        import numpy as np

        ids = self._ids_de_bloque(10, 30)
        antes = {
            columna: self.area._datos_columna(columna).copy()
            for columna in ("Fx", "Fy", "Fz")
        }
        intervalos_antes = {
            columna: list(self.area.gestores_intervalos[columna].listar())
            for columna in ("Fx", "Fy", "Fz")
        }
        self.area.aplicar_formula(
            {"clave": "fuerza_resultante", "intervalos": ids}
        )
        for columna, valores in antes.items():
            np.testing.assert_allclose(self.area._datos_columna(columna), valores)
        for columna, intervalos in intervalos_antes.items():
            ahora = self.area.gestores_intervalos[columna].listar()
            self.assertEqual(len(ahora), len(intervalos))
            for original, actual in zip(intervalos, ahora):
                self.assertEqual((original.desde, original.hasta),
                                 (actual.desde, actual.hasta))

    def test_la_curva_calculada_coincide_con_la_norma(self):
        import numpy as np

        self._aplicar_fr(10, 30)
        ventana = self.area._ventanas_resultados_fr[-1]
        x_seg, y_seg = ventana.segmentos[0]
        fx = self.area._datos_columna("Fx")
        fy = self.area._datos_columna("Fy")
        fz = self.area._datos_columna("Fz")
        indices = x_seg.astype(int) - 1  # los frames arrancan en 1
        esperado = np.sqrt(fx[indices] ** 2 + fy[indices] ** 2 + fz[indices] ** 2)
        np.testing.assert_allclose(y_seg, esperado)

    def test_la_ventana_muestra_las_muestras_y_los_limites(self):
        self._aplicar_fr(10, 30)
        ventana = self.area._ventanas_resultados_fr[-1]
        ventana.resize(900, 500)
        ventana.show()
        APLICACION.processEvents()

        self.assertEqual(len(ventana.segmentos), 1)
        x_seg, y_seg = ventana.segmentos[0]
        self.assertEqual(int(x_seg[0]), 10)
        self.assertEqual(int(x_seg[-1]), 30)

        grafica = ventana.grafica
        self.assertEqual(len(grafica._curvas_formula_dibujadas), 1)
        registro = grafica._curvas_formula_dibujadas[0]
        np.testing.assert_allclose(registro["x"], x_seg)
        self.assertEqual(registro["info"]["unidad"], "N")

    def test_la_lectura_por_cursor_informa_frame_y_valor(self):
        self._aplicar_fr(10, 30)
        ventana = self.area._ventanas_resultados_fr[-1]
        ventana.resize(900, 500)
        ventana.show()
        APLICACION.processEvents()

        grafica = ventana.grafica
        registro = grafica._curvas_formula_dibujadas[0]
        indice = 5
        x_dato = float(registro["x"][indice])
        y_dato = float(registro["y"][indice])
        posicion = registro["vista"].mapViewToScene(QPointF(x_dato, y_dato))

        grafica._actualizar_caja_valor(posicion)

        self.assertTrue(grafica.caja_valor.isVisible())
        html = grafica.caja_valor.toHtml()
        self.assertIn(f"Frame {x_dato:g}", html)
        self.assertIn(formulas_logica.formatear_valor(y_dato), html)

    def test_cerrar_la_ventana_no_deja_referencias_ni_curvas_residuales(self):
        self._aplicar_fr()
        ventana = self.area._ventanas_resultados_fr[-1]
        ventana.close()
        APLICACION.processEvents()
        self.assertEqual(getattr(self.area, "_ventanas_resultados_fr", []), [])
        for grafica in self.area.graficas_por_columna.values():
            self.assertEqual(len(grafica._curvas_formula_dibujadas), 0)

    def test_dos_bloques_completos_y_uno_incompleto_no_engana(self):
        ids = []
        for desde, hasta in ((5, 12), (20, 26)):
            for col in ("Fx", "Fy", "Fz"):
                ids.append(_marcar(self.area, col, desde, hasta))
        ids.append(_marcar(self.area, "Fx", 32, 38))  # incompleto
        ok = self.area.aplicar_formula(
            {"clave": "fuerza_resultante", "intervalos": ids}
        )
        self.assertTrue(ok)
        datos = self.area._calculos_formulas["fuerza_resultante"]["datos_panel"]
        self.assertEqual(len(datos["resultados"]), 2)
        self.assertTrue(
            any("Frame 32–38" in aviso for aviso in datos["advertencias"])
        )

    def test_las_demas_formulas_siguen_dibujandose_en_su_grafica(self):
        self.area.set_variables_sujeto({"masa": 70.0, "gravedad": 9.8})
        self.assertTrue(
            self.area.aplicar_formula(
                {
                    "clave": "aceleracion",
                    "intervalos": [_marcar(self.area, "Fz", 10, 30)],
                }
            )
        )
        grafica_fz = self.area.graficas_por_columna["Fz"]
        self.assertEqual(len(grafica_fz._curvas_formula_dibujadas), 1)


if __name__ == "__main__":
    unittest.main()