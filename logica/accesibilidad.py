"""Estado de sesión del modo accesible y de las opciones de renderizado.

Separa dos responsabilidades que antes convivían en la paleta:

* ``logica/paleta.py`` es la única fuente de verdad de los **colores**.
* Este módulo guarda el **estado** del modo accesible (activado o no), el tipo
  de visión cromática elegido y las opciones adicionales de renderizado (grosor
  de líneas, estilos de línea diferenciados y nombre del color en el intervalo).

Como en las demás opciones de sesión, nada de esto se persiste: se elige en
«Configurar» y vuelve a los valores por defecto al reiniciar la aplicación.

Con el modo accesible **desactivado** todo se comporta exactamente como hoy:
la paleta activa es la estándar, los grosores y estilos de línea son los
originales y no se muestra el nombre de los colores. Este módulo solo cambia
el comportamiento cuando ``activo()`` devuelve ``True``.
"""

from __future__ import annotations

from logica import paleta


# --- Tipos de visión cromática disponibles en la interfaz -------------------

# Se reutilizan las claves de ``paleta.PALETAS``: el color siempre lo define la
# paleta y aquí solo se recuerda cuál está activa.
TIPO_ROJO_VERDE = paleta.MODO_ROJO_VERDE
TIPO_AZUL_AMARILLO = paleta.MODO_AZUL_AMARILLO
TIPO_COMPLETO = paleta.MODO_COMPLETO

# Los modos que hoy se ofrecen al usuario. La arquitectura admite sumar más
# agregando una paleta respaldada por una fuente o criterio en
# ``paleta.PALETAS`` y su clave aquí.
TIPOS_DISPONIBLES = (
    TIPO_ROJO_VERDE,
    TIPO_AZUL_AMARILLO,
    TIPO_COMPLETO,
)
# --- Tipos de línea (señal original, filtrada y de fórmula) -----------------
TIPO_LINEA_ORIGINAL = "original"
TIPO_LINEA_FILTRADA = "filtrada"
TIPO_LINEA_FORMULA = "formula"
TIPO_LINEA_INTERVALO = "intervalo"
TIPOS_LINEA = (
    TIPO_LINEA_ORIGINAL,
    TIPO_LINEA_FILTRADA,
    TIPO_LINEA_FORMULA,
    TIPO_LINEA_INTERVALO,
)
# Estilos simbólicos: la capa gráfica los traduce al enum de Qt (SolidLine,
# DashLine, DotLine). Mantenerlos aquí evita hardcodear estilos en la UI.
ESTILO_SOLIDA = "solida"
ESTILO_DISCONTINUA = "discontinua"
ESTILO_PUNTEADA = "punteada"

# Grosor base de cada tipo de línea, el que se usa hoy con el modo desactivado.
_ANCHO_BASE = {
    TIPO_LINEA_ORIGINAL: 1.2,
    TIPO_LINEA_FILTRADA: 2.2,
    TIPO_LINEA_FORMULA: 2.0,
    TIPO_LINEA_INTERVALO: 2.0,
}

# Factor de ampliación del grosor cuando está activa «Aumentar las líneas».
# Es un valor visual empírico (no hay norma que lo fije): basta notarse como
# un paso perceptible sobre el grosor base. Ajustar aquí si se quiere otro.
_FACTOR_GROSOR = 1.7

# --- Estado de sesión --------------------------------------------------------
_activo = False
_tipo_vision = None
_mostrar_nombre_color = True
_estilos_linea = True
_aumentar_grosor = True

def activo() -> bool:
    """``True`` cuando el modo accesible está activado."""
    return _activo

def tipo_vision():
    """Tipo de visión cromática elegido, o ``None`` si no se eligió ninguno."""
    return _tipo_vision

def mostrar_nombre_color() -> bool:
    """Opcion «Mostrar nombre del color en el intervalo» (independiente del modo)."""
    return _mostrar_nombre_color

def estilos_linea_activos() -> bool:
    return _estilos_linea

def aumentar_grosor_activo() -> bool:
    return _aumentar_grosor

def _sincronizar_paleta() -> None:
    """Aplica en la paleta el modo que corresponde al estado actual.

    Solo se llama cuando cambia ``activo`` o el tipo de visión. Con el modo
    desactivado la paleta vuelve siempre a la estándar.
    """
    if _activo and _tipo_vision is not None:
        paleta.set_modo_visual(_tipo_vision)
    elif not _activo:
        paleta.set_modo_visual(paleta.MODO_ESTANDAR)

def set_activo(valor: bool) -> None:
    """Activa o desactiva el modo accesible, sincronizando la paleta."""
    global _activo
    _activo = bool(valor)
    _sincronizar_paleta()

def set_tipo_vision(tipo) -> None:
    """Elige el tipo de visión cromática (una clave de ``TIPOS_DISPONIBLES``).

    Si se pasa un tipo desconocido no se cambia nada.
    """
    global _tipo_vision
    if tipo not in TIPOS_DISPONIBLES:
        return
    _tipo_vision = tipo
    _sincronizar_paleta()

def set_mostrar_nombre_color(valor: bool) -> None:
    global _mostrar_nombre_color
    _mostrar_nombre_color = bool(valor)

def set_estilos_linea(valor: bool) -> None:
    global _estilos_linea
    _estilos_linea = bool(valor)

def set_aumentar_grosor(valor: bool) -> None:
    global _aumentar_grosor
    _aumentar_grosor = bool(valor)

# --- Opciones de renderizado -------------------------------------------------

def grosor_senal(tipo_linea: str) -> float:
    """Grosor de la línea ``tipo_linea`` según las opciones activas.

    Las opciones solo aplican con el modo accesible activado: si está
    desactivado se devuelve siempre el grosor base (el actual), aunque la
    opción «Aumentar grosor» esté marcada. Un tipo desconocido devuelve el
    grosor base de la original.
    """
    base = _ANCHO_BASE.get(tipo_linea, _ANCHO_BASE[TIPO_LINEA_ORIGINAL])
    if _activo and _aumentar_grosor:
        return round(base * _FACTOR_GROSOR, 2)
    return base

def grosor_intervalo() -> float:
    """Grosor de los bordes de los intervalos/sub-intervalos según las opciones."""
    return grosor_senal(TIPO_LINEA_INTERVALO)

def estilo_linea(tipo_linea: str) -> str:
    """Estilo simbólico de la línea ``tipo_linea``.

    Solo con el modo accesible activo **y** la opción «Estilos de línea
    diferenciados» marcada los tipos usan estilos distintos. En cualquier otro
    caso (modo desactivado u opción desmarcada) todos vuelven a la línea
    sólida.
    """
    if not (_activo and _estilos_linea):
        return ESTILO_SOLIDA

    estilos = {
        TIPO_LINEA_ORIGINAL: ESTILO_PUNTEADA,
        TIPO_LINEA_FILTRADA: ESTILO_SOLIDA,
        TIPO_LINEA_FORMULA: ESTILO_DISCONTINUA,
    }
    return estilos.get(tipo_linea, ESTILO_SOLIDA)


def reiniciar() -> None:
    """Vuelve el estado a los valores por defecto (sin tocar la paleta).

    Útil para los tests y para no arrastrar estado entre pruebas.
    """
    global _activo, _tipo_vision, _mostrar_nombre_color, _estilos_linea
    global _aumentar_grosor
    _activo = False
    _tipo_vision = None
    _mostrar_nombre_color = True
    _estilos_linea = True
    _aumentar_grosor = True
