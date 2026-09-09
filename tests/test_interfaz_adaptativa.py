import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

from logica.interfaz_adaptativa import (
    calcular_tamano_ventana,
    perfil_interfaz,
)


class TestCalculosInterfazAdaptativa(unittest.TestCase):
    def test_la_cabecera_de_1150_por_647_conserva_textos(self):
        perfil = perfil_interfaz(1150, 647)

        self.assertTrue(perfil.compacto)
        self.assertFalse(perfil.cabecera_compacta)
        self.assertFalse(perfil.cabecera_muy_compacta)

    def test_los_perfiles_reservan_espacio_para_las_graficas(self):
        for ancho, alto in ((640, 480), (800, 600), (1024, 768), (1920, 1080)):
            perfil = perfil_interfaz(ancho, alto)
            ocupado = (
                perfil.panel_izquierdo
                + perfil.barra_derecha
                + perfil.panel_derecho
            )
            self.assertLess(ocupado, ancho)
            self.assertLessEqual(
                perfil.panel_derecho_minimo,
                perfil.panel_derecho,
            )
            self.assertLessEqual(
                perfil.panel_derecho,
                perfil.panel_derecho_maximo,
            )

    def test_un_dialogo_nunca_supera_el_area_disponible(self):
        self.assertEqual(
            calcular_tamano_ventana(
                1366,
                768,
                ideal=(1200, 900),
                minimo=(700, 480),
                margen=40,
                piso=(320, 240),
            ),
            (1200, 728),
        )
        self.assertEqual(
            calcular_tamano_ventana(
                800,
                600,
                ideal=(1040, 720),
                minimo=(760, 420),
                margen=40,
                piso=(320, 240),
            ),
            (760, 560),
        )
        self.assertEqual(
            calcular_tamano_ventana(
                240,
                320,
                ideal=(680, 460),
                minimo=(420, 340),
                margen=24,
                piso=(300, 240),
            ),
            (216, 296),
        )


DEPENDENCIAS_UI = all(
    importlib.util.find_spec(modulo) is not None
    for modulo in ("PySide6", "pyqtgraph", "sqlalchemy")
)


@unittest.skipUnless(DEPENDENCIAS_UI, "Dependencias de interfaz no instaladas")
class TestVentanasAdaptativas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        import pandas as pd
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from logica import app_info
        from logica.config_db import Base

        cls.pd = pd
        cls.QSettings = QSettings
        cls.app_info = app_info
        cls.nombre_original = app_info.NOMBRE
        app_info.NOMBRE = f"LIBiAM-pruebas-interfaz-{os.getpid()}"
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        cls.ajustes = QSettings("LIBiAM", app_info.NOMBRE)
        cls.ajustes.clear()

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        cls.session = sessionmaker(bind=engine)()
        cls.temporal = tempfile.TemporaryDirectory()
        cls.ruta_temporal = Path(cls.temporal.name) / "resultado.csv"
        cls.ruta_temporal.write_text("a,b\n1,2\n", encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.ajustes.clear()
        cls.ajustes.sync()
        cls.session.close()
        cls.temporal.cleanup()
        cls.app_info.NOMBRE = cls.nombre_original

    @classmethod
    def _fabricas(cls):
        from ui.cabecera.cabeceraPrincipal.acerca_de import AcercaDeDialog
        from ui.cabecera.cabeceraPrincipal.cargarProyecto import CargarProyectoDialog
        from ui.cabecera.cabeceraPrincipal.configuracion import ConfiguracionDialog
        from ui.cabecera.cabeceraPrincipal.exportar import (
            ExportacionCompletadaDialog,
            ExportarDialog,
        )
        from ui.cabecera.cabeceraPrincipal.limpiarArchivos import (
            LimpiarArchivosDialog,
        )
        from ui.ventanaPrincipal.cargaCSV import CargaCSVDialog
        from ui.ventanaPrincipal.panelDerecho.constructorFormula import (
            ConstructorFormula,
        )
        from ui.ventanaPrincipal.panelDerecho.notaIntervalo import NotaDialog
        from ui.ventanaPrincipal.panelDerecho.ventanaEditorCSV import (
            VentanaEditorCSV,
        )
        from ui.ventanaPrincipal.ventana_principal import VentanaPrincipal
        from ui.ventanaRegion.ventanaRegion import VentanaRegion

        df = cls.pd.DataFrame({"Frame": [1, 2], "Fz": [10.0, 11.0]})
        ruta = str(cls.ruta_temporal)
        return {
            "principal": lambda: VentanaPrincipal(db_session=cls.session),
            "constructor": lambda: ConstructorFormula(),
            "subintervalos": lambda: VentanaRegion(
                titulo="Fz",
                x=[1.0, 2.0],
                y_original=[10.0, 11.0],
                columna="Fz",
            ),
            "editor_csv": lambda: VentanaEditorCSV(
                df,
                cls.session,
                ruta,
            ),
            "exportar": lambda: ExportarDialog(
                nombre_archivo="prueba.csv",
                cantidad_frames=2,
                cantidad_senales=1,
                intervalos=[],
            ),
            "exportacion_completada": lambda: ExportacionCompletadaDialog(
                None,
                cls.ruta_temporal,
                "Datos de las señales",
            ),
            "configuracion": lambda: ConfiguracionDialog(),
            "cargar_proyecto": lambda: CargarProyectoDialog(),
            "limpiar_archivos": lambda: LimpiarArchivosDialog(),
            "nota": lambda: NotaDialog(nombre="Intervalo 1"),
            "carga_csv": lambda: CargaCSVDialog(ruta),
            "acerca_de": lambda: AcercaDeDialog(),
        }

    @classmethod
    def _cerrar(cls, nombre, widget):
        if nombre == "carga_csv":
            widget.finalizar(False)
        else:
            widget.close()
        cls.app.processEvents()
        widget.deleteLater()
        cls.app.processEvents()

    def test_los_botones_estandar_de_qt_se_muestran_en_espanol(self):
        from PySide6.QtWidgets import QMessageBox

        from logica.idioma import configurar_idioma_espanol

        configurar_idioma_espanol(self.app)
        dialogo = QMessageBox()
        dialogo.setStandardButtons(
            QMessageBox.Yes
            | QMessageBox.No
            | QMessageBox.Ok
            | QMessageBox.Cancel
        )
        textos = {boton.text().replace("&", "") for boton in dialogo.buttons()}

        self.assertEqual(textos, {"Sí", "No", "Aceptar", "Cancelar"})
        dialogo.close()

    def test_la_cabecera_abrevia_el_laboratorio_sin_cortarlo(self):
        from logica import app_info
        from ui.cabecera.cabeceraPrincipal.cabecera import Cabecera

        cabecera = Cabecera()
        cabecera.ajustar_modo(False, False)
        self.assertEqual(cabecera.subtitulo.text(), app_info.LABORATORIO)
        self.assertTrue(cabecera.subtitulo.isVisibleTo(cabecera))

        cabecera.ajustar_modo(True, True)
        self.assertEqual(cabecera.subtitulo.text(), app_info.LABORATORIO_CORTO)
        self.assertTrue(cabecera.subtitulo.isVisibleTo(cabecera))
        cabecera.close()

    def test_el_orden_del_encabezado_comienza_por_inicio_abrir_guardar_exportar(self):
        from ui.cabecera.cabeceraPrincipal.cabecera import Cabecera

        cabecera = Cabecera()

        self.assertEqual(
            list(cabecera.botones)[:4],
            ["Inicio", "Abrir", "Guardar", "Exportar"],
        )
        cabecera.close()

    def test_todas_las_ventanas_recuerdan_su_tamano_y_siguen_visibles(self):
        for indice, (nombre, fabrica) in enumerate(self._fabricas().items()):
            with self.subTest(ventana=nombre):
                primera = fabrica()
                primera.show()
                self.app.processEvents()
                area = primera.screen().availableGeometry()
                self.assertTrue(area.intersects(primera.frameGeometry()))
                self.assertLessEqual(primera.frameGeometry().width(), area.width())
                self.assertLessEqual(primera.frameGeometry().height(), area.height())

                ancho = max(
                    primera.minimumWidth(),
                    min(area.width() - 36, primera.width() - 17),
                )
                alto = max(
                    primera.minimumHeight(),
                    min(area.height() - 36, primera.height() - 23),
                )
                primera.resize(ancho, alto)
                primera.move(area.left() + 8 + indice, area.top() + 8 + indice)
                self.app.processEvents()
                guardado = primera.size()
                self._cerrar(nombre, primera)

                segunda = fabrica()
                segunda.show()
                self.app.processEvents()
                self.assertLessEqual(abs(segunda.width() - guardado.width()), 3)
                self.assertLessEqual(abs(segunda.height() - guardado.height()), 3)
                self.assertTrue(area.intersects(segunda.frameGeometry()))
                self._cerrar(nombre, segunda)

    def test_inicio_descarta_todo_el_analisis_de_la_sesion(self):
        from ui.ventanaPrincipal.ventana_principal import VentanaPrincipal

        ventana = VentanaPrincipal(db_session=self.session)
        df = self.pd.DataFrame({"Frame": [1, 2, 3], "Fz": [10.0, 12.0, 11.0]})
        info = {
            "deteccion": {"mapeo": {"Fuerza": {"eje_z": "Fz"}}},
            "unidades": {"Fz": "N"},
        }
        ventana.area_central.cargar_dataframe("prueba.csv", df, info)
        ventana.panel_izquierdo.archivos_cargados = {"prueba.csv": {"df": df}}
        ventana.panel_izquierdo.archivo_actual = {"nombre": "prueba.csv"}
        ventana.panel_izquierdo.masa_actual = 70.0
        ventana.panel_izquierdo.estatura_actual = 1.75
        ventana.panel_izquierdo.input_masa.setText("70")
        ventana.panel_izquierdo.input_estatura.setText("1.75")
        ventana.area_central.gestores_intervalos = {"Fz": object()}
        ventana.area_central.formulas_activas = {"potencia": {}}
        ventana.area_central.columnas_filtradas = {"Fz"}
        ventana.barra_botones.toggle_panel("formulas")

        self.assertTrue(ventana._reiniciar_sesion(confirmar=False))
        self.assertIsNone(ventana.area_central.df_original)
        self.assertEqual(ventana.area_central.graficas, [])
        self.assertEqual(ventana.area_central.gestores_intervalos, {})
        self.assertEqual(ventana.area_central.formulas_activas, {})
        self.assertEqual(ventana.area_central.columnas_filtradas, set())
        self.assertEqual(ventana.panel_izquierdo.archivos_cargados, {})
        self.assertIsNone(ventana.panel_izquierdo.masa_actual)
        self.assertIsNone(ventana.panel_izquierdo.estatura_actual)
        self.assertEqual(ventana.panel_izquierdo.input_masa.text(), "")
        self.assertEqual(ventana.panel_izquierdo.input_estatura.text(), "")
        self.assertEqual(ventana.panel_izquierdo.input_gravedad.text(), "9.8")
        self.assertFalse(ventana.panel_derecho.isVisible())
        self.assertFalse(ventana.panel_derecho.expandido)
        self.assertIsNone(ventana.barra_botones.panel_activo)
        self.assertEqual(
            ventana.area_central.stack.currentWidget(),
            ventana.area_central.placeholder,
        )
        ventana.close()

    def test_el_panel_derecho_recupera_su_ancho_al_volver_a_pantalla_grande(self):
        from ui.ventanaPrincipal.panelDerecho.panelDerecho import PanelDerecho

        panel = PanelDerecho(db_session=self.session)
        panel._ancho_personalizado = True
        panel.ancho_preferido = 600
        panel.configurar_limites(220, 253, 253)
        self.assertEqual(panel.ancho_expandido_actual, 253)
        self.assertEqual(panel.ancho_preferido, 600)

        panel.configurar_limites(300, 800, 340)
        self.assertEqual(panel.ancho_expandido_actual, 600)
        panel.close()

    def test_una_ventana_guardada_fuera_de_pantalla_se_recupera(self):
        from ui.ventanaPrincipal.panelDerecho.constructorFormula import (
            ConstructorFormula,
        )

        self.ajustes.remove(ConstructorFormula.CLAVE_GEOMETRIA)
        primera = ConstructorFormula()
        primera.show()
        self.app.processEvents()
        primera.move(5000, 5000)
        primera.reject()
        self.app.processEvents()

        segunda = ConstructorFormula()
        segunda.show()
        self.app.processEvents()
        area = segunda.screen().availableGeometry()
        self.assertTrue(area.intersects(segunda.frameGeometry()))
        segunda.reject()
