"""Cálculo de potencia mecánica a partir de la fuerza vertical.

Independiente de la interfaz: recibe números y devuelve números.

En una plataforma de fuerza la potencia no se mide directamente, hace falta la
velocidad. Se obtiene por el método estándar (el que se usa para saltos):

    a(t) = (Fz(t) − m·g) / m        aceleración del centro de masa
    v(t) = ∫ a(t) dt                velocidad, partiendo del reposo
    P(t) = Fz(t) · v(t)             potencia instantánea, en watts

La integración se hace **una sola vez sobre el registro completo**, arrancando
con v = 0 desde el primer frame del CSV (que se captura con el sujeto en
reposo). El rango seleccionado solo se usa para recortar y analizar un segmento
del resultado; nunca reinicia la condición inicial de velocidad.
"""

from __future__ import annotations

import math

import numpy as np


class ErrorFormula(ValueError):
    """El cálculo no se puede hacer (datos o parámetros insuficientes)."""


NOMBRE_POTENCIA = "Potencia"
EXPRESION_POTENCIA = "P = Fz · v,  con v = ∫ (Fz − m·g)/m dt"
UNIDAD_POTENCIA = "W"


def _validar_parametros(masa, gravedad, frecuencia):
    """Comprueba lo que hace falta para poder integrar, con mensajes claros."""
    masa = float(masa or 0)
    gravedad = float(gravedad or 0)
    frecuencia = float(frecuencia or 0)

    if masa <= 0:
        raise ErrorFormula(
            "Cargá la masa del sujeto en el panel izquierdo para calcular la potencia."
        )
    if gravedad <= 0:
        raise ErrorFormula("La gravedad debe ser mayor que cero.")
    if frecuencia <= 0:
        raise ErrorFormula(
            "No se pudo determinar la frecuencia de muestreo del archivo, "
            "necesaria para integrar la velocidad."
        )
    return masa, gravedad, frecuencia

# -------------------------------------------------------------------------------------
# --- Aceleración, velocidad y potencia ------------------------------------------------
def aceleracion(fz, masa, gravedad):
    """a = (Fz − m·g) / m: aceleración del centro de masa."""
    fz = np.asarray(fz, dtype=float)
    return (fz - masa * gravedad) / masa

def velocidad(fz, masa, gravedad, frecuencia):
    """Integra la aceleración por trapecios, partiendo del reposo (v = 0)."""
    a = aceleracion(fz, masa, gravedad)
    if a.size < 2:
        raise ErrorFormula("El rango es demasiado corto para calcular la velocidad.")
    dt = 1.0 / frecuencia
    incrementos = (a[:-1] + a[1:]) * 0.5 * dt
    return np.concatenate(([0.0], np.cumsum(incrementos)))

def potencia(fz, masa, gravedad, frecuencia):
    """P = Fz · v, en watts. ``fz`` en newtons, ``frecuencia`` en Hz."""
    masa, gravedad, frecuencia = _validar_parametros(masa, gravedad, frecuencia)
    fz = np.asarray(fz, dtype=float)
    return fz * velocidad(fz, masa, gravedad, frecuencia)

# --- Presentación ------------------------------------------------------------
def formatear_valor(valor) -> str:
    if valor is None:
        return "—"
    valor = float(valor)
    if not math.isfinite(valor):
        return "—"

    magnitud = abs(valor)
    if magnitud >= 1000:
        texto = f"{valor:,.1f}"
    elif magnitud >= 1:
        texto = f"{valor:,.2f}"
    elif magnitud > 0:
        texto = f"{valor:.4g}"
    else:
        return "0"
    # Separador de miles con espacio fino, como se usa en informes técnicos.
    return texto.replace(",", " ")

# --- Resumen numérico --------------------------------------------------------
def resumen(x, y) -> dict:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mascara = np.isfinite(x) & np.isfinite(y)

    if not mascara.any():
        return {
            "pico": None, "x_pico": None, "minimo": None,
            "x_minimo": None, "media": None, "rms": None, "muestras": 0,
        }

    x_validos = x[mascara]
    y_validos = y[mascara]
    indice_pico = int(np.argmax(y_validos))
    indice_minimo = int(np.argmin(y_validos))

    return {
        "pico": float(y_validos[indice_pico]),
        "x_pico": float(x_validos[indice_pico]),
        "minimo": float(y_validos[indice_minimo]),
        "x_minimo": float(x_validos[indice_minimo]),
        "media": float(np.mean(y_validos)),
        "rms": float(np.sqrt(np.mean(y_validos**2))),
        "muestras": int(y_validos.size),
    }


# --- Registro de fórmulas --------------------------------------------------
# Una fórmula se define **una sola vez** acá; tanto el panel de rangos como la
# ventana de sub-rangos la consumen a través de ``computar_formula``.
def _potencia_desde(roles, contexto, eleccion=None):
    return potencia(
        roles["Fz"],
        contexto["masa"],
        contexto.get("gravedad", 9.8),
        contexto["frecuencia"],
    )

ROLES = {
    "Fx": ("Fuerza", "eje_x"), "Fy": ("Fuerza", "eje_y"),
    "Fz": ("Fuerza", "eje_z"),
    "Mx": ("Momento", "eje_x"), "My": ("Momento", "eje_y"),
    "Mz": ("Momento", "eje_z"),
    "Cx": ("COP", "eje_x"), "Cy": ("COP", "eje_y"),
    "Cz": ("COP", "eje_z"),
}


FORMULAS = {
    "potencia": {
        "nombre": NOMBRE_POTENCIA,
        "expresion": EXPRESION_POTENCIA,
        "unidad": UNIDAD_POTENCIA,
        "salida_rol": "Fz",
        "integra_en_registro": True,
        "requiere_roles": ("Fz",),
        "rangos_en_rol": {
            "rol": "Fz",
            "mensaje": "La potencia implementada en el sistema corresponde a la "
                       "potencia mecánica vertical y únicamente puede calcularse "
                       "sobre la fuerza vertical (Fz).",
        },
        "requiere": {
            "masa": "Cargá la masa del sujeto en el panel izquierdo para "
                    "poder calcular la potencia.",
            "gravedad": "La gravedad debe ser mayor que cero.",
            "frecuencia": "No se pudo determinar la frecuencia de muestreo "
                          "del archivo, necesaria para calcular la potencia.",
        },
        "computar": _potencia_desde,
    },
}


def descripcion_formula(clave):
    """Metadatos de una fórmula (nombre, unidad, rol origen, etc.)."""
    return FORMULAS[clave]


def hay_formula(clave):
    return clave in FORMULAS


def formula_predeterminada():
    """Primera fórmula del registro, para cuando no se eligió ninguna."""
    return next(iter(FORMULAS), None)


def validar_formula(clave, contexto, roles_disponibles=()):
    """Errores BLOQUEANTES: devuelve el motivo por el que no se puede calcular.

    Separada de ``resolver_roles`` (advertencias, no bloqueantes). Revisa:

    - que cada rol de ``requiere_roles`` esté entre ``roles_disponibles``, y
    - que las variables de ``requiere`` estén presentes en ``contexto``.

    Devuelve ``""`` si todo está en orden, o un mensaje claro para imprimir.
    """
    desc = FORMULAS[clave]
    disponibles = frozenset(roles_disponibles or ())
    for rol in desc.get("requiere_roles") or ():
        if rol not in disponibles:
            return (
                f"Necesito la señal {rol} para poder calcular "
                f"la {desc['nombre'].lower()}."
            )
    for variable, mensaje in (desc.get("requiere") or {}).items():
        valor = contexto.get(variable)
        if valor is None:
            return mensaje
        if isinstance(valor, (int, float)) and float(valor) <= 0:
            return mensaje
    return ""


def resolver_roles(clave, roles_disponibles=()):
    desc = FORMULAS[clave]
    disponibles = frozenset(roles_disponibles or ())
    roles = list(desc.get("requiere_roles") or ())
    eleccion = {}
    advertencias = []

    for ranura, spec in (desc.get("roles_opcionales") or {}).items():
        candidatos = (spec.get("candidatos") or ())
        recomendado = spec.get("recomendado")
        elegido = recomendado if recomendado in disponibles else None
        if elegido is None:
            for candidato in candidatos:
                if candidato in disponibles:
                    elegido = candidato
                    break
        eleccion[ranura] = elegido
        if elegido is None:
            continue
        roles.append(elegido)
        if elegido != recomendado:
            aviso = desc.get("advertencias", {}).get(elegido)
            encabezado = f"Se usó {elegido}"
            if recomendado:
                encabezado += f" (recomendado: {recomendado})"
            encabezado += "."
            advertencias.append(
                f"{encabezado} {aviso}" if aviso else encabezado
            )
    return roles, eleccion, advertencias


def computar_formula(clave, roles, x, contexto, intervalos, eleccion=None):
    desc = FORMULAS[clave]
    motivo = validar_formula(clave, contexto, set(roles))
    if motivo:
        raise ErrorFormula(motivo)

    resultados, segmentos = [], []
    frecuencia = contexto.get("frecuencia")

    # Máscara de validez común: se procesan las muestras finitas en orden, sin
    # interpolar los NaN (misma semántica para ambas rutas).
    finito = np.isfinite(x)
    for serie in roles.values():
        finito = finito & np.isfinite(serie)

    if desc.get("integra_en_registro"):
        if finito.sum() < 2:
            return resultados, segmentos
        x_reg = x[finito]
        roles_registro = {rol: serie[finito] for rol, serie in roles.items()}
        valores_registro = np.asarray(
            desc["computar"](roles_registro, contexto, eleccion), dtype=float
        )

        for datos in intervalos:
            desde, hasta = int(datos["desde"]), int(datos["hasta"])
            base = (x_reg >= desde) & (x_reg <= hasta)
            if base.sum() < 2:
                continue
            x_seg = x_reg[base]
            valores = valores_registro[base]
            datos_resumen = resumen(x_seg, valores)
            nombre_rango = datos.get("nombre") or f"Rango {datos.get('numero')}"

            resultados.append(
                {
                    "id": datos.get("id"),
                    "nombre": nombre_rango,
                    "senal": datos.get("senal", ""),
                    "desde": desde,
                    "hasta": hasta,
                    "duracion_s": (
                        (hasta - desde) / frecuencia if frecuencia else None
                    ),
                    "resumen": datos_resumen,
                }
            )
            segmentos.append((x_seg, valores))

        return resultados, segmentos

    # Cálculo por rango (fórmulas sin integración temporal): sin cambios.
    for datos in intervalos:
        desde, hasta = int(datos["desde"]), int(datos["hasta"])
        base = (x >= desde) & (x <= hasta)
        mascara = base & finito
        if mascara.sum() < 2:
            continue

        x_seg = x[mascara]
        seg_roles = {rol: serie[mascara] for rol, serie in roles.items()}
        valores = desc["computar"](seg_roles, contexto, eleccion)
        datos_resumen = resumen(x_seg, valores)
        nombre_rango = datos.get("nombre") or f"Rango {datos.get('numero')}"

        resultados.append(
            {
                "id": datos.get("id"),
                "nombre": nombre_rango,
                "senal": datos.get("senal", ""),
                "desde": desde,
                "hasta": hasta,
                "duracion_s": (
                    (hasta - desde) / frecuencia if frecuencia else None
                ),
                "resumen": datos_resumen,
            }
        )
        segmentos.append((x_seg, valores))

    return resultados, segmentos

def picos_de_resultados(resultados):
    """Marcadores para la gráfica (pico, frame, etiqueta) desde los resultados."""
    picos = []
    for datos in resultados:
        resumen_datos = datos.get("resumen") or {}
        pico = resumen_datos.get("pico")
        if pico is not None:
            picos.append(
                {
                    "x": resumen_datos["x_pico"],
                    "y": pico,
                    "etiqueta": datos["nombre"],
                    "resumen": resumen_datos,
                }
            )
    return picos

def concatenar_curva(segmentos):
    if not segmentos:
        return {"x": np.array([]), "y": np.array([])}
    x, y = [], []
    for indice, (sx, sy) in enumerate(segmentos):
        if indice:
            x.append(np.array([np.nan]))
            y.append(np.array([np.nan]))
        x.append(sx)
        y.append(sy)
    return {"x": np.concatenate(x), "y": np.concatenate(y)}
