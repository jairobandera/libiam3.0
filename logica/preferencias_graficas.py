"""Persistencia de preferencias visuales globales de las gráficas."""

from PySide6.QtCore import QSettings

from logica import app_info, paleta


CLAVE_COLOR_ORIGINAL = "graficas/color_senal_original"
CLAVE_COLOR_FILTRADA = "graficas/color_senal_filtrada"
CLAVE_MODO_ZOOM = "graficas/modo_zoom"

MODO_ZOOM_X = "x"
MODO_ZOOM_Y = "y"
MODO_ZOOM_XY = "xy"
MODOS_ZOOM = (MODO_ZOOM_X, MODO_ZOOM_Y, MODO_ZOOM_XY)

_modo_zoom_actual = MODO_ZOOM_X


def _ajustes():
    return QSettings("LIBiAM", app_info.NOMBRE)


def cargar_colores() -> dict:
    """Carga colores válidos y reemplaza valores dañados por los predeterminados."""
    ajustes = _ajustes()
    original = paleta.normalizar_color(ajustes.value(CLAVE_COLOR_ORIGINAL))
    filtrada = paleta.normalizar_color(ajustes.value(CLAVE_COLOR_FILTRADA))
    original = original or paleta.COLOR_ORIGINAL_PREDETERMINADO
    filtrada = filtrada or paleta.COLOR_FILTRADA_PREDETERMINADO
    paleta.set_colores_senales(original, filtrada)
    return paleta.colores_senales_configurados()


def guardar_colores(original, filtrada) -> dict:
    """Valida, aplica y guarda los dos colores de las señales."""
    paleta.set_colores_senales(original, filtrada)
    colores = paleta.colores_senales_configurados()
    ajustes = _ajustes()
    ajustes.setValue(CLAVE_COLOR_ORIGINAL, colores["senal_original"])
    ajustes.setValue(CLAVE_COLOR_FILTRADA, colores["senal_filtrada"])
    ajustes.sync()
    return colores


def restaurar_colores() -> dict:
    """Elimina la preferencia guardada y vuelve a la paleta estándar original."""
    ajustes = _ajustes()
    ajustes.remove(CLAVE_COLOR_ORIGINAL)
    ajustes.remove(CLAVE_COLOR_FILTRADA)
    ajustes.sync()
    paleta.restaurar_colores_senales()
    return paleta.colores_senales_configurados()


def _normalizar_modo_zoom(modo) -> str:
    modo = str(modo or "").strip().lower()
    return modo if modo in MODOS_ZOOM else MODO_ZOOM_X


def cargar_modo_zoom() -> str:
    """Carga el comportamiento de la rueda; X es el valor seguro por defecto."""
    global _modo_zoom_actual
    _modo_zoom_actual = _normalizar_modo_zoom(
        _ajustes().value(CLAVE_MODO_ZOOM, MODO_ZOOM_X)
    )
    return _modo_zoom_actual


def guardar_modo_zoom(modo) -> str:
    """Valida y conserva el eje o los ejes afectados por la rueda del mouse."""
    global _modo_zoom_actual
    _modo_zoom_actual = _normalizar_modo_zoom(modo)
    ajustes = _ajustes()
    ajustes.setValue(CLAVE_MODO_ZOOM, _modo_zoom_actual)
    ajustes.sync()
    return _modo_zoom_actual


def modo_zoom_actual() -> str:
    return _modo_zoom_actual


def restaurar_modo_zoom() -> str:
    global _modo_zoom_actual
    ajustes = _ajustes()
    ajustes.remove(CLAVE_MODO_ZOOM)
    ajustes.sync()
    _modo_zoom_actual = MODO_ZOOM_X
    return _modo_zoom_actual
