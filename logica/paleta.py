"""Paletas de color de las gráficas, con una variante accesible para daltonismo.

La aplicación tiene dos paletas y una sola activa por vez. El modo es una
opción de sesión (se elige en «Configurar» y no se guarda en la base de datos),
así que este módulo guarda el estado y el resto de la interfaz le pregunta el
color en vez de escribirlo a mano.

La paleta accesible usa la serie de **Okabe & Ito (2008)**, diseñada para
distinguirse bajo deuteranopía, protanopía y tritanopía, que cubren la enorme
mayoría de los casos de daltonismo. Tiene menos colores que la estándar a
propósito: agregar más tonos rompería justamente esa garantía, así que los
rangos vuelven a empezar el ciclo antes.
"""

from __future__ import annotations


MODO_ESTANDAR = "estandar"
MODO_DALTONICO = "daltonico"


PALETAS = {
    MODO_ESTANDAR: {
        "rangos": (
            "#42A5F5",
            "#66BB6A",
            "#FFCA28",
            "#AB47BC",
            "#FF7043",
            "#26C6DA",
            "#EC407A",
            "#9CCC65",
            "#7E57C2",
            "#FFA726",
            "#26A69A",
            "#5C6BC0",
        ),
        "senal_original": "#4FC3F7",
        "senal_filtrada": "#FFB300",
        "senal_formula": "#66BB6A",
        "seleccion": "#FFB74D",
    },
    MODO_DALTONICO: {
        # Okabe & Ito, sin el negro (ilegible sobre el fondo #1E1E1E).
        "rangos": (
            "#56B4E9",  # celeste
            "#E69F00",  # naranja
            "#009E73",  # verde azulado
            "#CC79A7",  # violeta rosado
            "#F0E442",  # amarillo
            "#0072B2",  # azul
            "#D55E00",  # bermellón
        ),
        "senal_original": "#56B4E9",
        "senal_filtrada": "#E69F00",
        # Violeta rosado: se separa del celeste y del naranja en los tres tipos.
        "senal_formula": "#CC79A7",
        # Amarillo para la selección: no se confunde con el naranja de la
        # señal filtrada en ninguno de los tres tipos de daltonismo.
        "seleccion": "#F0E442",
    },
}


_modo_actual = MODO_ESTANDAR


def modo_actual() -> str:
    return _modo_actual


def modo_daltonico_activo() -> bool:
    return _modo_actual == MODO_DALTONICO


def set_modo_daltonico(activo: bool) -> bool:
    """Cambia la paleta activa. Devuelve ``True`` si el modo realmente cambió."""
    global _modo_actual
    nuevo = MODO_DALTONICO if activo else MODO_ESTANDAR
    if nuevo == _modo_actual:
        return False
    _modo_actual = nuevo
    return True


def colores_rangos() -> tuple:
    return PALETAS[_modo_actual]["rangos"]


def color_rango(numero: int) -> str:
    """Color que le corresponde al rango ``numero`` en la paleta activa.

    Es determinístico: el mismo número siempre da el mismo color dentro de un
    modo, así al prender y apagar el modo los rangos vuelven a su color previo.
    """
    colores = colores_rangos()
    return colores[(int(numero) - 1) % len(colores)]


def color_senal_original() -> str:
    return PALETAS[_modo_actual]["senal_original"]


def color_senal_filtrada() -> str:
    return PALETAS[_modo_actual]["senal_filtrada"]


def color_senal_formula() -> str:
    return PALETAS[_modo_actual]["senal_formula"]


def color_seleccion() -> str:
    return PALETAS[_modo_actual]["seleccion"]
