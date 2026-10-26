import importlib.util
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd


DEPENDENCIAS_UI = all(
    importlib.util.find_spec(modulo) is not None
    for modulo in ("PySide6", "pyqtgraph")
)

if DEPENDENCIAS_UI:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import pyqtgraph as pg
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFrame

    from ui.ventanaPrincipal.areaCentralGraficas import (
        AreaCentralGraficas,
        GraficaSenal,
        ViewBoxFormula,
    )
    from ui.ventanaPrincipal.panelDerecho.formulas import Formulas
    from ui.ventanaPrincipal.panelDerecho.configColumnas import ConfigColumnas
    from ui.cabecera.cabeceraPrincipal.exportar import ExportarDialog
    from ui.ventanaRegion.ventanaRegion import VentanaRegion


@unittest.skipUnless(DEPENDENCIAS_UI, "PySide6 y pyqtgraph no están instalados")
class TestInteraccionGrafica(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_la_grafica_principal_usa_arrastre_para_desplazarse(self):
        grafica = GraficaSenal("Fz", unidad="N")
        try:
            vista = grafica.getViewBox()
            self.assertEqual(vista.state["mouseMode"], pg.ViewBox.PanMode)
            self.assertEqual(vista.mouseEnabled(), [True, False])
        finally:
            grafica.close()

    def test_restaurar_mapeo_repone_orden_y_visibilidad(self):
        panel = ConfigColumnas()
        info = {
            "deteccion": {
                "mapeo": {
                    "Fuerza": {
                        "eje_x": "Fx",
                        "eje_y": "Fy",
                        "eje_z": "Fz",
                    }
                }
            },
            "columnas_csv": ["Frame", "Fx", "Fy", "Fz"],
        }
        guardado = {
            "Fuerza": {
                "eje_x": {"columna": "Fx", "activo": False, "orden": 2},
                "eje_y": {"columna": "Fy", "activo": True, "orden": 1},
                "eje_z": {"columna": "Fz", "activo": True, "orden": 0},
            }
        }
        try:
            panel.cargar_datos(info)
            restaurado = panel.restaurar_mapeo_proyecto(guardado)

            self.assertFalse(restaurado["Fuerza"]["eje_x"]["activo"])
            self.assertEqual(restaurado["Fuerza"]["eje_z"]["orden"], 0)
            self.assertEqual(
                [panel.lista_filas.item(i).data(Qt.UserRole)[1] for i in range(3)],
                ["eje_z", "eje_y", "eje_x"],
            )
        finally:
            panel.close()

    def test_las_capas_de_formula_no_consumen_el_arrastre(self):
        class Evento:
            ignorado = False

            def ignore(self):
                self.ignorado = True

        for manejador in (
            ViewBoxFormula.mouseDragEvent,
            ViewBoxFormula.mouseClickEvent,
            ViewBoxFormula.wheelEvent,
        ):
            evento = Evento()
            manejador(None, evento)
            self.assertTrue(evento.ignorado)

    def test_escape_puede_cancelar_el_primer_punto_sin_salir_del_modo(self):
        grafica = GraficaSenal("Fz", unidad="N")
        try:
            grafica.set_modo_seleccion_intervalo(True)
            grafica.x_inicio = 25

            self.assertTrue(grafica.cancelar_propuesta_intervalo())
            self.assertIsNone(grafica.x_inicio)
            self.assertTrue(grafica.modo_seleccion_intervalo)
            self.assertFalse(grafica.cancelar_propuesta_intervalo())
        finally:
            grafica.close()

    def test_el_motor_principal_ignora_subintervalos(self):
        class GraficaVisible:
            @staticmethod
            def isHidden():
                return False

        intervalos = {
            "Fz::1": {
                "id": "Fz::1",
                "columna": "Fz",
                "desde": 10,
                "hasta": 20,
                "es_subintervalo": False,
            },
            "Fz::1::sub::1": {
                "id": "Fz::1::sub::1",
                "columna": "Fz",
                "desde": 10,
                "hasta": 20,
                "es_subintervalo": True,
            },
        }
        area = SimpleNamespace(
            graficas_por_columna={"Fz": GraficaVisible()},
            _buscar_intervalo=lambda identificador: intervalos.get(identificador),
        )

        seleccionados = AreaCentralGraficas._intervalos_seleccionados(
            area,
            ["Fz::1", "Fz::1::sub::1"],
        )

        self.assertEqual(
            [intervalo["id"] for intervalo in seleccionados],
            ["Fz::1"],
        )

    def test_el_panel_principal_envia_solo_intervalos_padre(self):
        panel = SimpleNamespace(
            intervalos=[
                {"id": "Fz::1", "columna": "Fz", "es_subintervalo": False},
                {
                    "id": "Fz::1::sub::1",
                    "columna": "Fz",
                    "es_subintervalo": True,
                },
                {"id": "Fx::1", "columna": "Fx", "es_subintervalo": False},
            ],
            cmb_senal=SimpleNamespace(currentData=lambda: "Fz"),
            _id_intervalo=lambda intervalo: intervalo["id"],
            obtener_intervalos_seleccionados=lambda: [
                "Fz::1",
                "Fz::1::sub::1",
                "Fx::1",
            ],
        )

        seleccionados = Formulas._intervalos_padre_seleccionados(panel)

        self.assertEqual(seleccionados, ["Fz::1"])

    def test_el_panel_principal_separa_padres_y_subintervalos(self):
        panel = Formulas()
        intervalos = [
            {
                "id": "Fz::1",
                "numero": 1,
                "orden": 1,
                "columna": "Fz",
                "senal": "Fuerza Z",
                "desde": 0,
                "hasta": 50,
                "nombre": "A",
                "color": "#42A5F5",
                "es_subintervalo": False,
                "padre": None,
            },
            {
                "id": "Fz::1::sub::1",
                "numero": 1,
                "orden": 1,
                "columna": "Fz",
                "senal": "Fuerza Z",
                "desde": 0,
                "hasta": 20,
                "nombre": "A1",
                "color": "#66BB6A",
                "es_subintervalo": True,
                "padre": "Fz::1",
            },
            {
                "id": "Fz::1::sub::2",
                "numero": 2,
                "orden": 2,
                "columna": "Fz",
                "senal": "Fuerza Z",
                "desde": 21,
                "hasta": 40,
                "nombre": "A2",
                "color": "#FFB300",
                "es_subintervalo": True,
                "padre": "Fz::1",
            },
        ]
        try:
            panel.cargar_intervalos(intervalos)
            self.assertEqual(set(panel.checkboxes), {"Fz::1"})

            panel._cambiar_nivel_calculo("subintervalos")
            self.assertEqual(
                set(panel.checkboxes),
                {"Fz::1::sub::1", "Fz::1::sub::2"},
            )
        finally:
            panel.close()

    def test_pares_de_subintervalos_se_aplican_en_masa_desde_la_principal(self):
        panel = Formulas()
        intervalos = []
        for padre in (1, 2):
            padre_id = f"Fz::{padre}"
            intervalos.append(
                {
                    "id": padre_id,
                    "numero": padre,
                    "orden": padre,
                    "columna": "Fz",
                    "senal": "Fuerza Z",
                    "desde": (padre - 1) * 100,
                    "hasta": padre * 100 - 1,
                    "nombre": f"Intervalo {padre}",
                    "color": "#42A5F5",
                    "es_subintervalo": False,
                    "padre": None,
                }
            )
            for sub in (1, 2):
                intervalos.append(
                    {
                        "id": f"{padre_id}::sub::{sub}",
                        "numero": sub,
                        "orden": sub,
                        "columna": "Fz",
                        "senal": "Fuerza Z",
                        "desde": (padre - 1) * 100 + (sub - 1) * 40,
                        "hasta": (padre - 1) * 100 + sub * 40 - 1,
                        "nombre": f"Sub-intervalo {sub}",
                        "color": "#66BB6A",
                        "es_subintervalo": True,
                        "padre": padre_id,
                    }
                )
        pedidos_sub = []
        pedidos_padre = []
        panel.formulaSubintervalosSolicitada.connect(pedidos_sub.append)
        panel.formulaSolicitada.connect(pedidos_padre.append)
        try:
            panel.cargar_intervalos(intervalos)
            panel._cambiar_nivel_calculo("subintervalos")
            panel._seleccionar("pares")
            panel._solicitar_formula()

            self.assertEqual(pedidos_padre, [])
            self.assertEqual(
                pedidos_sub[0]["intervalos"],
                ["Fz::1::sub::2", "Fz::2::sub::2"],
            )
        finally:
            panel.close()

    def test_la_capa_visible_no_mezcla_intervalos_y_subintervalos(self):
        grafica = Mock()
        grafica.isHidden.return_value = False
        calculo_padre = {
            "datos_panel": {"nombre": "Padres", "unidad": "N"},
            "por_grafica": {
                "Fz": {"resultados": [], "segmentos": [([0, 1], [1, 2])]}
            },
        }
        calculo_sub = {
            "datos_panel": {"nombre": "Subs", "unidad": "N"},
            "por_grafica": {
                "Fz": {"resultados": [], "segmentos": [([0, 1], [3, 4])]}
            },
        }
        area = SimpleNamespace(
            nivel_calculo_visible="subintervalos",
            graficas_por_columna={"Fz": grafica},
            formulas_activas={"padre": {}},
            _calculos_formulas={"padre": calculo_padre},
            formulas_subintervalos_activas={"sub": {}},
            _calculos_formulas_subintervalos={"sub": calculo_sub},
        )

        AreaCentralGraficas._redibujar_formulas_aplicadas(area)

        curvas = grafica.set_curvas_formulas.call_args.args[0]
        self.assertEqual([curva["nombre"] for curva in curvas], ["Subs"])

    def test_aplicar_subintervalos_no_modifica_el_registro_de_padres(self):
        subintervalo = {
            "id": "Fz::1::sub::2",
            "columna": "Fz",
            "es_subintervalo": True,
        }
        calculo = {
            "datos_panel": {"resultados": [{"id": subintervalo["id"]}]},
            "por_grafica": {},
        }
        padres = {"fuerza_neta": {"intervalos": ["Fz::1"]}}
        area = SimpleNamespace(
            df_grafica_original=object(),
            _ultimo_error_formula="",
            formulas_activas=padres,
            formulas_subintervalos_activas={},
            _calculos_formulas_subintervalos={},
            nivel_calculo_visible="subintervalos",
            _intervalos_para_panel=lambda: [subintervalo],
            _preparar_calculo_subintervalos_global=Mock(return_value=calculo),
            _sincronizar_ventanas_subintervalos=Mock(),
            _redibujar_formulas_aplicadas=Mock(),
            _emitir_resultado_formula_actual=Mock(),
            formulaEstadoCambiado=SimpleNamespace(emit=Mock()),
        )

        resultado = AreaCentralGraficas.aplicar_formula_subintervalos(
            area,
            {
                "clave": "fuerza_neta",
                "intervalos": [subintervalo["id"]],
            },
        )

        self.assertTrue(resultado)
        self.assertIs(area.formulas_activas, padres)
        self.assertEqual(
            area.formulas_subintervalos_activas["fuerza_neta"]["intervalos"],
            [subintervalo["id"]],
        )

    def test_un_recorte_de_fx_puede_calcular_una_formula_de_fz(self):
        datos_fz = pd.Series([700.0, 800.0, 900.0]).to_numpy()
        area = SimpleNamespace(
            graficas_por_columna={
                "Fz": SimpleNamespace(nombre_senal="Fuerza Z")
            },
            _columna_de_rol=lambda rol: "Fz" if rol == "Fz" else None,
            _roles_disponibles=lambda: {"Fz"},
            _datos_columna=lambda columna: datos_fz if columna == "Fz" else None,
            df_grafica_original=pd.DataFrame(
                {"Frame": [0.0, 1.0, 2.0], "Fz": datos_fz}
            ),
            columna_x="Frame",
            masa_sujeto=70.0,
            estatura_sujeto=1.75,
            gravedad=10.0,
            frecuencia_grafica=100.0,
        )
        intervalo_fx = {
            "id": "Fx::1",
            "columna": "Fx",
            "senal": "Fuerza X",
            "numero": 1,
            "desde": 0,
            "hasta": 2,
            "nombre": "Apoyo",
        }

        columna, resultados, _curva, _avisos, _segmentos = (
            AreaCentralGraficas._calcular_por_intervalos(
                area,
                "fuerza_neta",
                [intervalo_fx],
            )
        )

        self.assertEqual(columna, "Fz")
        self.assertEqual(resultados[0]["id"], "Fx::1")
        self.assertEqual(resultados[0]["senal"], "Fuerza Z")

    def test_la_ventana_reconstruye_resultados_desde_el_estado_central(self):
        subintervalo = {
            "id": "Fz::1::sub::1",
            "columna": "Fz",
            "padre": "Fz::1",
            "desde": 12,
            "hasta": 18,
            "es_subintervalo": True,
        }
        calculo = {
            "configuracion": {
                "clave": "potencia",
                "intervalos": [subintervalo["id"]],
            },
            "datos_panel": {"resultados": [{"id": subintervalo["id"]}]},
            "por_grafica": {},
        }
        area = SimpleNamespace(
            formulas_subintervalos_activas={
                "potencia": {
                    "clave": "potencia",
                    "intervalos": ["Fz::2", subintervalo["id"]],
                }
            },
            _id_intervalo=AreaCentralGraficas._id_intervalo,
            _intervalos_para_panel=lambda: [subintervalo],
            _preparar_calculo_subintervalos=Mock(return_value=calculo),
        )
        ventana = SimpleNamespace(
            clave_subgestor=("Fz", 1),
            establecer_calculos_formulas=Mock(),
            set_subintervalos_seleccionados=Mock(),
            panel_calculo=SimpleNamespace(set_formula=Mock()),
        )

        AreaCentralGraficas._recalcular_formulas_subintervalos(
            area,
            ventana,
            restaurar_seleccion=True,
        )

        aplicaciones, calculos = ventana.establecer_calculos_formulas.call_args.args
        self.assertEqual(
            aplicaciones["potencia"]["intervalos"],
            [subintervalo["id"]],
        )
        self.assertIs(calculos["potencia"], calculo)
        ventana.panel_calculo.set_formula.assert_called_once_with("potencia")
        ventana.set_subintervalos_seleccionados.assert_called_once_with(
            [subintervalo["id"]]
        )

    def test_el_panel_de_subintervalos_reutiliza_el_estilo_principal(self):
        ventana = VentanaRegion(
            titulo="Fz · Intervalo 1",
            x=[0.0, 1.0],
            y_original=[10.0, 12.0],
            columna="Fz",
        )
        try:
            self.assertIsNotNone(ventana.findChild(QFrame, "formulasPanel"))
            self.assertIsNotNone(ventana.findChild(QFrame, "seccionMapeo"))
            self.assertEqual(
                ventana.lista_subintervalos.objectName(),
                "listaSubintervalosCalculo",
            )
        finally:
            ventana.close()

    def test_la_lista_de_subintervalos_usa_el_color_de_la_grafica(self):
        ventana = VentanaRegion(
            titulo="Fz · Intervalo 1",
            x=[0.0, 1.0],
            y_original=[10.0, 12.0],
            columna="Fz",
        )
        try:
            subintervalo = SimpleNamespace(
                numero=1,
                nombre="Sub-intervalo 1",
                desde=0,
                hasta=1,
                color="#E53935",
            )
            ventana.mostrar_subintervalos([subintervalo])

            color_lista = (
                ventana.lista_subintervalos.item(0)
                .foreground()
                .color()
                .name()
                .upper()
            )
            self.assertEqual(color_lista, subintervalo.color)
        finally:
            ventana.close()

    def test_exportacion_puede_limitarse_a_recortes_elegidos(self):
        dialogo = ExportarDialog(
            nombre_archivo="prueba.csv",
            cantidad_frames=100,
            cantidad_senales=3,
            intervalos=[
                {
                    "id": "Fz::1",
                    "senal": "Fuerza Z",
                    "nombre": "A",
                    "desde": 10,
                    "hasta": 20,
                    "color": "#42A5F5",
                },
                {
                    "id": "Fx::2",
                    "senal": "Fuerza X",
                    "nombre": "B",
                    "desde": 30,
                    "hasta": 40,
                    "color": "#E53935",
                },
                {
                    "id": "Fy::3",
                    "senal": "Fuerza Y",
                    "nombre": "C",
                    "desde": 50,
                    "hasta": 60,
                    "color": "#66BB6A",
                },
            ],
        )
        try:
            self.assertEqual(dialogo.lista_recortes.count(), 3)
            self.assertEqual(
                [
                    dialogo.lista_recortes.item(indice).data(Qt.UserRole)
                    for indice in range(dialogo.lista_recortes.count())
                ],
                ["Fz::1", "Fx::2", "Fy::3"],
            )
            self.assertIsNone(dialogo.ids_intervalos_seleccionados())
            dialogo.radio_recortes.setChecked(True)
            dialogo._marcar_recortes(False)
            dialogo.lista_recortes.item(1).setCheckState(Qt.Checked)

            self.assertEqual(
                dialogo.ids_intervalos_seleccionados(),
                ["Fx::2"],
            )
        finally:
            dialogo.close()

    def test_tocar_la_lista_de_exportacion_activa_su_propio_alcance(self):
        dialogo = ExportarDialog(
            intervalos=[
                {
                    "id": "Fz::1",
                    "senal": "Fuerza Z",
                    "nombre": "A",
                    "desde": 10,
                    "hasta": 20,
                },
                {
                    "id": "Fx::1",
                    "senal": "Fuerza X",
                    "nombre": "A",
                    "desde": 10,
                    "hasta": 20,
                },
            ]
        )
        try:
            self.assertTrue(dialogo.radio_todo.isChecked())
            dialogo.lista_recortes.item(1).setCheckState(Qt.Unchecked)

            self.assertTrue(dialogo.radio_recortes.isChecked())
            self.assertEqual(dialogo.ids_intervalos_seleccionados(), ["Fz::1"])
        finally:
            dialogo.close()


if __name__ == "__main__":
    unittest.main()
