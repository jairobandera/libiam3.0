"""Configuración central de identidad y referencia de la aplicación.

Para publicar una nueva versión basta con editar los valores de esta primera
sección. El nombre visible y la referencia sugerida se generan automáticamente.
"""

NOMBRE_BASE = "ABS"
VERSION = "3.0"
ANIO = 2026
NOMBRE_COMPLETO = "Analysis of Biomechanical Signal"
NOMBRE_COMPLETO_ES = "Análisis Biomecánico de Señales"
ALCANCE_VERSION = "datos cinéticos — plataforma de fuerza"
AUTORES = (
    "Jairo Bandera",
    "Alan Ceballos",
    "Juan Macchi",
)
TUTORES = (
    "Marcelo Scotto (UTEC)",
    "Artur Bonezi (UdelaR)",
)
INSTITUCION = "Universidad Tecnológica (UTEC)"
LABORATORIO = (
    "Laboratorio de Investigación en Biomecánica y Análisis del Movimiento "
    "(LIBiAM) — DCB — Cenur Litoral Norte — UdelaR"
)
LABORATORIO_CABECERA = (
    "Laboratorio de Investigación en Biomecánica y Análisis del Movimiento "
    "(LIBiAM)"
)
LABORATORIO_CORTO = "LIBiAM — DCB — CenurLN — UdelaR"


NOMBRE = f"{NOMBRE_BASE} {VERSION}"
AUTORIA = ", ".join(AUTORES)
TUTORIA = " y ".join(TUTORES)
DESCRIPCION = (
    "Aplicación de escritorio para cargar, visualizar, filtrar y analizar "
    "señales biomecánicas exportadas en archivos CSV."
)
REFERENCIA_INGLES = (
    f"{NOMBRE_COMPLETO} ({NOMBRE_BASE}) — version {VERSION} for Windows & "
    f"macOS. Paysandú: Software LIBiAM (UdelaR) & Universidad Tecnológica "
    f"(UTEC) ({ANIO})."
)
REFERENCIA_ESPANOL = (
    f"{NOMBRE_COMPLETO_ES} ({NOMBRE_BASE}) — versión {VERSION} para Windows y "
    f"macOS. Paysandú: Aplicación LIBiAM (UdelaR) y Universidad Tecnológica "
    f"(UTEC) ({ANIO})."
)
REFERENCIA = (
    f"English:\n{REFERENCIA_INGLES}\n\n"
    f"Español:\n{REFERENCIA_ESPANOL}"
)
