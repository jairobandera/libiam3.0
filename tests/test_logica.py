import unittest
from pathlib import Path

import numpy as np

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


if __name__ == "__main__":
    unittest.main()
