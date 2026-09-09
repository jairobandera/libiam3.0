"""Tamaños adaptativos y memoria segura de ventanas."""

import weakref
from dataclasses import dataclass


@dataclass(frozen=True)
class PerfilInterfaz:
    compacto: bool
    muy_compacto: bool
    panel_izquierdo: int
    barra_derecha: int
    panel_derecho: int
    panel_derecho_minimo: int
    panel_derecho_maximo: int


def perfil_interfaz(ancho, alto):
    """Devuelve anchos útiles para la ventana principal en píxeles lógicos."""
    ancho = max(1, int(ancho or 1))
    alto = max(1, int(alto or 1))
    compacto = ancho < 1280 or alto < 720
    muy_compacto = ancho < 980

    if ancho < 760:
        izquierdo, barra, derecho, minimo = 165, 44, 195, 170
    elif muy_compacto:
        izquierdo, barra, derecho, minimo = 195, 52, 270, 220
    elif compacto:
        izquierdo, barra, derecho, minimo = 235, 62, 315, 260
    else:
        izquierdo, barra, derecho, minimo = 280, 80, 340, 300

    centro_minimo = 220 if ancho < 760 else 300 if muy_compacto else 360
    maximo_disponible = ancho - izquierdo - barra - centro_minimo
    maximo = max(minimo, min(800, maximo_disponible))
    derecho = max(minimo, min(derecho, maximo))
    return PerfilInterfaz(
        compacto=compacto,
        muy_compacto=muy_compacto,
        panel_izquierdo=izquierdo,
        barra_derecha=barra,
        panel_derecho=derecho,
        panel_derecho_minimo=minimo,
        panel_derecho_maximo=maximo,
    )


def calcular_tamano_ventana(
    ancho_disponible,
    alto_disponible,
    ideal,
    minimo,
    margen=24,
    piso=(280, 200),
):
    """Ajusta un tamaño ideal sin permitir que supere el área disponible."""
    ancho_maximo = max(1, int(ancho_disponible) - int(margen))
    alto_maximo = max(1, int(alto_disponible) - int(margen))
    ancho_minimo = min(max(int(piso[0]), int(minimo[0])), ancho_maximo)
    alto_minimo = min(max(int(piso[1]), int(minimo[1])), alto_maximo)
    ancho = max(ancho_minimo, min(int(ideal[0]), ancho_maximo))
    alto = max(alto_minimo, min(int(ideal[1]), alto_maximo))
    return ancho, alto


def area_disponible(widget=None):
    """Obtiene el área útil de la pantalla más cercana al widget."""
    from PySide6.QtGui import QGuiApplication

    pantalla = widget.screen() if widget is not None else None
    if pantalla is None and widget is not None:
        pantalla = QGuiApplication.screenAt(widget.frameGeometry().center())
    if pantalla is None:
        pantalla = QGuiApplication.primaryScreen()
    return pantalla.availableGeometry() if pantalla is not None else None


def ajustar_ventana_a_pantalla(
    widget,
    ideal,
    minimo,
    margen=24,
    piso=(280, 200),
):
    """Define un mínimo y un tamaño inicial compatibles con la pantalla."""
    area = area_disponible(widget)
    if area is None:
        widget.setMinimumSize(*minimo)
        widget.resize(*ideal)
        return tuple(ideal)

    ancho, alto = calcular_tamano_ventana(
        area.width(), area.height(), ideal, minimo, margen, piso
    )
    minimo_real = calcular_tamano_ventana(
        area.width(), area.height(), minimo, piso, margen, piso
    )
    widget.setMinimumSize(*minimo_real)
    widget.resize(ancho, alto)
    return ancho, alto


def asegurar_ventana_visible(widget, margen=8):
    """Reubica y limita una ventana restaurada si cambió el monitor."""
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QGuiApplication

    if widget.isMaximized() or widget.isFullScreen():
        return
    pantallas = list(QGuiApplication.screens())
    if not pantallas:
        return

    marco = widget.frameGeometry()
    pantalla = max(
        pantallas,
        key=lambda item: marco.intersected(item.availableGeometry()).width()
        * marco.intersected(item.availableGeometry()).height(),
    )
    area_pantalla = pantalla.availableGeometry()
    configuracion = getattr(widget, "_config_geometria_adaptativa", None)
    if configuracion:
        minimo = configuracion["minimo"]
        piso = configuracion["piso"]
        margen_configurado = configuracion["margen"]
        minimo_real = calcular_tamano_ventana(
            area_pantalla.width(),
            area_pantalla.height(),
            minimo,
            piso,
            margen_configurado,
            piso,
        )
        widget.setMinimumSize(*minimo_real)

    area = area_pantalla.adjusted(
        margen, margen, -margen, -margen
    )
    if area.width() <= 0 or area.height() <= 0:
        return

    if widget.width() > area.width() or widget.height() > area.height():
        widget.resize(
            min(widget.width(), area.width()),
            min(widget.height(), area.height()),
        )
        marco = widget.frameGeometry()

    x_maximo = max(area.left(), area.right() - marco.width() + 1)
    y_maximo = max(area.top(), area.bottom() - marco.height() + 1)
    x = min(max(marco.x(), area.left()), x_maximo)
    y = min(max(marco.y(), area.top()), y_maximo)
    widget.move(QPoint(x, y))


def _objeto_qt_valido(objeto):
    if objeto is None:
        return False
    try:
        from shiboken6 import isValid

        return bool(isValid(objeto))
    except (ImportError, RuntimeError):
        return False


def _asegurar_referencia_visible(referencia):
    widget = referencia()
    if not _objeto_qt_valido(widget):
        return
    asegurar_ventana_visible(widget)


class _GestorGeometriaVentana:
    """Filtro Qt creado de forma diferida para no exigir PySide al importar."""

    @staticmethod
    def crear(widget, ajustes, clave):
        from PySide6.QtCore import QEvent, QObject, QTimer

        referencia = weakref.ref(widget)

        class Gestor(QObject):
            def eventFilter(self, objeto, evento):
                try:
                    tipo = evento.type()
                    if tipo in (
                        QEvent.Type.Show,
                        QEvent.Type.ScreenChangeInternal,
                    ):
                        QTimer.singleShot(
                            0,
                            lambda: _asegurar_referencia_visible(referencia),
                        )
                    elif tipo in (QEvent.Type.Hide, QEvent.Type.Close):
                        self.guardar()
                except RuntimeError:
                    pass
                return False

            def guardar(self):
                objetivo = referencia()
                if not _objeto_qt_valido(objetivo):
                    return
                ajustes.setValue(clave, objetivo.saveGeometry())
                ajustes.sync()

        gestor = Gestor(widget)
        widget.installEventFilter(gestor)
        return gestor


def configurar_geometria_persistente(
    widget,
    clave,
    ideal,
    minimo,
    margen=24,
    piso=(280, 200),
):
    """Aplica tamaño adaptable, restaura geometría y la guarda al cerrar."""
    from PySide6.QtCore import QSettings, QTimer

    from logica import app_info

    ajustar_ventana_a_pantalla(widget, ideal, minimo, margen, piso)
    widget._config_geometria_adaptativa = {
        "ideal": tuple(ideal),
        "minimo": tuple(minimo),
        "margen": int(margen),
        "piso": tuple(piso),
    }
    ajustes = QSettings("LIBiAM", app_info.NOMBRE)
    geometria = ajustes.value(clave)
    restaurada = bool(geometria and widget.restoreGeometry(geometria))
    gestor = _GestorGeometriaVentana.crear(widget, ajustes, clave)
    widget._gestor_geometria_adaptativa = gestor
    if restaurada:
        referencia = weakref.ref(widget)
        QTimer.singleShot(0, lambda: _asegurar_referencia_visible(referencia))
    return restaurada, ajustes


def guardar_geometria(widget):
    gestor = getattr(widget, "_gestor_geometria_adaptativa", None)
    if gestor is not None:
        gestor.guardar()
