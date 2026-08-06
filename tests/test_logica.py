import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import numpy as np

from logica import formulas, paleta, proyecto
from logica.filtros_senales import (
    ErrorConfiguracionFiltro,
    aplicar_butterworth,
    aplicar_butterworth_pasabajos,
)
from logica.lector_csv import leer_csv_rapido
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
