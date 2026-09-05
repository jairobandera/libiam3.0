"""Vista matemática liviana para las fórmulas del constructor.

El motor conserva expresiones simples como ``Fz * integral(...)`` porque son
fáciles de guardar y validar. Este widget interpreta el mismo AST seguro y lo
dibuja con notación matemática, sin ejecutar la expresión ni depender de un
navegador, MathJax o una instalación de LaTeX.
"""

from __future__ import annotations

import ast
import math

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import (
    QFont,
    QFontDatabase,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QStyle, QStyleOption, QWidget

from logica import formulas as formulas_logica


class _Caja:
    """Elemento medido respecto de una línea base tipográfica."""

    def __init__(self, ancho, ascenso, descenso):
        self.ancho = float(max(0.0, ancho))
        self.ascenso = float(max(0.0, ascenso))
        self.descenso = float(max(0.0, descenso))

    @property
    def alto(self):
        return self.ascenso + self.descenso

    def pintar(self, pintor, x, base, color):  # pragma: no cover - interfaz
        raise NotImplementedError


class _CajaTexto(_Caja):
    def __init__(self, texto, fuente):
        self.texto = str(texto)
        self.fuente = QFont(fuente)
        metricas = QFontMetricsF(self.fuente)
        super().__init__(
            metricas.horizontalAdvance(self.texto),
            metricas.ascent(),
            metricas.descent(),
        )

    def pintar(self, pintor, x, base, color):
        pintor.setFont(self.fuente)
        pintor.setPen(color)
        pintor.drawText(QPointF(x, base), self.texto)


class _CajaEspacio(_Caja):
    def __init__(self, ancho):
        super().__init__(ancho, 0, 0)

    def pintar(self, _pintor, _x, _base, _color):
        return


class _CajaFila(_Caja):
    def __init__(self, elementos):
        self.elementos = tuple(elementos)
        super().__init__(
            sum(elemento.ancho for elemento in self.elementos),
            max((elemento.ascenso for elemento in self.elementos), default=0),
            max((elemento.descenso for elemento in self.elementos), default=0),
        )

    def pintar(self, pintor, x, base, color):
        cursor = x
        for elemento in self.elementos:
            elemento.pintar(pintor, cursor, base, color)
            cursor += elemento.ancho


class _CajaFraccion(_Caja):
    def __init__(self, numerador, denominador, escala):
        self.numerador = numerador
        self.denominador = denominador
        self.relleno = 4.0 * escala
        self.separacion = 2.6 * escala
        self.eje = 4.0 * escala
        self.grosor = max(1.0, 1.15 * escala)
        ancho = max(numerador.ancho, denominador.ancho) + 2 * self.relleno
        ascenso = self.eje + self.separacion + numerador.alto
        descenso = max(
            denominador.alto + self.separacion - self.eje,
            denominador.descenso,
        )
        super().__init__(ancho, ascenso, descenso)

    def pintar(self, pintor, x, base, color):
        y_linea = base - self.eje
        x_num = x + (self.ancho - self.numerador.ancho) / 2
        base_num = y_linea - self.separacion - self.numerador.descenso
        self.numerador.pintar(pintor, x_num, base_num, color)

        x_den = x + (self.ancho - self.denominador.ancho) / 2
        base_den = y_linea + self.separacion + self.denominador.ascenso
        self.denominador.pintar(pintor, x_den, base_den, color)

        pintor.save()
        pintor.setPen(QPen(color, self.grosor, Qt.SolidLine, Qt.RoundCap))
        pintor.drawLine(QPointF(x, y_linea), QPointF(x + self.ancho, y_linea))
        pintor.restore()


class _CajaPotencia(_Caja):
    def __init__(self, base, exponente, escala):
        self.base = base
        self.exponente = exponente
        self.espacio = 1.0 * escala
        self.elevacion = max(base.ascenso * 0.62, 7.0 * escala)
        super().__init__(
            base.ancho + self.espacio + exponente.ancho,
            max(base.ascenso, self.elevacion + exponente.ascenso),
            max(base.descenso, exponente.descenso - self.elevacion),
        )

    def pintar(self, pintor, x, base, color):
        self.base.pintar(pintor, x, base, color)
        self.exponente.pintar(
            pintor,
            x + self.base.ancho + self.espacio,
            base - self.elevacion,
            color,
        )


class _CajaSubindice(_Caja):
    def __init__(self, base, subindice, escala):
        self.base = base
        self.subindice = subindice
        self.caida = max(base.descenso + subindice.ascenso * 0.28, 3.5 * escala)
        super().__init__(
            base.ancho + subindice.ancho,
            max(base.ascenso, subindice.ascenso - self.caida),
            max(base.descenso, self.caida + subindice.descenso),
        )

    def pintar(self, pintor, x, base, color):
        self.base.pintar(pintor, x, base, color)
        self.subindice.pintar(
            pintor,
            x + self.base.ancho,
            base + self.caida,
            color,
        )


class _CajaDelimitada(_Caja):
    def __init__(self, contenido, escala, tipo="parentesis"):
        self.contenido = contenido
        self.tipo = tipo
        self.margen = 3.0 * escala
        self.ancho_delimitador = max(5.0, 5.8 * escala)
        super().__init__(
            contenido.ancho + 2 * (self.margen + self.ancho_delimitador),
            contenido.ascenso + 2.5 * escala,
            contenido.descenso + 2.5 * escala,
        )

    def _parentesis(self, pintor, x, arriba, abajo, izquierda):
        ancho = self.ancho_delimitador
        medio = (arriba + abajo) / 2
        ruta = QPainterPath()
        if izquierda:
            ruta.moveTo(x + ancho, arriba)
            ruta.cubicTo(x + 1, arriba + (medio - arriba) * 0.45,
                         x + 1, medio - (medio - arriba) * 0.12, x, medio)
            ruta.cubicTo(x + 1, medio + (abajo - medio) * 0.12,
                         x + 1, abajo - (abajo - medio) * 0.45, x + ancho, abajo)
        else:
            ruta.moveTo(x, arriba)
            ruta.cubicTo(x + ancho - 1, arriba + (medio - arriba) * 0.45,
                         x + ancho - 1, medio - (medio - arriba) * 0.12,
                         x + ancho, medio)
            ruta.cubicTo(x + ancho - 1, medio + (abajo - medio) * 0.12,
                         x + ancho - 1, abajo - (abajo - medio) * 0.45, x, abajo)
        pintor.drawPath(ruta)

    def pintar(self, pintor, x, base, color):
        arriba = base - self.ascenso + 1
        abajo = base + self.descenso - 1
        x_izq = x
        x_contenido = x + self.ancho_delimitador + self.margen
        x_der = x_contenido + self.contenido.ancho + self.margen

        pintor.save()
        pintor.setPen(QPen(color, 1.35, Qt.SolidLine, Qt.RoundCap))
        if self.tipo == "valor_absoluto":
            pintor.drawLine(QPointF(x_izq + self.ancho_delimitador / 2, arriba),
                            QPointF(x_izq + self.ancho_delimitador / 2, abajo))
            pintor.drawLine(QPointF(x_der + self.ancho_delimitador / 2, arriba),
                            QPointF(x_der + self.ancho_delimitador / 2, abajo))
        else:
            self._parentesis(pintor, x_izq, arriba, abajo, True)
            self._parentesis(pintor, x_der, arriba, abajo, False)
        pintor.restore()
        self.contenido.pintar(pintor, x_contenido, base, color)


class _CajaRaiz(_Caja):
    def __init__(self, radical, contenido, escala):
        self.radical = radical
        self.contenido = contenido
        self.solape = 2.0 * escala
        self.margen_superior = 2.5 * escala
        super().__init__(
            radical.ancho + contenido.ancho + self.solape,
            max(radical.ascenso, contenido.ascenso + self.margen_superior),
            max(radical.descenso, contenido.descenso),
        )

    def pintar(self, pintor, x, base, color):
        self.radical.pintar(pintor, x, base, color)
        x_contenido = x + self.radical.ancho + self.solape
        self.contenido.pintar(pintor, x_contenido, base, color)
        y = base - self.contenido.ascenso - self.margen_superior * 0.45
        pintor.save()
        pintor.setPen(QPen(color, 1.15, Qt.SolidLine, Qt.RoundCap))
        pintor.drawLine(
            QPointF(x + self.radical.ancho * 0.72, y),
            QPointF(x + self.ancho, y),
        )
        pintor.restore()


class _CajaSobrelinea(_Caja):
    def __init__(self, contenido, escala):
        self.contenido = contenido
        self.separacion = 2.2 * escala
        super().__init__(
            contenido.ancho,
            contenido.ascenso + self.separacion + 1,
            contenido.descenso,
        )

    def pintar(self, pintor, x, base, color):
        self.contenido.pintar(pintor, x, base, color)
        y = base - self.contenido.ascenso - self.separacion
        pintor.save()
        pintor.setPen(QPen(color, 1.1, Qt.SolidLine, Qt.RoundCap))
        pintor.drawLine(QPointF(x, y), QPointF(x + self.ancho, y))
        pintor.restore()


class _ConstructorCajas:
    """Convierte un AST validado en cajas tipográficas dibujables."""

    _PRECEDENCIA_SUMA = 10
    _PRECEDENCIA_PRODUCTO = 20
    _PRECEDENCIA_UNARIO = 25
    _PRECEDENCIA_POTENCIA = 30
    _PRECEDENCIA_ATOMO = 50

    def __init__(self, familia, tamano_px=19):
        self.familia = familia
        self.tamano_px = tamano_px

    def _fuente(self, escala=1.0, cursiva=False, negrita=False):
        fuente = QFont(self.familia)
        fuente.setPixelSize(max(7, round(self.tamano_px * escala)))
        fuente.setItalic(cursiva)
        if negrita:
            fuente.setWeight(QFont.Weight.DemiBold)
        return fuente

    def _texto(self, texto, escala=1.0, cursiva=False, negrita=False):
        return _CajaTexto(texto, self._fuente(escala, cursiva, negrita))

    @staticmethod
    def _fila(*elementos):
        return _CajaFila(elementos)

    def _espacio(self, escala=1.0, ancho=4.0):
        return _CajaEspacio(ancho * escala)

    def _operacion(self, izquierda, simbolo, derecha, escala):
        return self._fila(
            izquierda,
            self._espacio(escala),
            self._texto(simbolo, escala),
            self._espacio(escala),
            derecha,
        )

    def _variable(self, nombre, escala):
        if nombre in formulas_logica.ROLES:
            base = self._texto(nombre[0], escala, cursiva=True)
            sub = self._texto(nombre[1:].lower(), escala * 0.68, cursiva=True)
            simbolo = _CajaSubindice(base, sub, escala)
            return self._fila(
                simbolo,
                self._texto("(", escala),
                self._texto("t", escala, cursiva=True),
                self._texto(")", escala),
            )
        if nombre == formulas_logica.VARIABLE_SENAL_INTERVALO:
            return self._fila(
                self._texto("señal", escala),
                self._texto("(", escala),
                self._texto("t", escala, cursiva=True),
                self._texto(")", escala),
            )
        if nombre == "masa":
            return self._texto("m", escala, cursiva=True)
        if nombre == "estatura":
            return self._texto("h", escala, cursiva=True)
        if nombre == "gravedad":
            return self._texto("g", escala, cursiva=True)
        if nombre == "tiempo":
            return self._texto("t", escala, cursiva=True)
        if nombre == "frecuencia":
            return _CajaSubindice(
                self._texto("f", escala, cursiva=True),
                self._texto("s", escala * 0.68, cursiva=True),
                escala,
            )
        if nombre == "pi":
            return self._texto("π", escala, cursiva=True)
        if nombre == "e":
            return self._texto("e", escala, cursiva=True)
        return self._texto(nombre, escala, cursiva=True)

    def _funcion_con_parentesis(self, nombre, argumento, escala, negrita=False):
        return self._fila(
            self._texto(nombre, escala, negrita=negrita),
            self._espacio(escala, 1.4),
            _CajaDelimitada(argumento, escala),
        )

    def _integral(self, nodo_argumento, escala):
        argumento, _ = self._construir(nodo_argumento, escala, 0)
        return self._fila(
            self._texto("∫", escala * 1.85),
            self._espacio(escala, 2.5),
            argumento,
            self._espacio(escala, 4.0),
            self._texto("d", escala, cursiva=True),
            self._texto("t", escala, cursiva=True),
        )

    def _derivada(self, nodo_argumento, escala):
        argumento, precedencia = self._construir(nodo_argumento, escala * 0.9, 0)
        diferencial = self._texto("d", escala * 0.9, cursiva=True)
        dt = self._fila(
            self._texto("d", escala * 0.9, cursiva=True),
            self._texto("t", escala * 0.9, cursiva=True),
        )
        if precedencia >= self._PRECEDENCIA_ATOMO:
            numerador = self._fila(diferencial, argumento)
            return _CajaFraccion(numerador, dt, escala)
        operador = _CajaFraccion(diferencial, dt, escala)
        argumento_grande, _ = self._construir(nodo_argumento, escala, 0)
        return self._fila(
            operador,
            self._espacio(escala, 2.0),
            _CajaDelimitada(argumento_grande, escala),
        )

    def _llamada(self, nodo, escala):
        nombre = formulas_logica._funcion_canonica(nodo.func.id)
        argumento_nodo = nodo.args[0]
        if nombre == "integral":
            return self._integral(argumento_nodo, escala)
        if nombre == "derivada":
            return self._derivada(argumento_nodo, escala)

        argumento, _ = self._construir(argumento_nodo, escala, 0)
        if nombre == "raiz":
            radical = self._texto("√", escala * 1.18)
            return _CajaRaiz(radical, argumento, escala)
        if nombre == "abs":
            return _CajaDelimitada(argumento, escala, "valor_absoluto")
        if nombre == "promedio":
            return _CajaSobrelinea(argumento, escala)
        if nombre == "exp":
            exponente, _ = self._construir(argumento_nodo, escala * 0.7, 0)
            return _CajaPotencia(
                self._texto("e", escala, cursiva=True), exponente, escala
            )

        etiqueta = {
            "maximo": "máx",
            "minimo": "mín",
            "rms": "RMS",
            "suma": "Σ",
            "log": "ln",
        }.get(nombre, nombre)
        return self._funcion_con_parentesis(
            etiqueta, argumento, escala, negrita=(nombre == "rms")
        )

    @staticmethod
    def _numero(valor):
        if isinstance(valor, int):
            return str(valor)
        if float(valor).is_integer() and abs(float(valor)) < 1e12:
            return str(int(valor))
        return format(float(valor), ".10g")

    def _construir(self, nodo, escala=1.0, precedencia_padre=0):
        if isinstance(nodo, ast.Expression):
            return self._construir(nodo.body, escala, precedencia_padre)

        if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
            caja = self._texto(self._numero(nodo.value), escala)
            precedencia = self._PRECEDENCIA_ATOMO
        elif isinstance(nodo, ast.Name):
            caja = self._variable(nodo.id, escala)
            precedencia = self._PRECEDENCIA_ATOMO
        elif (
            isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.args
        ):
            caja = self._llamada(nodo, escala)
            precedencia = self._PRECEDENCIA_ATOMO
        elif isinstance(nodo, ast.UnaryOp) and isinstance(
            nodo.op, (ast.UAdd, ast.USub)
        ):
            operando, _ = self._construir(
                nodo.operand, escala, self._PRECEDENCIA_UNARIO
            )
            signo = "+" if isinstance(nodo.op, ast.UAdd) else "−"
            caja = self._fila(self._texto(signo, escala), operando)
            precedencia = self._PRECEDENCIA_UNARIO
        elif isinstance(nodo, ast.BinOp):
            if isinstance(nodo.op, ast.Div):
                numerador, _ = self._construir(nodo.left, escala * 0.9, 0)
                denominador, _ = self._construir(nodo.right, escala * 0.9, 0)
                caja = _CajaFraccion(numerador, denominador, escala)
                precedencia = self._PRECEDENCIA_PRODUCTO
            elif isinstance(nodo.op, ast.Pow):
                base, _ = self._construir(
                    nodo.left, escala, self._PRECEDENCIA_POTENCIA + 1
                )
                exponente, _ = self._construir(nodo.right, escala * 0.7, 0)
                caja = _CajaPotencia(base, exponente, escala)
                precedencia = self._PRECEDENCIA_POTENCIA
            elif isinstance(nodo.op, (ast.Mult, ast.Mod)):
                izquierda, _ = self._construir(
                    nodo.left, escala, self._PRECEDENCIA_PRODUCTO
                )
                derecha, _ = self._construir(
                    nodo.right, escala, self._PRECEDENCIA_PRODUCTO
                )
                simbolo = "·" if isinstance(nodo.op, ast.Mult) else "mod"
                caja = self._operacion(izquierda, simbolo, derecha, escala)
                precedencia = self._PRECEDENCIA_PRODUCTO
            elif isinstance(nodo.op, (ast.Add, ast.Sub)):
                precedencia = self._PRECEDENCIA_SUMA
                izquierda, _ = self._construir(nodo.left, escala, precedencia)
                derecha, _ = self._construir(
                    nodo.right,
                    escala,
                    precedencia + (1 if isinstance(nodo.op, ast.Sub) else 0),
                )
                simbolo = "+" if isinstance(nodo.op, ast.Add) else "−"
                caja = self._operacion(izquierda, simbolo, derecha, escala)
            else:
                caja = self._texto("?", escala)
                precedencia = self._PRECEDENCIA_ATOMO
        else:
            caja = self._texto("?", escala)
            precedencia = self._PRECEDENCIA_ATOMO

        if precedencia < precedencia_padre:
            caja = _CajaDelimitada(caja, escala)
        return caja, precedencia

    def construir(self, arbol):
        caja, _ = self._construir(arbol, 1.0, 0)
        return caja


def _familia_matematica():
    disponibles = set(QFontDatabase.families())
    for candidata in (
        "Cambria Math",
        "STIX Two Math",
        "STIXGeneral",
        "DejaVu Serif",
    ):
        if candidata in disponibles:
            return candidata
    return QFont().defaultFamily()


class VistaFormulaMatematica(QWidget):
    """Renderiza la expresión en notación matemática sin cambiar su contenido."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._texto_original = ""
        self._arbol = None
        self._caja = None
        self._familia = _familia_matematica()
        self.setObjectName("vistaFormula")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        politica = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        politica.setHeightForWidth(True)
        self.setSizePolicy(politica)
        self.setMinimumHeight(96)
        self.setAccessibleName("Vista matemática de la fórmula")

    def set_expresion(self, expresion):
        self._texto_original = str(expresion or "").strip()
        self._arbol = None
        self._caja = None
        if self._texto_original:
            try:
                texto = formulas_logica.normalizar_expresion_personalizada(
                    self._texto_original
                )
                if len(texto) <= 500:
                    self._arbol = ast.parse(texto, mode="eval")
                    self._caja = _ConstructorCajas(self._familia).construir(self._arbol)
            except (SyntaxError, TypeError, ValueError, RecursionError):
                self._arbol = None
                self._caja = None
        self.setAccessibleDescription(self._texto_original)
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        if self._caja is None:
            return QSize(560, 96)
        return QSize(
            560,
            max(96, min(150, math.ceil(self._caja.alto + 30))),
        )

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, ancho):
        if self._caja is None:
            return 96
        disponible = max(1.0, ancho - 28.0)
        escala = min(1.0, disponible / max(1.0, self._caja.ancho))
        return max(96, min(150, math.ceil(self._caja.alto * escala + 28)))

    def _dibujar_fondo(self, pintor):
        opcion = QStyleOption()
        opcion.initFrom(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, opcion, pintor, self
        )

    def paintEvent(self, _evento):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pintor.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self._dibujar_fondo(pintor)
        color = self.palette().color(QPalette.ColorRole.WindowText)

        if self._caja is None:
            fuente = QFont(self.font())
            fuente.setPixelSize(13)
            pintor.setFont(fuente)
            color_placeholder = self.palette().color(
                QPalette.ColorRole.PlaceholderText
            )
            pintor.setPen(color_placeholder)
            texto = (
                "La ecuación aparecerá aquí."
                if not self._texto_original
                else "Completá la fórmula para ver la ecuación."
            )
            pintor.drawText(
                self.rect().adjusted(12, 8, -12, -8),
                Qt.AlignmentFlag.AlignCenter,
                texto,
            )
            return

        margen = 14.0
        ancho_disponible = max(1.0, self.width() - 2 * margen)
        alto_disponible = max(1.0, self.height() - 2 * margen)
        escala = min(
            1.0,
            ancho_disponible / max(1.0, self._caja.ancho),
            alto_disponible / max(1.0, self._caja.alto),
        )
        ancho = self._caja.ancho * escala
        x = (self.width() - ancho) / 2
        base = (
            self.height()
            + escala * (self._caja.ascenso - self._caja.descenso)
        ) / 2

        pintor.save()
        pintor.translate(x, base)
        pintor.scale(escala, escala)
        self._caja.pintar(pintor, 0, 0, color)
        pintor.restore()
