"""Cálculos de potencia e impulso usados por la aplicación."""

from __future__ import annotations

import math

import numpy as np


class ErrorFormula(ValueError):
    pass


NOMBRE_POTENCIA = "Potencia"
EXPRESION_POTENCIA = "P = Fz · v,  con v = ∫ (Fz − m·g)/m dt"
UNIDAD_POTENCIA = "W"

NOMBRE_IMPULSO = "Impulso"
EXPRESION_IMPULSO = "J = ∫ (Fz − m·g) dt"
UNIDAD_IMPULSO = "N·s"

UNIDAD_VELOCIDAD = "m/s"


def _validar_parametros(masa, gravedad, frecuencia):
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

def _integrar_acumulado(valores, dt):
    """Integra por trapecios y devuelve una curva que comienza en cero."""
    valores = np.asarray(valores, dtype=float)
    if valores.size < 2:
        raise ErrorFormula("El tramo es demasiado corto para integrar.")
    incrementos = (valores[:-1] + valores[1:]) * 0.5 * dt
    return np.concatenate(([0.0], np.cumsum(incrementos)))

def fuerza_neta(fz, masa, gravedad):
    return np.asarray(fz, dtype=float) - masa * gravedad

def aceleracion(fz, masa, gravedad):
    return fuerza_neta(fz, masa, gravedad) / masa

def velocidad(fz, masa, gravedad, frecuencia):
    return _integrar_acumulado(aceleracion(fz, masa, gravedad), 1.0 / frecuencia)

def potencia(fz, masa, gravedad, frecuencia):
    masa, gravedad, frecuencia = _validar_parametros(masa, gravedad, frecuencia)
    fz = np.asarray(fz, dtype=float)
    return fz * velocidad(fz, masa, gravedad, frecuencia)

def impulso(fz, masa, gravedad, frecuencia):
    """Devuelve el impulso acumulado desde el inicio del registro."""
    masa, gravedad, frecuencia = _validar_parametros(masa, gravedad, frecuencia)
    return _integrar_acumulado(fuerza_neta(fz, masa, gravedad), 1.0 / frecuencia)

def detalles_impulso(valores, roles, contexto, eleccion=None):
    """Resume el cambio neto y las fases propulsiva y de frenado."""
    valores = np.asarray(valores, dtype=float)
    if valores.size < 2:
        return []

    masa = float(contexto["masa"])
    gravedad = float(contexto.get("gravedad", 9.8))
    frecuencia = float(contexto["frecuencia"])
    dt = 1.0 / frecuencia

    # La curva ya está acumulada; el tramo es la diferencia entre sus extremos.
    total = float(valores[-1] - valores[0])
    neta = fuerza_neta(roles["Fz"], masa, gravedad)

    return [
        {"etiqueta": "impulso neto", "valor": total, "unidad": UNIDAD_IMPULSO},
        {"etiqueta": "Δ velocidad", "valor": total / masa, "unidad": UNIDAD_VELOCIDAD},
        {
            "etiqueta": "propulsivo",
            "valor": float(_integrar_acumulado(np.clip(neta, 0.0, None), dt)[-1]),
            "unidad": UNIDAD_IMPULSO,
        },
        {
            "etiqueta": "frenado",
            "valor": float(_integrar_acumulado(np.clip(neta, None, 0.0), dt)[-1]),
            "unidad": UNIDAD_IMPULSO,
        },
    ]

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
    # Separa los miles con espacios para evitar la notación científica.
    return texto.replace(",", " ")

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


# La interfaz obtiene de este registro las fórmulas disponibles.
def _potencia_desde(roles, contexto, eleccion=None):
    return potencia(
        roles["Fz"],
        contexto["masa"],
        contexto.get("gravedad", 9.8),
        contexto["frecuencia"],
    )

def _impulso_desde(roles, contexto, eleccion=None):
    return impulso(
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
        "articulo": "la",
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
    "impulso": {
        "nombre": NOMBRE_IMPULSO,
        "articulo": "el",
        "expresion": EXPRESION_IMPULSO,
        "unidad": UNIDAD_IMPULSO,
        "salida_rol": "Fz",
        "integra_en_registro": True,
        "requiere_roles": ("Fz",),
        "rangos_en_rol": {
            "rol": "Fz",
            "mensaje": "El impulso se calcula sobre la componente vertical de "
                       "la fuerza (Fz), que es la que acelera al sujeto contra "
                       "la gravedad.",
        },
        "requiere": {
            "masa": "Cargá la masa del sujeto en el panel izquierdo para "
                    "poder calcular el impulso.",
            "gravedad": "La gravedad debe ser mayor que cero.",
            "frecuencia": "No se pudo determinar la frecuencia de muestreo "
                          "del archivo, necesaria para calcular el impulso.",
        },
        "computar": _impulso_desde,
        "detalles": detalles_impulso,
    },
}


def descripcion_formula(clave):
    return FORMULAS[clave]


def nombre_con_articulo(clave_o_desc):
    desc = (
        clave_o_desc
        if isinstance(clave_o_desc, dict)
        else FORMULAS[clave_o_desc]
    )
    return f"{desc.get('articulo', 'la')} {desc['nombre'].lower()}"


def hay_formula(clave):
    return clave in FORMULAS


def formula_predeterminada():
    return next(iter(FORMULAS), None)


def validar_formula(clave, contexto, roles_disponibles=()):
    """Devuelve un mensaje cuando falta una señal o un parámetro requerido."""
    desc = FORMULAS[clave]
    disponibles = frozenset(roles_disponibles or ())
    for rol in desc.get("requiere_roles") or ():
        if rol not in disponibles:
            return (
                f"Necesito la señal {rol} para poder calcular "
                f"{nombre_con_articulo(desc)}."
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


def _detalles_de(desc, valores, roles_tramo, contexto, eleccion):
    calcular = desc.get("detalles")
    if not calcular:
        return []
    return calcular(valores, roles_tramo, contexto, eleccion)


def computar_formula(clave, roles, x, contexto, intervalos, eleccion=None):
    desc = FORMULAS[clave]
    motivo = validar_formula(clave, contexto, set(roles))
    if motivo:
        raise ErrorFormula(motivo)

    resultados, segmentos = [], []
    frecuencia = contexto.get("frecuencia")

    # Se omiten las posiciones inválidas sin inventar valores intermedios.
    finito = np.isfinite(x)
    for serie in roles.values():
        finito = finito & np.isfinite(serie)

    if desc.get("integra_en_registro"):
        # Las curvas acumuladas se calculan una vez y después se recortan.
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
                    "detalles": _detalles_de(
                        desc,
                        valores,
                        {rol: serie[base] for rol, serie in roles_registro.items()},
                        contexto,
                        eleccion,
                    ),
                }
            )
            segmentos.append((x_seg, valores))

        return resultados, segmentos

    # Las demás fórmulas se calculan por separado en cada rango.
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
                "detalles": _detalles_de(
                    desc, valores, seg_roles, contexto, eleccion
                ),
            }
        )
        segmentos.append((x_seg, valores))

    return resultados, segmentos

def picos_de_resultados(resultados):
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
