"""Preparacion y escritura de los archivos que salen desde «Exportar».

La interfaz entrega el estado actual de las graficas y este modulo lo convierte
en tablas. No depende de Qt, de modo que el contenido exportado se puede probar
sin abrir ventanas.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import stat
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


MODO_DATOS = "datos"
MODO_INTERVALOS = "intervalos"
MODO_RESULTADOS = "resultados"
MODO_COMPLETO = "completo"

EXTENSIONES_MODO = {
    MODO_DATOS: ".csv",
    MODO_INTERVALOS: ".csv",
    MODO_RESULTADOS: ".csv",
    MODO_COMPLETO: ".zip",
}

COLUMNAS_INTERVALOS = (
    "Tipo",
    "ID",
    "Señal",
    "Columna de origen",
    "Número",
    "Intervalo padre",
    "Desde",
    "Hasta",
    "Nombre",
    "Nota",
    "Datos utilizados",
)

COLUMNAS_RESULTADOS = (
    "Fórmula",
    "Intervalo",
    "Señal",
    "Desde",
    "Hasta",
    "Duración (s)",
    "Resultado",
    "Unidad",
    "Datos utilizados",
    "Expresión",
    "ID del intervalo",
)

ETIQUETAS_FUENTE = {
    "original": "Señal original",
    "filtrada": "Señal filtrada",
    "mixta": "Señales mixtas",
}


def nombre_base(nombre_archivo) -> str:
    """Nombre seguro y reconocible para sugerir en el selector de archivos."""
    nombre = Path(str(nombre_archivo or "")).stem.strip()
    nombre = re.sub(r'[<>:"/\\|?*]+', "_", nombre).rstrip(". ")
    return nombre or "analisis"


def asegurar_extension(ruta, extension) -> str:
    """Agrega la extension esperada sin duplicarla por mayusculas/minusculas."""
    ruta = str(ruta or "").strip()
    extension = str(extension or "").strip()
    if extension and not extension.startswith("."):
        extension = f".{extension}"
    if ruta and extension and not ruta.lower().endswith(extension.lower()):
        ruta += extension
    return ruta


def _nombre_unico(nombre, existentes) -> str:
    base = str(nombre or "dato").strip() or "dato"
    candidato = base
    numero = 2
    while candidato in existentes:
        candidato = f"{base} ({numero})"
        numero += 1
    return candidato


def _fuente_legible(fuente) -> str:
    texto = str(fuente or "").strip()
    return ETIQUETAS_FUENTE.get(texto.lower(), texto)


def _serie_tiene_datos(serie) -> bool:
    """Distingue una columna útil de otra compuesta solo por vacíos."""
    for valor in serie:
        if valor is None:
            continue
        if isinstance(valor, str):
            if valor.strip():
                return True
            continue
        try:
            if pd.isna(valor):
                continue
        except (TypeError, ValueError):
            pass
        return True
    return False


def _encabezado_senal(columna, nombres=None, unidades=None) -> str:
    nombres = nombres or {}
    unidades = unidades or {}
    nombre = str(nombres.get(columna) or columna).strip() or str(columna)
    unidad = str(unidades.get(columna) or "").strip()
    if unidad and f"({unidad})" not in nombre:
        nombre = f"{nombre} ({unidad})"
    return nombre


def preparar_datos(
    df_original,
    df_filtrado=None,
    columna_x=None,
    columnas=None,
    columnas_filtradas=(),
    curvas_formula=(),
    nombres=None,
    unidades=None,
) -> pd.DataFrame:
    """Crea la tabla de señales sin reemplazar los valores originales.

    Cada filtro se agrega en una columna independiente con el sufijo
    ``[filtrada]``. Los nombres visibles y sus unidades pueden reemplazar los
    encabezados técnicos sin alterar los datos. Las curvas de fórmulas se
    alinean por el eje horizontal y quedan vacías fuera de sus intervalos.
    """
    if df_original is None or len(df_original.columns) == 0:
        raise ValueError("No hay datos cargados para exportar.")

    columna_x = columna_x if columna_x in df_original.columns else df_original.columns[0]
    if columnas is None:
        columnas = [col for col in df_original.columns if col != columna_x]

    salida = pd.DataFrame(index=df_original.index)
    salida[columna_x] = df_original[columna_x].to_numpy(copy=True)
    existentes = {str(columna_x)}
    filtradas = set(columnas_filtradas or ())

    for columna in columnas:
        if columna == columna_x or columna not in df_original.columns:
            continue
        encabezado = _encabezado_senal(columna, nombres, unidades)
        nombre_original = _nombre_unico(encabezado, existentes)
        salida[nombre_original] = df_original[columna].to_numpy(copy=True)
        existentes.add(nombre_original)

        if (
            columna in filtradas
            and df_filtrado is not None
            and columna in df_filtrado.columns
            and len(df_filtrado) == len(df_original)
        ):
            nombre_filtrado = _nombre_unico(
                f"{encabezado} [filtrada]", existentes
            )
            salida[nombre_filtrado] = df_filtrado[columna].to_numpy(copy=True)
            existentes.add(nombre_filtrado)

    eje_exportado = pd.to_numeric(salida[columna_x], errors="coerce")
    for curva in curvas_formula or ():
        x = np.asarray(curva.get("x", ()), dtype=float)
        y = np.asarray(curva.get("y", ()), dtype=float)
        if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or not len(x):
            continue
        mascara = np.isfinite(x) & np.isfinite(y)
        if not mascara.any():
            continue

        nombre = str(curva.get("nombre") or "Formula").strip()
        senal = str(curva.get("senal") or curva.get("columna") or "").strip()
        unidad = str(curva.get("unidad") or "").strip()
        etiqueta = f"{senal} - {nombre}" if senal else nombre
        if unidad:
            etiqueta += f" ({unidad})"
        etiqueta = _nombre_unico(etiqueta, existentes)

        # Los intervalos de una misma grafica no se superponen. Si una entrada
        # externa repitiera el eje, se conserva el ultimo valor de ese punto.
        por_x = pd.Series(y[mascara], index=x[mascara]).groupby(level=0).last()
        salida[etiqueta] = eje_exportado.map(por_x)
        existentes.add(etiqueta)

    return salida.reset_index(drop=True)


def preparar_intervalos(intervalos) -> pd.DataFrame:
    """Una fila por intervalo o sub-intervalo, con limites, nombre y nota."""
    filas = []
    for intervalo in intervalos or ():
        es_subintervalo = bool(intervalo.get("es_subintervalo")) or intervalo.get("tipo") == "subintervalo"
        identificador = intervalo.get("id") or _identificador_intervalo(intervalo, es_subintervalo)
        filas.append(
            {
                "Tipo": "Sub-intervalo" if es_subintervalo else "Intervalo",
                "ID": identificador,
                "Señal": intervalo.get("senal", ""),
                "Columna de origen": intervalo.get("columna", ""),
                "Número": intervalo.get("numero", ""),
                "Intervalo padre": intervalo.get("padre") or "",
                "Desde": intervalo.get("desde", ""),
                "Hasta": intervalo.get("hasta", ""),
                "Nombre": intervalo.get("nombre", ""),
                "Nota": intervalo.get("nota", ""),
                "Datos utilizados": _fuente_legible(intervalo.get("fuente", "")),
            }
        )
    return pd.DataFrame(filas, columns=COLUMNAS_INTERVALOS)


def _identificador_intervalo(intervalo, es_subintervalo=False) -> str:
    columna = str(intervalo.get("columna") or "")
    numero = intervalo.get("numero", "")
    if es_subintervalo:
        padre = str(intervalo.get("padre") or "")
        return f"{padre}::sub::{numero}" if padre else f"{columna}::sub::{numero}"
    return f"{columna}::{numero}"


def preparar_muestras_intervalos(
    intervalos,
    df_original,
    df_filtrado=None,
    columna_x=None,
    columnas_filtradas=(),
) -> pd.DataFrame:
    """Exporta las muestras reales que pertenecen a cada intervalo."""
    metadatos = [
        "Tipo",
        "ID del intervalo",
        "Intervalo",
        "Señal",
        "Columna de origen",
        "Desde",
        "Hasta",
        "Nota",
        "Datos utilizados",
    ]
    if df_original is None or len(df_original.columns) == 0:
        return pd.DataFrame(
            columns=metadatos
            + ["Eje horizontal", "Valor original", "Valor filtrado"]
        )

    columna_x = columna_x if columna_x in df_original.columns else df_original.columns[0]
    nombre_eje = _nombre_unico(str(columna_x), set(metadatos))
    columnas_salida = metadatos + [nombre_eje, "Valor original", "Valor filtrado"]
    eje = pd.to_numeric(df_original[columna_x], errors="coerce")
    filtradas = set(columnas_filtradas or ())
    filas = []

    for intervalo in intervalos or ():
        columna = intervalo.get("columna")
        if columna not in df_original.columns:
            continue
        try:
            desde = float(intervalo.get("desde"))
            hasta = float(intervalo.get("hasta"))
        except (TypeError, ValueError):
            continue

        es_subintervalo = bool(intervalo.get("es_subintervalo")) or intervalo.get("tipo") == "subintervalo"
        identificador = intervalo.get("id") or _identificador_intervalo(intervalo, es_subintervalo)
        mascara = eje.between(min(desde, hasta), max(desde, hasta), inclusive="both")
        indices = np.flatnonzero(mascara.to_numpy(dtype=bool))
        tiene_filtrado = (
            columna in filtradas
            and df_filtrado is not None
            and columna in df_filtrado.columns
            and len(df_filtrado) == len(df_original)
        )

        for indice in indices:
            filas.append(
                {
                    "Tipo": "Sub-intervalo" if es_subintervalo else "Intervalo",
                    "ID del intervalo": identificador,
                    "Intervalo": intervalo.get("nombre", ""),
                    "Señal": intervalo.get("senal", ""),
                    "Columna de origen": columna,
                    "Desde": intervalo.get("desde", ""),
                    "Hasta": intervalo.get("hasta", ""),
                    "Nota": intervalo.get("nota", ""),
                    "Datos utilizados": _fuente_legible(intervalo.get("fuente", "")),
                    nombre_eje: df_original.iloc[indice][columna_x],
                    "Valor original": df_original.iloc[indice][columna],
                    "Valor filtrado": (
                        df_filtrado.iloc[indice][columna] if tiene_filtrado else np.nan
                    ),
                }
            )

    tabla = pd.DataFrame(filas, columns=columnas_salida)
    if len(tabla) and not _serie_tiene_datos(tabla["Valor filtrado"]):
        tabla = tabla.drop(columns="Valor filtrado")
    return tabla


def preparar_resultados_formula(datos) -> pd.DataFrame:
    """Convierte el último cálculo en una tabla clara y sin columnas vacías."""
    if not datos or not datos.get("resultados"):
        return pd.DataFrame(columns=COLUMNAS_RESULTADOS)

    comunes = {
        "Fórmula": datos.get("nombre", ""),
        "Unidad": datos.get("unidad", ""),
        "Datos utilizados": _fuente_legible(datos.get("fuente", "")),
        "Filtro": datos.get("detalle_filtro", ""),
        "Advertencias": "; ".join(
            str(a) for a in datos.get("advertencias") or () if a
        ),
        "Expresión": datos.get("expresion", ""),
    }
    filas = []
    columnas_detalle = []

    for resultado in datos["resultados"]:
        resumen = resultado.get("resumen") or {}
        fila = {
            **comunes,
            "ID del intervalo": resultado.get("id", ""),
            "Intervalo": resultado.get("nombre", ""),
            "Señal": resultado.get("senal", ""),
            "Desde": resultado.get("desde", ""),
            "Hasta": resultado.get("hasta", ""),
            "Duración (s)": resultado.get("duracion_s"),
            "Resultado": resultado.get("valor"),
            "Pico": resumen.get("pico"),
            "Frame del pico": resumen.get("x_pico"),
            "Mínimo": resumen.get("minimo"),
            "Frame del mínimo": resumen.get("x_minimo"),
            "Media": resumen.get("media"),
            "RMS": resumen.get("rms"),
            "Muestras válidas": resumen.get("muestras"),
        }
        for detalle in resultado.get("detalles") or ():
            etiqueta = str(detalle.get("etiqueta") or "detalle").strip()
            etiqueta = etiqueta[:1].upper() + etiqueta[1:]
            unidad = str(detalle.get("unidad") or "").strip()
            base_columna = f"{etiqueta} ({unidad})" if unidad else etiqueta
            # La misma magnitud de distintos intervalos debe caer en la misma
            # columna. Solo se numera cuando una unica fila trae dos detalles
            # con exactamente la misma etiqueta.
            columna = (
                base_columna
                if base_columna in columnas_detalle and base_columna not in fila
                else _nombre_unico(base_columna, set(fila))
            )
            fila[columna] = detalle.get("valor")
            if columna not in columnas_detalle:
                columnas_detalle.append(columna)
        filas.append(fila)

    tabla = pd.DataFrame(filas)
    esenciales = ["Fórmula", "Intervalo", "Señal", "Desde", "Hasta", "Duración (s)"]
    # Si la fórmula ya define medidas propias (por ejemplo, impulso neto y
    # propulsivo), esas son más útiles que repetir un resumen estadístico
    # genérico de la curva. Las fórmulas sin detalles sí conservan pico,
    # mínimo, media y RMS.
    medidas = ["Resultado"]
    if columnas_detalle:
        medidas.append("Muestras válidas")
    else:
        medidas.extend(
            [
                "Pico",
                "Frame del pico",
                "Mínimo",
                "Frame del mínimo",
                "Media",
                "RMS",
                "Muestras válidas",
            ]
        )
    metadatos = [
        "Unidad",
        "Datos utilizados",
        "Filtro",
        "Advertencias",
        "Expresión",
        "ID del intervalo",
    ]
    columnas = list(esenciales)
    columnas.extend(
        columna
        for columna in medidas
        if columna in tabla and _serie_tiene_datos(tabla[columna])
    )
    columnas.extend(
        columna
        for columna in columnas_detalle
        if columna in tabla and _serie_tiene_datos(tabla[columna])
    )
    columnas.extend(
        columna
        for columna in metadatos
        if columna in tabla
        and (columna in {"Unidad", "Datos utilizados", "Expresión", "ID del intervalo"}
             or _serie_tiene_datos(tabla[columna]))
    )
    return tabla.reindex(columns=columnas)


def preparar_resultados_formulas(calculos) -> pd.DataFrame:
    """Reúne los resultados de todas las fórmulas aplicadas."""
    tablas = [
        tabla
        for datos in calculos or ()
        if not (tabla := preparar_resultados_formula(datos)).empty
    ]
    if not tablas:
        return pd.DataFrame(columns=COLUMNAS_RESULTADOS)
    return pd.concat(tablas, ignore_index=True, sort=False)


def preparar_informacion(
    nombre_archivo,
    columna_x,
    columnas,
    unidades=None,
    frecuencia=None,
    filtros=None,
    formula=None,
    nombres=None,
) -> str:
    """Resumen legible que acompaña al paquete completo."""
    try:
        frecuencia_valida = float(frecuencia)
    except (TypeError, ValueError):
        frecuencia_valida = 0.0
    if not np.isfinite(frecuencia_valida) or frecuencia_valida <= 0:
        frecuencia_valida = 0.0
    columnas = list(columnas) if columnas is not None else []

    lineas = [
        "ABS 3.0 — Resumen de exportación",
        "=================================",
        "",
        "EXPORTACIÓN",
        "-----------",
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        f"Archivo de origen: {nombre_archivo or 'sin nombre'}",
        f"Eje horizontal: {columna_x or 'no identificado'}",
        (
            f"Frecuencia efectiva: {frecuencia_valida:g} Hz"
            if frecuencia_valida
            else "Frecuencia efectiva: no disponible"
        ),
        "Formato de tablas: CSV UTF-8 · separador ; · decimal ,",
        "",
        "SEÑALES INCLUIDAS",
        "-----------------",
    ]
    unidades = unidades or {}
    nombres = nombres or {}
    for columna in columnas:
        unidad = str(unidades.get(columna) or "").strip()
        nombre = str(nombres.get(columna) or columna)
        referencia = f" [{columna}]" if nombre != str(columna) else ""
        lineas.append(f"- {nombre}{referencia}{f' · {unidad}' if unidad else ''}")
    if not columnas:
        lineas.append("- No se incluyeron señales.")

    filtros = filtros or {}
    if filtros:
        lineas.extend(("", "FILTROS APLICADOS", "-----------------"))
        for columna, descripcion in filtros.items():
            nombre = str(nombres.get(columna) or columna)
            lineas.append(f"- {nombre}: {descripcion or 'Filtro aplicado'}")

    formulas_aplicadas = (
        list(formula)
        if isinstance(formula, (list, tuple))
        else ([formula] if formula else [])
    )
    formulas_aplicadas = [
        datos for datos in formulas_aplicadas if datos and datos.get("resultados")
    ]
    lineas.extend(("", "FÓRMULAS APLICADAS", "------------------"))
    if formulas_aplicadas:
        for indice, datos in enumerate(formulas_aplicadas, start=1):
            if len(formulas_aplicadas) > 1:
                lineas.append(f"Fórmula {indice}")
            lineas.extend(
                (
                    f"- Nombre: {datos.get('nombre', '')}",
                    f"- Expresión: {datos.get('expresion', '')}",
                    f"- Unidad: {datos.get('unidad') or 'sin unidad'}",
                    f"- Datos utilizados: {_fuente_legible(datos.get('fuente')) or 'Señal original'}",
                    f"- Resultados: {len(datos.get('resultados') or ())}",
                )
            )
            if indice < len(formulas_aplicadas):
                lineas.append("")
    else:
        lineas.append("- No hay resultados de fórmula en esta exportación.")
    return "\n".join(lineas) + "\n"


def _csv_en_bytes(tabla) -> bytes:
    buffer = io.StringIO(newline="")
    tabla.to_csv(
        buffer,
        index=False,
        sep=";",
        decimal=",",
        na_rep="",
        lineterminator="\r\n",
    )
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _ruta_temporal(ruta):
    ruta = os.path.abspath(os.fspath(ruta))
    carpeta = os.path.dirname(ruta)
    if not os.path.isdir(carpeta):
        raise FileNotFoundError(f"La carpeta de destino no existe: {carpeta}")
    descriptor, temporal = tempfile.mkstemp(
        prefix=".abs_exportacion_",
        suffix=Path(ruta).suffix,
        dir=carpeta,
    )
    os.close(descriptor)
    return ruta, temporal


def _reemplazar_destino(temporal, ruta):
    """Reemplaza el destino y usa escritura directa si el sistema la exige."""
    try:
        os.replace(temporal, ruta)
        return
    except (PermissionError, FileExistsError) as error_reemplazo:
        if not os.path.isfile(ruta) or os.path.islink(ruta):
            raise error_reemplazo

    try:
        try:
            modo = os.stat(ruta).st_mode
            os.chmod(ruta, modo | stat.S_IWUSR)
        except OSError:
            pass
        with open(temporal, "rb") as origen, open(ruta, "wb") as destino:
            shutil.copyfileobj(origen, destino)
            destino.flush()
            os.fsync(destino.fileno())
        try:
            os.remove(temporal)
        except OSError:
            pass
    except PermissionError as exc:
        nombre = os.path.basename(ruta)
        raise PermissionError(
            f"No se puede sobrescribir «{nombre}» porque está abierto o "
            "bloqueado por otra aplicación. Cerralo y volvé a exportar."
        ) from exc


def escribir_csv(ruta, tabla) -> str:
    """Escribe un CSV UTF-8 compatible con Excel sin dejar archivos parciales."""
    ruta, temporal = _ruta_temporal(ruta)
    try:
        with open(temporal, "wb") as archivo:
            archivo.write(_csv_en_bytes(tabla))
        _reemplazar_destino(temporal, ruta)
    except Exception:
        try:
            os.remove(temporal)
        except OSError:
            pass
        raise
    return ruta


def escribir_paquete(ruta, tablas, informacion="") -> str:
    """Crea un ZIP comprobado con los CSV del analisis actual."""
    ruta, temporal = _ruta_temporal(ruta)
    try:
        with zipfile.ZipFile(
            temporal, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as paquete:
            for nombre, tabla in tablas.items():
                paquete.writestr(nombre, _csv_en_bytes(tabla))
            if informacion:
                paquete.writestr(
                    "informacion.txt", ("\ufeff" + informacion).encode("utf-8")
                )

        with zipfile.ZipFile(temporal, "r") as paquete:
            archivo_danado = paquete.testzip()
            if archivo_danado:
                raise OSError(f"No se pudo verificar {archivo_danado}.")
        _reemplazar_destino(temporal, ruta)
    except Exception:
        try:
            os.remove(temporal)
        except OSError:
            pass
        raise
    return ruta
