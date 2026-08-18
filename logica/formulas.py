"""Cálculos de potencia e impulso usados por la aplicación."""

from __future__ import annotations

import ast
import math
import re

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

NOMBRES_ROLES = {
    "Fx": "Fuerza en X", "Fy": "Fuerza en Y", "Fz": "Fuerza en Z",
    "Mx": "Momento en X", "My": "Momento en Y", "Mz": "Momento en Z",
    "Cx": "Centro de presión en X",
    "Cy": "Centro de presión en Y",
    "Cz": "Centro de presión en Z",
}


# --- Fórmulas creadas por el usuario ----------------------------------------
# El texto nunca pasa por eval(). Se analiza con ast y se interpreta solo si
# todos sus componentes pertenecen a esta lista blanca.
VARIABLE_SENAL_RANGO = "senal"
VARIABLES_CONTEXTO = {
    "masa": "Cargá la masa del sujeto en el panel izquierdo.",
    "gravedad": "La gravedad debe ser mayor que cero.",
    "frecuencia": "No se pudo determinar la frecuencia de muestreo. "
                  "Ingresala manualmente en «Filtro de frecuencias».",
}
CONSTANTES_PERSONALIZADAS = {"pi": math.pi, "e": math.e}

UNIDADES_CONSTRUCTOR = (
    ("Sin unidad", ""),
    ("Fuerza — newton (N)", "N"),
    ("Impulso — newton-segundo (N·s)", "N·s"),
    ("Momento — newton-metro (N·m)", "N·m"),
    ("Momento — newton-milímetro (N·mm)", "N·mm"),
    ("Potencia — watt (W)", "W"),
    ("Energía — joule (J)", "J"),
    ("Velocidad — metro por segundo (m/s)", "m/s"),
    ("Aceleración — metro por segundo cuadrado (m/s²)", "m/s²"),
    ("Distancia — metro (m)", "m"),
    ("Distancia — milímetro (mm)", "mm"),
    ("Frecuencia — hertz (Hz)", "Hz"),
    ("Voltaje — voltio (V)", "V"),
    ("Voltaje — milivoltio (mV)", "mV"),
    ("Voltaje — microvoltio (µV)", "µV"),
    ("Peso corporal (BW)", "BW"),
    ("Porcentaje (%)", "%"),
)


def nombre_variable_constructor(variable) -> str:
    """Nombre entendible para los datos que aparecen en el constructor."""
    if variable == VARIABLE_SENAL_RANGO:
        return "Señal del rango"
    if variable in NOMBRES_ROLES:
        return f"{variable} ({NOMBRES_ROLES[variable].lower()})"
    return {
        "masa": "masa",
        "gravedad": "gravedad",
        "frecuencia": "frecuencia",
        "tiempo": "tiempo",
        "pi": "π",
        "e": "e",
    }.get(variable, str(variable))


def normalizar_unidad_formula(unidad) -> str:
    """Convierte formas fáciles de escribir a los símbolos usados en pantalla."""
    texto = str(unidad or "").strip()
    texto = (
        texto.replace("⋅", "·")
        .replace("×", "·")
        .replace("*", "·")
        .replace("^2", "²")
        .replace("^3", "³")
    )
    aliases = {
        "n.s": "N·s",
        "n s": "N·s",
        "n.m": "N·m",
        "n m": "N·m",
        "n.mm": "N·mm",
        "n mm": "N·mm",
        "uv": "µV",
    }
    texto = aliases.get(texto.casefold(), texto)
    conocidas = {
        valor.casefold(): valor
        for _etiqueta, valor in UNIDADES_CONSTRUCTOR
        if valor
    }
    return conocidas.get(texto.casefold(), texto)


CALCULOS_AUXILIARES = (
    {
        "clave": "aux_fuerza_neta_vertical",
        "nombre": "Fuerza neta vertical",
        "expresion": "Fz - masa * gravedad",
        "descripcion": "Resta el peso corporal a la fuerza vertical.",
        "unidad": "N",
    },
    {
        "clave": "aux_aceleracion_vertical",
        "nombre": "Aceleración vertical",
        "expresion": "(Fz - masa * gravedad) / masa",
        "descripcion": "Obtiene la aceleración vertical a partir de la fuerza neta.",
        "unidad": "m/s²",
    },
    {
        "clave": "aux_velocidad_vertical",
        "nombre": "Velocidad vertical",
        "expresion": "integral((Fz - masa * gravedad) / masa)",
        "descripcion": "Integra la aceleración vertical usando la frecuencia del archivo.",
        "unidad": "m/s",
    },
)

# (texto que se muestra, nombre que se inserta, explicación breve)
FUNCIONES_CONSTRUCTOR = (
    ("Absoluto", "abs", "Valor absoluto de cada muestra"),
    ("Raíz", "raiz", "Raíz cuadrada"),
    ("Integral", "integral", "Integral acumulada usando la frecuencia"),
    ("Derivada", "derivada", "Cambio por segundo"),
    ("Promedio", "promedio", "Promedio del rango"),
    ("Máximo", "maximo", "Máximo del rango"),
    ("Mínimo", "minimo", "Mínimo del rango"),
    ("RMS", "rms", "Valor cuadrático medio del rango"),
    ("Suma", "suma", "Suma de las muestras del rango"),
    ("Log", "log", "Logaritmo natural"),
    ("Exp", "exp", "Exponencial"),
)

_ALIAS_FUNCIONES = {
    "sqrt": "raiz",
    "mean": "promedio",
    "average": "promedio",
    "max": "maximo",
    "min": "minimo",
    "sum": "suma",
    "integrate": "integral",
    "gradient": "derivada",
}
_FUNCIONES_PERMITIDAS = {
    nombre for _texto, nombre, _ayuda in FUNCIONES_CONSTRUCTOR
} | set(_ALIAS_FUNCIONES)
_FUNCIONES_REDUCTORAS = {"promedio", "maximo", "minimo", "rms", "suma"}
_FUNCIONES_TEMPORALES = {"integral", "derivada"}
_OPERADORES_BINARIOS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a**b,
    ast.Mod: lambda a, b: a % b,
}
_OPERADORES_UNARIOS = {ast.UAdd: lambda a: a, ast.USub: lambda a: -a}


def normalizar_expresion_personalizada(expresion) -> str:
    """Acepta símbolos habituales sin obligar al usuario a conocer Python."""
    texto = str(expresion or "").strip()
    texto = (
        texto.replace("×", "*")
        .replace("·", "*")
        .replace("÷", "/")
        .replace("−", "-")
        .replace("^", "**")
    )
    texto = re.sub(r"(?<=\d),(?=\d)", ".", texto)
    texto = re.sub(r"\bseñal\b", VARIABLE_SENAL_RANGO, texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bfs\b", "frecuencia", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bg\b", "gravedad", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bF\b", VARIABLE_SENAL_RANGO, texto)
    for rol in ROLES:
        texto = re.sub(rf"\b{re.escape(rol)}\b", rol, texto, flags=re.IGNORECASE)
    for nombre in (*VARIABLES_CONTEXTO, "tiempo", "pi", "e"):
        texto = re.sub(
            rf"\b{re.escape(nombre)}\b", nombre, texto, flags=re.IGNORECASE
        )
    texto = re.sub(r"\braíz\b", "raiz", texto, flags=re.IGNORECASE)
    for funcion in _FUNCIONES_PERMITIDAS:
        texto = re.sub(
            rf"\b{re.escape(funcion)}\b",
            funcion,
            texto,
            flags=re.IGNORECASE,
        )
    return texto


def _funcion_canonica(nombre):
    return _ALIAS_FUNCIONES.get(nombre, nombre)


def _validar_nodo_expresion(nodo, variables, funciones):
    if isinstance(nodo, ast.Expression):
        _validar_nodo_expresion(nodo.body, variables, funciones)
        return
    if isinstance(nodo, ast.Constant):
        if type(nodo.value) not in (int, float):
            raise ErrorFormula("La fórmula solo admite constantes numéricas.")
        if not math.isfinite(float(nodo.value)) or abs(float(nodo.value)) > 1e12:
            raise ErrorFormula("La fórmula contiene un número fuera del límite permitido.")
        return
    if isinstance(nodo, ast.Name):
        permitidas = (
            set(ROLES)
            | {VARIABLE_SENAL_RANGO, "tiempo"}
            | set(VARIABLES_CONTEXTO)
            | set(CONSTANTES_PERSONALIZADAS)
        )
        if nodo.id not in permitidas:
            raise ErrorFormula(f"No se reconoce «{nodo.id}» como dato o constante.")
        variables.add(nodo.id)
        return
    if isinstance(nodo, ast.BinOp):
        if type(nodo.op) not in _OPERADORES_BINARIOS:
            raise ErrorFormula("Ese operador no está permitido en las fórmulas.")
        if isinstance(nodo.op, ast.Pow) and isinstance(nodo.right, ast.Constant):
            if abs(float(nodo.right.value)) > 20:
                raise ErrorFormula("El exponente debe estar entre -20 y 20.")
        _validar_nodo_expresion(nodo.left, variables, funciones)
        _validar_nodo_expresion(nodo.right, variables, funciones)
        return
    if isinstance(nodo, ast.UnaryOp):
        if type(nodo.op) not in _OPERADORES_UNARIOS:
            raise ErrorFormula("Ese operador unario no está permitido.")
        _validar_nodo_expresion(nodo.operand, variables, funciones)
        return
    if isinstance(nodo, ast.Call):
        if (
            not isinstance(nodo.func, ast.Name)
            or nodo.func.id not in _FUNCIONES_PERMITIDAS
        ):
            nombre = nodo.func.id if isinstance(nodo.func, ast.Name) else "esa función"
            raise ErrorFormula(f"No se permite usar «{nombre}» en una fórmula.")
        if nodo.keywords or len(nodo.args) != 1:
            raise ErrorFormula("Cada función del constructor recibe un solo elemento.")
        funciones.add(_funcion_canonica(nodo.func.id))
        _validar_nodo_expresion(nodo.args[0], variables, funciones)
        return
    raise ErrorFormula(
        "La expresión contiene una construcción no permitida. Usá solo los "
        "datos, operadores y funciones del constructor."
    )


def _nodo_devuelve_vector(nodo):
    """Infiere si el resultado conserva una muestra por frame o es un dato."""
    if isinstance(nodo, ast.Constant):
        return False
    if isinstance(nodo, ast.Name):
        return nodo.id in set(ROLES) | {VARIABLE_SENAL_RANGO, "tiempo"}
    if isinstance(nodo, ast.UnaryOp):
        return _nodo_devuelve_vector(nodo.operand)
    if isinstance(nodo, ast.BinOp):
        return _nodo_devuelve_vector(nodo.left) or _nodo_devuelve_vector(nodo.right)
    if isinstance(nodo, ast.Call):
        funcion = _funcion_canonica(nodo.func.id)
        if funcion in _FUNCIONES_REDUCTORAS:
            return False
        return _nodo_devuelve_vector(nodo.args[0])
    return False


def analizar_expresion_personalizada(expresion) -> dict:
    """Valida la expresión y devuelve qué datos y funciones necesita."""
    texto = normalizar_expresion_personalizada(expresion)
    if not texto:
        raise ErrorFormula("Armá la fórmula antes de guardarla.")
    if len(texto) > 500:
        raise ErrorFormula("La fórmula es demasiado larga (máximo 500 caracteres).")
    try:
        arbol = ast.parse(texto, mode="eval")
    except SyntaxError as exc:
        raise ErrorFormula(
            "La fórmula está incompleta. Revisá los operadores y paréntesis."
        ) from exc
    if sum(1 for _nodo in ast.walk(arbol)) > 120:
        raise ErrorFormula("La fórmula contiene demasiadas operaciones.")

    variables, funciones = set(), set()
    _validar_nodo_expresion(arbol, variables, funciones)
    senales = (variables & set(ROLES)) | ({VARIABLE_SENAL_RANGO} & variables)
    if not senales:
        raise ErrorFormula(
            "La fórmula debe usar al menos una señal, por ejemplo «Señal del "
            "rango» o Fz."
        )

    return {
        "texto": texto,
        "arbol": arbol,
        "variables": frozenset(variables),
        "funciones": frozenset(funciones),
        "resultado_escalar": not _nodo_devuelve_vector(arbol.body),
    }


def _reducir_finito(valor, funcion, nombre):
    arreglo = np.asarray(valor, dtype=float).reshape(-1)
    finitos = arreglo[np.isfinite(arreglo)]
    if finitos.size == 0:
        raise ErrorFormula(f"«{nombre}» no recibió muestras válidas.")
    return float(funcion(finitos))


def _evaluar_nodo_personalizado(nodo, variables, frecuencia):
    if isinstance(nodo, ast.Constant):
        return float(nodo.value)
    if isinstance(nodo, ast.Name):
        if nodo.id in CONSTANTES_PERSONALIZADAS:
            return CONSTANTES_PERSONALIZADAS[nodo.id]
        if nodo.id not in variables:
            raise ErrorFormula(f"No está disponible el dato «{nodo.id}».")
        return variables[nodo.id]
    if isinstance(nodo, ast.UnaryOp):
        return _OPERADORES_UNARIOS[type(nodo.op)](
            _evaluar_nodo_personalizado(nodo.operand, variables, frecuencia)
        )
    if isinstance(nodo, ast.BinOp):
        izquierda = _evaluar_nodo_personalizado(nodo.left, variables, frecuencia)
        derecha = _evaluar_nodo_personalizado(nodo.right, variables, frecuencia)
        with np.errstate(all="ignore"):
            return _OPERADORES_BINARIOS[type(nodo.op)](izquierda, derecha)
    if isinstance(nodo, ast.Call):
        nombre = _funcion_canonica(nodo.func.id)
        valor = _evaluar_nodo_personalizado(nodo.args[0], variables, frecuencia)
        if nombre == "abs":
            return np.abs(valor)
        if nombre == "raiz":
            with np.errstate(all="ignore"):
                return np.sqrt(valor)
        if nombre == "log":
            with np.errstate(all="ignore"):
                return np.log(valor)
        if nombre == "exp":
            with np.errstate(all="ignore"):
                return np.exp(valor)
        if nombre == "promedio":
            return _reducir_finito(valor, np.mean, nombre)
        if nombre == "maximo":
            return _reducir_finito(valor, np.max, nombre)
        if nombre == "minimo":
            return _reducir_finito(valor, np.min, nombre)
        if nombre == "rms":
            return _reducir_finito(
                valor, lambda datos: np.sqrt(np.mean(datos**2)), nombre
            )
        if nombre == "suma":
            return _reducir_finito(valor, np.sum, nombre)
        frecuencia = float(frecuencia or 0)
        if frecuencia <= 0:
            raise ErrorFormula(VARIABLES_CONTEXTO["frecuencia"])
        arreglo = np.asarray(valor, dtype=float)
        if arreglo.ndim != 1 or arreglo.size < 2:
            raise ErrorFormula(
                f"«{nombre}» necesita una señal con al menos dos muestras."
            )
        if nombre == "integral":
            return _integrar_acumulado(arreglo, 1.0 / frecuencia)
        if nombre == "derivada":
            return np.gradient(arreglo, 1.0 / frecuencia, edge_order=1)
    raise ErrorFormula("No se pudo interpretar la fórmula.")


def _evaluar_analisis_personalizado(analisis, variables, frecuencia=None):
    resultado = _evaluar_nodo_personalizado(
        analisis["arbol"].body, variables, frecuencia
    )
    arreglo = np.asarray(resultado, dtype=float)
    if arreglo.ndim > 1:
        raise ErrorFormula("La fórmula debe devolver un número o una sola señal.")
    if arreglo.size == 0 or not np.isfinite(arreglo).any():
        raise ErrorFormula(
            "La fórmula no produjo valores válidos. Revisá raíces y divisiones por cero."
        )
    return float(arreglo) if arreglo.ndim == 0 else arreglo


def evaluar_expresion_personalizada(expresion, variables, frecuencia=None):
    """Evalúa una expresión validada sin ejecutar código arbitrario."""
    analisis = analizar_expresion_personalizada(expresion)
    return _evaluar_analisis_personalizado(analisis, variables, frecuencia)


FORMULAS = {
    "potencia": {
        "nombre": NOMBRE_POTENCIA,
        "articulo": "la",
        "expresion": EXPRESION_POTENCIA,
        "expresion_constructor": (
            "Fz * integral((Fz - masa * gravedad) / masa)"
        ),
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
        "expresion_constructor": "integral(Fz - masa * gravedad)",
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


_CLAVES_INTEGRADAS = frozenset(FORMULAS)


def crear_descriptor_personalizado(datos) -> dict:
    """Convierte un registro persistido en una fórmula consumible por el motor."""
    clave = str(datos.get("clave") or "").strip()
    nombre = str(datos.get("nombre") or "").strip()
    unidad = normalizar_unidad_formula(datos.get("unidad"))
    descripcion = str(datos.get("descripcion") or "").strip()
    if not clave or clave in _CLAVES_INTEGRADAS:
        raise ErrorFormula("La fórmula personalizada no tiene una clave válida.")
    if not nombre:
        raise ErrorFormula("Ingresá un nombre para guardar la fórmula.")

    analisis = analizar_expresion_personalizada(datos.get("expresion"))
    variables = analisis["variables"]
    roles_requeridos = tuple(rol for rol in ROLES if rol in variables)
    usa_senal = VARIABLE_SENAL_RANGO in variables
    funciones_temporales = bool(analisis["funciones"] & _FUNCIONES_TEMPORALES)

    requiere = {
        variable: mensaje
        for variable, mensaje in VARIABLES_CONTEXTO.items()
        if variable in variables
    }
    if funciones_temporales or "tiempo" in variables:
        requiere["frecuencia"] = VARIABLES_CONTEXTO["frecuencia"]

    def _computar(roles, contexto, eleccion=None):
        valores = dict(roles)
        for variable in VARIABLES_CONTEXTO:
            if variable in variables:
                valores[variable] = contexto.get(variable)

        if "tiempo" in variables:
            series = [
                np.asarray(serie, dtype=float)
                for serie in roles.values()
                if np.asarray(serie).ndim == 1
            ]
            if not series:
                raise ErrorFormula("No hay una señal para construir el eje de tiempo.")
            frecuencia = float(contexto.get("frecuencia") or 0)
            if frecuencia <= 0:
                raise ErrorFormula(VARIABLES_CONTEXTO["frecuencia"])
            valores["tiempo"] = np.arange(series[0].size, dtype=float) / frecuencia

        return _evaluar_analisis_personalizado(
            analisis, valores, contexto.get("frecuencia")
        )

    descriptor = {
        "nombre": nombre,
        "articulo": "la",
        "expresion": analisis["texto"],
        "expresion_constructor": analisis["texto"],
        "descripcion": descripcion,
        "unidad": unidad,
        "salida_rol": VARIABLE_SENAL_RANGO if usa_senal else roles_requeridos[0],
        "integra_en_registro": (
            (funciones_temporales or "tiempo" in variables)
            and not analisis["resultado_escalar"]
        ),
        "resultado_escalar": analisis["resultado_escalar"],
        "requiere_roles": roles_requeridos,
        "requiere": requiere,
        "usa_senal_rango": usa_senal,
        "personalizada": True,
        "reutilizable": bool(datos.get("reutilizable", True)),
        "id_db": datos.get("id"),
        "computar": _computar,
    }
    if not usa_senal and len(roles_requeridos) == 1:
        rol = roles_requeridos[0]
        descriptor["rangos_en_rol"] = {
            "rol": rol,
            "mensaje": (
                f"«{nombre}» usa {rol} como señal principal. Seleccioná rangos "
                f"de la gráfica correspondiente a {rol}."
            ),
        }
    return descriptor


def registrar_formula_personalizada(datos) -> str:
    clave = str(datos.get("clave") or "").strip()
    descriptor = crear_descriptor_personalizado(datos)
    FORMULAS[clave] = descriptor
    return clave


def quitar_formula_personalizada(clave) -> bool:
    if clave in _CLAVES_INTEGRADAS or clave not in FORMULAS:
        return False
    del FORMULAS[clave]
    return True


def limpiar_formulas_personalizadas():
    for clave in list(FORMULAS):
        if clave not in _CLAVES_INTEGRADAS:
            del FORMULAS[clave]


def es_formula_personalizada(clave) -> bool:
    return bool(FORMULAS.get(clave, {}).get("personalizada"))


def nombre_formula_en_uso(nombre, excluir_clave=None) -> bool:
    buscado = str(nombre or "").strip().casefold()
    return any(
        clave != excluir_clave
        and str(descripcion.get("nombre") or "").strip().casefold() == buscado
        for clave, descripcion in FORMULAS.items()
    )


def descripcion_formula(clave):
    return FORMULAS[clave]


def calculos_reutilizables(excluir_clave=None):
    """Cálculos que el constructor puede copiar dentro de otra expresión."""
    disponibles = []
    for calculo in CALCULOS_AUXILIARES:
        analisis = analizar_expresion_personalizada(calculo["expresion"])
        disponibles.append(
            {
                **calculo,
                "expresion": analisis["texto"],
                "tipo": "Cálculo auxiliar",
                "resultado_escalar": analisis["resultado_escalar"],
            }
        )

    for clave, descripcion in FORMULAS.items():
        if clave == excluir_clave:
            continue
        if (
            descripcion.get("personalizada")
            and not descripcion.get("reutilizable", True)
        ):
            continue
        expresion = descripcion.get("expresion_constructor")
        if not expresion:
            continue
        try:
            analisis = analizar_expresion_personalizada(expresion)
        except ErrorFormula:
            continue
        disponibles.append(
            {
                "clave": clave,
                "nombre": descripcion["nombre"],
                "expresion": analisis["texto"],
                "descripcion": descripcion.get("descripcion") or (
                    "Copia el cálculo interno de esta fórmula."
                ),
                "unidad": descripcion.get("unidad") or "",
                "tipo": (
                    "Fórmula propia"
                    if descripcion.get("personalizada")
                    else "Fórmula incorporada"
                ),
                "resultado_escalar": analisis["resultado_escalar"],
            }
        )
    return disponibles


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


def registrar_aplicacion_formula(aplicaciones, configuracion):
    """Agrega rangos a una fórmula sin borrar aplicaciones anteriores."""
    configuracion = dict(configuracion or {})
    clave = str(configuracion.get("clave") or "").strip()
    if not clave:
        raise ErrorFormula("La aplicación no identifica qué fórmula debe usar.")

    resultado = {
        str(clave_existente): dict(datos)
        for clave_existente, datos in (aplicaciones or {}).items()
    }
    anterior = resultado.get(clave, {})
    configuracion = {**anterior, **configuracion, "clave": clave}
    configuracion["rangos"] = list(
        dict.fromkeys(
            [
                *(anterior.get("rangos") or ()),
                *(configuracion.get("rangos") or ()),
            ]
        )
    )
    # Sacarla y volverla a insertar deja al final la aplicación más reciente.
    resultado.pop(clave, None)
    resultado[clave] = configuracion
    return resultado


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


def _preparar_salida_personalizada(valores, x_segmento):
    """Separa un resultado único de una señal con una muestra por frame."""
    arreglo = np.asarray(valores, dtype=float)
    if arreglo.ndim == 0 or arreglo.size == 1:
        valor = float(arreglo.reshape(-1)[0])
        return (valor, None) if math.isfinite(valor) else (None, None)
    if arreglo.ndim != 1 or arreglo.size != len(x_segmento):
        raise ErrorFormula(
            "La fórmula produjo una cantidad de valores distinta a la señal de entrada."
        )
    return None, arreglo


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
        if valores_registro.ndim != 1 or valores_registro.size != x_reg.size:
            raise ErrorFormula(
                "La fórmula temporal debe producir una muestra por cada frame."
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
        calculado = desc["computar"](seg_roles, contexto, eleccion)
        valor_escalar, valores = _preparar_salida_personalizada(calculado, x_seg)
        if valor_escalar is None and valores is None:
            continue
        datos_resumen = resumen(x_seg, valores) if valores is not None else resumen([], [])
        nombre_rango = datos.get("nombre") or f"Rango {datos.get('numero')}"

        resultado = {
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
                valores if valores is not None else np.asarray([valor_escalar]),
                seg_roles,
                contexto,
                eleccion,
            ),
        }
        if valor_escalar is not None:
            resultado["valor"] = valor_escalar
        resultados.append(resultado)
        segmentos.append(
            (x_seg, valores)
            if valores is not None
            else (np.array([], dtype=float), np.array([], dtype=float))
        )

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
                    "desde": datos.get("desde"),
                    "hasta": datos.get("hasta"),
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


def preparar_curvas_formulas_por_grafica(calculos, orden=None):
    """Prepara cada formula como una curva independiente por grafica."""
    calculos = calculos or {}
    claves = list(orden) if orden is not None else list(calculos)
    por_grafica = {}

    for clave in claves:
        calculo = calculos.get(clave)
        if calculo is None:
            continue
        datos_panel = calculo.get("datos_panel") or {}
        nombre = datos_panel.get("nombre") or clave
        unidad = datos_panel.get("unidad") or ""

        for propietario, grupo in (calculo.get("por_grafica") or {}).items():
            curva = concatenar_curva(grupo.get("segmentos") or [])
            picos = picos_de_resultados(grupo.get("resultados") or [])
            for pico in picos:
                pico.update({"formula": nombre, "unidad": unidad})

            por_grafica.setdefault(propietario, []).append(
                {
                    "clave": clave,
                    "nombre": nombre,
                    "unidad": unidad,
                    "x": curva["x"],
                    "y": curva["y"],
                    "picos": picos,
                }
            )

    return por_grafica
