import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import numpy as np

from logica import accesibilidad, formulas, paleta, proyecto
from logica.filtros_senales import (
    ErrorConfiguracionFiltro,
    aplicar_butterworth,
    aplicar_butterworth_pasabajos,
)
from logica.lector_csv import calcular_frecuencia_efectiva, leer_csv_rapido
from logica.rangos import GestorRangos, RangoSuperpuestoError


RAIZ = Path(__file__).resolve().parents[1]
CSV_FUERZA = RAIZ / "utilidades" / "resources" / "Carlos Bigolotti Americano CM Fuerza solo.csv"


class TestLectorCSV(unittest.TestCase):
    def test_detecta_cabecera_unidades_y_frecuencia(self):
        df, metadatos = leer_csv_rapido(CSV_FUERZA)

        self.assertEqual(df.shape, (49304, 11))
        self.assertEqual(df.columns[:4].tolist(), ["Frame", "Sub Frame", "Fx", "Fy"])
        self.assertEqual(metadatos["unidades"]["Fx"], "N")
        self.assertEqual(metadatos["unidades"]["Mx"], "N.mm")
        self.assertEqual(metadatos["unidades"]["Cx"], "mm")
        self.assertEqual(metadatos["frecuencia_muestreo"], 2000.0)
        self.assertTrue(all(np.issubdtype(tipo, np.number) for tipo in df.dtypes))

    def test_ajusta_la_frecuencia_original_por_subframes(self):
        subframes = {"tiene_subframes": True, "max_por_frame": 8}

        self.assertEqual(calcular_frecuencia_efectiva(2000, subframes), 250.0)
        self.assertEqual(
            calcular_frecuencia_efectiva(1000, {"tiene_subframes": False}),
            1000.0,
        )
        self.assertIsNone(calcular_frecuencia_efectiva(0, subframes))


class TestFiltro(unittest.TestCase):
    def test_pasabajos_reduce_componente_alta(self):
        frecuencia = 200.0
        tiempo = np.arange(0, 2, 1 / frecuencia)
        datos = np.sin(2 * np.pi * 2 * tiempo) + 0.5 * np.sin(2 * np.pi * 40 * tiempo)

        filtrados = aplicar_butterworth_pasabajos(datos, frecuencia, 10, orden=4)
        espectro_original = np.abs(np.fft.rfft(datos))
        espectro_filtrado = np.abs(np.fft.rfft(filtrados))
        frecuencias = np.fft.rfftfreq(len(datos), 1 / frecuencia)
        indice_2 = int(np.argmin(np.abs(frecuencias - 2)))
        indice_40 = int(np.argmin(np.abs(frecuencias - 40)))

        self.assertGreater(espectro_filtrado[indice_2], espectro_original[indice_2] * 0.9)
        self.assertLess(espectro_filtrado[indice_40], espectro_original[indice_40] * 0.05)

    def test_rechaza_corte_sobre_nyquist(self):
        with self.assertRaises(ErrorConfiguracionFiltro):
            aplicar_butterworth_pasabajos(np.arange(100), 100, 50, orden=4)

    def test_pasaaltos_reduce_componente_baja(self):
        frecuencia = 200.0
        tiempo = np.arange(0, 2, 1 / frecuencia)
        datos = np.sin(2 * np.pi * 2 * tiempo) + 0.5 * np.sin(2 * np.pi * 40 * tiempo)

        filtrados = aplicar_butterworth(datos, frecuencia, "highpass", 10, orden=4)
        espectro_original = np.abs(np.fft.rfft(datos))
        espectro_filtrado = np.abs(np.fft.rfft(filtrados))
        frecuencias = np.fft.rfftfreq(len(datos), 1 / frecuencia)
        indice_2 = int(np.argmin(np.abs(frecuencias - 2)))
        indice_40 = int(np.argmin(np.abs(frecuencias - 40)))

        self.assertLess(espectro_filtrado[indice_2], espectro_original[indice_2] * 0.05)
        self.assertGreater(espectro_filtrado[indice_40], espectro_original[indice_40] * 0.9)

    def test_pasabanda_conserva_solo_intervalo_elegido(self):
        frecuencia = 500.0
        tiempo = np.arange(0, 4, 1 / frecuencia)
        datos = (
            np.sin(2 * np.pi * 5 * tiempo)
            + 0.8 * np.sin(2 * np.pi * 40 * tiempo)
            + 0.6 * np.sin(2 * np.pi * 120 * tiempo)
        )

        filtrados = aplicar_butterworth(datos, frecuencia, "bandpass", (30, 60), orden=4)
        espectro_original = np.abs(np.fft.rfft(datos))
        espectro_filtrado = np.abs(np.fft.rfft(filtrados))
        frecuencias = np.fft.rfftfreq(len(datos), 1 / frecuencia)

        for frecuencia_fuera in (5, 120):
            indice = int(np.argmin(np.abs(frecuencias - frecuencia_fuera)))
            self.assertLess(espectro_filtrado[indice], espectro_original[indice] * 0.05)

        indice_40 = int(np.argmin(np.abs(frecuencias - 40)))
        self.assertGreater(espectro_filtrado[indice_40], espectro_original[indice_40] * 0.9)

    def test_rechaza_intervalo_invertido(self):
        with self.assertRaises(ErrorConfiguracionFiltro):
            aplicar_butterworth(np.arange(200), 200, "bandpass", (60, 30), orden=4)

    def test_conserva_los_huecos_originales(self):
        datos = np.sin(np.linspace(0, 20, 400))
        datos[100:110] = np.nan

        filtrados = aplicar_butterworth(datos, 200, "lowpass", 20, orden=4)

        self.assertTrue(np.isnan(filtrados[100:110]).all())
        self.assertTrue(np.isfinite(filtrados[:100]).all())


class TestRangos(unittest.TestCase):
    def test_agrega_colores_y_rechaza_superposicion(self):
        gestor = GestorRangos()
        primero = gestor.agregar(30, 40)
        segundo = gestor.agregar(50, 60)

        self.assertEqual((primero.numero, primero.desde, primero.hasta), (1, 30, 40))
        self.assertNotEqual(primero.color, segundo.color)
        with self.assertRaises(RangoSuperpuestoError):
            gestor.agregar(40, 45)

    def test_elimina_solo_los_indicados(self):
        gestor = GestorRangos()
        gestor.agregar(10, 20)
        gestor.agregar(30, 40)
        gestor.eliminar([1])
        self.assertEqual([rango.numero for rango in gestor.listar()], [2])

    def test_ordena_y_renumera_visualmente_de_izquierda_a_derecha(self):
        gestor = GestorRangos()
        primero_creado = gestor.agregar(100, 200)
        segundo_creado = gestor.agregar(50, 80)

        visibles = gestor.listar()

        self.assertEqual(
            [(rango.desde, rango.hasta) for rango in visibles],
            [(50, 80), (100, 200)],
        )
        self.assertEqual([rango.orden for rango in visibles], [1, 2])
        self.assertEqual([rango.nombre for rango in visibles], ["Rango 1", "Rango 2"])
        # Las identidades no cambian: siguen sirviendo para notas y borrado.
        self.assertEqual(
            [rango.numero for rango in visibles],
            [segundo_creado.numero, primero_creado.numero],
        )

    def test_conserva_nombres_personalizados_al_reordenar(self):
        gestor = GestorRangos()
        gestor.agregar(100, 200, "Despegue")
        gestor.agregar(50, 80)

        self.assertEqual(
            [rango.nombre for rango in gestor.listar()],
            ["Rango 1", "Despegue"],
        )

    def test_ajusta_inicio_ocupado_al_primer_frame_libre(self):
        gestor = GestorRangos()
        gestor.agregar(20, 30)

        nuevo, fue_ajustado = gestor.agregar_ajustado(24, 50)

        self.assertTrue(fue_ajustado)
        self.assertEqual((nuevo.desde, nuevo.hasta), (31, 50))

    def test_recorta_en_el_primer_rango_que_encuentra(self):
        gestor = GestorRangos()
        gestor.agregar(20, 30)

        nuevo, fue_ajustado = gestor.agregar_ajustado(10, 50)

        self.assertTrue(fue_ajustado)
        self.assertEqual((nuevo.desde, nuevo.hasta), (10, 19))

    def test_restaura_conservando_numero_y_color(self):
        gestor = GestorRangos()
        original = gestor.agregar(30, 40)
        gestor.agregar(50, 60)

        restaurado = GestorRangos()
        # Se reponen en desorden, como podrían venir del CSV de anotaciones.
        restaurado.restaurar(2, 50, 60, "Rango 2")
        repuesto = restaurado.restaurar(1, 30, 40, "Apoyo")

        self.assertEqual([r.numero for r in restaurado.listar()], [1, 2])
        self.assertEqual(repuesto.color, original.color)
        self.assertEqual(repuesto.nombre, "Apoyo")

    def test_restaurar_no_valida_superposicion_y_sigue_numerando(self):
        gestor = GestorRangos()
        gestor.restaurar(1, 30, 40)
        gestor.restaurar(3, 35, 45)  # superpuesto: ya se aceptó al crearlo

        self.assertEqual([r.numero for r in gestor.listar()], [1, 3])
        self.assertEqual(gestor.agregar(100, 110).numero, 4)

    def test_los_subgestores_nombran_sub_rangos(self):
        # Los sub-rangos usan otro prefijo para no confundirse con su padre.
        sub = GestorRangos("Sub-rango")
        self.assertEqual(sub.agregar(10, 20).nombre, "Sub-rango 1")
        self.assertEqual(sub.restaurar(3, 30, 40).nombre, "Sub-rango 3")
        # Un nombre propio siempre gana sobre el prefijo.
        self.assertEqual(sub.agregar(50, 60, "Impulso").nombre, "Impulso")
        # El gestor de rangos padre no cambia.
        self.assertEqual(GestorRangos().agregar(10, 20).nombre, "Rango 1")

    def test_restaurar_rechaza_rango_degenerado(self):
        gestor = GestorRangos()
        with self.assertRaises(ValueError):
            gestor.restaurar(1, 30, 30)


class TestPotencia(unittest.TestCase):
    MASA = 70.0
    G = 10.0  # redondo, para que las cuentas del test se sigan a mano

    def test_en_reposo_la_potencia_es_cero(self):
        # Con Fz igual al peso no hay aceleración: ni velocidad ni potencia.
        fz = np.full(50, self.MASA * self.G)
        resultado = formulas.potencia(fz, self.MASA, self.G, frecuencia=100.0)
        np.testing.assert_allclose(resultado, 0.0, atol=1e-9)

    def test_la_velocidad_arranca_del_reposo(self):
        fz = np.full(10, self.MASA * self.G * 2)  # 1 g de aceleración neta
        v = formulas.velocidad(fz, self.MASA, self.G, frecuencia=100.0)
        self.assertEqual(v[0], 0.0)

    def test_integra_una_aceleracion_constante(self):
        # Fz = 2·m·g deja una aceleración neta de g = 10 m/s².
        # Tras 1 s la velocidad tiene que ser 10 m/s.
        frecuencia = 100.0
        fz = np.full(int(frecuencia) + 1, self.MASA * self.G * 2)
        v = formulas.velocidad(fz, self.MASA, self.G, frecuencia)
        self.assertAlmostEqual(v[-1], 10.0, places=6)
        # P = Fz·v al final: 1400 N · 10 m/s = 14 000 W
        p = formulas.potencia(fz, self.MASA, self.G, frecuencia)
        self.assertAlmostEqual(p[-1], 14000.0, places=3)

    def test_aceleracion_descuenta_el_peso(self):
        a = formulas.aceleracion([self.MASA * self.G], self.MASA, self.G)
        self.assertAlmostEqual(a[0], 0.0)

    def test_sin_masa_explica_que_falta(self):
        with self.assertRaises(formulas.ErrorFormula) as contexto:
            formulas.potencia([700.0, 700.0], None, self.G, 100.0)
        self.assertIn("masa", str(contexto.exception).lower())

    def test_sin_frecuencia_explica_que_falta(self):
        with self.assertRaises(formulas.ErrorFormula) as contexto:
            formulas.potencia([700.0, 700.0], self.MASA, self.G, 0)
        self.assertIn("frecuencia", str(contexto.exception).lower())

    def test_rango_de_una_sola_muestra_no_revienta(self):
        with self.assertRaises(formulas.ErrorFormula):
            formulas.potencia([700.0], self.MASA, self.G, 100.0)


class TestImpulso(unittest.TestCase):
    MASA = 70.0
    G = 10.0  # redondo, para que las cuentas del test se sigan a mano
    FRECUENCIA = 100.0

    def test_en_reposo_el_impulso_es_cero(self):
        # Con Fz igual al peso la fuerza neta es cero: no se acumula impulso.
        fz = np.full(50, self.MASA * self.G)
        resultado = formulas.impulso(fz, self.MASA, self.G, self.FRECUENCIA)
        np.testing.assert_allclose(resultado, 0.0, atol=1e-9)

    def test_arranca_de_cero(self):
        fz = np.full(10, self.MASA * self.G * 2)
        j = formulas.impulso(fz, self.MASA, self.G, self.FRECUENCIA)
        self.assertEqual(j[0], 0.0)

    def test_integra_una_fuerza_neta_constante(self):
        # Fz = 2·m·g deja una fuerza neta de m·g = 700 N.
        # Tras 1 s el impulso tiene que ser 700 N · 1 s = 700 N·s.
        fz = np.full(int(self.FRECUENCIA) + 1, self.MASA * self.G * 2)
        j = formulas.impulso(fz, self.MASA, self.G, self.FRECUENCIA)
        self.assertAlmostEqual(j[-1], 700.0, places=6)

    def test_equivale_a_masa_por_velocidad(self):
        # Teorema del impulso: J = m·Δv. Vale para cualquier señal.
        rng = np.random.default_rng(7)
        fz = self.MASA * self.G + rng.normal(0.0, 300.0, size=200)

        j = formulas.impulso(fz, self.MASA, self.G, self.FRECUENCIA)
        v = formulas.velocidad(fz, self.MASA, self.G, self.FRECUENCIA)

        np.testing.assert_allclose(j, self.MASA * v, rtol=1e-9, atol=1e-9)

    def _contexto(self):
        return {
            "masa": self.MASA,
            "gravedad": self.G,
            "frecuencia": self.FRECUENCIA,
        }

    def _detalles(self, fz, valores=None):
        """Detalles del tramo, con la firma que consume ``computar_formula``."""
        fz = np.asarray(fz, dtype=float)
        if valores is None:
            valores = formulas.impulso(fz, self.MASA, self.G, self.FRECUENCIA)
        return {
            detalle["etiqueta"]: detalle["valor"]
            for detalle in formulas.detalles_impulso(
                valores, {"Fz": fz}, self._contexto()
            )
        }

    def test_separa_la_fase_de_frenado_de_la_de_propulsion(self):
        # Fuerza neta lineal de −700 N a +700 N en 1 s: cruza cero justo en una
        # muestra, así que las dos áreas son triángulos exactos de 175 N·s.
        t = np.linspace(0.0, 1.0, int(self.FRECUENCIA) + 1)
        fz = self.MASA * self.G + (1400.0 * t - 700.0)

        detalles = self._detalles(fz)

        self.assertAlmostEqual(detalles["propulsivo"], 175.0, places=6)
        self.assertAlmostEqual(detalles["frenado"], -175.0, places=6)
        # Lo que sube y lo que baja se cancela: el neto es cero.
        self.assertAlmostEqual(detalles["impulso neto"], 0.0, places=6)

    def test_el_delta_de_velocidad_sale_del_impulso_neto(self):
        # 700 N·s sobre 70 kg son 10 m/s de cambio de velocidad.
        fz = np.full(int(self.FRECUENCIA) + 1, self.MASA * self.G * 2)
        self.assertAlmostEqual(self._detalles(fz)["Δ velocidad"], 10.0, places=6)

    def test_las_unidades_acompanan_a_cada_valor(self):
        fz = np.full(20, self.MASA * self.G * 2)
        detalles = formulas.detalles_impulso(
            formulas.impulso(fz, self.MASA, self.G, self.FRECUENCIA),
            {"Fz": fz},
            self._contexto(),
        )
        unidades = {d["etiqueta"]: d["unidad"] for d in detalles}
        self.assertEqual(unidades["impulso neto"], "N·s")
        self.assertEqual(unidades["Δ velocidad"], "m/s")

    def test_el_neto_del_rango_resta_los_extremos_del_recorte(self):
        # La integración arranca en el primer frame del registro, no en el
        # rango. Con un impulso previo al tramo, tomar el último valor de la
        # curva daría el acumulado desde el inicio del archivo en vez del neto
        # del rango: por eso se restan los extremos.
        n = 301
        x = np.arange(n, dtype=float)
        fz = np.full(n, self.MASA * self.G)
        fz[0:101] += 700.0        # primer envión, antes del rango
        fz[200:n] += 700.0        # segundo envión, dentro del rango

        curva = formulas.impulso(fz, self.MASA, self.G, self.FRECUENCIA)
        acumulado_al_final = curva[-1]
        neto_esperado = curva[-1] - curva[200]

        resultados, _ = formulas.computar_formula(
            "impulso", {"Fz": fz}, x, self._contexto(),
            [{"id": "r1", "numero": 1, "desde": 200, "hasta": 300}],
        )
        detalles = {
            d["etiqueta"]: d["valor"] for d in resultados[0]["detalles"]
        }

        self.assertAlmostEqual(detalles["impulso neto"], neto_esperado, places=9)
        # Y no es el acumulado desde el frame 0, que es casi el doble.
        self.assertLess(detalles["impulso neto"], acumulado_al_final * 0.75)

    def test_sin_masa_explica_que_falta(self):
        with self.assertRaises(formulas.ErrorFormula) as contexto:
            formulas.impulso([700.0, 700.0], None, self.G, self.FRECUENCIA)
        self.assertIn("masa", str(contexto.exception).lower())

    def test_sin_frecuencia_explica_que_falta(self):
        with self.assertRaises(formulas.ErrorFormula) as contexto:
            formulas.impulso([700.0, 700.0], self.MASA, self.G, 0)
        self.assertIn("frecuencia", str(contexto.exception).lower())

    def test_rango_de_una_sola_muestra_no_revienta(self):
        with self.assertRaises(formulas.ErrorFormula):
            formulas.impulso([700.0], self.MASA, self.G, self.FRECUENCIA)


class TestRegistroFormulas(unittest.TestCase):
    """El registro es lo único que hay que tocar para sumar una fórmula."""

    def test_el_impulso_esta_registrado(self):
        self.assertTrue(formulas.hay_formula("impulso"))
        descripcion = formulas.descripcion_formula("impulso")
        self.assertEqual(descripcion["nombre"], formulas.NOMBRE_IMPULSO)
        self.assertEqual(descripcion["unidad"], formulas.UNIDAD_IMPULSO)

    def test_cada_formula_declara_lo_que_la_interfaz_necesita(self):
        for clave, descripcion in formulas.FORMULAS.items():
            with self.subTest(formula=clave):
                self.assertTrue(descripcion["nombre"])
                self.assertTrue(descripcion["unidad"])
                self.assertTrue(callable(descripcion["computar"]))
                self.assertIn(descripcion["salida_rol"], formulas.ROLES)

    def test_la_potencia_sigue_siendo_la_predeterminada(self):
        # El combo abre en la primera del registro; que no cambie sin querer.
        self.assertEqual(formulas.formula_predeterminada(), "potencia")

    def test_aplicar_impulso_no_reemplaza_la_potencia(self):
        aplicaciones = formulas.registrar_aplicacion_formula(
            {}, {"clave": "potencia", "rangos": ["Fz::1", "Fz::3"]}
        )
        aplicaciones = formulas.registrar_aplicacion_formula(
            aplicaciones,
            {"clave": "impulso", "rangos": ["Fz::2", "Fz::4"]},
        )

        self.assertEqual(
            aplicaciones["potencia"]["rangos"], ["Fz::1", "Fz::3"]
        )
        self.assertEqual(
            aplicaciones["impulso"]["rangos"], ["Fz::2", "Fz::4"]
        )

    def test_reaplicar_una_formula_agrega_rangos_sin_borrar_los_anteriores(self):
        aplicaciones = {
            "potencia": {
                "clave": "potencia",
                "rangos": ["Fz::1", "Fz::2"],
            },
            "impulso": {"clave": "impulso", "rangos": ["Fz::4"]},
        }
        aplicaciones = formulas.registrar_aplicacion_formula(
            aplicaciones,
            {"clave": "potencia", "rangos": ["Fz::3", "Fz::3"]},
        )

        self.assertEqual(aplicaciones["impulso"]["rangos"], ["Fz::4"])
        self.assertEqual(
            aplicaciones["potencia"]["rangos"],
            ["Fz::1", "Fz::2", "Fz::3"],
        )
        self.assertEqual(list(aplicaciones), ["impulso", "potencia"])

    def test_cada_formula_conserva_su_curva_visual_al_agregar_otra(self):
        potencia_y = np.array([10.0, 40.0, 20.0])
        impulso_y = np.array([900.0, 1200.0, 950.0])
        calculos = {
            "potencia": {
                "datos_panel": {"nombre": "Potencia", "unidad": "W"},
                "por_grafica": {
                    "Fz": {
                        "segmentos": [(np.array([1, 2, 3]), potencia_y)],
                        "resultados": [],
                    }
                },
            },
            "impulso": {
                "datos_panel": {"nombre": "Impulso", "unidad": "N·s"},
                "por_grafica": {
                    "Fz": {
                        "segmentos": [(np.array([4, 5, 6]), impulso_y)],
                        "resultados": [],
                    }
                },
            },
        }

        potencia_sola = formulas.preparar_curvas_formulas_por_grafica(
            calculos, ["potencia"]
        )["Fz"][0]
        juntas = formulas.preparar_curvas_formulas_por_grafica(
            calculos, ["potencia", "impulso"]
        )["Fz"]

        self.assertEqual([curva["clave"] for curva in juntas], ["potencia", "impulso"])
        np.testing.assert_array_equal(juntas[0]["y"], potencia_sola["y"])
        np.testing.assert_array_equal(juntas[1]["y"], impulso_y)

    def test_solo_el_impulso_trae_detalles(self):
        # La potencia se describe con pico y media; el impulso necesita los suyos.
        self.assertIsNone(formulas.FORMULAS["potencia"].get("detalles"))
        self.assertTrue(callable(formulas.FORMULAS["impulso"]["detalles"]))

    def test_el_impulso_necesita_masa_y_fz(self):
        motivo = formulas.validar_formula("impulso", {"masa": 70.0}, roles_disponibles=())
        self.assertIn("Fz", motivo)
        motivo = formulas.validar_formula(
            "impulso", {"masa": 0, "gravedad": 9.8, "frecuencia": 100.0},
            roles_disponibles=("Fz",),
        )
        self.assertIn("masa", motivo.lower())


class TestConstructorFormulas(unittest.TestCase):
    def test_los_roles_tienen_nombres_entendibles(self):
        self.assertEqual(formulas.NOMBRES_ROLES["Fx"], "Fuerza en X")
        self.assertEqual(formulas.NOMBRES_ROLES["Fz"], "Fuerza en Z")
        self.assertEqual(
            formulas.NOMBRES_ROLES["Cx"], "Centro de presión en X"
        )
        self.assertEqual(
            formulas.nombre_variable_constructor("Fz"),
            "Fz (fuerza en z)",
        )

    def test_ofrece_unidades_con_simbolos_dificiles(self):
        unidades = {valor for _etiqueta, valor in formulas.UNIDADES_CONSTRUCTOR}
        self.assertIn("N·s", unidades)
        self.assertIn("N·m", unidades)
        self.assertIn("N·mm", unidades)
        self.assertIn("m/s²", unidades)
        self.assertIn("µV", unidades)

    def test_normaliza_unidades_escritas_con_el_teclado(self):
        self.assertEqual(formulas.normalizar_unidad_formula("N*s"), "N·s")
        self.assertEqual(formulas.normalizar_unidad_formula("N.s"), "N·s")
        self.assertEqual(formulas.normalizar_unidad_formula("N.mm"), "N·mm")
        self.assertEqual(formulas.normalizar_unidad_formula("m/s^2"), "m/s²")
        self.assertEqual(formulas.normalizar_unidad_formula("uV"), "µV")

    def test_los_calculos_auxiliares_son_formulas_validas(self):
        disponibles = formulas.calculos_reutilizables()
        auxiliares = [d for d in disponibles if d["tipo"] == "Cálculo auxiliar"]

        self.assertEqual(len(auxiliares), 3)
        self.assertIn("Velocidad vertical", {d["nombre"] for d in auxiliares})
        for calculo in auxiliares:
            with self.subTest(calculo=calculo["nombre"]):
                analisis = formulas.analizar_expresion_personalizada(
                    calculo["expresion"]
                )
                self.assertIn("Fz", analisis["variables"])

    def test_la_velocidad_reutilizada_permite_construir_potencia(self):
        velocidad = next(
            calculo
            for calculo in formulas.calculos_reutilizables()
            if calculo["clave"] == "aux_velocidad_vertical"
        )
        expresion = f"Fz * ({velocidad['expresion']})"
        fz = np.array([700.0, 840.0, 980.0, 1120.0])
        variables = {"Fz": fz, "masa": 70.0, "gravedad": 10.0}

        construida = formulas.evaluar_expresion_personalizada(
            expresion, variables, frecuencia=100.0
        )
        esperada = formulas.potencia(fz, 70.0, 10.0, 100.0)

        np.testing.assert_allclose(construida, esperada)

    def test_puede_copiar_una_formula_personalizada_dentro_de_otra(self):
        clave = "formula_reutilizable_test"
        formulas.registrar_formula_personalizada(
            {
                "clave": clave,
                "nombre": "Fuerza duplicada de prueba",
                "expresion": "Fz * 2",
                "unidad": "N",
            }
        )
        try:
            disponibles = formulas.calculos_reutilizables()
            reutilizable = next(d for d in disponibles if d["clave"] == clave)

            self.assertEqual(reutilizable["expresion"], "Fz * 2")
            self.assertEqual(reutilizable["tipo"], "Fórmula propia")
            compuesta = f"({reutilizable['expresion']}) + Fz"
            salida = formulas.evaluar_expresion_personalizada(
                compuesta, {"Fz": np.array([1.0, 2.0])}
            )
            np.testing.assert_allclose(salida, [3.0, 6.0])
        finally:
            formulas.quitar_formula_personalizada(clave)

    def test_solo_reutiliza_la_formula_marcada_y_conserva_su_nombre(self):
        clave_visible = "formula_reutilizable_visible_test"
        clave_oculta = "formula_reutilizable_oculta_test"
        nombre = "Índice vertical — sujeto A"
        formulas.registrar_formula_personalizada(
            {
                "clave": clave_visible,
                "nombre": nombre,
                "expresion": "Fz / 2",
                "unidad": "N",
                "reutilizable": True,
            }
        )
        formulas.registrar_formula_personalizada(
            {
                "clave": clave_oculta,
                "nombre": "Solo para resultados",
                "expresion": "Fz * 3",
                "unidad": "N",
                "reutilizable": False,
            }
        )
        try:
            disponibles = {
                calculo["clave"]: calculo
                for calculo in formulas.calculos_reutilizables()
            }

            self.assertEqual(disponibles[clave_visible]["nombre"], nombre)
            self.assertNotIn(clave_oculta, disponibles)
        finally:
            formulas.quitar_formula_personalizada(clave_visible)
            formulas.quitar_formula_personalizada(clave_oculta)

    def test_al_editar_no_ofrece_insertar_la_misma_formula(self):
        clave = "formula_excluida_test"
        formulas.registrar_formula_personalizada(
            {
                "clave": clave,
                "nombre": "Fórmula excluida de prueba",
                "expresion": "senal * 2",
                "unidad": "",
            }
        )
        try:
            claves = {
                calculo["clave"]
                for calculo in formulas.calculos_reutilizables(clave)
            }
            self.assertNotIn(clave, claves)
        finally:
            formulas.quitar_formula_personalizada(clave)


class TestResumenFormula(unittest.TestCase):
    def test_encuentra_el_pico_y_su_posicion(self):
        x = np.array([10.0, 11.0, 12.0, 13.0])
        y = np.array([1.0, 9.0, 4.0, 2.0])

        datos = formulas.resumen(x, y)

        self.assertEqual(datos["pico"], 9.0)
        self.assertEqual(datos["x_pico"], 11.0)
        self.assertEqual(datos["minimo"], 1.0)
        self.assertEqual(datos["muestras"], 4)
        self.assertAlmostEqual(datos["media"], 4.0)

    def test_ignora_los_nan(self):
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([np.nan, 5.0, np.nan])

        datos = formulas.resumen(x, y)

        self.assertEqual((datos["pico"], datos["x_pico"], datos["muestras"]), (5.0, 2.0, 1))

    def test_senal_toda_invalida_no_revienta(self):
        datos = formulas.resumen([1.0, 2.0], [np.nan, np.nan])
        self.assertIsNone(datos["pico"])
        self.assertEqual(datos["muestras"], 0)

    def test_formatea_sin_notacion_cientifica(self):
        # 1138 N se veía como «1.14e+03» con %g: justo el caso más común.
        self.assertEqual(formulas.formatear_valor(1138.02), "1 138.0")
        self.assertEqual(formulas.formatear_valor(12.5), "12.50")
        self.assertEqual(formulas.formatear_valor(0.18085), "0.1809")
        self.assertEqual(formulas.formatear_valor(0), "0")
        self.assertEqual(formulas.formatear_valor(None), "—")
        self.assertEqual(formulas.formatear_valor(float("nan")), "—")
        self.assertNotIn("e", formulas.formatear_valor(1234567.0))


class TestPaleta(unittest.TestCase):
    def tearDown(self):
        paleta.set_modo_daltonico(False)

    def test_cambia_la_paleta_y_avisa_solo_si_hubo_cambio(self):
        self.assertFalse(paleta.modo_daltonico_activo())
        self.assertTrue(paleta.set_modo_daltonico(True))
        self.assertFalse(paleta.set_modo_daltonico(True))
        self.assertTrue(paleta.modo_daltonico_activo())
        self.assertNotEqual(
            paleta.color_senal_filtrada(),
            paleta.PALETAS[paleta.MODO_ESTANDAR]["senal_filtrada"],
        )

    def test_colores_de_rango_son_deterministicos_y_ciclan(self):
        colores = paleta.colores_rangos()
        self.assertEqual(paleta.color_rango(1), colores[0])
        self.assertEqual(paleta.color_rango(len(colores) + 1), colores[0])

    def test_recolorear_ida_y_vuelta_devuelve_los_colores_originales(self):
        gestor = GestorRangos()
        gestor.agregar(10, 20)
        gestor.agregar(30, 40)
        originales = [rango.color for rango in gestor.listar()]

        paleta.set_modo_daltonico(True)
        gestor.recolorear()
        daltonicos = [rango.color for rango in gestor.listar()]

        paleta.set_modo_daltonico(False)
        gestor.recolorear()

        self.assertNotEqual(daltonicos, originales)
        self.assertEqual([rango.color for rango in gestor.listar()], originales)
        # Recolorear no toca los datos del rango.
        self.assertEqual(
            [(r.numero, r.desde, r.hasta) for r in gestor.listar()],
            [(1, 10, 20), (2, 30, 40)],
        )

    def test_la_paleta_accesible_no_repite_colores(self):
        colores = paleta.PALETAS[paleta.MODO_DALTONICO]["rangos"]
        self.assertEqual(len(colores), len(set(colores)))

    def test_nuevos_modos_y_modo_visual_desconocido(self):
        # La paleta rojo-verde es la misma Okabe-Ito del modo histórico.
        self.assertEqual(paleta.MODO_DALTONICO, paleta.MODO_ROJO_VERDE)
        self.assertIn(paleta.MODO_COMPLETO, paleta.PALETAS)
        self.assertIn(paleta.MODO_AZUL_AMARILLO, paleta.PALETAS)
        # Un modo desconocido no cambia la paleta activa.
        actual = paleta.modo_actual()
        self.assertFalse(paleta.set_modo_visual("no_existe"))
        self.assertEqual(paleta.modo_actual(), actual)

    def test_modo_completo_es_una_rampa_de_grises_sin_repetir(self):
        paleta.set_modo_visual(paleta.MODO_COMPLETO)
        try:
            grises = paleta.colores_rangos()
            self.assertEqual(len(grises), len(set(grises)))
            # Todos son grises (R == G == B).
            for hex_color in grises:
                valor = hex_color[1:]
                rojo = int(valor[0:2], 16)
                verde = int(valor[2:4], 16)
                azul = int(valor[4:6], 16)
                self.assertEqual((rojo, verde), (azul, azul))
        finally:
            paleta.set_modo_visual(paleta.MODO_ESTANDAR)

    def test_nombre_color_resuelve_y_falla_de_grado(self):
        self.assertEqual(paleta.nombre_color("#42A5F5"), "azul")
        # Acepta minúsculas y sin numeral.
        self.assertEqual(paleta.nombre_color("42a5f5"), "azul")
        # Un color no conocido devuelve el propio valor.
        self.assertEqual(paleta.nombre_color("#123456"), "#123456")

    def test_paleta_azul_amarillo_esta_definida_y_sin_repetir(self):
        colores = paleta.PALETAS[paleta.MODO_AZUL_AMARILLO]
        rangos = colores["rangos"]
        self.assertEqual(len(rangos), len(set(rangos)))
        # Todos los colores usados tienen nombre humano para el tooltip.
        usados = list(rangos) + [colores["senal_original"], colores["senal_filtrada"],
                                 colores["senal_formula"], colores["seleccion"]]
        for hex_color in usados:
            self.assertIn(hex_color.upper(), paleta.NOMBRES_COLOR)


class TestAccesibilidad(unittest.TestCase):
    def setUp(self):
        accesibilidad.reiniciar()
        paleta.set_modo_visual(paleta.MODO_ESTANDAR)

    def tearDown(self):
        accesibilidad.reiniciar()
        paleta.set_modo_visual(paleta.MODO_ESTANDAR)

    def test_por_defecto_el_modo_esta_desactivado_y_sin_tipo(self):
        self.assertFalse(accesibilidad.activo())
        self.assertIsNone(accesibilidad.tipo_vision())
        # Las opciones adicionales vienen activas por defecto.
        self.assertTrue(accesibilidad.mostrar_nombre_color())
        self.assertTrue(accesibilidad.estilos_linea_activos())
        self.assertTrue(accesibilidad.aumentar_grosor_activo())

    def test_desactivado_se_comporta_como_hoy(self):
        # Grosor base, línea sólida y paleta estándar sin importar las opciones.
        self.assertEqual(accesibilidad.grosor_senal("original"), 1.2)
        self.assertEqual(accesibilidad.grosor_senal("filtrada"), 2.2)
        self.assertEqual(accesibilidad.grosor_rango(), 2.0)
        for tipo in (accesibilidad.TIPO_LINEA_ORIGINAL,
                     accesibilidad.TIPO_LINEA_FILTRADA,
                     accesibilidad.TIPO_LINEA_FORMULA):
            self.assertEqual(accesibilidad.estilo_linea(tipo), accesibilidad.ESTILO_SOLIDA)
        self.assertEqual(paleta.modo_actual(), paleta.MODO_ESTANDAR)

    def test_activar_con_tipo_sincroniza_la_paleta(self):
        accesibilidad.set_tipo_vision(accesibilidad.TIPO_ROJO_VERDE)
        # Con el modo apagado el tipo no cambia la paleta.
        self.assertEqual(paleta.modo_actual(), paleta.MODO_ESTANDAR)
        accesibilidad.set_activo(True)
        self.assertEqual(paleta.modo_actual(), paleta.MODO_ROJO_VERDE)
        accesibilidad.set_tipo_vision(accesibilidad.TIPO_COMPLETO)
        self.assertEqual(paleta.modo_actual(), paleta.MODO_COMPLETO)
        accesibilidad.set_activo(False)
        self.assertEqual(paleta.modo_actual(), paleta.MODO_ESTANDAR)

    def test_azul_amarillo_es_un_tipo_disponible_y_sincroniza_la_paleta(self):
        self.assertIn(accesibilidad.TIPO_AZUL_AMARILLO, accesibilidad.TIPOS_DISPONIBLES)
        accesibilidad.set_activo(True)
        accesibilidad.set_tipo_vision(accesibilidad.TIPO_AZUL_AMARILLO)
        self.assertEqual(paleta.modo_actual(), paleta.MODO_AZUL_AMARILLO)
        # Las opciones de renderizado aplican igual que en los otros tipos.
        self.assertEqual(accesibilidad.grosor_senal("original"), round(1.2 * 1.7, 2))
        self.assertEqual(accesibilidad.estilo_linea("formula"), accesibilidad.ESTILO_DISCONTINUA)

    def test_tipo_desconocido_no_cambia_nada(self):
        accesibilidad.set_activo(True)
        accesibilidad.set_tipo_vision(accesibilidad.TIPO_ROJO_VERDE)
        accesibilidad.set_tipo_vision("no_existe")
        self.assertEqual(accesibilidad.tipo_vision(), accesibilidad.TIPO_ROJO_VERDE)
        self.assertEqual(paleta.modo_actual(), paleta.MODO_ROJO_VERDE)

    def test_opciones_adicionales_son_independientes(self):
        accesibilidad.set_activo(True)
        accesibilidad.set_tipo_vision(accesibilidad.TIPO_ROJO_VERDE)
        # Desactivar solo el grosor: los estilos se mantienen.
        accesibilidad.set_aumentar_grosor(False)
        self.assertEqual(accesibilidad.grosor_senal("original"), 1.2)
        self.assertEqual(accesibilidad.estilo_linea("original"), accesibilidad.ESTILO_PUNTEADA)
        # Desactivar solo los estilos: el grosor sigue en su estado (base).
        accesibilidad.set_estilos_linea(False)
        self.assertEqual(accesibilidad.estilo_linea("original"), accesibilidad.ESTILO_SOLIDA)
        self.assertEqual(accesibilidad.estilo_linea("filtrada"), accesibilidad.ESTILO_SOLIDA)
        self.assertEqual(accesibilidad.grosor_senal("filtrada"), 2.2)
        # Reactivar el grosor sin tocar los estilos: ampliado y sigue sólido.
        accesibilidad.set_aumentar_grosor(True)
        self.assertGreater(accesibilidad.grosor_senal("filtrada"), 2.2)
        self.assertEqual(accesibilidad.estilo_linea("original"), accesibilidad.ESTILO_SOLIDA)
        # Reactivar los estilos.
        accesibilidad.set_estilos_linea(True)
        self.assertEqual(accesibilidad.estilo_linea("formula"), accesibilidad.ESTILO_DISCONTINUA)

    def test_grosor_y_estilo_con_modo_activo(self):
        accesibilidad.set_activo(True)
        accesibilidad.set_tipo_vision(accesibilidad.TIPO_COMPLETO)
        self.assertEqual(accesibilidad.grosor_senal("original"), round(1.2 * 1.7, 2))
        self.assertEqual(accesibilidad.grosor_rango(), round(2.0 * 1.7, 2))
        self.assertEqual(accesibilidad.estilo_linea("original"), accesibilidad.ESTILO_PUNTEADA)
        self.assertEqual(accesibilidad.estilo_linea("filtrada"), accesibilidad.ESTILO_SOLIDA)
        self.assertEqual(accesibilidad.estilo_linea("formula"), accesibilidad.ESTILO_DISCONTINUA)

    def test_la_opcion_de_nombre_es_un_flag_independiente_del_modo(self):
        accesibilidad.set_mostrar_nombre_color(False)
        self.assertFalse(accesibilidad.mostrar_nombre_color())
        accesibilidad.set_activo(True)
        # Con el modo activo y la opción apagada no se muestra.
        self.assertFalse(accesibilidad.mostrar_nombre_color())
        accesibilidad.set_mostrar_nombre_color(True)
        self.assertTrue(accesibilidad.mostrar_nombre_color())


class TestProyecto(unittest.TestCase):
    def test_sanea_nombres_invalidos_en_windows(self):
        self.assertEqual(proyecto.sanear_nombre(' Salto: prueba/1 '), "Salto_ prueba_1")
        self.assertEqual(proyecto.sanear_nombre("marcha.CSV"), "marcha")
        self.assertEqual(proyecto.sanear_nombre("  ...  "), "")

    def test_ida_y_vuelta_de_anotaciones(self):
        filas = [
            {
                "tipo": "rango", "senal": "Fuerza X - Fx", "columna": "Fx",
                "numero": 1, "padre": "", "desde": 1, "hasta": 297,
                "nombre": "Rango 1", "nota": "El usuario está sentado",
                "fuente": "original",
            },
            {
                "tipo": "subrango", "senal": "Fuerza X - Fx", "columna": "Fx",
                "numero": 1, "padre": "Fx::1", "desde": 10, "hasta": 50,
                "nombre": "Rango 1", "nota": "", "fuente": "",
            },
        ]

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "prueba_anotaciones.csv"
            proyecto.escribir_anotaciones(ruta, filas)
            leidas = proyecto.leer_anotaciones(ruta)

        self.assertEqual(leidas, filas)

    def test_conserva_la_procedencia_de_los_datos(self):
        filas = [
            {
                "tipo": "rango", "senal": "Fuerza X - Fx", "columna": "Fx",
                "numero": 1, "padre": "", "desde": 1, "hasta": 297,
                "nombre": "Rango 1", "nota": "", "fuente": "filtrada",
            },
        ]

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "anotaciones.csv"
            proyecto.escribir_anotaciones(ruta, filas)
            leidas = proyecto.leer_anotaciones(ruta)

        self.assertEqual(leidas[0]["fuente"], "filtrada")

    def test_lee_archivos_viejos_sin_columna_fuente(self):
        # Formato anterior: los proyectos ya guardados no tienen «fuente».
        contenido = (
            "tipo,senal,columna,numero,padre,desde,hasta,nombre,nota\n"
            "rango,Fuerza X - Fx,Fx,1,,1,297,Rango 1,El usuario esta sentado\n"
        )

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "anotaciones.csv"
            ruta.write_text(contenido, encoding="utf-8-sig")
            leidas = proyecto.leer_anotaciones(ruta)

        self.assertEqual(len(leidas), 1)
        self.assertEqual(leidas[0]["fuente"], "")
        self.assertEqual(leidas[0]["nota"], "El usuario esta sentado")

    def test_descarta_filas_corruptas(self):
        contenido = (
            "tipo,senal,columna,numero,padre,desde,hasta,nombre,nota\n"
            "rango,Fuerza X - Fx,Fx,1,,1,297,Rango 1,ok\n"
            "rango,Fuerza X - Fx,Fx,dos,,1,297,Rango 2,numero invalido\n"
            "basura,Fuerza X - Fx,Fx,3,,1,297,Rango 3,tipo invalido\n"
            "rango,Fuerza X - Fx,,4,,1,297,Rango 4,sin columna\n"
        )

        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "anotaciones.csv"
            ruta.write_text(contenido, encoding="utf-8-sig")
            leidas = proyecto.leer_anotaciones(ruta)

        self.assertEqual([fila["numero"] for fila in leidas], [1])

    def test_sin_archivo_de_anotaciones_devuelve_vacio(self):
        with tempfile.TemporaryDirectory() as carpeta:
            self.assertEqual(
                proyecto.leer_anotaciones(Path(carpeta) / "no_existe.csv"), []
            )


class TestLimpiezaProyectos(unittest.TestCase):
    AHORA = datetime(2026, 7, 27, 15, 0, 0)

    def _proyecto(self, nombre, dias_atras=0, horas_atras=0):
        momento = self.AHORA - timedelta(days=dias_atras, hours=horas_atras)
        return {"nombre": nombre, "modificado": momento.timestamp(), "tamano": 100}

    def test_hoy_va_desde_la_medianoche_no_las_ultimas_24_horas(self):
        proyectos = [
            self._proyecto("de_esta_manana", horas_atras=14),  # 01:00 de hoy
            self._proyecto("de_anoche", horas_atras=20),  # 19:00 de ayer
        ]

        elegidos = proyecto.filtrar_por_periodo(
            proyectos, proyecto.PERIODO_HOY, ahora=self.AHORA
        )

        self.assertEqual([p["nombre"] for p in elegidos], ["de_esta_manana"])

    def test_cada_ventana_incluye_solo_lo_suficientemente_reciente(self):
        proyectos = [
            self._proyecto("hoy"),
            self._proyecto("hace_5_dias", dias_atras=5),
            self._proyecto("hace_20_dias", dias_atras=20),
            self._proyecto("hace_200_dias", dias_atras=200),
            self._proyecto("hace_2_anios", dias_atras=730),
        ]

        def nombres(periodo):
            return [
                p["nombre"]
                for p in proyecto.filtrar_por_periodo(
                    proyectos, periodo, ahora=self.AHORA
                )
            ]

        self.assertEqual(nombres(proyecto.PERIODO_SEMANA), ["hoy", "hace_5_dias"])
        self.assertEqual(
            nombres(proyecto.PERIODO_MES), ["hoy", "hace_5_dias", "hace_20_dias"]
        )
        self.assertEqual(
            nombres(proyecto.PERIODO_ANIO),
            ["hoy", "hace_5_dias", "hace_20_dias", "hace_200_dias"],
        )
        self.assertEqual(len(nombres(proyecto.PERIODO_TODOS)), 5)

    def test_elegir_archivo_no_preselecciona_nada(self):
        proyectos = [self._proyecto("uno"), self._proyecto("dos")]
        self.assertEqual(
            proyecto.filtrar_por_periodo(
                proyectos, proyecto.PERIODO_ARCHIVO, ahora=self.AHORA
            ),
            [],
        )

    def test_periodo_desconocido_falla(self):
        with self.assertRaises(ValueError):
            proyecto.filtrar_por_periodo([], "el_mes_pasado", ahora=self.AHORA)

    def test_elimina_el_csv_y_sus_anotaciones(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with mock.patch.object(
                proyecto, "carpeta_archivos", return_value=carpeta
            ):
                for nombre in ("marcha", "salto"):
                    Path(proyecto.ruta_csv(nombre)).write_text("x", encoding="utf-8")
                    Path(proyecto.ruta_anotaciones(nombre)).write_text(
                        "x", encoding="utf-8"
                    )

                eliminados, errores = proyecto.eliminar_proyectos(["marcha"])

                self.assertEqual(eliminados, ["marcha"])
                self.assertEqual(errores, [])
                self.assertFalse(os.path.exists(proyecto.ruta_csv("marcha")))
                self.assertFalse(
                    os.path.exists(proyecto.ruta_anotaciones("marcha"))
                )
                # El otro proyecto queda intacto.
                self.assertTrue(os.path.exists(proyecto.ruta_csv("salto")))

    def test_elimina_aunque_no_haya_archivo_de_anotaciones(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with mock.patch.object(
                proyecto, "carpeta_archivos", return_value=carpeta
            ):
                Path(proyecto.ruta_csv("suelto")).write_text("x", encoding="utf-8")

                eliminados, errores = proyecto.eliminar_proyectos(["suelto"])

                self.assertEqual((eliminados, errores), (["suelto"], []))

    def test_ignora_nombres_que_no_existen(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with mock.patch.object(
                proyecto, "carpeta_archivos", return_value=carpeta
            ):
                self.assertEqual(
                    proyecto.eliminar_proyectos(["fantasma"]), ([], [])
                )

    def test_no_sale_de_la_carpeta_de_archivos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            afuera = Path(carpeta).parent / "no_tocar.csv"
            afuera.write_text("importante", encoding="utf-8")
            interna = Path(carpeta) / "archivos"
            interna.mkdir()

            with mock.patch.object(
                proyecto, "carpeta_archivos", return_value=str(interna)
            ):
                eliminados, errores = proyecto.eliminar_proyectos(
                    [os.path.join("..", "no_tocar")]
                )

            self.assertEqual(eliminados, [])
            self.assertEqual(len(errores), 1)
            self.assertTrue(afuera.exists())

    def test_formatea_tamanos_legibles(self):
        self.assertEqual(proyecto.formatear_tamano(512), "512 B")
        self.assertEqual(proyecto.formatear_tamano(2048), "2,0 KB")
        self.assertEqual(proyecto.formatear_tamano(5 * 1024 * 1024), "5,0 MB")


if __name__ == "__main__":
    unittest.main()
