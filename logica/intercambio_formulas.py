"""Formato portable para compartir fórmulas personalizadas de ABS.

El archivo usa JSON aunque su extensión sea ``.txt``: así sigue siendo legible
para una persona, pero también puede validarse sin interpretar código.
"""

from __future__ import annotations

import json

from logica import formulas as formulas_logica


FORMATO = "ABS_FORMULAS_PERSONALIZADAS"
VERSION = 1
MAXIMO_CARACTERES = 1_000_000
MAXIMO_FORMULAS = 500


class ErrorIntercambioFormulas(ValueError):
    """El archivo no pertenece al formato esperado o contiene datos inválidos."""


def _texto_una_linea(valor):
    return " ".join(str(valor).split())


def _normalizar_formula(datos, posicion=None):
    if not isinstance(datos, dict):
        raise ErrorIntercambioFormulas(
            _con_posicion("Cada fórmula debe ser un objeto.", posicion)
        )

    nombre_original = datos.get("nombre")
    expresion_original = datos.get("expresion")
    unidad_original = datos.get("unidad", "")
    descripcion_original = datos.get("descripcion", "")
    reutilizable = datos.get("reutilizable", True)

    if not isinstance(nombre_original, str) or not nombre_original.strip():
        raise ErrorIntercambioFormulas(
            _con_posicion("Falta el nombre de la fórmula.", posicion)
        )
    if not isinstance(expresion_original, str) or not expresion_original.strip():
        raise ErrorIntercambioFormulas(
            _con_posicion("Falta la expresión de la fórmula.", posicion)
        )
    if not isinstance(unidad_original, str) or not isinstance(
        descripcion_original, str
    ):
        raise ErrorIntercambioFormulas(
            _con_posicion("La unidad y la descripción deben ser texto.", posicion)
        )
    if not isinstance(reutilizable, bool):
        raise ErrorIntercambioFormulas(
            _con_posicion("El campo reutilizable debe ser verdadero o falso.", posicion)
        )

    nombre = _texto_una_linea(nombre_original)
    unidad = formulas_logica.normalizar_unidad_formula(
        _texto_una_linea(unidad_original)
    )
    descripcion = _texto_una_linea(descripcion_original)
    if len(nombre) > 80:
        raise ErrorIntercambioFormulas(
            _con_posicion("El nombre supera los 80 caracteres.", posicion)
        )
    if len(unidad) > 24:
        raise ErrorIntercambioFormulas(
            _con_posicion("La unidad supera los 24 caracteres.", posicion)
        )
    if len(descripcion) > 180:
        raise ErrorIntercambioFormulas(
            _con_posicion("La descripción supera los 180 caracteres.", posicion)
        )

    try:
        analisis = formulas_logica.analizar_expresion_personalizada(
            expresion_original
        )
    except formulas_logica.ErrorFormula as exc:
        raise ErrorIntercambioFormulas(
            _con_posicion(f"La expresión no es válida: {exc}", posicion)
        ) from exc

    return {
        "nombre": nombre,
        "expresion": analisis["texto"],
        "unidad": unidad,
        "descripcion": descripcion,
        "reutilizable": reutilizable,
    }


def _con_posicion(mensaje, posicion):
    if posicion is None:
        return mensaje
    return f"Fórmula {posicion}: {mensaje}"


def serializar_formulas(formulas):
    """Devuelve el contenido UTF-8 del ``.txt`` de intercambio."""
    formulas = list(formulas or [])
    if len(formulas) > MAXIMO_FORMULAS:
        raise ErrorIntercambioFormulas(
            f"Solo se pueden exportar hasta {MAXIMO_FORMULAS} fórmulas por archivo."
        )
    normalizadas = [
        _normalizar_formula(datos, indice)
        for indice, datos in enumerate(formulas, start=1)
    ]
    documento = {
        "formato": FORMATO,
        "version": VERSION,
        "formulas": normalizadas,
    }
    return json.dumps(documento, ensure_ascii=False, indent=2) + "\n"


def deserializar_formulas(texto):
    """Lee y valida por completo un archivo antes de permitir su importación."""
    if not isinstance(texto, str) or not texto.strip():
        raise ErrorIntercambioFormulas("El archivo está vacío.")
    if len(texto) > MAXIMO_CARACTERES:
        raise ErrorIntercambioFormulas("El archivo es demasiado grande.")
    try:
        documento = json.loads(texto)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ErrorIntercambioFormulas(
            "El archivo no contiene un documento de fórmulas válido."
        ) from exc

    if not isinstance(documento, dict) or documento.get("formato") != FORMATO:
        raise ErrorIntercambioFormulas(
            "El archivo no fue reconocido como un paquete de fórmulas de ABS."
        )
    if documento.get("version") != VERSION:
        raise ErrorIntercambioFormulas(
            f"La versión del archivo no es compatible (se admite la {VERSION})."
        )

    formulas = documento.get("formulas")
    if not isinstance(formulas, list):
        raise ErrorIntercambioFormulas("El archivo no contiene una lista de fórmulas.")
    if len(formulas) > MAXIMO_FORMULAS:
        raise ErrorIntercambioFormulas(
            f"El archivo supera el máximo de {MAXIMO_FORMULAS} fórmulas."
        )
    return [
        _normalizar_formula(datos, indice)
        for indice, datos in enumerate(formulas, start=1)
    ]


def _firma_formula(datos):
    expresion = formulas_logica.normalizar_expresion_personalizada(
        datos.get("expresion") or datos.get("expresion_constructor") or ""
    )
    return (
        expresion,
        formulas_logica.normalizar_unidad_formula(datos.get("unidad")),
        _texto_una_linea(datos.get("descripcion") or ""),
        bool(datos.get("reutilizable", True)),
    )


def _nombre_importado_disponible(nombre, nombres_ocupados):
    numero = 1
    while True:
        sufijo = " (importada)" if numero == 1 else f" (importada {numero})"
        base = nombre[: 80 - len(sufijo)].rstrip()
        candidato = f"{base}{sufijo}"
        if candidato.casefold() not in nombres_ocupados:
            return candidato
        numero += 1


def resolver_conflictos(formulas_importadas, formulas_existentes=()):
    """Omite duplicados exactos y renombra colisiones sin pisar fórmulas."""
    existentes = [dict(datos) for datos in (formulas_existentes or [])]
    nombres_ocupados = {
        _texto_una_linea(datos.get("nombre") or "").casefold()
        for datos in existentes
        if datos.get("nombre")
    }
    por_nombre = {}
    for datos in existentes:
        nombre = _texto_una_linea(datos.get("nombre") or "").casefold()
        if nombre:
            por_nombre.setdefault(nombre, []).append(datos)

    nuevas = []
    omitidas = 0
    renombradas = 0
    for posicion, original in enumerate(formulas_importadas or (), start=1):
        formula = _normalizar_formula(original, posicion)
        nombre_clave = formula["nombre"].casefold()
        coincidencias = por_nombre.get(nombre_clave, [])
        if any(_firma_formula(datos) == _firma_formula(formula) for datos in coincidencias):
            omitidas += 1
            continue
        if nombre_clave in nombres_ocupados:
            formula["nombre"] = _nombre_importado_disponible(
                formula["nombre"], nombres_ocupados
            )
            nombre_clave = formula["nombre"].casefold()
            renombradas += 1

        nuevas.append(formula)
        nombres_ocupados.add(nombre_clave)
        por_nombre.setdefault(nombre_clave, []).append(formula)

    return {
        "formulas": nuevas,
        "omitidas": omitidas,
        "renombradas": renombradas,
    }
