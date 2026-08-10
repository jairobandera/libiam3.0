"""Paletas de color de las gráficas, según el modo visual y la accesibilidad.

La aplicación tiene varias paletas y una sola activa por vez. El modo es una
opción de sesión (se elige en «Configurar» y no se guarda en la base de datos),
así que este módulo guarda el estado y el resto de la interfaz le pregunta el
color en vez de escribirlo a mano.

Existen cuatro paletas:

* ``estandar``: la paleta por defecto, la que se usa hoy.
* ``rojo_verde``: serie de **Okabe & Ito (2008)**, apta para deuteranopía,
  protanopía y deuteranomalía/protanomalía. Tiene menos colores que la
  estándar a propósito: agregar tonos rompería justamente esa garantía.
* ``azul_amarillo``: variante para tritanomalía y tritanopía. En esta
  deficiencia se confunden sobre todo estos pares —azul↔verde, amarillo↔rojo,
  violeta↔rojo y amarillo↔rosado—, así que la paleta los separa por tonalidad y
  por luminancia en vez de eliminar los colores (no busca simular la visión,
  solo dar una configuración visual con menos ambigüedades).
* ``completa``: escala de grises por luminancia para la acromatopsia /
  monocromatismo, donde solo se diferencia el brillo.

La arquitectura permite agregar más modos añadiendo una entrada a ``PALETAS``;
cada paleta requiere su fuente o criterio documentado, no colores inventados.
"""

from __future__ import annotations


MODO_ESTANDAR = "estandar"
MODO_ROJO_VERDE = "rojo_verde"
MODO_AZUL_AMARILLO = "azul_amarillo"
MODO_COMPLETO = "completo"

# Alias histórico: los consumidores antiguos (``set_modo_daltonico``, rangos.py
# y tests) seguían hablando del antiguo modo booleano «daltónico». Ahora ese
# modo es la paleta rojo-verde; se mantiene la constante para no romperlos.
MODO_DALTONICO = MODO_ROJO_VERDE


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
    MODO_ROJO_VERDE: {
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
        # Violeta rosado: se separa del celeste y del naranja en los tres.
        "senal_formula": "#CC79A7",
        # Amarillo para la selección: no se confunde con el naranja de la
        # señal filtrada en ninguno de los tres tipos de daltonismo.
        "seleccion": "#F0E442",
    },
    MODO_AZUL_AMARILLO: {
        # Variante para tritanomalía/tritanopía. El criterio es el de la
        # investigación sobre esa deficiencia: los pares azul↔verde,
        # amarillo↔rojo, violeta↔rojo y amarillo↔rosado se confunden.
        "rangos": (
            "#C0392B",  # rojo oscuro
            "#E67E22",  # naranja
            "#43A047",  # verde claro
            "#8E44AD",  # violeta
            "#F1C40F",  # amarillo
            "#1B4F9E",  # azul oscuro
            "#7B7D7D",  # gris
        ),
        "senal_original": "#E67E22",
        "senal_filtrada": "#1E8449",
        "senal_formula": "#8E44AD",
        "seleccion": "#F1C40F",
    },
    MODO_COMPLETO: {
        # Del gris más claro al más oscuro: en acromatopsia solo importa el
        # brillo, así que la secuencia es una rampa de luminancia decreciente.
        "rangos": (
            "#F4F4F4",
            "#DCDCDC",
            "#C4C4C4",
            "#ACACAC",
            "#949494",
            "#7C7C7C",
        ),
        "senal_original": "#F0F0F0",
        "senal_filtrada": "#A8A8A8",
        "senal_formula": "#D8D8D8",
        "seleccion": "#9E9E9E",
    },
}

# Nombre humano de cada color, para la opción «mostrar el nombre del color en
# el rango» (se muestra en el tooltip). Un mismo hex vale en todas las paletas.
NOMBRES_COLOR = {
    # Paleta estándar.
    "#42A5F5": "azul",
    "#66BB6A": "verde",
    "#FFCA28": "amarillo",
    "#AB47BC": "violeta",
    "#FF7043": "naranja",
    "#26C6DA": "cian",
    "#EC407A": "rosa",
    "#9CCC65": "verde claro",
    "#7E57C2": "morado",
    "#FFA726": "naranja claro",
    "#26A69A": "verde azulado",
    "#5C6BC0": "azul índigo",
    "#4FC3F7": "azul claro",
    "#FFB300": "ámbar",
    "#FFB74D": "naranja claro",
    # Paleta rojo-verde (Okabe & Ito).
    "#56B4E9": "celeste",
    "#E69F00": "naranja",
    "#009E73": "verde azulado",
    "#CC79A7": "violeta rosado",
    "#F0E442": "amarillo",
    "#0072B2": "azul",
    "#D55E00": "bermellón",
    # Paleta azul-amarillo (tritanomalía/tritanopía).
    "#C0392B": "rojo oscuro",
    "#E67E22": "naranja",
    "#43A047": "verde claro",
    "#8E44AD": "violeta",
    "#F1C40F": "amarillo",
    "#1B4F9E": "azul oscuro",
    "#7B7D7D": "gris",
    "#1E8449": "verde oscuro",
    # Paleta completa (escala de grises).
    "#F4F4F4": "blanco",
    "#DCDCDC": "gris muy claro",
    "#C4C4C4": "gris claro",
    "#ACACAC": "gris medio claro",
    "#949494": "gris medio",
    "#7C7C7C": "gris oscuro",
    "#F0F0F0": "blanco",
    "#A8A8A8": "gris",
    "#D8D8D8": "gris claro",
    "#9E9E9E": "gris",
}


_modo_actual = MODO_ESTANDAR


def modo_actual() -> str:
    return _modo_actual


def modo_accesible_activo() -> bool:
    """``True`` cuando la paleta activa es una de accesibilidad (no la estándar)."""
    return _modo_actual != MODO_ESTANDAR


def modo_daltonico_activo() -> bool:
    # Alias de compatibilidad: algunas partes de la interfaz consultan este
    # nombre histórico para cambiar un detalle visual (p. ej. el ✓/✕).
    return modo_accesible_activo()


def set_modo_visual(modo: str) -> bool:
    """Cambia la paleta activa. Devuelve ``True`` si el modo cambió de verdad.

    ``modo`` debe ser una clave de ``PALETAS``. Si llega un modo desconocido no
    se toca nada.
    """
    global _modo_actual
    if modo not in PALETAS:
        return False
    if modo == _modo_actual:
        return False
    _modo_actual = modo
    return True


def set_modo_daltonico(activo: bool) -> bool:
    """Compatibilidad: activar → paleta rojo-verde; desactivar → estándar."""
    return set_modo_visual(MODO_ROJO_VERDE if activo else MODO_ESTANDAR)


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


def nombre_color(color: str) -> str:
    """Nombre humano de un color, o el propio hex si no es conocido."""
    valor = (color or "").upper()
    if not valor.startswith("#"):
        valor = "#" + valor
    return NOMBRES_COLOR.get(valor, valor)
