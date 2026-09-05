"""Lectura rápida de CSV biomecánicos y extracción de sus metadatos."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Callable

import pandas as pd


DELIMITADORES = (",", ";", "\t", "|")
NOMBRES_EJE_X = {
    "frame",
    "subframe",
    "sample",
    "muestra",
    "time",
    "times",
    "tiempo",
    "timestamp",
}

ProgresoCarga = Callable[[int, str], None]


def _informar_progreso(
    progreso: ProgresoCarga | None,
    porcentaje: int,
    mensaje: str,
) -> None:
    if progreso is not None:
        progreso(porcentaje, mensaje)


def calcular_frecuencia_efectiva(frecuencia_muestreo, subframes=None):
    """Frecuencia disponible después de preparar los datos para graficar.

    El valor que informa o ingresa el usuario es la frecuencia original del
    registro. Si varias muestras ``SubFrame`` se promedian en un único frame,
    la frecuencia efectiva se divide por esa cantidad.
    """
    if frecuencia_muestreo in (None, ""):
        return None

    try:
        frecuencia = float(frecuencia_muestreo)
    except (TypeError, ValueError):
        return None
    if frecuencia <= 0:
        return None

    subframes = subframes or {}
    divisor = 1
    if subframes.get("tiene_subframes"):
        try:
            divisor = max(1, int(subframes.get("max_por_frame", 1)))
        except (TypeError, ValueError):
            divisor = 1
    return frecuencia / divisor


def _normalizar_saltos_linea(datos: bytes) -> bytes:
    """Normaliza incluso exportaciones que contienen la secuencia CR-CR-LF."""
    return (
        datos.replace(b"\r\r\n", b"\n")
        .replace(b"\r\n", b"\n")
        .replace(b"\r", b"\n")
    )


def _decodificar_muestra(datos: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return datos.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", errors="replace"), "utf-8"


def _detectar_delimitador(texto: str) -> str:
    muestra = "\n".join(linea for linea in texto.splitlines()[:40] if linea.strip())
    try:
        return csv.Sniffer().sniff(muestra, delimiters="".join(DELIMITADORES)).delimiter
    except csv.Error:
        conteos = {delimitador: muestra.count(delimitador) for delimitador in DELIMITADORES}
        return max(conteos, key=conteos.get)


def _normalizar_nombre(valor: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(valor).strip().lower())


def _es_numero(valor: str) -> bool:
    try:
        float(valor.strip())
        return True
    except (TypeError, ValueError):
        return False


def _es_unidad(valor: str) -> bool:
    unidad = valor.strip().lower().replace(" ", "")
    if not unidad:
        return False

    unidades_conocidas = {
        "%",
        "n",
        "nm",
        "n.m",
        "n·m",
        "nmm",
        "n.mm",
        "n·mm",
        "m",
        "cm",
        "mm",
        "s",
        "ms",
        "hz",
        "v",
        "mv",
        "uv",
        "µv",
        "deg",
        "°",
        "rad",
        "rad/s",
        "m/s",
        "m/s2",
        "m/s²",
        "deg/s",
        "°/s",
        "kg",
    }
    if unidad in unidades_conocidas:
        return True

    return bool(re.fullmatch(r"[a-zµ°]+(?:[./·*^-][a-z0-9µ°²]+)+", unidad))


def _parece_fila_unidades(fila: list[str]) -> bool:
    valores = [valor.strip() for valor in fila if valor.strip()]
    if not valores:
        return False
    coincidencias = sum(_es_unidad(valor) for valor in valores)
    return coincidencias / len(valores) >= 0.8


def _siguiente_fila_no_vacia(filas: list[list[str]], inicio: int) -> tuple[int | None, list[str] | None]:
    for indice in range(inicio, len(filas)):
        if any(valor.strip() for valor in filas[indice]):
            return indice, filas[indice]
    return None, None


def _detectar_fila_cabecera(filas: list[list[str]]) -> int:
    mejor_indice = 0
    mejor_puntaje = float("-inf")

    for indice, fila in enumerate(filas):
        valores = [valor.strip() for valor in fila if valor.strip()]
        if len(valores) < 2 or _parece_fila_unidades(fila):
            continue

        normalizados = {_normalizar_nombre(valor) for valor in valores}
        conocidos = len(normalizados & NOMBRES_EJE_X)
        textos = sum(not _es_numero(valor) for valor in valores)
        numeros = len(valores) - textos

        siguiente_indice, siguiente = _siguiente_fila_no_vacia(filas, indice + 1)
        if siguiente is not None and _parece_fila_unidades(siguiente):
            _, siguiente = _siguiente_fila_no_vacia(filas, siguiente_indice + 1)

        fraccion_numerica_siguiente = 0.0
        if siguiente:
            siguientes = [valor.strip() for valor in siguiente if valor.strip()]
            if siguientes:
                fraccion_numerica_siguiente = sum(_es_numero(v) for v in siguientes) / len(siguientes)

        puntaje = conocidos * 100 + textos - numeros * 2
        if fraccion_numerica_siguiente >= 0.5:
            puntaje += 30

        if puntaje > mejor_puntaje:
            mejor_indice = indice
            mejor_puntaje = puntaje

    return mejor_indice


def _extraer_frecuencia(filas: list[list[str]], fila_cabecera: int) -> float | None:
    for fila in filas[:fila_cabecera]:
        valores = [valor.strip() for valor in fila if valor.strip()]
        if len(valores) != 1 or not _es_numero(valores[0]):
            continue
        frecuencia = float(valores[0])
        if 1 <= frecuencia <= 1_000_000:
            return frecuencia
    return None


def _unidad_desde_nombre_columna(nombre: object) -> str | None:
    texto = str(nombre).strip()
    coincidencia = re.search(
        r"(?:^|[_\s(])(%|N\.mm|Nmm|Nm|N|mm|cm|ms|mV|uV|µV|Hz|s)(?:\)?$)",
        texto,
        flags=re.IGNORECASE,
    )
    return coincidencia.group(1) if coincidencia else None


def es_columna_fuera_alcance_actual(nombre: object, grupo: object = "") -> bool:
    """Indica si el canal pertenece a equipos que aún no analiza ABS 3.0."""
    grupo_normalizado = _normalizar_nombre(grupo)
    if "delsys" in grupo_normalizado or "electromiograf" in grupo_normalizado:
        return True

    nombre_normalizado = _normalizar_nombre(nombre)
    return nombre_normalizado.startswith(("emg", "imemg"))


def _tipo_grupo_biomecanico(grupo: object) -> str | None:
    grupo_normalizado = _normalizar_nombre(grupo)
    if "force" in grupo_normalizado or "fuerza" in grupo_normalizado:
        return "fuerza"
    if "moment" in grupo_normalizado or "momento" in grupo_normalizado:
        return "momento"
    if "cop" in grupo_normalizado or "centerofpressure" in grupo_normalizado:
        return "cop"
    return None


def _es_grupo_combinado_reemplazado(
    grupo: object,
    tipos_amti: set[str],
) -> bool:
    grupo_normalizado = _normalizar_nombre(grupo)
    es_combinado = (
        "combined" in grupo_normalizado or "combinad" in grupo_normalizado
    )
    return es_combinado and _tipo_grupo_biomecanico(grupo) in tipos_amti


def _grupos_de_columnas(
    filas: list[list[str]],
    fila_cabecera: int,
) -> list[str]:
    """Expande la fila de grupos para asociar cada canal con su dispositivo."""
    fila_grupos = None
    for indice in range(fila_cabecera - 1, -1, -1):
        candidata = filas[indice]
        valores = [valor.strip() for valor in candidata if valor.strip()]
        if len(candidata) > 1 and len(valores) > 1:
            fila_grupos = candidata
            break

    cantidad = len(filas[fila_cabecera])
    if fila_grupos is None:
        return [""] * cantidad

    grupos = []
    grupo_actual = ""
    for posicion in range(cantidad):
        valor = fila_grupos[posicion].strip() if posicion < len(fila_grupos) else ""
        if valor:
            grupo_actual = valor
        grupos.append(grupo_actual)
    return grupos


def _columnas_del_alcance(
    filas: list[list[str]],
    fila_cabecera: int,
) -> tuple[list[int] | None, list[dict[str, str]], list[str]]:
    cabecera = filas[fila_cabecera]
    grupos = _grupos_de_columnas(filas, fila_cabecera)
    indices = []
    ignoradas = []
    tipos_amti = {
        tipo
        for grupo in grupos
        if "amti" in _normalizar_nombre(grupo)
        if (tipo := _tipo_grupo_biomecanico(grupo)) is not None
    }

    for indice, nombre in enumerate(cabecera):
        grupo = grupos[indice] if indice < len(grupos) else ""
        if es_columna_fuera_alcance_actual(
            nombre,
            grupo,
        ) or _es_grupo_combinado_reemplazado(grupo, tipos_amti):
            ignoradas.append({"nombre": nombre.strip(), "grupo": grupo})
        else:
            indices.append(indice)

    return (indices if ignoradas else None), ignoradas, grupos


def _fuente_para_pandas(ruta: Path, muestra: bytes):
    saltos_inusuales = b"\r\r\n" in muestra or (b"\r" in muestra and b"\n" not in muestra)
    if saltos_inusuales:
        return io.BytesIO(_normalizar_saltos_linea(ruta.read_bytes()))
    return ruta


def _filas_del_bloque_principal(
    ruta: Path,
    encoding: str,
    delimitador: str,
    primera_fila_datos: int,
    muestra: bytes,
) -> int | None:
    """Cuenta las filas hasta la siguiente sección independiente del CSV."""
    if b"\r\r\n" in muestra or (b"\r" in muestra and b"\n" not in muestra):
        return None

    cantidad = 0
    with ruta.open("r", encoding=encoding, errors="replace", newline=None) as archivo:
        for indice, linea in enumerate(archivo):
            if indice < primera_fila_datos:
                continue
            texto = linea.strip()
            if not texto:
                continue
            if delimitador not in texto and not _es_numero(texto):
                return cantidad
            cantidad += 1
    return None


def leer_csv_rapido(
    ruta_archivo: str | Path,
    progreso: ProgresoCarga | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Lee un CSV con el motor C y conserva cabecera, unidades y frecuencia.

    Muchas exportaciones biomecánicas incluyen filas de metadatos antes de la
    cabecera y una fila de unidades inmediatamente después. Esas filas se
    detectan antes de cargar el bloque numérico para evitar que todas las
    columnas terminen con tipo ``object``.
    """
    ruta = Path(ruta_archivo)
    _informar_progreso(progreso, 5, "Inspeccionando el archivo…")
    with ruta.open("rb") as archivo:
        muestra = archivo.read(512_000)
    muestra_normalizada = _normalizar_saltos_linea(muestra)
    texto, encoding = _decodificar_muestra(muestra_normalizada)
    delimitador = _detectar_delimitador(texto)

    _informar_progreso(progreso, 12, "Detectando la estructura…")

    lector = csv.reader(io.StringIO(texto), delimiter=delimitador)
    filas = [fila for _, fila in zip(range(120), lector)]
    fila_cabecera = _detectar_fila_cabecera(filas)
    usecols, columnas_ignoradas, grupos = _columnas_del_alcance(
        filas, fila_cabecera
    )

    fila_unidades = None
    indice_unidades, posible_unidad = _siguiente_fila_no_vacia(filas, fila_cabecera + 1)
    if posible_unidad is not None and _parece_fila_unidades(posible_unidad):
        fila_unidades = indice_unidades

    skiprows = [fila_unidades] if fila_unidades is not None else None
    nrows = None
    if columnas_ignoradas:
        primera_fila_datos = (
            fila_unidades + 1
            if fila_unidades is not None
            else fila_cabecera + 1
        )
        nrows = _filas_del_bloque_principal(
            ruta,
            encoding,
            delimitador,
            primera_fila_datos,
            muestra,
        )
    _informar_progreso(progreso, 22, "Leyendo los datos…")
    fuente = _fuente_para_pandas(ruta, muestra)
    df = pd.read_csv(
        fuente,
        sep=delimitador,
        header=fila_cabecera,
        skiprows=skiprows,
        usecols=usecols,
        nrows=nrows,
        engine="c",
        encoding=encoding,
        low_memory=False,
    )

    _informar_progreso(progreso, 72, "Preparando las columnas…")
    indices_origen = usecols or list(range(len(df.columns)))
    columnas_leidas = [str(columna).strip() for columna in df.columns]
    origen_por_columna = dict(zip(columnas_leidas, indices_origen))
    df.columns = columnas_leidas
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    df.columns = [str(columna).strip() for columna in df.columns]

    unidades = {}
    if fila_unidades is not None and fila_unidades < len(filas):
        valores_unidad = filas[fila_unidades]
        for columna in df.columns:
            indice_origen = origen_por_columna.get(columna)
            unidad = (
                valores_unidad[indice_origen].strip()
                if indice_origen is not None and indice_origen < len(valores_unidad)
                else ""
            )
            if unidad:
                unidades[columna] = unidad

    for columna in df.columns:
        if columna not in unidades:
            unidad = _unidad_desde_nombre_columna(columna)
            if unidad:
                unidades[columna] = unidad

    grupos_columnas = {}
    for columna in df.columns:
        indice_origen = origen_por_columna.get(columna)
        if indice_origen is not None and indice_origen < len(grupos):
            grupo = grupos[indice_origen]
            if grupo:
                grupos_columnas[columna] = grupo

    metadatos = {
        "unidades": unidades,
        "grupos_columnas": grupos_columnas,
        "columnas_ignoradas": columnas_ignoradas,
        "cantidad_columnas_ignoradas": len(columnas_ignoradas),
        "frecuencia_muestreo": _extraer_frecuencia(filas, fila_cabecera),
        "separador": delimitador,
        "fila_cabecera": fila_cabecera,
        "fila_unidades": fila_unidades,
    }
    df.attrs.update(metadatos)
    _informar_progreso(progreso, 80, "Lectura completa.")
    return df, metadatos


def leer_csv_crudo(ruta_archivo: str | Path) -> pd.DataFrame:
    """Lee todas las filas, todavía sin interpretar secciones manuales."""
    ruta = Path(ruta_archivo)
    datos = _normalizar_saltos_linea(ruta.read_bytes())
    texto, encoding = _decodificar_muestra(datos[:256_000])
    delimitador = _detectar_delimitador(texto)
    return pd.read_csv(
        io.BytesIO(datos),
        sep=delimitador,
        engine="c",
        encoding=encoding,
        header=None,
        skip_blank_lines=True,
        low_memory=False,
    )
