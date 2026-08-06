"""Cálculo de potencia mecánica a partir de la fuerza vertical.

Independiente de la interfaz: recibe números y devuelve números.

En una plataforma de fuerza la potencia no se mide directamente, hace falta la
velocidad. Se obtiene por el método estándar (el que se usa para saltos):

    a(t) = (Fz(t) − m·g) / m        aceleración del centro de masa
    v(t) = ∫ a(t) dt                velocidad, partiendo del reposo
    P(t) = Fz(t) · v(t)             potencia instantánea, en watts

La integración se hace **dentro de cada rango marcado**, arrancando de v = 0.
Eso supone que el sujeto está quieto al inicio del recorte, que es la condición
habitual en un salto: el rango se marca desde la posición estática previa.
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


def aceleracion(fz, masa, gravedad):
    """a = (Fz − m·g) / m: aceleración del centro de masa.

    Se le resta el peso porque en reposo la plataforma ya mide m·g: lo que
    acelera al sujeto es únicamente el exceso de fuerza sobre ese valor.
    """
    fz = np.asarray(fz, dtype=float)
    return (fz - masa * gravedad) / masa


def velocidad(fz, masa, gravedad, frecuencia):
    """Integra la aceleración por trapecios, partiendo del reposo (v = 0)."""
    a = aceleracion(fz, masa, gravedad)
    if a.size < 2:
        raise ErrorFormula("El rango es demasiado corto para calcular la velocidad.")

    dt = 1.0 / frecuencia
    # Regla del trapecio: cada paso suma el promedio de las dos aceleraciones.
    # Es más exacta que la suma simple, sobre todo con señales con picos.
    incrementos = (a[:-1] + a[1:]) * 0.5 * dt
    return np.concatenate(([0.0], np.cumsum(incrementos)))


def potencia(fz, masa, gravedad, frecuencia):
    """P = Fz · v, en watts. ``fz`` en newtons, ``frecuencia`` en Hz."""
    masa, gravedad, frecuencia = _validar_parametros(masa, gravedad, frecuencia)
    fz = np.asarray(fz, dtype=float)
    return fz * velocidad(fz, masa, gravedad, frecuencia)


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
