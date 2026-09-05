"""Constructor visual y seguro de fórmulas personalizadas."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from logica import formulas as formulas_logica
from ui.ventanaPrincipal.panelDerecho.vistaFormula import VistaFormulaMatematica


PLANTILLAS = (
    {
        "texto": "Potencia",
        "nombre": "Potencia personalizada",
        "expresion": "Fz * integral((Fz - masa * gravedad) / masa)",
        "unidad": "W",
        "ayuda": "Usa Fz.",
    },
    {
        "texto": "Impulso",
        "nombre": "Impulso personalizado",
        "expresion": "integral(Fz - masa * gravedad)",
        "unidad": "N·s",
        "ayuda": "Usa Fz.",
    },
)


class ConstructorFormula(QDialog):
    """Arma una expresión mediante piezas clicables y la valida en vivo."""

    # Tamaño ideal; en pantallas chicas se recorta al espacio disponible.
    TAMANO_IDEAL = (1040, 720)
    # Piso de usabilidad: abajo de esto el diálogo deja de ser manejable.
    # El editor y la paleta scrollean, así que tamaños menores siguen siendo
    # funcionales; este piso solo evita ventanas absurdas.
    TAMANO_MINIMO = (760, 420)
    PISO_ABSOLUTO = (320, 240)
    # Margen para el marco y la barra de título que dibuja el sistema sobre
    # el área disponible (availableGeometry ya excluye la barra de tareas).
    MARGEN_DECORACION = 40

    def __init__(
        self,
        parent=None,
        variables_disponibles=None,
        formula_existente=None,
    ):
        super().__init__(parent)
        self.variables_disponibles = list(variables_disponibles or [])
        self.formula_existente = dict(formula_existente or {})
        self.analisis_actual = None
        self.setWindowTitle(
            "Editar fórmula" if self.formula_existente else "Crear fórmula"
        )
        self.setObjectName("constructorFormulaDialog")
        self.setModal(True)
        ancho, alto = self._tamaño_inicial()
        self.resize(ancho, alto)
        minimo_ancho, minimo_alto = self._tamaño_minimo_pantalla()
        self.setMinimumSize(minimo_ancho, minimo_alto)
        self._crear_ui()
        self._cargar_formula()
        self._validar()
        self.input_expresion.setFocus()

    def _pantalla_disponible(self):
        """Área utilizable de la pantalla donde va a aparecer el diálogo."""
        pantalla = self.screen()
        if pantalla is None:
            pantalla = QApplication.primaryScreen()
        if pantalla is None:
            return None
        return pantalla.availableGeometry()

    @classmethod
    def _tamaño_en_area(cls, disponible):
        """Tamaño (ancho, alto) del diálogo para un área disponible dada.

        Usa el ideal cuando entra; si no, lo mayor que siga cabiendo entero.
        """
        if disponible is None:
            return cls.TAMANO_IDEAL
        margen = cls.MARGEN_DECORACION
        ancho_max = max(disponible.width() - margen, cls.PISO_ABSOLUTO[0])
        alto_max = max(disponible.height() - margen, cls.PISO_ABSOLUTO[1])
        return (
            min(cls.TAMANO_IDEAL[0], ancho_max),
            min(cls.TAMANO_IDEAL[1], alto_max),
        )

    def _tamaño_inicial(self):
        return self._tamaño_en_area(self._pantalla_disponible())

    def _tamaño_minimo_pantalla(self):
        """Mínimo razonable, pero nunca más grande que la pantalla.

        Si el mínimo de usabilidad no entra en el área disponible, se baja
        hasta entrar: de nada sirve un mínimo que obligue a Windows a abrir
        la ventana cortada por el borde o por la barra de tareas.
        """
        return self._mínimo_en_area(self._pantalla_disponible())

    @classmethod
    def _mínimo_en_area(cls, disponible):
        if disponible is None:
            return cls.TAMANO_MINIMO
        margen = cls.MARGEN_DECORACION
        ancho_max = max(disponible.width() - margen, cls.PISO_ABSOLUTO[0])
        alto_max = max(disponible.height() - margen, cls.PISO_ABSOLUTO[1])
        return (
            min(cls.TAMANO_MINIMO[0], ancho_max),
            min(cls.TAMANO_MINIMO[1], alto_max),
        )

    def _crear_ui(self):
        principal = QVBoxLayout()
        principal.setContentsMargins(0, 0, 0, 0)
        principal.setSpacing(0)
        principal.addWidget(self._crear_encabezado())

        cuerpo = QWidget()
        cuerpo.setObjectName("cuerpoConstructorFormula")
        cuerpo_layout = QHBoxLayout()
        cuerpo_layout.setContentsMargins(18, 16, 18, 16)
        cuerpo_layout.setSpacing(14)

        columna_editor = QWidget()
        columna_editor.setObjectName("columnaConstructorFormula")
        columna_layout = QVBoxLayout()
        columna_layout.setContentsMargins(0, 0, 0, 0)
        columna_layout.setSpacing(12)
        columna_layout.addWidget(self._crear_editor(), 1)
        columna_layout.addWidget(self._crear_datos_generales())
        columna_editor.setLayout(columna_layout)

        scroll_editor = QScrollArea()
        scroll_editor.setObjectName("scrollEditorFormula")
        scroll_editor.setWidgetResizable(True)
        scroll_editor.setFrameShape(QFrame.NoFrame)
        scroll_editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_editor.viewport().setObjectName("viewportEditorFormula")
        scroll_editor.setWidget(columna_editor)

        cuerpo_layout.addWidget(scroll_editor, 3)
        cuerpo_layout.addWidget(self._crear_paleta(), 2)
        cuerpo.setLayout(cuerpo_layout)
        principal.addWidget(cuerpo, 1)

        pie = QFrame()
        pie.setObjectName("pieConstructorFormula")
        pie_layout = QHBoxLayout()
        pie_layout.setContentsMargins(18, 11, 18, 11)
        pie_layout.setSpacing(12)

        self.lbl_estado_guardado = QLabel("")
        self.lbl_estado_guardado.setObjectName("estadoGuardadoFormula")
        pie_layout.addWidget(self.lbl_estado_guardado, 1)

        self.botones_dialogo = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        self.btn_guardar = self.botones_dialogo.button(QDialogButtonBox.Save)
        self.btn_guardar.setText("Guardar fórmula")
        self.btn_guardar.setObjectName("btnGuardarFormula")
        self.btn_guardar.setDefault(True)
        btn_cancelar = self.botones_dialogo.button(QDialogButtonBox.Cancel)
        btn_cancelar.setText("Cancelar")
        btn_cancelar.setObjectName("btnCancelarFormula")
        self.botones_dialogo.accepted.connect(self._aceptar)
        self.botones_dialogo.rejected.connect(self.reject)
        pie_layout.addWidget(self.botones_dialogo)
        pie.setLayout(pie_layout)
        principal.addWidget(pie)
        self.setLayout(principal)

    def _crear_encabezado(self):
        encabezado = QFrame()
        encabezado.setObjectName("encabezadoConstructorFormula")
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 15, 20, 14)
        layout.setSpacing(14)

        textos = QVBoxLayout()
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(3)
        titulo = QLabel(
            "Editar fórmula"
            if self.formula_existente
            else "Nueva fórmula"
        )
        titulo.setObjectName("tituloConstructorFormula")
        textos.addWidget(titulo)

        layout.addLayout(textos, 1)
        encabezado.setLayout(layout)
        return encabezado

    @staticmethod
    def _tarjeta(titulo, paso=None, descripcion=""):
        marco = QFrame()
        marco.setObjectName("tarjetaConstructorFormula")
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 13, 14, 13)
        layout.setSpacing(8)

        cabecera = QHBoxLayout()
        cabecera.setContentsMargins(0, 0, 0, 0)
        cabecera.setSpacing(8)
        if paso is not None:
            numero = QLabel(str(paso))
            numero.setObjectName("pasoConstructorFormula")
            numero.setAlignment(Qt.AlignCenter)
            cabecera.addWidget(numero)
        etiqueta = QLabel(titulo)
        etiqueta.setObjectName("tituloTarjetaFormula")
        cabecera.addWidget(etiqueta)
        cabecera.addStretch()
        layout.addLayout(cabecera)

        if descripcion:
            ayuda = QLabel(descripcion)
            ayuda.setWordWrap(True)
            ayuda.setObjectName("subtituloConstructorFormula")
            layout.addWidget(ayuda)
        marco.setLayout(layout)
        return marco, layout

    def _crear_datos_generales(self):
        marco, layout = self._tarjeta(
            "Identificá el cálculo",
            2,
        )
        formulario = QGridLayout()
        formulario.setContentsMargins(0, 0, 0, 0)
        formulario.setHorizontalSpacing(12)
        formulario.setVerticalSpacing(5)
        formulario.setColumnStretch(0, 2)
        formulario.setColumnStretch(1, 3)

        lbl_nombre = QLabel("Nombre *")
        lbl_nombre.setObjectName("etiquetaCampoFormula")
        lbl_unidad = QLabel("Unidad")
        lbl_unidad.setObjectName("etiquetaCampoFormula")
        formulario.addWidget(lbl_nombre, 0, 0)
        formulario.addWidget(lbl_unidad, 0, 1)

        self.input_nombre = QLineEdit()
        self.input_nombre.setMaxLength(80)
        self.input_nombre.setPlaceholderText("Ej.: Potencia vertical")
        self.input_nombre.setObjectName("inputFormula")
        self.input_nombre.textChanged.connect(self._validar)

        self.input_unidad = QComboBox()
        self.input_unidad.setEditable(True)
        self.input_unidad.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.input_unidad.setMaxVisibleItems(16)
        self.input_unidad.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.input_unidad.setMinimumContentsLength(8)
        self.input_unidad.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.input_unidad.setObjectName("comboUnidadFormula")
        self.input_unidad.setAccessibleName("Unidad de la fórmula")
        for etiqueta, valor in formulas_logica.UNIDADES_CONSTRUCTOR:
            self.input_unidad.addItem(etiqueta, valor)
        self.input_unidad.setCurrentIndex(-1)
        self.input_unidad.activated.connect(self._usar_unidad_predefinida)
        editor_unidad = self.input_unidad.lineEdit()
        editor_unidad.setMaxLength(24)
        editor_unidad.setPlaceholderText("Elegí una unidad o escribí otra")

        fila_unidad = QWidget()
        fila_unidad.setObjectName("filaUnidadFormula")
        fila_unidad_layout = QHBoxLayout()
        fila_unidad_layout.setContentsMargins(0, 0, 0, 0)
        fila_unidad_layout.setSpacing(4)
        fila_unidad_layout.addWidget(self.input_unidad, 1)
        for simbolo, ayuda in (
            ("·", "Insertar el punto centrado de N·s o N·m"),
            ("²", "Insertar exponente al cuadrado"),
            ("³", "Insertar exponente al cubo"),
            ("µ", "Insertar el símbolo micro"),
        ):
            boton = QToolButton()
            boton.setText(simbolo)
            boton.setObjectName("btnSimboloUnidad")
            boton.setCursor(Qt.PointingHandCursor)
            boton.setToolTip(ayuda)
            boton.clicked.connect(
                lambda _marcado=False, valor=simbolo: self._insertar_simbolo_unidad(
                    valor
                )
            )
            fila_unidad_layout.addWidget(boton)
        fila_unidad.setLayout(fila_unidad_layout)

        formulario.addWidget(self.input_nombre, 1, 0)
        formulario.addWidget(fila_unidad, 1, 1)

        self.input_descripcion = QLineEdit()
        self.input_descripcion.setMaxLength(180)
        self.input_descripcion.setPlaceholderText("Opcional: para qué se usa")
        self.input_descripcion.setObjectName("inputFormula")

        lbl_descripcion = QLabel("Descripción (opcional)")
        lbl_descripcion.setObjectName("etiquetaCampoFormula")
        formulario.addWidget(lbl_descripcion, 2, 0, 1, 2)
        formulario.addWidget(self.input_descripcion, 3, 0, 1, 2)

        self.chk_reutilizable = QCheckBox(
            "Disponible para usar dentro de otras fórmulas"
        )
        self.chk_reutilizable.setObjectName("chkFormulaReutilizable")
        formulario.addWidget(self.chk_reutilizable, 4, 0, 1, 2)
        layout.addLayout(formulario)
        return marco

    def _crear_editor(self):
        marco, layout = self._tarjeta(
            "Construí la expresión",
            1,
        )

        inicio = QHBoxLayout()
        inicio.setContentsMargins(0, 0, 0, 0)
        inicio.setSpacing(6)
        lbl_inicio = QLabel("Inicio rápido")
        lbl_inicio.setObjectName("etiquetaGrupoFormula")
        inicio.addWidget(lbl_inicio)
        for plantilla in PLANTILLAS:
            boton = QPushButton(plantilla["texto"])
            boton.setObjectName("btnPlantillaFormula")
            boton.setCursor(Qt.PointingHandCursor)
            boton.setToolTip(
                f"{plantilla['ayuda']}\n{plantilla['expresion']}"
            )
            boton.clicked.connect(
                lambda _marcado=False, datos=plantilla: self._usar_plantilla(datos)
            )
            inicio.addWidget(boton, 1)
        layout.addLayout(inicio)

        lbl_expresion = QLabel("Expresión")
        lbl_expresion.setObjectName("etiquetaCampoFormula")
        layout.addWidget(lbl_expresion)
        self.input_expresion = QLineEdit()
        self.input_expresion.setObjectName("inputExpresionFormula")
        self.input_expresion.setMaxLength(500)
        self.input_expresion.setPlaceholderText(
            "Ej.: senal / (masa * gravedad)"
        )
        self.input_expresion.setClearButtonEnabled(True)
        self.input_expresion.setAccessibleName("Expresión de la fórmula")
        self.input_expresion.textChanged.connect(self._validar)
        layout.addWidget(self.input_expresion)

        etiqueta_vista = QLabel("Vista previa")
        etiqueta_vista.setObjectName("etiquetaCampoFormula")
        layout.addWidget(etiqueta_vista)

        self.vista_formula = VistaFormulaMatematica()
        layout.addWidget(self.vista_formula)

        self.lbl_validacion = QLabel("")
        self.lbl_validacion.setWordWrap(True)
        self.lbl_validacion.setObjectName("lblValidacionFormula")
        layout.addWidget(self.lbl_validacion)
        return marco

    def _crear_paleta(self):
        marco, layout = self._tarjeta("Añadí piezas")
        marco.setMinimumWidth(350)
        self.tabs_constructor = QTabWidget()
        self.tabs_constructor.setObjectName("tabsConstructorFormula")
        self.tabs_constructor.addTab(
            self._envolver_tab(self._crear_tab_datos()), "Datos"
        )
        self.tabs_constructor.addTab(
            self._envolver_tab(self._crear_tab_operaciones()), "Operaciones"
        )
        self.tabs_constructor.addTab(
            self._envolver_tab(self._crear_tab_calculos()), "Reutilizar"
        )
        layout.addWidget(self.tabs_constructor, 1)
        return marco

    @staticmethod
    def _envolver_tab(contenido):
        scroll = QScrollArea()
        scroll.setObjectName("scrollPaletaFormula")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setObjectName("viewportPaletaFormula")
        scroll.setWidget(contenido)
        return scroll

    def _crear_tab_datos(self):
        contenido = QWidget()
        contenido.setObjectName("contenidoTabFormula")
        layout = QVBoxLayout()
        layout.setContentsMargins(11, 11, 11, 11)
        layout.setSpacing(8)

        titulo_senales = QLabel("Señales")
        titulo_senales.setObjectName("etiquetaGrupoFormula")
        layout.addWidget(titulo_senales)

        rejilla = QGridLayout()
        rejilla.setSpacing(5)
        variables = [
            {
                "token": formulas_logica.VARIABLE_SENAL_INTERVALO,
                "nombre": "Señal del intervalo",
                "detalle": "Señal asociada al intervalo.",
            }
        ]
        vistos = {formulas_logica.VARIABLE_SENAL_INTERVALO}
        for variable in self.variables_disponibles:
            token = str(variable.get("token") or "")
            if token and token not in vistos:
                variables.append(variable)
                vistos.add(token)

        for indice, variable in enumerate(variables):
            token = variable["token"]
            nombre_boton = variable.get("nombre") or token
            if token in formulas_logica.NOMBRES_ROLES:
                nombre_corto = formulas_logica.NOMBRES_ROLES[token]
                nombre_corto = nombre_corto.replace(
                    "Centro de presión", "Centro presión"
                ).replace(" en ", " ")
                nombre_boton = f"{token} · {nombre_corto}"
            boton = self._boton_pieza(
                nombre_boton,
                token,
                variable.get("detalle") or "",
                tipo="senal",
            )
            rejilla.addWidget(boton, indice // 2, indice % 2)
        rejilla.setColumnStretch(0, 1)
        rejilla.setColumnStretch(1, 1)
        layout.addLayout(rejilla)

        titulo_contexto = QLabel("Valores del archivo")
        titulo_contexto.setObjectName("etiquetaGrupoFormula")
        layout.addWidget(titulo_contexto)

        contexto = QGridLayout()
        contexto.setSpacing(5)
        for indice, (texto, token, ayuda) in enumerate((
            ("Masa", "masa", "Masa cargada en el panel izquierdo"),
            ("Estatura", "estatura", "Estatura cargada en metros"),
            ("Gravedad", "gravedad", "Gravedad configurada"),
            ("Frecuencia", "frecuencia", "Frecuencia efectiva en Hz"),
            ("Tiempo", "tiempo", "Segundos desde el inicio del registro"),
            ("π", "pi", "Constante pi"),
            ("e", "e", "Constante de Euler"),
        )):
            contexto.addWidget(
                self._boton_pieza(texto, token, ayuda, tipo="contexto"),
                indice // 2,
                indice % 2,
            )
        contexto.setColumnStretch(0, 1)
        contexto.setColumnStretch(1, 1)
        layout.addLayout(contexto)
        layout.addStretch()
        contenido.setLayout(layout)
        return contenido

    def _crear_tab_calculos(self):
        contenido = QWidget()
        contenido.setObjectName("contenidoTabFormula")
        layout = QVBoxLayout()
        layout.setContentsMargins(11, 11, 11, 11)
        layout.setSpacing(9)

        self.cmb_calculo_reutilizable = QComboBox()
        self.cmb_calculo_reutilizable.setObjectName("comboConstructorFormula")
        self.cmb_calculo_reutilizable.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.cmb_calculo_reutilizable.setMinimumContentsLength(18)
        excluir = self.formula_existente.get("clave")
        for calculo in formulas_logica.calculos_reutilizables(excluir):
            self.cmb_calculo_reutilizable.addItem(calculo["nombre"], calculo)
        self.cmb_calculo_reutilizable.currentIndexChanged.connect(
            self._actualizar_calculo_reutilizable
        )
        layout.addWidget(self.cmb_calculo_reutilizable)

        self.lbl_calculo_reutilizable = QLabel("")
        self.lbl_calculo_reutilizable.setWordWrap(True)
        self.lbl_calculo_reutilizable.setTextFormat(Qt.PlainText)
        self.lbl_calculo_reutilizable.setObjectName("detalleCalculoReutilizable")
        layout.addWidget(self.lbl_calculo_reutilizable)

        self.btn_insertar_calculo = QPushButton("Insertar en la fórmula")
        self.btn_insertar_calculo.setObjectName("btnInsertarCalculoFormula")
        self.btn_insertar_calculo.setCursor(Qt.PointingHandCursor)
        self.btn_insertar_calculo.clicked.connect(
            self._insertar_calculo_reutilizable
        )
        layout.addWidget(self.btn_insertar_calculo)

        nota = QLabel("Se insertará una copia independiente.")
        nota.setWordWrap(True)
        nota.setObjectName("ayudaConstructorFormula")
        layout.addWidget(nota)

        hay_calculos = self.cmb_calculo_reutilizable.count() > 0
        self.cmb_calculo_reutilizable.setEnabled(hay_calculos)
        self.btn_insertar_calculo.setEnabled(hay_calculos)
        self._actualizar_calculo_reutilizable()
        layout.addStretch()
        contenido.setLayout(layout)
        return contenido

    def _crear_tab_operaciones(self):
        contenido = QWidget()
        contenido.setObjectName("contenidoTabFormula")
        layout = QVBoxLayout()
        layout.setContentsMargins(11, 11, 11, 11)
        layout.setSpacing(8)

        titulo_operadores = QLabel("Números y operadores")
        titulo_operadores.setObjectName("etiquetaGrupoFormula")
        layout.addWidget(titulo_operadores)
        rejilla = QGridLayout()
        rejilla.setSpacing(5)
        for columna in range(4):
            rejilla.setColumnStretch(columna, 1)
        piezas = (
            ("7", "7"), ("8", "8"), ("9", "9"), ("÷", " / "),
            ("4", "4"), ("5", "5"), ("6", "6"), ("×", " * "),
            ("1", "1"), ("2", "2"), ("3", "3"), ("−", " - "),
            ("0", "0"), (",", "."), ("+", " + "), ("^", " ** "),
            ("(", "("), (")", ")"),
        )
        for indice, (texto, token) in enumerate(piezas):
            tipo = "numero" if texto.isdigit() or texto == "," else "operador"
            rejilla.addWidget(
                self._boton_pieza(texto, token, tipo=tipo),
                indice // 4,
                indice % 4,
            )

        borrar = QToolButton()
        borrar.setText("⌫")
        borrar.setToolTip("Borrar el carácter anterior")
        borrar.setObjectName("btnPiezaFormula")
        borrar.setProperty("tipo", "control")
        borrar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        borrar.clicked.connect(self.input_expresion.backspace)
        rejilla.addWidget(borrar, 4, 2)

        limpiar = QToolButton()
        limpiar.setText("Limpiar")
        limpiar.setToolTip("Vaciar la fórmula")
        limpiar.setObjectName("btnPiezaFormula")
        limpiar.setProperty("tipo", "control")
        limpiar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        limpiar.clicked.connect(self.input_expresion.clear)
        rejilla.addWidget(limpiar, 4, 3)
        layout.addLayout(rejilla)

        titulo_funciones = QLabel("Funciones")
        titulo_funciones.setObjectName("etiquetaGrupoFormula")
        layout.addWidget(titulo_funciones)
        rejilla_funciones = QGridLayout()
        rejilla_funciones.setSpacing(5)
        for columna in range(3):
            rejilla_funciones.setColumnStretch(columna, 1)
        for indice, (texto, funcion, ayuda) in enumerate(
            formulas_logica.FUNCIONES_CONSTRUCTOR
        ):
            boton = self._boton_pieza(
                texto,
                funcion,
                ayuda,
                es_funcion=True,
                tipo="funcion",
            )
            rejilla_funciones.addWidget(boton, indice // 3, indice % 3)
        layout.addLayout(rejilla_funciones)

        layout.addStretch()
        contenido.setLayout(layout)
        return contenido

    def _actualizar_calculo_reutilizable(self, _indice=None):
        calculo = self.cmb_calculo_reutilizable.currentData()
        if not calculo:
            self.lbl_calculo_reutilizable.setText(
                "No hay cálculos disponibles para insertar."
            )
            return
        salida = (
            "un resultado por intervalo"
            if calculo.get("resultado_escalar")
            else "una curva"
        )
        unidad = calculo.get("unidad") or "sin unidad definida"
        self.lbl_calculo_reutilizable.setText(
            f"{calculo['expresion']}\n\n{salida.capitalize()} · {unidad}"
        )

    def _insertar_calculo_reutilizable(self):
        calculo = self.cmb_calculo_reutilizable.currentData()
        if not calculo:
            return
        self._insertar(f"({calculo['expresion']})")

    def _unidad_actual(self):
        indice = self.input_unidad.currentIndex()
        texto = self.input_unidad.currentText()
        if indice >= 0 and texto == self.input_unidad.itemText(indice):
            texto = self.input_unidad.itemData(indice) or ""
        return formulas_logica.normalizar_unidad_formula(texto)

    def _fijar_unidad(self, unidad):
        unidad = formulas_logica.normalizar_unidad_formula(unidad)
        if not unidad:
            self.input_unidad.setCurrentIndex(-1)
            self.input_unidad.setEditText("")
            return
        indice = self.input_unidad.findData(unidad)
        if indice >= 0:
            self.input_unidad.setCurrentIndex(indice)
            self.input_unidad.setEditText(unidad)
        else:
            self.input_unidad.setEditText(unidad)

    def _usar_unidad_predefinida(self, indice):
        valor = self.input_unidad.itemData(indice) or ""
        self.input_unidad.setEditText(valor)
        self.input_unidad.lineEdit().setFocus()

    def _insertar_simbolo_unidad(self, simbolo):
        unidad = self._unidad_actual()
        self.input_unidad.setEditText(unidad)
        editor = self.input_unidad.lineEdit()
        editor.insert(simbolo)
        editor.setFocus()

    def _boton_pieza(
        self,
        texto,
        token,
        ayuda="",
        es_funcion=False,
        tipo="dato",
    ):
        boton = QToolButton()
        boton.setText(texto)
        boton.setObjectName("btnPiezaFormula")
        boton.setProperty("tipo", tipo)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        if ayuda:
            boton.setToolTip(ayuda)
        if es_funcion:
            boton.clicked.connect(
                lambda _marcado=False, nombre=token: self._insertar_funcion(nombre)
            )
        else:
            boton.clicked.connect(
                lambda _marcado=False, valor=token: self._insertar(valor)
            )
        return boton

    def _insertar(self, texto):
        self.input_expresion.insert(str(texto))
        self.input_expresion.setFocus()

    def _insertar_funcion(self, nombre):
        seleccionado = self.input_expresion.selectedText()
        inicio = self.input_expresion.selectionStart()
        if seleccionado and inicio >= 0:
            texto = self.input_expresion.text()
            nuevo = f"{nombre}({seleccionado})"
            self.input_expresion.setText(
                texto[:inicio] + nuevo + texto[inicio + len(seleccionado):]
            )
            self.input_expresion.setCursorPosition(inicio + len(nuevo))
        else:
            posicion = self.input_expresion.cursorPosition()
            self.input_expresion.insert(f"{nombre}()")
            self.input_expresion.setCursorPosition(posicion + len(nombre) + 1)
        self.input_expresion.setFocus()

    def _usar_plantilla(self, plantilla):
        self.input_expresion.setText(plantilla["expresion"])
        if not self.input_nombre.text().strip():
            self.input_nombre.setText(plantilla["nombre"])
        if not self._unidad_actual():
            self._fijar_unidad(plantilla["unidad"])
        self.input_expresion.setFocus()

    def _cargar_formula(self):
        if not self.formula_existente:
            return
        self.input_nombre.setText(self.formula_existente.get("nombre") or "")
        self._fijar_unidad(self.formula_existente.get("unidad") or "")
        self.input_descripcion.setText(
            self.formula_existente.get("descripcion") or ""
        )
        self.input_expresion.setText(
            self.formula_existente.get("expresion") or ""
        )
        self.chk_reutilizable.setChecked(
            bool(self.formula_existente.get("reutilizable", True))
        )

    @staticmethod
    def _reaplicar_estilo(widget):
        estilo = widget.style()
        estilo.unpolish(widget)
        estilo.polish(widget)
        widget.update()

    def _mostrar_validacion(self, estado, mensaje, mensaje_pie):
        self.lbl_validacion.setProperty("estado", estado)
        self.lbl_validacion.setText(mensaje)
        self._reaplicar_estilo(self.lbl_validacion)
        if hasattr(self, "lbl_estado_guardado"):
            self.lbl_estado_guardado.setProperty("estado", estado)
            self.lbl_estado_guardado.setText(mensaje_pie)
            self._reaplicar_estilo(self.lbl_estado_guardado)

    def _validar(self):
        expresion = self.input_expresion.text()
        self.vista_formula.set_expresion(expresion)
        nombre_valido = bool(self.input_nombre.text().strip())
        if not expresion.strip():
            self.analisis_actual = None
            self._mostrar_validacion(
                "neutral",
                "Ingresá una expresión.",
                "Nombre y expresión obligatorios.",
            )
            if hasattr(self, "btn_guardar"):
                self.btn_guardar.setEnabled(False)
            return
        try:
            self.analisis_actual = formulas_logica.analizar_expresion_personalizada(
                expresion
            )
        except formulas_logica.ErrorFormula as exc:
            self.analisis_actual = None
            self._mostrar_validacion(
                "error",
                f"✕ {exc}",
                "Corregí la expresión.",
            )
        else:
            variables = ", ".join(
                formulas_logica.nombre_variable_constructor(variable)
                for variable in sorted(self.analisis_actual["variables"])
            )
            tipo = (
                "un resultado por intervalo"
                if self.analisis_actual["resultado_escalar"]
                else "una curva con un valor por frame"
            )
            mensaje_pie = (
                "Lista para guardar."
                if nombre_valido
                else "Falta el nombre."
            )
            self._mostrar_validacion(
                "ok",
                f"✓ Fórmula válida · {tipo} · usa {variables}.",
                mensaje_pie,
            )
        if hasattr(self, "btn_guardar"):
            self.btn_guardar.setEnabled(
                nombre_valido and self.analisis_actual is not None
            )

    def _aceptar(self):
        self._validar()
        if self.analisis_actual is not None and self.input_nombre.text().strip():
            self.accept()

    def datos_formula(self):
        return {
            "clave": self.formula_existente.get("clave"),
            "nombre": self.input_nombre.text().strip(),
            "unidad": self._unidad_actual(),
            "descripcion": self.input_descripcion.text().strip(),
            "expresion": self.analisis_actual["texto"],
            "reutilizable": self.chk_reutilizable.isChecked(),
        }
