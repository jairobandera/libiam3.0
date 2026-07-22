"""Configuración central de identidad y referencia de la aplicación.

Para publicar una nueva versión basta con editar los valores de esta primera
sección. El nombre visible y la referencia sugerida se generan automáticamente.
"""

NOMBRE_BASE = "ABS"
VERSION = "3.0"
ANIO = 2026
NOMBRE_COMPLETO = "Analysis of Biomechanical Signals"
AUTORES = (
    "Jairo Bandera",
    "Alan Ceballos",
    "Juan Macchi",
)
INSTITUCION = "Universidad Tecnológica (UTEC)"
LABORATORIO = "Laboratorio de Investigación en Biomecánica y Análisis del Movimiento (LIBiAM)"


NOMBRE = f"{NOMBRE_BASE} {VERSION}"
AUTORIA = ", ".join(AUTORES)
DESCRIPCION = (
    "Aplicación de escritorio para cargar, visualizar, filtrar y analizar "
    "señales biomecánicas exportadas en archivos CSV."
)
REFERENCIA = (
    f"{AUTORIA} ({ANIO}). {NOMBRE_COMPLETO} ({NOMBRE_BASE}, versión {VERSION}) "
    f"[Software]. {INSTITUCION}, {LABORATORIO}."
)
