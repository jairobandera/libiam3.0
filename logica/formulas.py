"""Cálculos sobre la fuerza vertical: potencia mecánica e impulso.

Independiente de la interfaz: recibe números y devuelve números.

En una plataforma de fuerza la potencia no se mide directamente, hace falta la
velocidad. Se obtiene por el método estándar (el que se usa para saltos):

    a(t) = (Fz(t) − m·g) / m        aceleración del centro de masa
    v(t) = ∫ a(t) dt                velocidad, partiendo del reposo
    P(t) = Fz(t) · v(t)             potencia instantánea, en watts

El impulso es la otra cara de la misma integral, sin dividir por la masa:

    J(t) = ∫ (Fz(t) − m·g) dt       impulso neto acumulado, en N·s

Ambas integraciones se hacen **dentro de cada rango marcado**, arrancando de
cero. Para la potencia eso supone que el sujeto está quieto al inicio del
recorte, que es la condición habitual en un salto: el rango se marca desde la
posición estática previa.

El impulso no necesita ese supuesto. Por el teorema del impulso J = m·Δv, así
que el valor total de un rango da el **cambio** de velocidad, empiece el tramo
como empiece. Es lo que lo hace más robusto que la potencia cuando el rango no
arranca del reposo; el supuesto solo hace falta si se quiere la velocidad
absoluta.
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
            "Cargá la masa del sujeto en el panel izquierdo para hacer el cálculo."
        )
    if gravedad <= 0:
        raise ErrorFormula("La gravedad debe ser mayor que cero.")
    if frecuencia <= 0:
        raise ErrorFormula(
            "No se pudo determinar la frecuencia de muestreo del archivo, "
            "necesaria para integrar."
        )
    return masa, gravedad, frecuencia


def _integrar_acumulado(valores, dt):
    """Integral acumulada por trapecios, arrancando de cero.

    Una sola implementación para la velocidad y para el impulso: si algún día
    cambia la regla de integración, cambia para las dos a la vez.
    """
    valores = np.asarray(valores, dtype=float)
    if valores.size < 2:
        raise ErrorFormula(
            "El rango es demasiado corto para integrar: hacen falta al menos "
            "dos muestras."
        )
    # Regla del trapecio: cada paso suma el promedio de los dos extremos. Es
    # más exacta que la suma simple, sobre todo con señales con picos.
    incrementos = (valores[:-1] + valores[1:]) * 0.5 * dt
    return np.concatenate(([0.0], np.cumsum(incrementos)))


def fuerza_neta(fz, masa, gravedad):
    """Fz − m·g: el exceso de fuerza sobre el peso, que es lo que acelera.

    En reposo la plataforma ya mide m·g, así que ese valor no mueve nada.
    """
    return np.asarray(fz, dtype=float) - masa * gravedad


def aceleracion(fz, masa, gravedad):
    """a = (Fz − m·g) / m: aceleración del centro de masa."""
    return fuerza_neta(fz, masa, gravedad) / masa


def velocidad(fz, masa, gravedad, frecuencia):
    """Integra la aceleración por trapecios, partiendo del reposo (v = 0)."""
    return _integrar_acumulado(
        aceleracion(fz, masa, gravedad), 1.0 / frecuencia
    )


def potencia(fz, masa, gravedad, frecuencia):
    """P = Fz · v, en watts. ``fz`` en newtons, ``frecuencia`` en Hz."""
    masa, gravedad, frecuencia = _validar_parametros(masa, gravedad, frecuencia)
    fz = np.asarray(fz, dtype=float)
    return fz * velocidad(fz, masa, gravedad, frecuencia)


def impulso(fz, masa, gravedad, frecuencia):
    """J = ∫ (Fz − m·g) dt acumulado, en N·s.

    Devuelve la curva acumulada, no un único número: así se ve **dónde** se
    gana y se pierde impulso dentro del rango (la fase de frenado lo baja, la
    de propulsión lo sube). El valor final es el impulso neto del tramo.

    Equivale exactamente a ``masa · velocidad(...)``, que es el teorema del
    impulso escrito con las funciones de este módulo.
    """
    masa, gravedad, frecuencia = _validar_parametros(masa, gravedad, frecuencia)
    return _integrar_acumulado(
        fuerza_neta(fz, masa, gravedad), 1.0 / frecuencia
    )


def detalles_impulso(valores, fz, masa, gravedad, frecuencia) -> list:
    """Valores derivados del impulso de un rango, listos para mostrar.

    ``valores`` es la curva que devuelve :func:`impulso`. Se separan las dos
    fases porque en un gesto real el impulso neto es la resta entre ellas y el
    número solo no dice cuál pesó más.

    El corte por signo integra cada parte por separado; en el cruce por cero el
    trapecio reparte de más, pero a las frecuencias de una plataforma (cientos
    o miles de Hz) el error queda muy por debajo de la resolución del gesto.
    """
    masa, gravedad, frecuencia = _validar_parametros(masa, gravedad, frecuencia)
    valores = np.asarray(valores, dtype=float)
    if valores.size == 0:
        return []

    neta = fuerza_neta(fz, masa, gravedad)
    dt = 1.0 / frecuencia
    total = float(valores[-1])

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


# Metadatos de cada fórmula, para que la interfaz no repita nombres ni unidades.
CLAVE_POTENCIA = "potencia"
CLAVE_IMPULSO = "impulso"

FORMULAS = {
    CLAVE_POTENCIA: {
        "nombre": NOMBRE_POTENCIA,
        "expresion": EXPRESION_POTENCIA,
        "unidad": UNIDAD_POTENCIA,
        "calcular": potencia,
        "descripcion": (
            "Potencia instantánea. Integra la velocidad desde el reposo dentro "
            "de cada rango, así que el tramo tiene que arrancar con el sujeto "
            "quieto."
        ),
    },
    CLAVE_IMPULSO: {
        "nombre": NOMBRE_IMPULSO,
        "expresion": EXPRESION_IMPULSO,
        "unidad": UNIDAD_IMPULSO,
        "calcular": impulso,
        "descripcion": (
            "Impulso neto acumulado. El valor final de cada rango es el cambio "
            "de velocidad por la masa (J = m·Δv), sin suponer que el tramo "
            "arranca del reposo."
        ),
    },
}


def formula(clave) -> dict:
    """Metadatos de una fórmula; cae en potencia si la clave no se conoce."""
    return FORMULAS.get(clave, FORMULAS[CLAVE_POTENCIA])


# --- Presentación ------------------------------------------------------------


def formatear_valor(valor) -> str:
    """Número legible para la interfaz, sin notación científica.

    ``%g`` pasa a ``1.14e+03`` justo en los valores más comunes, que es lo
    último que quiere leer alguien mirando un pico.
    """
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
    """Valores destacados de una curva, para mostrarle al usuario.

    Devuelve ``None`` en los campos que no se puedan calcular en vez de
    reventar: una señal puede venir entera en NaN.
    """
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
