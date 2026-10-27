import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_la_navegacion_derecha_permanece_compacta(self):
        self.assertEqual(perfil_interfaz(1920, 1080).barra_derecha, 124)
        self.assertEqual(perfil_interfaz(1150, 647).barra_derecha, 116)
        self.assertEqual(perfil_interfaz(800, 600).barra_derecha, 108)

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
        from logica import paleta

        paleta.restaurar_colores_senales()
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
        self.assertEqual(
            cabecera.subtitulo.text(),
            app_info.LABORATORIO_CABECERA,
        )
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

    def test_configuracion_cambia_y_recuerda_los_colores_de_las_graficas(self):
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QColorDialog

        from logica import paleta, preferencias_graficas
        from ui.cabecera.cabeceraPrincipal.configuracion import ConfiguracionDialog

        preferencias_graficas.restaurar_colores()
        dialogo = ConfiguracionDialog()
        cambios = []
        dialogo.coloresGraficasCambiaron.connect(lambda: cambios.append(True))

        with mock.patch.object(
            QColorDialog,
            "getColor",
            return_value=QColor("#123ABC"),
        ):
            dialogo.btn_color_original.click()

        self.assertEqual(paleta.color_senal_original(), "#123ABC")
        self.assertEqual(dialogo.btn_color_original.text(), "#123ABC")
        self.assertEqual(len(cambios), 1)
        dialogo.close()

        paleta.restaurar_colores_senales()
        preferencias_graficas.cargar_colores()
        self.assertEqual(paleta.color_senal_original(), "#123ABC")

        reabierto = ConfiguracionDialog()
        self.assertEqual(reabierto.btn_color_original.text(), "#123ABC")
        reabierto.btn_restaurar_colores.click()
        self.assertEqual(
            paleta.color_senal_original(),
            paleta.COLOR_ORIGINAL_PREDETERMINADO,
        )
        self.assertFalse(reabierto.btn_restaurar_colores.isEnabled())
        reabierto.close()

    def test_configuracion_recuerda_el_modo_de_zoom(self):
        from logica import preferencias_graficas
        from ui.cabecera.cabeceraPrincipal.configuracion import ConfiguracionDialog

        preferencias_graficas.restaurar_modo_zoom()
        primero = ConfiguracionDialog()
        self.assertTrue(primero.radio_zoom_x.isChecked())
        primero.radio_zoom_y.click()
        self.assertEqual(
            preferencias_graficas.modo_zoom_actual(),
            preferencias_graficas.MODO_ZOOM_Y,
        )
        primero.close()

        preferencias_graficas.cargar_modo_zoom()
        segundo = ConfiguracionDialog()
        self.assertTrue(segundo.radio_zoom_y.isChecked())
        segundo.radio_zoom_xy.click()
        segundo.close()

        preferencias_graficas.cargar_modo_zoom()
        self.assertEqual(
            preferencias_graficas.modo_zoom_actual(),
            preferencias_graficas.MODO_ZOOM_XY,
        )
        preferencias_graficas.restaurar_modo_zoom()

    def test_inicio_rapido_incluye_impacto_como_pico_de_fz(self):
        from PySide6.QtWidgets import QPushButton

        from ui.ventanaPrincipal.panelDerecho.constructorFormula import (
            ConstructorFormula,
        )

        dialogo = ConstructorFormula()
        try:
            boton = next(
                boton
                for boton in dialogo.findChildren(QPushButton)
                if boton.text() == "Impacto"
            )
            boton.click()
            self.assertEqual(dialogo.input_expresion.text(), "maximo(Fz)")
            self.assertEqual(dialogo.input_nombre.text(), "Impacto personalizado")
            self.assertEqual(dialogo._unidad_actual(), "N")
            self.assertTrue(dialogo.analisis_actual["resultado_escalar"])
        finally:
            dialogo.close()

    def test_el_cambio_de_color_repinta_curvas_ya_cargadas(self):
        from logica import paleta
        from ui.ventanaPrincipal.areaCentralGraficas import (
            AreaCentralGraficas,
            GraficaSenal,
        )

        area = AreaCentralGraficas()
        grafica = GraficaSenal("Fuerza Z", unidad="N", columna="Fz")
        grafica.set_datos(
            [1, 2, 3],
            [10, 20, 30],
            [11, 19, 31],
        )
        area.graficas_por_columna = {"Fz": grafica}

        try:
            paleta.set_colores_senales("#112233", "#DDEEFF")
            area.aplicar_colores_graficas()
            self.assertEqual(
                grafica.curva_original.opts["pen"].color().name().upper(),
                "#112233",
            )
            self.assertEqual(
                grafica.curva_filtrada.opts["pen"].color().name().upper(),
                "#DDEEFF",
            )
        finally:
            paleta.restaurar_colores_senales()
            grafica.close()
            area.close()

    def test_el_menu_derecho_muestra_nombres_sin_esperar_tooltips(self):
        from ui.ventanaPrincipal.barraBotones import BarraBotones
        from ui.ventanaPrincipal.panelDerecho.panelDerecho import PanelDerecho

        panel = PanelDerecho(db_session=self.session)
        barra = BarraBotones(panel)

        self.assertEqual(
            [
                barra.btn_mapeo.text(),
                barra.btn_filtros.text(),
                barra.btn_formulas.text().replace("\n", " "),
                barra.btn_detectar_cabeceras.text(),
            ],
            ["Variables", "Filtros", "Recorte y fórmulas", "Cabeceras"],
        )
        barra.close()
        panel.close()

    def test_acerca_de_muestra_tutores_laboratorio_y_dos_referencias(self):
        from PySide6.QtWidgets import QLabel

        from logica import app_info
        from ui.cabecera.cabeceraPrincipal.acerca_de import AcercaDeDialog

        dialogo = AcercaDeDialog()
        textos = " ".join(
            etiqueta.text() for etiqueta in dialogo.findChildren(QLabel)
        )

        self.assertIn("Marcelo Scotto (UTEC)", textos)
        self.assertIn("Artur Bonezi (UdelaR)", textos)
        self.assertIn("DCB", textos)
        self.assertIn("Cenur Litoral Norte", textos)
        self.assertIn(app_info.REFERENCIA_INGLES, dialogo.txt_referencia.toPlainText())
        self.assertIn(app_info.REFERENCIA_ESPANOL, dialogo.txt_referencia.toPlainText())
        dialogo.close()

    def test_masa_corporal_y_total_se_guardan_y_aparecen_en_el_constructor(self):
        from PySide6.QtWidgets import QAbstractButton

        from logica.config_db import obtener_variable_archivo
        from ui.ventanaPrincipal.panelDerecho.constructorFormula import (
            ConstructorFormula,
        )
        from ui.ventanaPrincipal.panelizquierdo import PanelIzquierdo

        ruta = str(Path(self.temporal.name) / "masas.csv")
        panel = PanelIzquierdo(db_session=self.session)
        panel.archivo_actual = {"ruta": ruta}
        panel._set_variables_archivo_habilitadas(True)
        panel.input_masa.setText("72,5")
        panel.input_masa_total.setText("82,5")
        panel.guardar_masa()
        panel.guardar_masa_total()

        self.assertEqual(obtener_variable_archivo(self.session, ruta, "masa"), 72.5)
        self.assertEqual(
            obtener_variable_archivo(self.session, ruta, "masa_total"),
            82.5,
        )
        self.assertEqual(panel.variables_para_proyecto()["masa_total"], 82.5)

        constructor = ConstructorFormula()
        textos = {
            boton.text() for boton in constructor.findChildren(QAbstractButton)
        }
        self.assertIn("Masa corporal", textos)
        self.assertIn("Masa total", textos)
        constructor.close()
        panel.close()

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
        ventana.panel_izquierdo.masa_total_actual = 80.0
        ventana.panel_izquierdo.estatura_actual = 1.75
        ventana.panel_izquierdo.input_masa.setText("70")
        ventana.panel_izquierdo.input_masa_total.setText("80")
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
        self.assertIsNone(ventana.panel_izquierdo.masa_total_actual)
        self.assertIsNone(ventana.panel_izquierdo.estatura_actual)
        self.assertEqual(ventana.panel_izquierdo.input_masa.text(), "")
        self.assertEqual(ventana.panel_izquierdo.input_masa_total.text(), "")
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
