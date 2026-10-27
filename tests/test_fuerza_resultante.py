import unittest
import numpy as np

from logica import formulas


class TestFuerzaResultante(unittest.TestCase):

    def test_norma_tridimensional(self):
        fx = np.array([3.0, -3.0, 0.0, 1.0])
        fy = np.array([4.0, 4.0, 5.0, 2.0])
        fz = np.array([0.0, 12.0, 12.0, 2.0])
        esperado = np.sqrt(fx * fx + fy * fy + fz * fz)
        res = formulas._fuerza_resultante_desde({'Fx': fx, 'Fy': fy, 'Fz': fz}, {})
        np.testing.assert_allclose(res, esperado)

    def test_ceros_y_negativos(self):
        fx = np.array([-3.0])
        fy = np.array([4.0])
        fz = np.array([12.0])
        res = formulas._fuerza_resultante_desde({'Fx': fx, 'Fy': fy, 'Fz': fz}, {})
        self.assertAlmostEqual(res[0], 13.0)
        self.assertGreaterEqual(res[0], 0.0)

    def test_todos_cero(self):
        fx = np.array([0.0, 0.0])
        fy = np.array([0.0, 0.0])
        fz = np.array([0.0, 0.0])
        res = formulas._fuerza_resultante_desde({'Fx': fx, 'Fy': fy, 'Fz': fz}, {})
        np.testing.assert_allclose(res, [0.0, 0.0])

    def test_registro_existe_y_sin_masa_gravedad(self):
        self.assertIn('fuerza_resultante', formulas.FORMULAS)
        desc = formulas.FORMULAS['fuerza_resultante']
        self.assertEqual(desc['requiere_roles'], ('Fx', 'Fy', 'Fz'))
        self.assertFalse(desc['integra_en_registro'])
        self.assertNotIn('masa', desc.get('requiere', {}))
        self.assertNotIn('gravedad', desc.get('requiere', {}))
        self.assertEqual(desc['unidad'], 'N')

    def test_validacion_requiere_tres_roles(self):
        roles_disponibles = {'Fx', 'Fy'}  # faltan Fz
        msg = formulas.validar_formula('fuerza_resultante', {}, roles_disponibles)
        self.assertIsNotNone(msg)
        self.assertTrue(len(msg) > 0)

    def test_no_modifica_entradas(self):
        fx = np.array([1.0, 2.0, 3.0])
        fy = np.array([0.0, -1.0, 4.0])
        fz = np.array([5.0, 0.0, -2.0])
        fx_c = fx.copy()
        fy_c = fy.copy()
        fz_c = fz.copy()
        _ = formulas._fuerza_resultante_desde({'Fx': fx, 'Fy': fy, 'Fz': fz}, {})
        np.testing.assert_allclose(fx, fx_c)
        np.testing.assert_allclose(fy, fy_c)
        np.testing.assert_allclose(fz, fz_c)


COLUMNAS = {"Fx": "Fx", "Fy": "Fy", "Fz": "Fz"}


def _intervalo(columna, desde, hasta, numero=1, nombre=None):
    return {
        "columna": columna,
        "desde": desde,
        "hasta": hasta,
        "numero": numero,
        "nombre": nombre or f"Intervalo {numero}",
        "id": f"{columna}::{numero}",
        "senal": columna,
    }


class TestAgrupacionFuerzaResultante(unittest.TestCase):
    """Fase 2: la FR exige Fx, Fy y Fz con idénticos límites de frame."""

    def _agrupar(self, intervalos, columnas=None):
        return formulas.agrupar_intervalos_fuerza_resultante(
            intervalos, COLUMNAS if columnas is None else columnas
        )

    def test_tres_componentes_con_los_mismos_limites(self):
        grupos, advertencias = self._agrupar(
            [
                _intervalo("Fx", 10, 30),
                _intervalo("Fy", 10, 30),
                _intervalo("Fz", 10, 30),
            ]
        )
        self.assertEqual(len(grupos), 1)
        self.assertEqual((grupos[0]["desde"], grupos[0]["hasta"]), (10, 30))
        self.assertEqual(grupos[0]["componentes"], COLUMNAS)
        self.assertEqual(
            grupos[0]["ids_origen"],
            ["Fx::1", "Fy::1", "Fz::1"],
        )
        self.assertEqual(advertencias, [])

    def test_solo_fx_se_rechaza(self):
        grupos, advertencias = self._agrupar([_intervalo("Fx", 10, 30)])
        self.assertEqual(grupos, [])
        self.assertTrue(any("Fy" in aviso and "Fz" in aviso for aviso in advertencias))

    def test_solo_fy_se_rechaza(self):
        grupos, _ = self._agrupar([_intervalo("Fy", 10, 30)])
        self.assertEqual(grupos, [])

    def test_solo_fz_se_rechaza(self):
        grupos, _ = self._agrupar([_intervalo("Fz", 10, 30)])
        self.assertEqual(grupos, [])

    def test_fx_y_fy_sin_fz_se_rechaza(self):
        grupos, advertencias = self._agrupar(
            [_intervalo("Fx", 10, 30), _intervalo("Fy", 10, 30)]
        )
        self.assertEqual(grupos, [])
        self.assertTrue(any("Fz" in aviso for aviso in advertencias))

    def test_fx_y_fz_sin_fy_se_rechaza(self):
        grupos, _ = self._agrupar(
            [_intervalo("Fx", 10, 30), _intervalo("Fz", 10, 30)]
        )
        self.assertEqual(grupos, [])

    def test_fy_y_fz_sin_fx_se_rechaza(self):
        grupos, _ = self._agrupar(
            [_intervalo("Fy", 10, 30), _intervalo("Fz", 10, 30)]
        )
        self.assertEqual(grupos, [])

    def test_limites_de_frame_distintos_rechazan_el_grupo(self):
        grupos, advertencias = self._agrupar(
            [
                _intervalo("Fx", 10, 20),
                _intervalo("Fy", 10, 20),
                _intervalo("Fz", 30, 40),
            ]
        )
        self.assertEqual(grupos, [])
        # Un aviso por cada bloque incompleto (10–20 sin Fz y 30–40 sin Fx/Fy).
        self.assertEqual(len(advertencias), 2)
        self.assertTrue(any("Frame 10–20" in aviso for aviso in advertencias))
        self.assertTrue(any("Frame 30–40" in aviso for aviso in advertencias))

    def test_una_componente_sin_rol_mapeado_no_forma_grupo(self):
        grupos, advertencias = self._agrupar(
            [
                _intervalo("Fx", 10, 30),
                _intervalo("Fy", 10, 30),
                _intervalo("Fz", 10, 30),
            ],
            columnas={"Fx": "Fx", "Fy": "Fy", "Fz": None},
        )
        self.assertEqual(grupos, [])
        self.assertTrue(advertencias)

    def test_dos_grupos_completos_dan_dos_resultados(self):
        grupos, advertencias = self._agrupar(
            [
                _intervalo("Fx", 5, 10),
                _intervalo("Fy", 5, 10),
                _intervalo("Fz", 5, 10),
                _intervalo("Fx", 25, 30),
                _intervalo("Fy", 25, 30),
                _intervalo("Fz", 25, 30),
            ]
        )
        self.assertEqual(
            [(g["desde"], g["hasta"]) for g in grupos], [(5, 10), (25, 30)]
        )
        self.assertEqual(advertencias, [])

    def test_grupo_completo_mas_grupo_incompleto(self):
        grupos, advertencias = self._agrupar(
            [
                _intervalo("Fx", 5, 10),
                _intervalo("Fy", 5, 10),
                _intervalo("Fz", 5, 10),
                _intervalo("Fx", 25, 30),
                _intervalo("Fy", 25, 30),
                _intervalo("Fz", 25, 30),
                _intervalo("Fx", 50, 60),  # falta Fy y Fz
            ]
        )
        self.assertEqual(len(grupos), 2)
        self.assertEqual(len(advertencias), 1)
        self.assertIn("Frame 50–60", advertencias[0])

    def test_los_roles_se_resuelven_con_el_mapeo(self):
        # Columnas con nombres arbitrarios: el mapeo decide qué es cada rol.
        columnas = {"Fx": "ForX", "Fy": "ForY", "Fz": "ForZ"}
        grupos, advertencias = self._agrupar(
            [
                _intervalo("ForX", 10, 30),
                _intervalo("ForY", 10, 30),
                _intervalo("ForZ", 10, 30),
            ],
            columnas=columnas,
        )
        self.assertEqual(len(grupos), 1)
        self.assertEqual(grupos[0]["componentes"], columnas)
        self.assertEqual(advertencias, [])

    def test_los_intervalos_ajenos_se_avisan(self):
        grupos, advertencias = self._agrupar(
            [
                _intervalo("Fx", 10, 30),
                _intervalo("Fy", 10, 30),
                _intervalo("Fz", 10, 30),
                _intervalo("Mx", 10, 30),
            ]
        )
        self.assertEqual(len(grupos), 1)
        self.assertTrue(any("Mx" in aviso for aviso in advertencias))

    def test_dos_intervalos_del_mismo_rol_en_un_bloque_no_duplican_el_grupo(self):
        grupos, _ = self._agrupar(
            [
                _intervalo("Fx", 10, 30, numero=1),
                _intervalo("Fx", 10, 30, numero=2),
                _intervalo("Fy", 10, 30),
                _intervalo("Fz", 10, 30),
            ]
        )
        self.assertEqual(len(grupos), 1)


if __name__ == '__main__':
    unittest.main()
