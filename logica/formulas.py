"""Cálculos sobre la fuerza vertical: potencia mecánica e impulso.

Independiente de la interfaz: recibe números y devuelve números.

En una plataforma de fuerza la potencia no se mide directamente, hace falta la
velocidad. Se obtiene por el método estándar (el que se usa para saltos):

    a(t) = (Fz(t) − m·g) / m        aceleración del centro de masa
    v(t) = ∫ a(t) dt                velocidad, partiendo del reposo
    P(t) = Fz(t) · v(t)             potencia instantánea, en watts

El impulso es la otra cara de la misma integral, sin dividir por la masa:

    J(t) = ∫ (Fz(t) − m·g) dt       impulso neto acumulado, en N·s

La integración se hace **una sola vez sobre el registro completo**, arrancando
de cero desde el primer frame del CSV (que se captura con el sujeto en
reposo). El rango seleccionado solo se usa para recortar y analizar un segmento
del resultado; nunca reinicia la condición inicial.

De ahí que el impulso **neto de un rango** sea la diferencia entre los extremos
de su recorte, no el último valor de la curva. Por el teorema del impulso
J = m·Δv, ese neto es el cambio de velocidad del tramo, y a diferencia de la
potencia no depende de que el rango arranque en reposo: solo el origen de la
curva acumulada lo hace.
"""

from __future__ import annotations

import math

import numpy as np


class ErrorFormula(ValueError):
    """El cálculo no se puede hacer (datos o parámetros insuficientes)."""


NOMBRE_POTENCIA = "Potencia"
EXPRESION_POTENCIA = "P = Fz · v,  con v = ∫ (Fz − m·g)/m dt"
UNIDAD_POTENCIA = "W"

NOMBRE_IMPULSO = "Impulso"
EXPRESION_IMPULSO = "J = ∫ (Fz − m·g) dt"
UNIDAD_IMPULSO = "N·s"

UNIDAD_VELOCIDAD = "m/s"


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
def _integrar_acumulado(valores, dt):
    """Integral acumulada por trapecios, arrancando de cero.

    Un solo integrador para la velocidad y para el impulso: si cambia la regla
    de integración, cambia para las dos a la vez.
    """
    valores = np.asarray(valores, dtype=float)
    if valores.size < 2:
        raise ErrorFormula("El tramo es demasiado corto para integrar.")
    incrementos = (valores[:-1] + valores[1:]) * 0.5 * dt
    return np.concatenate(([0.0], np.cumsum(incrementos)))

def fuerza_neta(fz, masa, gravedad):
    """Fz − m·g: el exceso de fuerza sobre el peso, que es lo que acelera."""
    return np.asarray(fz, dtype=float) - masa * gravedad

def aceleracion(fz, masa, gravedad):
    """a = (Fz − m·g) / m: aceleración del centro de masa."""
    return fuerza_neta(fz, masa, gravedad) / masa

def velocidad(fz, masa, gravedad, frecuencia):
    """Integra la aceleración por trapecios, partiendo del reposo (v = 0)."""
    return _integrar_acumulado(aceleracion(fz, masa, gravedad), 1.0 / frecuencia)

def potencia(fz, masa, gravedad, frecuencia):
    """P = Fz · v, en watts. ``fz`` en newtons, ``frecuencia`` en Hz."""
    masa, gravedad, frecuencia = _validar_parametros(masa, gravedad, frecuencia)
    fz = np.asarray(fz, dtype=float)
    return fz * velocidad(fz, masa, gravedad, frecuencia)

# --- Impulso -------------------------------------------------------------------------
def impulso(fz, masa, gravedad, frecuencia):
    """J = ∫ (Fz − m·g) dt acumulado, en N·s.

    Devuelve la curva acumulada, no un número: así se ve **dónde** se gana y se
    pierde impulso (la fase de frenado lo baja, la de propulsión lo sube).

    Igual que la potencia, se integra sobre el registro completo desde el
    primer frame. El impulso **neto de un rango** es entonces la diferencia
    entre sus extremos, no el último valor: de eso se encarga
    :func:`detalles_impulso`.

    Equivale exactamente a ``masa · velocidad(...)``, que es el teorema del
    impulso escrito con las funciones de este módulo.
    """
    masa, gravedad, frecuencia = _validar_parametros(masa, gravedad, frecuencia)
    return _integrar_acumulado(fuerza_neta(fz, masa, gravedad), 1.0 / frecuencia)

def detalles_impulso(valores, roles, contexto, eleccion=None):
    """Valores derivados del impulso de un tramo, listos para mostrar.

    ``valores`` es el recorte de la curva acumulada y ``roles`` el recorte de
    las señales de entrada. El neto sale de **restar los extremos** porque la
    integración arranca en el primer frame del registro, no en el rango.

    Las dos fases se informan por separado porque el neto es la resta entre
    ellas y ese número solo no dice cuál pesó más. El corte por signo integra
    cada parte aparte; en el cruce por cero el trapecio reparte de más, pero a
    las frecuencias de una plataforma el error queda muy por debajo de la
    resolución del gesto.
    """
    valores = np.asarray(valores, dtype=float)
    if valores.size < 2:
        return []

    masa = float(contexto["masa"])
    gravedad = float(contexto.get("gravedad", 9.8))
    frecuencia = float(contexto["frecuencia"])
    dt = 1.0 / frecuencia

    total = float(valores[-1] - valores[0])
    neta = fuerza_neta(roles["Fz"], masa, gravedad)

    return [
        {"etiqueta": "impulso neto", "valor": total, "unidad": UNIDAD_IMPULSO},
        # J = m·Δv: el cambio de velocidad no depende de cómo arranque el
        # tramo, a diferencia de la velocidad absoluta que usa la potencia.
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
        # Igual que la potencia: se integra el registro entero y el rango solo
        # recorta. El neto del tramo sale de restar los extremos del recorte.
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
        # El pico de una curva acumulada dice poco: lo que importa es el neto
        # del tramo, el Δv que implica y cómo se reparte entre las dos fases.
        "detalles": detalles_impulso,
    },
}


def descripcion_formula(clave):
    """Metadatos de una fórmula (nombre, unidad, rol origen, etc.)."""
    return FORMULAS[clave]


def nombre_con_articulo(clave_o_desc):
    """«la potencia», «el impulso»: para armar mensajes sin errores de género.

    El artículo va en el registro junto al nombre. Si no está declarado se usa
    «la», que era el único caso cuando la potencia era la única fórmula.
    """
    desc = (
        clave_o_desc
        if isinstance(clave_o_desc, dict)
        else FORMULAS[clave_o_desc]
    )
    return f"{desc.get('articulo', 'la')} {desc['nombre'].lower()}"


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
    """Valores extra de un tramo, si la fórmula define cómo calcularlos.

    Las fórmulas instantáneas (la potencia) se describen bien con el pico y la
    media del resumen. Las acumuladas necesitan sus propios números, y cada uno
    trae su unidad para que N·s y m/s convivan en el mismo bloque.
    """
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
                "detalles": _detalles_de(
                    desc, valores, seg_roles, contexto, eleccion
                ),
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
