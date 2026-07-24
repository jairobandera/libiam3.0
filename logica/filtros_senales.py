"""Filtros digitales utilizados por las gráficas de ABS 3.0."""

from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt


class ErrorConfiguracionFiltro(ValueError):
    """La configuración del filtro no es válida para los datos actuales."""


TIPOS_FILTRO = {"lowpass", "highpass", "bandpass", "bandstop"}


def _normalizar_frecuencias_corte(tipo: str, frecuencias_corte) -> float | tuple[float, float]:
    if tipo not in TIPOS_FILTRO:
        raise ErrorConfiguracionFiltro("El tipo de filtro seleccionado no es válido.")

    if tipo in ("bandpass", "bandstop"):
        try:
            inferior, superior = frecuencias_corte
        except (TypeError, ValueError) as exc:
            raise ErrorConfiguracionFiltro(
                "El filtro necesita una frecuencia inferior y otra superior."
            ) from exc
        return float(inferior), float(superior)

    try:
        return float(frecuencias_corte)
    except (TypeError, ValueError) as exc:
        raise ErrorConfiguracionFiltro("La frecuencia de corte no es válida.") from exc


def _validar_configuracion(
    frecuencia_muestreo: float,
    tipo: str,
    frecuencias_corte: float | tuple[float, float],
    orden: int,
) -> None:
    if frecuencia_muestreo <= 0:
        raise ErrorConfiguracionFiltro("La frecuencia de muestreo debe ser mayor que cero.")
    if not 1 <= orden <= 10:
        raise ErrorConfiguracionFiltro("El orden debe estar entre 1 y 10.")

    limite = frecuencia_muestreo / 2
    if tipo in ("bandpass", "bandstop"):
        inferior, superior = frecuencias_corte
        if inferior <= 0 or superior <= 0:
            raise ErrorConfiguracionFiltro(
                "Las frecuencias de corte deben ser mayores que cero."
            )
        if inferior >= superior:
            raise ErrorConfiguracionFiltro(
                "La frecuencia inferior debe ser menor que la superior."
            )
        if superior >= limite:
            raise ErrorConfiguracionFiltro(
                "La frecuencia superior debe ser menor que la mitad de la frecuencia "
                f"de muestreo ({limite:g} Hz)."
            )
        return

    if frecuencias_corte <= 0:
        raise ErrorConfiguracionFiltro("La frecuencia de corte debe ser mayor que cero.")
    if frecuencias_corte >= limite:
        raise ErrorConfiguracionFiltro(
            "La frecuencia de corte debe ser menor que la mitad de la frecuencia "
            f"de muestreo ({limite:g} Hz)."
        )


def aplicar_butterworth(
    valores,
    frecuencia_muestreo: float,
    tipo: str,
    frecuencias_corte,
    orden: int = 4,
) -> np.ndarray:
    """Aplica un Butterworth sin desplazamiento temporal apreciable.

    ``frecuencias_corte`` recibe un único valor en los modos pasa-bajos y
    pasa-altos, y un par ``(inferior, superior)`` en los modos pasa-banda
    y rechazo de banda.
    """
    frecuencia_muestreo = float(frecuencia_muestreo)
    tipo = str(tipo).strip().lower()
    orden = int(orden)
    frecuencias_corte = _normalizar_frecuencias_corte(tipo, frecuencias_corte)
    _validar_configuracion(frecuencia_muestreo, tipo, frecuencias_corte, orden)

    datos = np.asarray(valores, dtype=float)
    if datos.ndim != 1:
        raise ErrorConfiguracionFiltro("La señal debe contener una sola serie de valores.")

    finitos = np.isfinite(datos)
    if finitos.sum() < max(12, orden * 4):
        raise ErrorConfiguracionFiltro("La señal no tiene suficientes datos válidos para filtrarse.")

    indices = np.arange(len(datos), dtype=float)
    datos_continuos = datos.copy()
    if not finitos.all():
        datos_continuos[~finitos] = np.interp(indices[~finitos], indices[finitos], datos[finitos])

    nyq = frecuencia_muestreo / 2.0
    if tipo in ("bandpass", "bandstop"):
        Wn = [frecuencias_corte[0] / nyq, frecuencias_corte[1] / nyq]
        btype = "band" if tipo == "bandpass" else "bandstop"
    elif tipo == "lowpass":
        Wn = frecuencias_corte / nyq
        btype = "low"
    else:
        Wn = frecuencias_corte / nyq
        btype = "high"

    b, a = butter(orden, Wn, btype=btype)
    try:
        filtrados = filtfilt(b, a, datos_continuos)
    except ValueError as exc:
        raise ErrorConfiguracionFiltro(
            "La señal es demasiado corta para esta configuración de filtro."
        ) from exc

    filtrados[~finitos] = np.nan
    return filtrados


def aplicar_butterworth_pasabajos(
    valores,
    frecuencia_muestreo: float,
    frecuencia_corte: float,
    orden: int = 4,
) -> np.ndarray:
    """Mantiene compatibilidad con el filtro pasa-bajos inicial."""
    return aplicar_butterworth(
        valores,
        frecuencia_muestreo,
        "lowpass",
        frecuencia_corte,
        orden,
    )
