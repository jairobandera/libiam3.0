import importlib.util
import os
import unittest


DEPENDENCIAS_UI = all(
    importlib.util.find_spec(modulo) is not None
    for modulo in ("PySide6", "pyqtgraph")
)

if DEPENDENCIAS_UI:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import pyqtgraph as pg
    from PySide6.QtWidgets import QApplication

    from ui.ventanaPrincipal.areaCentralGraficas import (
        GraficaSenal,
        ViewBoxFormula,
    )


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


if __name__ == "__main__":
    unittest.main()
