import codecs
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from logica import exportacion


class TestExportacion(unittest.TestCase):
    def setUp(self):
        self.original = pd.DataFrame(
            {
                "Frame": [0, 1, 2, 3],
                "Fz": [100.0, 200.0, 300.0, 400.0],
                "Fx": [1.0, 2.0, 3.0, 4.0],
            }
        )
        self.filtrado = self.original.copy()
        self.filtrado["Fz"] = [110.0, 190.0, 310.0, 390.0]

    def test_datos_conservan_original_y_separan_filtro_y_formula(self):
        tabla = exportacion.preparar_datos(
            self.original,
            self.filtrado,
            "Frame",
            ["Fz", "Fx"],
            {"Fz"},
            [
                {
                    "senal": "Fuerza Z",
                    "nombre": "Potencia",
                    "unidad": "W",
                    "x": np.array([1.0, 2.0]),
                    "y": np.array([12.5, 18.0]),
                }
            ],
        )

        self.assertEqual(
            tabla.columns.tolist(),
            ["Frame", "Fz", "Fz [filtrada]", "Fx", "Fuerza Z - Potencia (W)"],
        )
        self.assertEqual(tabla["Fz"].tolist(), [100.0, 200.0, 300.0, 400.0])
        self.assertEqual(tabla["Fz [filtrada]"].tolist(), [110.0, 190.0, 310.0, 390.0])
        self.assertTrue(np.isnan(tabla.loc[0, "Fuerza Z - Potencia (W)"]))
        self.assertEqual(tabla.loc[2, "Fuerza Z - Potencia (W)"], 18.0)

    def test_datos_pueden_usar_nombres_visibles_y_unidades(self):
        tabla = exportacion.preparar_datos(
            self.original,
            self.filtrado,
            "Frame",
            ["Fz", "Fx"],
            {"Fz"},
            nombres={"Fz": "Fuerza Z", "Fx": "Fuerza X"},
            unidades={"Fz": "N", "Fx": "N"},
        )

        self.assertEqual(
            tabla.columns.tolist(),
            [
                "Frame",
                "Fuerza Z (N)",
                "Fuerza Z (N) [filtrada]",
                "Fuerza X (N)",
            ],
        )

    def test_datos_pueden_limitarse_a_recortes_especificos(self):
        tabla = exportacion.preparar_datos(
            self.original,
            columna_x="Frame",
            columnas=["Fz", "Fx"],
            intervalos=[
                {"id": "Fz::1", "desde": 1, "hasta": 1},
                {"id": "Fx::2", "desde": 3, "hasta": 3},
            ],
        )

        self.assertEqual(tabla["Frame"].tolist(), [1, 3])
        self.assertEqual(tabla["Fz"].tolist(), [200.0, 400.0])

    def test_todo_conserva_cada_intervalo_sin_mirar_selecciones_externas(self):
        intervalos = [
            {"id": "Fz::1", "seleccionado_calculo": True},
            {"id": "Fx::1", "seleccionado_calculo": False},
            {"id": "Fy::1", "seleccionado_calculo": False},
        ]

        exportados = exportacion.filtrar_intervalos(intervalos, None)

        self.assertEqual(
            [intervalo["id"] for intervalo in exportados],
            ["Fz::1", "Fx::1", "Fy::1"],
        )

    def test_intervalos_exportan_sus_muestras_y_notas(self):
        intervalos = [
            {
                "id": "Fz::1",
                "numero": 1,
                "senal": "Fuerza Z",
                "columna": "Fz",
                "desde": 1,
                "hasta": 2,
                "nombre": "Salto",
                "nota": "Intento válido",
                "fuente": "filtrada",
                "es_subintervalo": False,
            }
        ]
        tabla = exportacion.preparar_muestras_intervalos(
            intervalos, self.original, self.filtrado, "Frame", {"Fz"}
        )

        self.assertEqual(tabla["Frame"].tolist(), [1, 2])
        self.assertEqual(tabla["Valor original"].tolist(), [200.0, 300.0])
        self.assertEqual(tabla["Valor filtrado"].tolist(), [190.0, 310.0])
        self.assertEqual(tabla["Nota"].tolist(), ["Intento válido", "Intento válido"])
        self.assertEqual(tabla.loc[0, "Datos utilizados"], "Señal filtrada")

    def test_resultados_incluyen_resumen_y_detalles(self):
        tabla = exportacion.preparar_resultados_formula(
            {
                "nombre": "Impulso",
                "expresion": "J = integral(Fz)",
                "unidad": "N·s",
                "fuente": "filtrada",
                "detalle_filtro": "pasa-bajos 20 Hz",
                "advertencias": ["Ejemplo"],
                "resultados": [
                    {
                        "id": "Fz::1",
                        "nombre": "Intervalo 1",
                        "senal": "Fuerza Z",
                        "desde": 1,
                        "hasta": 2,
                        "duracion_s": 0.004,
                        "resumen": {
                            "pico": 4.0,
                            "x_pico": 2,
                            "minimo": 0.0,
                            "x_minimo": 1,
                            "media": 2.0,
                            "rms": 2.8,
                            "muestras": 2,
                        },
                        "detalles": [
                            {"etiqueta": "impulso neto", "valor": 4.0, "unidad": "N·s"}
                        ],
                    },
                    {
                        "id": "Fz::2",
                        "nombre": "Intervalo 2",
                        "senal": "Fuerza Z",
                        "desde": 3,
                        "hasta": 4,
                        "duracion_s": 0.004,
                        "resumen": {"muestras": 2},
                        "detalles": [
                            {"etiqueta": "impulso neto", "valor": 6.0, "unidad": "N·s"}
                        ],
                    },
                ],
            }
        )

        self.assertEqual(tabla.loc[0, "Fórmula"], "Impulso")
        self.assertEqual(tabla.loc[0, "Muestras válidas"], 2)
        self.assertEqual(tabla.loc[0, "Impulso neto (N·s)"], 4.0)
        self.assertEqual(tabla.loc[1, "Impulso neto (N·s)"], 6.0)
        self.assertEqual(tabla.loc[0, "Promedio"], 2.0)
        self.assertEqual(tabla.loc[0, "Máximo"], 4.0)
        self.assertEqual(tabla.loc[0, "Frame del máximo"], 2)
        self.assertEqual(tabla.loc[0, "Datos utilizados"], "Señal filtrada")
        self.assertNotIn("Resultado", tabla.columns)
        self.assertNotIn("Impulso neto (N·s) (2)", tabla.columns)

    def test_resultados_de_curva_sin_detalles_incluyen_su_resumen(self):
        tabla = exportacion.preparar_resultados_formula(
            {
                "nombre": "Potencia",
                "expresion": "P = Fz · v",
                "unidad": "W",
                "fuente": "original",
                "resultados": [
                    {
                        "id": "Fz::1",
                        "nombre": "Intervalo 1",
                        "senal": "Fuerza Z",
                        "desde": 1,
                        "hasta": 2,
                        "duracion_s": 0.004,
                        "resumen": {
                            "pico": 420.0,
                            "x_pico": 2,
                            "minimo": 10.0,
                            "x_minimo": 1,
                            "media": 215.0,
                            "rms": 297.1,
                            "muestras": 2,
                        },
                    }
                ],
            }
        )

        self.assertEqual(tabla.loc[0, "Máximo"], 420.0)
        self.assertEqual(tabla.loc[0, "Frame del máximo"], 2)
        self.assertEqual(tabla.loc[0, "Promedio"], 215.0)
        self.assertNotIn("Resultado", tabla.columns)

    def test_exporta_juntas_varias_formulas_aplicadas(self):
        calculos = [
            {
                "nombre": "Potencia",
                "expresion": "P = Fz · v",
                "unidad": "W",
                "fuente": "original",
                "resultados": [
                    {
                        "id": "Fz::1",
                        "nombre": "Intervalo 1",
                        "senal": "Fuerza Z",
                        "desde": 1,
                        "hasta": 2,
                        "resumen": {"pico": 420.0, "x_pico": 2, "muestras": 2},
                    }
                ],
            },
            {
                "nombre": "Impulso",
                "expresion": "J = integral(Fz)",
                "unidad": "N·s",
                "fuente": "filtrada",
                "resultados": [
                    {
                        "id": "Fz::2",
                        "nombre": "Intervalo 2",
                        "senal": "Fuerza Z",
                        "desde": 3,
                        "hasta": 4,
                        "resumen": {"muestras": 2},
                        "detalles": [
                            {
                                "etiqueta": "impulso neto",
                                "valor": 6.0,
                                "unidad": "N·s",
                            }
                        ],
                    }
                ],
            },
        ]

        tabla = exportacion.preparar_resultados_formulas(calculos)

        self.assertEqual(tabla["Fórmula"].tolist(), ["Potencia", "Impulso"])
        self.assertEqual(tabla.loc[0, "Máximo"], 420.0)
        self.assertEqual(tabla.loc[1, "Impulso neto (N·s)"], 6.0)

    def test_resultados_pueden_filtrarse_por_recortes(self):
        calculos = [
            {
                "nombre": "Potencia",
                "resultados": [
                    {"id": "Fz::1", "nombre": "A", "resumen": {"media": 1}},
                    {"id": "Fz::2", "nombre": "B", "resumen": {"media": 2}},
                ],
            }
        ]

        filtrados = exportacion.filtrar_resultados_formulas(
            calculos,
            ["Fz::2"],
        )

        self.assertEqual(
            [resultado["id"] for resultado in filtrados[0]["resultados"]],
            ["Fz::2"],
        )
        self.assertEqual(len(calculos[0]["resultados"]), 2)

    def test_csv_usa_bom_y_el_paquete_es_integro(self):
        with tempfile.TemporaryDirectory() as carpeta:
            carpeta = Path(carpeta)
            csv = carpeta / "datos.csv"
            exportacion.escribir_csv(csv, self.original)
            self.assertTrue(csv.read_bytes().startswith(codecs.BOM_UTF8))
            self.assertIn("Frame;Fz;Fx", csv.read_text(encoding="utf-8-sig"))
            self.assertIn("100,0", csv.read_text(encoding="utf-8-sig"))
            leido = pd.read_csv(csv, sep=";", decimal=",")
            pd.testing.assert_frame_equal(leido, self.original)

            paquete = carpeta / "analisis.zip"
            exportacion.escribir_paquete(
                paquete,
                {"datos.csv": self.original, "intervalos.csv": pd.DataFrame()},
                "Información de prueba\n",
            )
            with zipfile.ZipFile(paquete) as archivo:
                self.assertIsNone(archivo.testzip())
                self.assertEqual(
                    set(archivo.namelist()),
                    {"datos.csv", "intervalos.csv", "informacion.txt"},
                )
                self.assertTrue(archivo.read("datos.csv").startswith(codecs.BOM_UTF8))

    def test_sobrescribe_csv_y_zip_exportados_previamente(self):
        with tempfile.TemporaryDirectory() as carpeta:
            carpeta = Path(carpeta)
            primera = pd.DataFrame({"valor": [1]})
            segunda = pd.DataFrame({"valor": [2]})

            csv = carpeta / "datos.csv"
            exportacion.escribir_csv(csv, primera)
            exportacion.escribir_csv(csv, segunda)
            leido = pd.read_csv(csv, sep=";", decimal=",")
            pd.testing.assert_frame_equal(leido, segunda)

            paquete = carpeta / "analisis.zip"
            exportacion.escribir_paquete(paquete, {"primero.csv": primera})
            exportacion.escribir_paquete(paquete, {"segundo.csv": segunda})
            with zipfile.ZipFile(paquete) as archivo:
                self.assertEqual(archivo.namelist(), ["segundo.csv"])
                self.assertIsNone(archivo.testzip())

    def test_usa_respaldo_si_el_reemplazo_atomico_es_rechazado(self):
        with tempfile.TemporaryDirectory() as carpeta:
            destino = Path(carpeta) / "datos.csv"
            destino.write_text("contenido anterior", encoding="utf-8")
            tabla = pd.DataFrame({"valor": [7]})

            with mock.patch(
                "logica.exportacion.os.replace",
                side_effect=PermissionError("reemplazo no permitido"),
            ):
                exportacion.escribir_csv(destino, tabla)

            leido = pd.read_csv(destino, sep=";", decimal=",")
            pd.testing.assert_frame_equal(leido, tabla)

    def test_resumen_del_paquete_es_legible(self):
        texto = exportacion.preparar_informacion(
            "salto.csv",
            "Frame",
            ["Fz"],
            unidades={"Fz": "N"},
            frecuencia=500,
            filtros={"Fz": "Pasa-bajos 20 Hz"},
            formula={
                "nombre": "Impulso",
                "expresion": "J = integral(F)",
                "unidad": "N·s",
                "fuente": "filtrada",
                "resultados": [{"valor": 4.0}],
            },
            nombres={"Fz": "Fuerza Z"},
        )

        self.assertIn("ABS 3.0 — Resumen de exportación", texto)
        self.assertIn("Fuerza Z [Fz] · N", texto)
        self.assertIn("Datos utilizados: Señal filtrada", texto)
        self.assertIn("separador ; · decimal ,", texto)

    def test_nombres_y_extensiones_son_seguros(self):
        self.assertEqual(exportacion.nombre_base("prueba:fuerza.csv"), "prueba_fuerza")
        self.assertEqual(exportacion.asegurar_extension("salida", ".csv"), "salida.csv")
        self.assertEqual(exportacion.asegurar_extension("salida.CSV", ".csv"), "salida.CSV")


if __name__ == "__main__":
    unittest.main()
