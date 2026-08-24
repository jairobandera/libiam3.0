import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from logica import formulas as formulas_logica
from logica.config_db import (
    eliminar_formula_personalizada,
    formula_personalizada_a_dict,
    guardar_formula_personalizada,
    listar_formulas_personalizadas,
)

from ui.ventanaPrincipal.panelDerecho.constructorFormula import ConstructorFormula
from ui.ventanaPrincipal.panelDerecho.panelCalculo import PanelCalculo


BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)


class Formulas(QFrame):
    """Selecciona qué intervalos estarán disponibles para los cálculos."""

    eliminarIntervalosSolicitado = Signal(object)
    seleccionIntervalosCambiada = Signal(object)
    aplicarATodasCambiado = Signal(bool)
    notaGuardada = Signal(str, str)
    formulaSolicitada = Signal(object)
    quitarFormulaSolicitado = Signal()
    fuenteCalculoCambiada = Signal(str)
    formulasCambiaron = Signal()

    def __init__(self, db_session=None):
        super().__init__()
        self.db_session = db_session
        self.setObjectName("formulasPanel")
        self.checkboxes = {}
        self.intervalos = []
        self.estados_seleccion = {}
        self.subintervalos_colapsados = set()
        self.modo_seleccion = None
        self.variables_formula = []
        self._cargar_formulas_guardadas()
        self.init_ui()

    def _cargar_formulas_guardadas(self):
        if self.db_session is None:
            return
        formulas_logica.limpiar_formulas_personalizadas()
        for registro in listar_formulas_personalizadas(self.db_session):
            try:
                formulas_logica.registrar_formula_personalizada(
                    formula_personalizada_a_dict(registro)
                )
            except formulas_logica.ErrorFormula:
                # Una fórmula antigua o dañada no debe impedir que abra la app.
                continue

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        titulo = QLabel("Intervalos para cálculos")
        titulo.setObjectName("tituloPanel")
        subtitulo = QLabel("Elegí todos, algunos, pares o impares")
        subtitulo.setObjectName("subtituloPanel")

        seleccion = QFrame()
        seleccion.setObjectName("seccionMapeo")
        seleccion_layout = QVBoxLayout()
        seleccion_layout.setContentsMargins(10, 10, 10, 10)
        seleccion_layout.setSpacing(8)

        ayuda = QLabel(
            "Los intervalos pertenecen a la gráfica donde se marcan. Elegí una "
            "señal y seleccioná los que usarán las operaciones de cálculo."
        )
        ayuda.setWordWrap(True)
        ayuda.setObjectName("lblDeteccion")

        fila_senal = QHBoxLayout()
        fila_senal.addWidget(QLabel("Señal:"))
        self.cmb_senal = QComboBox()
        self.cmb_senal.setMinimumWidth(190)
        fila_senal.addWidget(self.cmb_senal, 1)

        # Cuando está activo, cada recorte se aplica a todas las gráficas visibles.
        self.chk_todas = QCheckBox("Aplicar recorte a todas las gráficas visibles")
        self.chk_todas.setObjectName("chkRecorteTodas")
        self.chk_todas.setChecked(False)
        self.chk_todas.setToolTip(
            "Si está marcado, el próximo recorte se agrega a todas las señales visibles."
        )
        self.chk_todas.toggled.connect(self.aplicarATodasCambiado.emit)

        accesos = QGridLayout()
        self.botones_seleccion = {}
        for indice, (texto, modo) in enumerate(
            (("Todos", "todos"), ("Pares", "pares"), ("Impares", "impares"), ("Ninguno", "ninguno"))
        ):
            boton = QPushButton(texto)
            boton.setObjectName("btnResetMapeo")
            boton.setCursor(Qt.PointingHandCursor)
            boton.clicked.connect(lambda _, valor=modo: self._seleccionar(valor))
            accesos.addWidget(boton, indice // 2, indice % 2)
            self.botones_seleccion[modo] = boton

        self.contenedor = QWidget()
        self.layout_intervalos = QVBoxLayout()
        self.layout_intervalos.setContentsMargins(0, 0, 0, 0)
        self.layout_intervalos.setSpacing(6)
        self.contenedor.setLayout(self.layout_intervalos)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(250)
        self.scroll.setWidget(self.contenedor)

        self.lbl_resumen = QLabel("No hay intervalos marcados.")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setObjectName("lblDeteccion")
        self.lbl_error = QLabel("")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setStyleSheet("color: #EF5350;")

        seleccion_layout.addWidget(ayuda)
        seleccion_layout.addLayout(fila_senal)
        seleccion_layout.addWidget(self.chk_todas)
        seleccion_layout.addLayout(accesos)
        seleccion_layout.addWidget(self.scroll)
        seleccion_layout.addWidget(self.lbl_resumen)
        seleccion_layout.addWidget(self.lbl_error)
        self.panel_calculo = PanelCalculo(
            permitir_gestion=self.db_session is not None
        )
        self.panel_calculo.calcularSolicitado.connect(self._solicitar_formula)
        self.panel_calculo.quitarFormulaSolicitado.connect(
            self.quitarFormulaSolicitado.emit
        )
        self.panel_calculo.fuenteCalculoCambiada.connect(
            self.fuenteCalculoCambiada.emit
        )
        if self.db_session is not None:
            self.panel_calculo.crearFormulaSolicitado.connect(
                self._crear_formula_personalizada
            )
            self.panel_calculo.editarFormulaSolicitado.connect(
                self._editar_formula_personalizada
            )
            self.panel_calculo.eliminarFormulaSolicitado.connect(
                self._eliminar_formula_personalizada
            )
        seleccion_layout.addWidget(self.panel_calculo)
        seleccion.setLayout(seleccion_layout)

        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addWidget(seleccion)
        layout.addStretch()
        self.setLayout(layout)

        self.cmb_senal.currentIndexChanged.connect(self._renderizar_intervalos_actuales)
        self._actualizar_botones()

    def set_hay_filtro(self, hay_filtro):
        """Solo tiene sentido elegir la fuente si alguna señal visible tiene filtro."""
        self.panel_calculo.set_hay_filtro(hay_filtro)

    def cargar_variables_formula(self, variables):
        """Datos que el constructor puede ofrecer como piezas clicables."""
        self.variables_formula = list(variables or [])

    def _crear_formula_personalizada(self):
        self._abrir_constructor_formula()

    def _editar_formula_personalizada(self, clave):
        descripcion = formulas_logica.FORMULAS.get(clave)
        if not descripcion or not descripcion.get("personalizada"):
            return
        existente = dict(descripcion)
        existente["clave"] = clave
        self._abrir_constructor_formula(existente)

    def _abrir_constructor_formula(self, formula_existente=None):
        dialogo = ConstructorFormula(
            self,
            variables_disponibles=self.variables_formula,
            formula_existente=formula_existente,
        )
        if not dialogo.exec():
            return
        self._guardar_formula_personalizada(
            dialogo.datos_formula(),
            es_edicion=bool(formula_existente),
        )

    def _guardar_formula_personalizada(self, datos, es_edicion=False):
        clave_anterior = datos.get("clave")
        if formulas_logica.nombre_formula_en_uso(
            datos.get("nombre"), excluir_clave=clave_anterior
        ):
            QMessageBox.warning(
                self,
                "Guardar fórmula",
                "Ya existe una fórmula con ese nombre. Elegí otro para distinguirla.",
            )
            return
        try:
            registro = guardar_formula_personalizada(
                self.db_session,
                nombre=datos["nombre"],
                expresion=datos["expresion"],
                unidad=datos.get("unidad", ""),
                descripcion=datos.get("descripcion", ""),
                reutilizable=datos.get("reutilizable", False),
                clave=clave_anterior,
            )
            persistida = formula_personalizada_a_dict(registro)
            clave = formulas_logica.registrar_formula_personalizada(persistida)
        except Exception as exc:
            if self.db_session is not None:
                self.db_session.rollback()
            QMessageBox.warning(
                self,
                "Guardar fórmula",
                f"No se pudo guardar la fórmula:\n{exc}",
            )
            return

        self.panel_calculo.recargar_formulas(seleccionar=clave)
        self.formulasCambiaron.emit()
        accion = "actualizada" if es_edicion else "guardada"
        self.panel_calculo.actualizar_estado(
            True,
            f"Fórmula «{persistida['nombre']}» {accion}. Ya está disponible en la lista.",
        )

    def _eliminar_formula_personalizada(self, clave):
        descripcion = formulas_logica.FORMULAS.get(clave)
        if not descripcion or not descripcion.get("personalizada"):
            return
        nombre = descripcion["nombre"]
        if not self._confirmar_eliminacion(
            "Eliminar fórmula",
            f"¿Eliminar la fórmula guardada «{nombre}»?",
        ):
            return
        try:
            eliminada = eliminar_formula_personalizada(self.db_session, clave)
        except Exception as exc:
            self.db_session.rollback()
            QMessageBox.warning(
                self,
                "Eliminar fórmula",
                f"No se pudo eliminar la fórmula:\n{exc}",
            )
            return
        if not eliminada:
            return
        formulas_logica.quitar_formula_personalizada(clave)
        self.panel_calculo.recargar_formulas()
        self.formulasCambiaron.emit()
        self.panel_calculo.actualizar_estado(
            True, f"Se eliminó la fórmula guardada «{nombre}»."
        )

    def _intervalos_padre_seleccionados(self):
        """Solo los intervalos, sin sub-intervalos.

        Desde este panel la fórmula se calcula únicamente sobre los intervalos.
        Los sub-intervalos se calculan en la ventana que se abre al hacer doble
        clic sobre un intervalo, que es donde se los ve en detalle.
        """
        subintervalos = {
            self._id_intervalo(intervalo)
            for intervalo in self.intervalos
            if intervalo.get("es_subintervalo")
        }
        return [
            identificador
            for identificador in self.obtener_intervalos_seleccionados()
            if identificador not in subintervalos
        ]

    def _solicitar_formula(self):
        """Pide el cálculo con los intervalos que estén marcados en ese momento."""
        seleccionados = self._intervalos_padre_seleccionados()
        if not seleccionados:
            self.actualizar_estado_formula(
                False, "Marcá al menos un intervalo para poder calcular."
            )
            return
        clave = self.panel_calculo.formula_seleccionada() or (
            formulas_logica.formula_predeterminada()
        )
        self.formulaSolicitada.emit({"clave": clave, "intervalos": seleccionados})

    def actualizar_estado_formula(self, exito, mensaje):
        """Forward: el componente de cálculo es quien pinta el estado."""
        self.panel_calculo.actualizar_estado(exito, mensaje)

    def limpiar_resultados_formula(self):
        """Deja el recuadro como si nunca se hubiera aplicado una fórmula."""
        self.modo_seleccion = None
        self.panel_calculo.limpiar_resultados()

    def mostrar_resultados_formula(self, datos):
        """Un bloque por intervalo calculado, con sus valores destacados."""
        self.panel_calculo.mostrar_resultados(datos)

    def cargar_intervalos(self, intervalos):
        self._guardar_estados_visibles()
        ids_anteriores = {self._id_intervalo(intervalo) for intervalo in self.intervalos}
        self.intervalos = list(intervalos or [])
        intervalos_nuevos = [
            intervalo
            for intervalo in self.intervalos
            if self._id_intervalo(intervalo) not in ids_anteriores
        ]
        ids_validos = {self._id_intervalo(intervalo) for intervalo in self.intervalos}
        self.estados_seleccion = {
            identificador: self.estados_seleccion.get(identificador, True)
            for identificador in ids_validos
        }

        columna_actual = (
            intervalos_nuevos[-1].get("columna", "__global__")
            if intervalos_nuevos
            else self.cmb_senal.currentData()
        )
        senales = []
        for intervalo in self.intervalos:
            columna = intervalo.get("columna", "__global__")
            if columna not in {item[0] for item in senales}:
                senales.append((columna, intervalo.get("senal", str(columna))))

        self.cmb_senal.blockSignals(True)
        self.cmb_senal.clear()
        for columna, nombre in senales:
            self.cmb_senal.addItem(nombre, columna)
        if columna_actual is not None:
            indice = self.cmb_senal.findData(columna_actual)
            if indice >= 0:
                self.cmb_senal.setCurrentIndex(indice)
        self.cmb_senal.setEnabled(bool(senales))
        self.cmb_senal.blockSignals(False)
        self._renderizar_intervalos_actuales()

    @staticmethod
    def _id_intervalo(intervalo):
        return intervalo.get("id", intervalo.get("numero"))

    def _guardar_estados_visibles(self):
        for identificador, checkbox in self.checkboxes.items():
            self.estados_seleccion[identificador] = checkbox.isChecked()

    def _renderizar_intervalos_actuales(self):
        self._guardar_estados_visibles()
        self.checkboxes = {}
        while self.layout_intervalos.count():
            item = self.layout_intervalos.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        columna_actual = self.cmb_senal.currentData()
        padres_visibles = [
            intervalo
            for intervalo in self.intervalos
            if intervalo.get("columna", "__global__") == columna_actual
            and not intervalo.get("es_subintervalo")
        ]

        if not padres_visibles:
            texto = (
                "Todavía no se seleccionaron intervalos en esta señal."
                if self.intervalos
                else "Todavía no se seleccionaron intervalos."
            )
            vacio = QLabel(texto)
            vacio.setObjectName("lblDeteccion")
            vacio.setAlignment(Qt.AlignCenter)
            self.layout_intervalos.addWidget(vacio)

        for padre in padres_visibles:
            padre_id = self._id_intervalo(padre)
            subintervalos = [r for r in self.intervalos if r.get("padre") == padre_id]
            colapsado = padre_id in self.subintervalos_colapsados

            # Fila del intervalo padre, con toggle si tiene sub-intervalos.
            fila = QWidget()
            fila_layout = QHBoxLayout()
            fila_layout.setContentsMargins(0, 0, 0, 0)
            fila_layout.setSpacing(4)

            if subintervalos:
                btn_toggle = QToolButton()
                btn_toggle.setText("▸" if colapsado else "▾")
                btn_toggle.setObjectName("btnToggleSubintervalos")
                btn_toggle.setCursor(Qt.PointingHandCursor)
                btn_toggle.setToolTip(
                    "Mostrar sub-intervalos" if colapsado else "Ocultar sub-intervalos"
                )
                btn_toggle.clicked.connect(
                    lambda _=False, pid=padre_id: self._toggle_subintervalos(pid)
                )
                fila_layout.addWidget(btn_toggle)
            else:
                espacio = QLabel("")
                espacio.setFixedWidth(18)
                fila_layout.addWidget(espacio)

            fila_layout.addWidget(self._crear_checkbox_intervalo(padre))
            fila_layout.addWidget(self._crear_boton_nota(padre))
            fila_layout.addStretch(1)

            # Botón para eliminar de una todos los sub-intervalos del padre (el
            # intervalo en sí se mantiene).
            if subintervalos:
                btn_del_todos = QToolButton()
                btn_del_todos.setText("↳✕")
                btn_del_todos.setObjectName("btnEliminarTodosSubintervalos")
                btn_del_todos.setCursor(Qt.PointingHandCursor)
                btn_del_todos.setToolTip(
                    "Eliminar todos los sub-intervalos de este intervalo (el intervalo no se elimina)"
                )
                btn_del_todos.clicked.connect(
                    lambda _=False, pid=padre_id: self._eliminar_subintervalos_de(pid)
                )
                fila_layout.addWidget(btn_del_todos)

            # Botón para eliminar el intervalo en sí (arrastra sus sub-intervalos, si tiene).
            btn_del_intervalo = QToolButton()
            btn_del_intervalo.setText("✕")
            btn_del_intervalo.setObjectName("btnEliminarIntervalo")
            btn_del_intervalo.setCursor(Qt.PointingHandCursor)
            tooltip_intervalo = "Eliminar este intervalo"
            if subintervalos:
                plural = "sub-intervalo" if len(subintervalos) == 1 else "sub-intervalos"
                tooltip_intervalo += f" y sus {len(subintervalos)} {plural}"
            btn_del_intervalo.setToolTip(tooltip_intervalo)
            btn_del_intervalo.clicked.connect(
                lambda _=False, pid=padre_id: self._eliminar_intervalo(pid)
            )
            fila_layout.addWidget(btn_del_intervalo)

            fila.setLayout(fila_layout)
            self.layout_intervalos.addWidget(fila)

            # Sub-intervalos indentados (si no está colapsado).
            if subintervalos and not colapsado:
                for sub in subintervalos:
                    sub_id = self._id_intervalo(sub)
                    contenedor = QWidget()
                    cont_layout = QHBoxLayout()
                    cont_layout.setContentsMargins(44, 0, 0, 0)
                    cont_layout.setSpacing(4)
                    cont_layout.addWidget(self._crear_checkbox_intervalo(sub, es_sub=True))
                    cont_layout.addWidget(self._crear_boton_nota(sub))
                    cont_layout.addStretch(1)
                    btn_del_sub = QToolButton()
                    btn_del_sub.setText("✕")
                    btn_del_sub.setObjectName("btnEliminarSubintervalo")
                    btn_del_sub.setCursor(Qt.PointingHandCursor)
                    btn_del_sub.setToolTip("Eliminar este sub-intervalo")
                    btn_del_sub.clicked.connect(
                        lambda _=False, sid=sub_id: self._eliminar_subintervalo(sid)
                    )
                    cont_layout.addWidget(btn_del_sub)
                    contenedor.setLayout(cont_layout)
                    self.layout_intervalos.addWidget(contenedor)

        self.layout_intervalos.addStretch()
        self.lbl_error.clear()
        self._emitir_seleccion()
        self._actualizar_botones()

    LARGO_MAX_ETIQUETA = 24

    def _crear_checkbox_intervalo(self, intervalo, es_sub=False):
        """Crea el checkbox de un intervalo o sub-intervalo y lo registra.

        La etiqueta se acorta con «…» para que la fila entre en el panel angosto
        y el botón de nota y el de eliminar (a la derecha) queden siempre
        visibles. El nombre completo y el origen quedan en el tooltip.
        """
        numero_interno = int(intervalo["numero"])
        numero = int(intervalo.get("orden") or numero_interno)
        identificador = self._id_intervalo(intervalo)
        # Los guardados con el formato anterior traen «Rango N» también en los
        # sub-intervalos; acá se muestran igual como «Sub-intervalo N».
        predeterminado = f"{'Sub-intervalo' if es_sub else 'Intervalo'} {numero}"
        nombre_completo = intervalo.get("nombre") or predeterminado
        if es_sub and nombre_completo == f"Rango {numero_interno}":
            nombre_completo = predeterminado
        medidas = f"{int(intervalo['desde'])} – {int(intervalo['hasta'])}"
        prefijo = "↳ " if es_sub else ""
        sufijo = f": {medidas}"

        disponible = self.LARGO_MAX_ETIQUETA - len(prefijo) - len(sufijo)
        nombre = nombre_completo
        if len(nombre) > disponible:
            nombre = nombre[: max(1, disponible - 1)] + "…"
        texto = f"{prefijo}{nombre}{sufijo}"

        checkbox = QCheckBox(texto)
        # QCheckBox no puede encogerse por debajo de su texto (minimumSizeHint ==
        # sizeHint). Se le fija un ancho máximo para dejarle lugar garantizado a
        # los botones de nota y eliminar dentro del panel angosto.
        ancho_max = 176 if es_sub else 200
        checkbox.setMaximumWidth(ancho_max)
        tooltip = nombre_completo
        if not es_sub and intervalo.get("fuente") == "filtrada":
            tooltip += " · datos filtrados"
        checkbox.setToolTip(tooltip)
        checkbox.setChecked(self.estados_seleccion.get(identificador, True))
        peso = "500" if es_sub else "600"
        checkbox.setStyleSheet(
            f"QCheckBox {{ color: {intervalo['color']}; font-weight: {peso}; }}"
        )
        checkbox.toggled.connect(
            lambda activo, ident=identificador: self._cambiar_estado(ident, activo)
        )
        self.checkboxes[identificador] = checkbox
        return checkbox

    @staticmethod
    def _ruta_icono(nombre):
        return os.path.join(BASE_DIR, "utilidades", "icons", nombre)

    def _crear_boton_nota(self, intervalo):
        """Botón para agregar/editar la nota del intervalo, junto al frame final."""
        identificador = self._id_intervalo(intervalo)
        nota = intervalo.get("nota", "")
        boton = QToolButton()
        boton.setObjectName("btnNotaIntervalo")
        boton.setCursor(Qt.PointingHandCursor)
        boton.setIconSize(QSize(16, 16))
        if nota:
            boton.setIcon(QIcon(self._ruta_icono("nota_editar.svg")))
            boton.setProperty("tienenota", "true")
            preview = nota[:120] + ("…" if len(nota) > 120 else "")
            boton.setToolTip(f"Ver o editar la nota — {preview}")
        else:
            boton.setIcon(QIcon(self._ruta_icono("nota_agregar.svg")))
            boton.setProperty("tienenota", "false")
            boton.setToolTip("Agregar una nota a este intervalo")
        numero = int(intervalo.get("orden") or intervalo["numero"])
        nombre = intervalo.get("nombre") or f"Intervalo {numero}"
        boton.clicked.connect(
            lambda _=False, ident=identificador, nom=nombre, nt=nota: self._abrir_nota(
                ident, nom, nt
            )
        )
        return boton

    def _abrir_nota(self, identificador, nombre, nota_actual):
        """Abre el editor de nota y emite el resultado si se guarda."""
        from ui.ventanaPrincipal.panelDerecho.notaIntervalo import NotaDialog

        dialogo = NotaDialog(self.window(), nombre=nombre, nota=nota_actual)
        if dialogo.exec():
            self.notaGuardada.emit(identificador, dialogo.texto())

    def _toggle_subintervalos(self, padre_id):
        """Oculta o muestra los sub-intervalos de un intervalo padre."""
        if padre_id in self.subintervalos_colapsados:
            self.subintervalos_colapsados.discard(padre_id)
        else:
            self.subintervalos_colapsados.add(padre_id)
        self._renderizar_intervalos_actuales()

    def _nombre_intervalo(self, intervalo):
        numero_interno = int(intervalo["numero"])
        numero = int(intervalo.get("orden") or numero_interno)
        predeterminado = f"{'Sub-intervalo' if intervalo.get('es_subintervalo') else 'Intervalo'} {numero}"
        nombre = intervalo.get("nombre") or predeterminado
        if intervalo.get("es_subintervalo") and nombre == f"Intervalo {numero_interno}":
            nombre = predeterminado
        return nombre

    def _confirmar_eliminacion(self, titulo, mensaje):
        """Cartel de advertencia antes de cualquier borrado de intervalos."""
        respuesta = QMessageBox.question(
            self,
            titulo,
            mensaje,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return respuesta == QMessageBox.Yes

    def _eliminar_intervalo(self, padre_id):
        """Elimina un intervalo puntual (y sus sub-intervalos, si tiene)."""
        intervalo = next(
            (r for r in self.intervalos if self._id_intervalo(r) == padre_id and not r.get("es_subintervalo")),
            None,
        )
        if intervalo is None:
            return
        subintervalos = [r for r in self.intervalos if r.get("padre") == padre_id]
        mensaje = f"¿Eliminar el intervalo «{self._nombre_intervalo(intervalo)}»?"
        if subintervalos:
            plural = "sub-intervalo" if len(subintervalos) == 1 else "sub-intervalos"
            mensaje += f"\n\nTambién se eliminarán sus {len(subintervalos)} {plural}."
        if not self._confirmar_eliminacion("Eliminar intervalo", mensaje):
            return
        self.eliminarIntervalosSolicitado.emit([padre_id])

    def _eliminar_subintervalo(self, sub_id):
        """Elimina un único sub-intervalo."""
        intervalo = next((r for r in self.intervalos if self._id_intervalo(r) == sub_id), None)
        nombre = self._nombre_intervalo(intervalo) if intervalo else "este sub-intervalo"
        mensaje = f"¿Eliminar el sub-intervalo «{nombre}»?"
        if not self._confirmar_eliminacion("Eliminar sub-intervalo", mensaje):
            return
        self.eliminarIntervalosSolicitado.emit([sub_id])

    def _eliminar_subintervalos_de(self, padre_id):
        """Elimina de una todos los sub-intervalos de un intervalo padre."""
        ids = [
            self._id_intervalo(intervalo)
            for intervalo in self.intervalos
            if intervalo.get("padre") == padre_id
        ]
        if not ids:
            return
        padre = next((r for r in self.intervalos if self._id_intervalo(r) == padre_id), None)
        nombre_padre = self._nombre_intervalo(padre) if padre else "este intervalo"
        plural = "sub-intervalo" if len(ids) == 1 else "sub-intervalos"
        mensaje = f"¿Eliminar los {len(ids)} {plural} de «{nombre_padre}»?"
        if not self._confirmar_eliminacion("Eliminar sub-intervalos", mensaje):
            return
        self.eliminarIntervalosSolicitado.emit(ids)

    def _marcar_modo_seleccion(self, modo):
        """Resalta el botón activo. El borde lo pone el QSS por la propiedad."""
        self.modo_seleccion = modo
        for clave, boton in self.botones_seleccion.items():
            boton.setProperty("activo", "true" if clave == modo else "false")
            boton.style().unpolish(boton)
            boton.style().polish(boton)

    def _seleccionar(self, modo):
        self._marcar_modo_seleccion(modo)
        for identificador, checkbox in self.checkboxes.items():
            numero = next(
                int(intervalo.get("orden") or intervalo["numero"])
                for intervalo in self.intervalos
                if self._id_intervalo(intervalo) == identificador
            )
            if modo == "todos":
                activo = True
            elif modo == "pares":
                activo = numero % 2 == 0
            elif modo == "impares":
                activo = numero % 2 == 1
            else:
                activo = False
            checkbox.blockSignals(True)
            checkbox.setChecked(activo)
            checkbox.blockSignals(False)
            self.estados_seleccion[identificador] = activo
        self._emitir_seleccion()

    def obtener_intervalos_seleccionados(self):
        return [
            identificador
            for identificador, activo in self.estados_seleccion.items()
            if activo
        ]

    def _obtener_visibles_seleccionados(self):
        return [
            identificador
            for identificador, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

    def _cambiar_estado(self, identificador, activo):
        self.estados_seleccion[identificador] = activo
        self._emitir_seleccion()

    def _emitir_seleccion(self):
        seleccionados = self.obtener_intervalos_seleccionados()
        seleccionados_visibles = self._obtener_visibles_seleccionados()
        total = len(self.checkboxes)
        self.lbl_resumen.setText(
            f"{len(seleccionados_visibles)} de {total} intervalo(s) seleccionados en esta señal."
            if total
            else "No hay intervalos marcados."
        )
        self.seleccionIntervalosCambiada.emit(seleccionados)
        self._actualizar_botones()

    def _actualizar_botones(self):
        # El cálculo corre sobre intervalos (no sub-intervalos): sin ninguno marcado
        # no hay nada que calcular, así que el botón queda gris con la razón en
        # el tooltip. El texto es genérico: vale para cualquier fórmula.
        hay_seleccion = bool(self._intervalos_padre_seleccionados())
        self.panel_calculo.set_aplicar_habilitado(
            hay_seleccion,
            "Calcula la fórmula seleccionada en los intervalos marcados. Los "
            "sub-intervalos se calculan al abrirlos con doble clic."
            if hay_seleccion
            else "Marcá al menos un intervalo para poder calcular.",
        )

    def mostrar_error_intervalo(self, mensaje):
        self.lbl_error.setStyleSheet("color: #EF5350;")
        self.lbl_error.setText(mensaje)

    def mostrar_aviso_intervalo(self, mensaje):
        self.lbl_error.setStyleSheet("color: #66BB6A;")
        self.lbl_error.setText(mensaje)
