"""Proyectos guardados en la carpeta «archivos».

Un proyecto son hasta tres archivos hermanos dentro de esa carpeta:

``<nombre>.csv``              copia del CSV original.
``<nombre>_anotaciones.csv``  intervalos, sub-intervalos y notas trabajados.
``<nombre>_estado.json``      variables, filtros y disposición de gráficas.

El archivo de estado es opcional para que los proyectos creados por versiones
anteriores, que solo tienen CSV y anotaciones, continúen abriendo normalmente.
Los archivos se asocian por nombre y la carpeta no se puede cambiar desde la
interfaz.
"""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timedelta


SUFIJO_ANOTACIONES = "_anotaciones"
SUFIJO_ESTADO = "_estado"
VERSION_ESTADO = 1

# Criterios de limpieza de la carpeta. El orden es el que ve el usuario en el
# desplegable; ``archivo`` no filtra nada, deja que elija a mano.
PERIODO_TODOS = "todos"
PERIODO_HOY = "hoy"
PERIODO_SEMANA = "semana"
PERIODO_MES = "mes"
PERIODO_ANIO = "anio"
PERIODO_ARCHIVO = "archivo"

PERIODOS = (
    (PERIODO_TODOS, "Todos los archivos guardados"),
    (PERIODO_HOY, "Los guardados hoy"),
    (PERIODO_SEMANA, "Los guardados en los últimos 7 días"),
    (PERIODO_MES, "Los guardados en los últimos 30 días"),
    (PERIODO_ANIO, "Los guardados en el último año"),
    (PERIODO_ARCHIVO, "Elegir un archivo en particular"),
)

_DIAS_POR_PERIODO = {
    PERIODO_SEMANA: 7,
    PERIODO_MES: 30,
    PERIODO_ANIO: 365,
}

CAMPOS_ANOTACIONES = (
    "tipo",
    "senal",
    "columna",
    "numero",
    "padre",
    "desde",
    "hasta",
    "nombre",
    "nota",
    # Sobre qué serie se trabajó el intervalo: "original" o "filtrada". Se agregó
    # después, así que los archivos viejos no la traen y se leen igual.
    "fuente",
    # Los intervalos replicados comparten el índice de la paleta. Es opcional
    # para mantener compatibles los proyectos guardados por versiones previas.
    "indice_color",
)


def carpeta_archivos() -> str:
    """Ruta absoluta de la carpeta «archivos» del proyecto."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, "archivos")


def asegurar_carpeta() -> str:
    """Devuelve la carpeta «archivos», creándola si todavía no existe."""
    carpeta = carpeta_archivos()
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def sanear_nombre(nombre: str) -> str:
    """Limpia el nombre pedido al usuario para que sea válido en Windows."""
    nombre = re.sub(r'[<>:"/\\|?*]', "_", (nombre or "").strip()).rstrip(". ")
    if nombre.lower().endswith(".csv"):
        nombre = nombre[:-4].rstrip(". ")
    return nombre


def ruta_csv(nombre: str) -> str:
    return os.path.join(carpeta_archivos(), f"{nombre}.csv")


def ruta_anotaciones(nombre: str) -> str:
    return os.path.join(carpeta_archivos(), f"{nombre}{SUFIJO_ANOTACIONES}.csv")


def ruta_estado(nombre: str) -> str:
    return os.path.join(carpeta_archivos(), f"{nombre}{SUFIJO_ESTADO}.json")


def listar_proyectos() -> list[dict]:
    """Lista los proyectos guardados, del más reciente al más antiguo.

    Solo mira la carpeta «archivos» y solo devuelve los ``.csv`` que no son
    archivos de anotaciones. Cada elemento indica qué archivos asociados tiene.
    """
    carpeta = carpeta_archivos()
    if not os.path.isdir(carpeta):
        return []

    proyectos = []
    for archivo in os.listdir(carpeta):
        if not archivo.lower().endswith(".csv"):
            continue
        nombre = archivo[:-4]
        if nombre.endswith(SUFIJO_ANOTACIONES):
            continue

        ruta = os.path.join(carpeta, archivo)
        if not os.path.isfile(ruta):
            continue

        ruta_anot = ruta_anotaciones(nombre)
        ruta_est = ruta_estado(nombre)
        try:
            modificado = os.path.getmtime(ruta)
            tamano = os.path.getsize(ruta)
        except OSError:
            modificado, tamano = 0.0, 0

        proyectos.append(
            {
                "nombre": nombre,
                "archivo": archivo,
                "ruta": ruta,
                "ruta_anotaciones": ruta_anot,
                "tiene_anotaciones": os.path.isfile(ruta_anot),
                "ruta_estado": ruta_est,
                "tiene_estado": os.path.isfile(ruta_est),
                "modificado": modificado,
                "tamano": tamano,
            }
        )

    proyectos.sort(key=lambda p: p["modificado"], reverse=True)
    return proyectos


def filtrar_por_periodo(proyectos, periodo: str, ahora: datetime | None = None) -> list[dict]:
    """Devuelve los proyectos guardados dentro del período pedido.

    ``PERIODO_ARCHIVO`` no selecciona nada a propósito: en ese modo el usuario
    elige a mano. ``PERIODO_HOY`` va desde la medianoche de hoy, no las últimas
    24 horas, que es lo que espera alguien que pide «los de hoy».
    """
    proyectos = list(proyectos)
    if periodo == PERIODO_TODOS:
        return proyectos
    if periodo == PERIODO_ARCHIVO:
        return []

    ahora = ahora or datetime.now()
    if periodo == PERIODO_HOY:
        limite = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo in _DIAS_POR_PERIODO:
        limite = ahora - timedelta(days=_DIAS_POR_PERIODO[periodo])
    else:
        raise ValueError(f"Período desconocido: {periodo!r}")

    marca = limite.timestamp()
    return [p for p in proyectos if p["modificado"] >= marca]


def eliminar_proyectos(nombres) -> tuple[list[str], list[str]]:
    """Borra los proyectos indicados y todos sus archivos asociados.

    Devuelve ``(eliminados, errores)``: los nombres que se borraron y los
    mensajes de los que fallaron. Nunca sale de la carpeta «archivos».
    """
    def _normalizar(ruta):
        # normcase para que la comparación no falle por mayúsculas en Windows.
        return os.path.normcase(os.path.normpath(os.path.abspath(ruta)))

    carpeta = _normalizar(carpeta_archivos())
    eliminados = []
    errores = []

    for nombre in nombres:
        rutas = [ruta_csv(nombre), ruta_anotaciones(nombre), ruta_estado(nombre)]
        fallo = None
        borro_algo = False

        for ruta in rutas:
            # Cinturón de seguridad: nunca tocar nada fuera de «archivos».
            if os.path.dirname(_normalizar(ruta)) != carpeta:
                fallo = f"«{nombre}»: ruta fuera de la carpeta de archivos."
                break
            if not os.path.isfile(ruta):
                continue
            try:
                os.remove(ruta)
                borro_algo = True
            except OSError as exc:
                fallo = f"«{nombre}»: {exc.strerror or exc}"
                break

        if fallo:
            errores.append(fallo)
        elif borro_algo:
            eliminados.append(nombre)

    return eliminados, errores


def formatear_tamano(bytes_totales: int) -> str:
    """Tamaño legible para mostrar en la interfaz."""
    tamano = float(bytes_totales)
    for unidad in ("B", "KB", "MB", "GB"):
        if tamano < 1024 or unidad == "GB":
            if unidad == "B":
                return f"{int(tamano)} B"
            return f"{tamano:.1f} {unidad}".replace(".", ",")
        tamano /= 1024
    return f"{tamano:.1f} GB".replace(".", ",")


def escribir_anotaciones(ruta: str, filas) -> None:
    """Escribe el CSV de anotaciones con la cabecera fija del formato."""
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(CAMPOS_ANOTACIONES))
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({campo: fila.get(campo, "") for campo in CAMPOS_ANOTACIONES})


def escribir_estado(ruta: str, estado) -> None:
    """Guarda el estado complementario en JSON mediante reemplazo atómico."""
    if not isinstance(estado, dict):
        raise ValueError("El estado del proyecto debe ser un objeto.")

    contenido = dict(estado)
    contenido["version"] = VERSION_ESTADO
    ruta = os.fspath(ruta)
    temporal = f"{ruta}.tmp"
    try:
        with open(temporal, "w", encoding="utf-8", newline="\n") as archivo:
            json.dump(contenido, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
        os.replace(temporal, ruta)
    finally:
        if os.path.isfile(temporal):
            try:
                os.remove(temporal)
            except OSError:
                pass


def leer_estado(ruta: str) -> dict:
    """Lee el estado opcional; la ausencia representa un proyecto antiguo."""
    if not ruta or not os.path.isfile(ruta):
        return {}

    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            estado = json.load(archivo)
    except json.JSONDecodeError as exc:
        raise ValueError("El archivo de estado del proyecto no es válido.") from exc

    if not isinstance(estado, dict):
        raise ValueError("El archivo de estado del proyecto no contiene un objeto.")
    return estado


def leer_anotaciones(ruta: str) -> list[dict]:
    """Lee un CSV de anotaciones y normaliza sus campos.

    Las filas incompletas o con números inválidos se descartan en silencio:
    el archivo lo puede haber tocado el usuario a mano.
    """
    if not os.path.isfile(ruta):
        return []

    filas = []
    with open(ruta, "r", newline="", encoding="utf-8-sig") as archivo:
        for cruda in csv.DictReader(archivo):
            tipo = (cruda.get("tipo") or "").strip().lower()
            # El vocabulario persistido no cambia: los proyectos viejos siguen
            # leyéndose tal cual, aunque la interfaz diga «intervalo».
            if tipo not in ("rango", "subrango"):
                continue
            columna = (cruda.get("columna") or "").strip()
            if not columna:
                continue
            try:
                numero = int(float(cruda.get("numero")))
                desde = int(float(cruda.get("desde")))
                hasta = int(float(cruda.get("hasta")))
            except (TypeError, ValueError):
                continue
            if numero < 1:
                continue

            fila = {
                    "tipo": tipo,
                    "senal": (cruda.get("senal") or "").strip(),
                    "columna": columna,
                    "numero": numero,
                    "padre": (cruda.get("padre") or "").strip(),
                    "desde": desde,
                    "hasta": hasta,
                    "nombre": (cruda.get("nombre") or "").strip(),
                    "nota": (cruda.get("nota") or "").strip(),
                    "fuente": (cruda.get("fuente") or "").strip(),
                }
            try:
                indice_color = int(float(cruda.get("indice_color") or 0))
            except (TypeError, ValueError):
                indice_color = 0
            if indice_color > 0:
                fila["indice_color"] = indice_color
            filas.append(fila)
    return filas
