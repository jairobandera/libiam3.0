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
from logica import paleta


BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)


class Formulas(QFrame):
    """Selecciona qué rangos estarán disponibles para los cálculos."""

    eliminarRangosSolicitado = Signal(object)
    limpiarRangosSolicitado = Signal()
    seleccionRangosCambiada = Signal(object)
    aplicarATodasCambiado = Signal(bool)
    notaGuardada = Signal(str, str)
    formulaSolicitada = Signal(object)
    quitarFormulaSolicitado = Signal()
    fuenteCalculoCambiada = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("formulasPanel")
        self.checkboxes = {}
        self.rangos = []
        self.estados_seleccion = {}
        self.subrangos_colapsados = set()
        self.ultimos_resultados = None
        self.modo_seleccion = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        titulo = QLabel("Rangos para cálculos")
        titulo.setObjectName("tituloPanel")
        subtitulo = QLabel("Elegí todos, algunos, pares o impares")
        subtitulo.setObjectName("subtituloPanel")

        seleccion = QFrame()
        seleccion.setObjectName("seccionMapeo")
        seleccion_layout = QVBoxLayout()
        seleccion_layout.setContentsMargins(10, 10, 10, 10)
        seleccion_layout.setSpacing(8)

        ayuda = QLabel(
            "Los rangos pertenecen a la gráfica donde se marcan. Elegí una "
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
        self.layout_rangos = QVBoxLayout()
        self.layout_rangos.setContentsMargins(0, 0, 0, 0)
        self.layout_rangos.setSpacing(6)
        self.contenedor.setLayout(self.layout_rangos)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(250)
        self.scroll.setWidget(self.contenedor)

        self.lbl_resumen = QLabel("No hay rangos marcados.")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setObjectName("lblDeteccion")
        self.lbl_error = QLabel("")
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setStyleSheet("color: #EF5350;")

        botones = QHBoxLayout()
        self.btn_eliminar = QPushButton("Eliminar de esta señal")
        self.btn_eliminar.setObjectName("btnResetMapeo")
        self.btn_limpiar = QPushButton("Eliminar todos")
        self.btn_limpiar.setObjectName("btnResetMapeo")
        self.btn_limpiar.setToolTip("Elimina los rangos de todas las señales")
        botones.addWidget(self.btn_eliminar)
        botones.addWidget(self.btn_limpiar)

        seleccion_layout.addWidget(ayuda)
        seleccion_layout.addLayout(fila_senal)
        seleccion_layout.addWidget(self.chk_todas)
        seleccion_layout.addLayout(accesos)
        seleccion_layout.addWidget(self.scroll)
        seleccion_layout.addWidget(self.lbl_resumen)
        seleccion_layout.addWidget(self.lbl_error)
        seleccion_layout.addWidget(self._crear_seccion_formulas())
        seleccion_layout.addLayout(botones)
        seleccion.setLayout(seleccion_layout)

        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addWidget(seleccion)
        layout.addStretch()
        self.setLayout(layout)

        self.btn_eliminar.clicked.connect(self._eliminar_seleccionados)
        self.btn_limpiar.clicked.connect(self._eliminar_todos)
        self.cmb_senal.currentIndexChanged.connect(self._renderizar_rangos_actuales)
        self._actualizar_botones()

    def _crear_seccion_formulas(self):
        """Recuadro de Potencia: se calcula sobre los rangos marcados."""
        seccion = QFrame()
        seccion.setObjectName("seccionFormulas")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        titulo = QLabel("Potencia")
        titulo.setObjectName("tituloSeccionMapeo")
        layout.addWidget(titulo)

        self.lbl_expresion = QLabel(
            f"<b>{formulas_logica.EXPRESION_POTENCIA}</b><br>"
            "Se calcula sobre la fuerza vertical (Fz), dentro de cada rango "
            "marcado y arrancando del reposo. La curva se dibuja solo sobre Fz."
        )
        self.lbl_expresion.setWordWrap(True)
        self.lbl_expresion.setObjectName("lblExpresionFormula")
        layout.addWidget(self.lbl_expresion)

        ayuda = QLabel(
            "Marcá los rangos con los botones de arriba y pasá el mouse por la "
            "curva para ver los valores."
        )
        ayuda.setWordWrap(True)
        ayuda.setObjectName("lblDeteccion")
        layout.addWidget(ayuda)

        # Elegir sobre qué serie se calcula. No se exige filtro para calcular:
        # un pasa-bajos achata los picos, así que forzarlo sesgaría los valores.
        fila_fuente = QHBoxLayout()
        fila_fuente.setSpacing(6)
        lbl_fuente = QLabel("Calcular sobre:")
        lbl_fuente.setObjectName("lblExpresionFormula")
        self.cmb_fuente = QComboBox()
        self.cmb_fuente.setObjectName("comboFormula")
        self.cmb_fuente.addItem("Señal filtrada", "filtrada")
        self.cmb_fuente.addItem("Señal original", "original")
        self.cmb_fuente.currentIndexChanged.connect(
            lambda _i: self.fuenteCalculoCambiada.emit(self.cmb_fuente.currentData())
        )
        fila_fuente.addWidget(lbl_fuente)
        fila_fuente.addWidget(self.cmb_fuente, 1)
        layout.addLayout(fila_fuente)
        self.set_hay_filtro(False)

        fila = QHBoxLayout()
        self.btn_aplicar_formula = QPushButton("Aplicar")
        self.btn_aplicar_formula.setObjectName("btnAplicarMapeo")
        self.btn_aplicar_formula.setCursor(Qt.PointingHandCursor)
        self.btn_aplicar_formula.clicked.connect(self._solicitar_potencia)
        self.btn_quitar_formula = QPushButton("Quitar")
        self.btn_quitar_formula.setObjectName("btnResetMapeo")
        self.btn_quitar_formula.setCursor(Qt.PointingHandCursor)
        self.btn_quitar_formula.setEnabled(False)
        self.btn_quitar_formula.clicked.connect(self.quitarFormulaSolicitado.emit)
        fila.addWidget(self.btn_aplicar_formula)
        fila.addWidget(self.btn_quitar_formula)
        layout.addLayout(fila)

        self.lbl_estado_formula = QLabel("")
        self.lbl_estado_formula.setWordWrap(True)
        self.lbl_estado_formula.setObjectName("lblEstadoFormula")
        layout.addWidget(self.lbl_estado_formula)

        self.lbl_resultados = QLabel("")
        self.lbl_resultados.setWordWrap(True)
        self.lbl_resultados.setObjectName("lblResultadosFormula")
        self.lbl_resultados.hide()
        layout.addWidget(self.lbl_resultados)

        seccion.setLayout(layout)
        return seccion

    def set_hay_filtro(self, hay_filtro):
        """Solo tiene sentido elegir la fuente si alguna señal visible tiene filtro."""
        self.cmb_fuente.setEnabled(bool(hay_filtro))
        if hay_filtro:
            self.cmb_fuente.setToolTip(
                "Sobre qué serie se calcula. Ojo: el filtro achata los picos, "
                "así que el pico sobre la señal original suele ser mayor."
            )
        else:
            self.cmb_fuente.setToolTip(
                "No hay ninguna señal visible con filtro: se calcula sobre la "
                "señal original."
            )

    def _rangos_padre_seleccionados(self):
        """Solo los rangos, sin sub-rangos.

        Desde este panel la potencia se calcula únicamente sobre los rangos.
        Los sub-rangos se calculan en la ventana que se abre al hacer doble
        clic sobre un rango, que es donde se los ve en detalle.
        """
        subrangos = {
            self._id_rango(rango)
            for rango in self.rangos
            if rango.get("es_subrango")
        }
        return [
            identificador
            for identificador in self.obtener_rangos_seleccionados()
            if identificador not in subrangos
        ]

    def _solicitar_potencia(self):
        """Pide el cálculo con los rangos que estén marcados en ese momento."""
        seleccionados = self._rangos_padre_seleccionados()
        if not seleccionados:
            self.actualizar_estado_formula(
                False, "Marcá al menos un rango para calcular la potencia."
            )
            return
        self.formulaSolicitada.emit({"rangos": seleccionados})

    def actualizar_estado_formula(self, exito, mensaje):
        color = "#66BB6A" if exito else "#EF5350"
        if paleta.modo_daltonico_activo():
            color = "#56B4E9" if exito else "#D55E00"
        simbolo = "✓" if exito else "✕"
        self.lbl_estado_formula.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.lbl_estado_formula.setText(f"{simbolo} {mensaje}" if mensaje else "")

    def limpiar_resultados_formula(self):
        """Deja el recuadro como si nunca se hubiera aplicado una fórmula."""
        self.ultimos_resultados = None
        self.modo_seleccion = None
        self.lbl_resultados.setText("")
        self.lbl_resultados.hide()
        self.lbl_estado_formula.setText("")
        self.btn_quitar_formula.setEnabled(False)

    def mostrar_resultados_formula(self, datos):
        """Un bloque por rango calculado, con sus valores destacados."""
        if not datos or not datos.get("resultados"):
            self.limpiar_resultados_formula()
            return
        self.ultimos_resultados = datos

        resultados = datos["resultados"]
        unidad = datos.get("unidad") or ""
        sufijo = f" {unidad}" if unidad else ""

        encabezado = [(f"<b>{datos.get('nombre', 'Potencia')}</b>", "")]
        senal = datos.get("senal")
        procedencia = self._texto_procedencia(datos)
        if senal:
            procedencia = f"sobre {senal} · {procedencia.removeprefix('sobre ')}"
        encabezado.append((procedencia, "color:#8A8A8A;"))
        partes = [self._divs_con_separacion(encabezado)]

        for resultado in resultados:
            partes.append(self._bloque_valores(resultado, sufijo))

        self.lbl_resultados.setText("".join(partes))
        self.lbl_resultados.show()
        self.btn_quitar_formula.setEnabled(True)

    ETIQUETAS_FUENTE = {
        "filtrada": "señal filtrada",
        "original": "señal original",
        "mixta": "señales mixtas",
    }

    @classmethod
    def _texto_procedencia(cls, datos):
        fuente = datos.get("fuente") or "original"
        etiqueta = cls.ETIQUETAS_FUENTE.get(fuente, "señal original")
        detalle = datos.get("detalle_filtro") or ""
        return f"sobre {etiqueta} · {detalle}" if detalle else f"sobre {etiqueta}"

    # Separación entre entradas, ≈ una línea en blanco.
    SEPARACION_ENTRADAS = 12

    def _bloque_valores(self, resultado, sufijo):
        """Un rango como bloque con salto de línea, no como renglón corrido."""
        resumen = resultado.get("resumen") or {}
        pico = resumen.get("pico")

        tramo = f"frames {resultado['desde']}–{resultado['hasta']}"
        duracion = resultado.get("duracion_s")
        if duracion:
            tramo += f" · {duracion:.3g} s"
        lineas = [
            (f"<b>{resultado['nombre']}</b>", "color:#E0E0E0;"),
            (tramo, "color:#8A8A8A; font-size:10px;"),
        ]

        if pico is None:
            lineas.append(("sin datos válidos", "color:#8A8A8A;"))
        else:
            valor_pico = formulas_logica.formatear_valor(pico)
            valor_media = formulas_logica.formatear_valor(resumen.get("media"))
            lineas.append(
                (
                    f"pico <b>{valor_pico}{sufijo}</b> "
                    f'<span style="color:#8A8A8A;">(frame {resumen["x_pico"]:g})</span>',
                    "",
                )
            )
            lineas.append((f"media <b>{valor_media}{sufijo}</b>", ""))

        return self._divs_con_separacion(lineas)

    @classmethod
    def _divs_con_separacion(cls, lineas):
        """Arma los <div> y separa del bloque siguiente.

        El margen va en el **último div hoja**, no en un contenedor: Qt ignora
        ``margin-bottom`` en un div que solo contiene otros divs, así que un
        wrapper no separa nada (comprobado midiendo ``heightForWidth``).
        """
        partes = []
        for indice, (contenido, estilo) in enumerate(lineas):
            if indice == len(lineas) - 1:
                estilo = f"{estilo} margin-bottom:{cls.SEPARACION_ENTRADAS}px;".strip()
            atributo = f' style="{estilo}"' if estilo else ""
            partes.append(f"<div{atributo}>{contenido}</div>")
        return "".join(partes)

    def cargar_rangos(self, rangos):
        self._guardar_estados_visibles()
        ids_anteriores = {self._id_rango(rango) for rango in self.rangos}
        self.rangos = list(rangos or [])
        rangos_nuevos = [
            rango
            for rango in self.rangos
            if self._id_rango(rango) not in ids_anteriores
        ]
        ids_validos = {self._id_rango(rango) for rango in self.rangos}
        self.estados_seleccion = {
            identificador: self.estados_seleccion.get(identificador, True)
            for identificador in ids_validos
        }

        columna_actual = (
            rangos_nuevos[-1].get("columna", "__global__")
            if rangos_nuevos
            else self.cmb_senal.currentData()
        )
        senales = []
        for rango in self.rangos:
            columna = rango.get("columna", "__global__")
            if columna not in {item[0] for item in senales}:
                senales.append((columna, rango.get("senal", str(columna))))

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
        self._renderizar_rangos_actuales()

    @staticmethod
    def _id_rango(rango):
        return rango.get("id", rango.get("numero"))

    def _guardar_estados_visibles(self):
        for identificador, checkbox in self.checkboxes.items():
            self.estados_seleccion[identificador] = checkbox.isChecked()

    def _renderizar_rangos_actuales(self):
        self._guardar_estados_visibles()
        self.checkboxes = {}
        while self.layout_rangos.count():
            item = self.layout_rangos.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        columna_actual = self.cmb_senal.currentData()
        padres_visibles = [
            rango
            for rango in self.rangos
            if rango.get("columna", "__global__") == columna_actual
            and not rango.get("es_subrango")
        ]

        if not padres_visibles:
            texto = (
                "Todavía no se seleccionaron rangos en esta señal."
                if self.rangos
                else "Todavía no se seleccionaron rangos."
            )
            vacio = QLabel(texto)
            vacio.setObjectName("lblDeteccion")
            vacio.setAlignment(Qt.AlignCenter)
            self.layout_rangos.addWidget(vacio)

        for padre in padres_visibles:
            padre_id = self._id_rango(padre)
            subrangos = [r for r in self.rangos if r.get("padre") == padre_id]
            colapsado = padre_id in self.subrangos_colapsados

            # Fila del rango padre, con toggle si tiene sub-rangos.
            fila = QWidget()
            fila_layout = QHBoxLayout()
            fila_layout.setContentsMargins(0, 0, 0, 0)
            fila_layout.setSpacing(4)

            if subrangos:
                btn_toggle = QToolButton()
                btn_toggle.setText("▸" if colapsado else "▾")
                btn_toggle.setObjectName("btnToggleSubrangos")
                btn_toggle.setCursor(Qt.PointingHandCursor)
                btn_toggle.setToolTip(
                    "Mostrar sub-rangos" if colapsado else "Ocultar sub-rangos"
                )
                btn_toggle.clicked.connect(
                    lambda _=False, pid=padre_id: self._toggle_subrangos(pid)
                )
                fila_layout.addWidget(btn_toggle)
            else:
                espacio = QLabel("")
                espacio.setFixedWidth(18)
                fila_layout.addWidget(espacio)

            fila_layout.addWidget(self._crear_checkbox_rango(padre))
            fila_layout.addWidget(self._crear_boton_nota(padre))
            fila_layout.addStretch(1)

            # Botón para eliminar de una todos los sub-rangos del padre (el
            # rango en sí se mantiene).
            if subrangos:
                btn_del_todos = QToolButton()
                btn_del_todos.setText("↳✕")
                btn_del_todos.setObjectName("btnEliminarTodosSubrangos")
                btn_del_todos.setCursor(Qt.PointingHandCursor)
                btn_del_todos.setToolTip(
                    "Eliminar todos los sub-rangos de este rango (el rango no se elimina)"
                )
                btn_del_todos.clicked.connect(
                    lambda _=False, pid=padre_id: self._eliminar_subrangos_de(pid)
                )
                fila_layout.addWidget(btn_del_todos)

            # Botón para eliminar el rango en sí (arrastra sus sub-rangos, si tiene).
            btn_del_rango = QToolButton()
            btn_del_rango.setText("✕")
            btn_del_rango.setObjectName("btnEliminarRango")
            btn_del_rango.setCursor(Qt.PointingHandCursor)
            tooltip_rango = "Eliminar este rango"
            if subrangos:
                plural = "sub-rango" if len(subrangos) == 1 else "sub-rangos"
                tooltip_rango += f" y sus {len(subrangos)} {plural}"
            btn_del_rango.setToolTip(tooltip_rango)
            btn_del_rango.clicked.connect(
                lambda _=False, pid=padre_id: self._eliminar_rango(pid)
            )
            fila_layout.addWidget(btn_del_rango)

            fila.setLayout(fila_layout)
            self.layout_rangos.addWidget(fila)

            # Sub-rangos indentados (si no está colapsado).
            if subrangos and not colapsado:
                for sub in subrangos:
                    sub_id = self._id_rango(sub)
                    contenedor = QWidget()
                    cont_layout = QHBoxLayout()
                    cont_layout.setContentsMargins(44, 0, 0, 0)
                    cont_layout.setSpacing(4)
                    cont_layout.addWidget(self._crear_checkbox_rango(sub, es_sub=True))
                    cont_layout.addWidget(self._crear_boton_nota(sub))
                    cont_layout.addStretch(1)
                    btn_del_sub = QToolButton()
                    btn_del_sub.setText("✕")
                    btn_del_sub.setObjectName("btnEliminarSubrango")
                    btn_del_sub.setCursor(Qt.PointingHandCursor)
                    btn_del_sub.setToolTip("Eliminar este sub-rango")
                    btn_del_sub.clicked.connect(
                        lambda _=False, sid=sub_id: self._eliminar_subrango(sid)
                    )
                    cont_layout.addWidget(btn_del_sub)
                    contenedor.setLayout(cont_layout)
                    self.layout_rangos.addWidget(contenedor)

        self.layout_rangos.addStretch()
        self.lbl_error.clear()
        self._emitir_seleccion()
        self._actualizar_botones()

    LARGO_MAX_ETIQUETA = 24

    def _crear_checkbox_rango(self, rango, es_sub=False):
        """Crea el checkbox de un rango o sub-rango y lo registra.

        La etiqueta se acorta con «…» para que la fila entre en el panel angosto
        y el botón de nota y el de eliminar (a la derecha) queden siempre
        visibles. El nombre completo y el origen quedan en el tooltip.
        """
        numero = int(rango["numero"])
        identificador = self._id_rango(rango)
        # Los guardados con el formato anterior traen «Rango N» también en los
        # sub-rangos; acá se muestran igual como «Sub-rango N».
        predeterminado = f"{'Sub-rango' if es_sub else 'Rango'} {numero}"
        nombre_completo = rango.get("nombre") or predeterminado
        if es_sub and nombre_completo == f"Rango {numero}":
            nombre_completo = predeterminado
        medidas = f"{int(rango['desde'])} – {int(rango['hasta'])}"
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
        if not es_sub and rango.get("fuente") == "filtrada":
            tooltip += " · datos filtrados"
        checkbox.setToolTip(tooltip)
        checkbox.setChecked(self.estados_seleccion.get(identificador, True))
        peso = "500" if es_sub else "600"
        checkbox.setStyleSheet(
            f"QCheckBox {{ color: {rango['color']}; font-weight: {peso}; }}"
        )
        checkbox.toggled.connect(
            lambda activo, ident=identificador: self._cambiar_estado(ident, activo)
        )
        self.checkboxes[identificador] = checkbox
        return checkbox

    @staticmethod
    def _ruta_icono(nombre):
        return os.path.join(BASE_DIR, "utilidades", "icons", nombre)

    def _crear_boton_nota(self, rango):
        """Botón para agregar/editar la nota del rango, junto al frame final."""
        identificador = self._id_rango(rango)
        nota = rango.get("nota", "")
        boton = QToolButton()
        boton.setObjectName("btnNotaRango")
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
            boton.setToolTip("Agregar una nota a este rango")
        nombre = rango.get("nombre") or f"Rango {int(rango['numero'])}"
        boton.clicked.connect(
            lambda _=False, ident=identificador, nom=nombre, nt=nota: self._abrir_nota(
                ident, nom, nt
            )
        )
        return boton

    def _abrir_nota(self, identificador, nombre, nota_actual):
        """Abre el editor de nota y emite el resultado si se guarda."""
        from ui.ventanaPrincipal.panelDerecho.notaRango import NotaDialog

        dialogo = NotaDialog(self.window(), nombre=nombre, nota=nota_actual)
        if dialogo.exec():
            self.notaGuardada.emit(identificador, dialogo.texto())

    def _toggle_subrangos(self, padre_id):
        """Oculta o muestra los sub-rangos de un rango padre."""
        if padre_id in self.subrangos_colapsados:
            self.subrangos_colapsados.discard(padre_id)
        else:
            self.subrangos_colapsados.add(padre_id)
        self._renderizar_rangos_actuales()

    def _nombre_rango(self, rango):
        numero = int(rango["numero"])
        predeterminado = f"{'Sub-rango' if rango.get('es_subrango') else 'Rango'} {numero}"
        nombre = rango.get("nombre") or predeterminado
        if rango.get("es_subrango") and nombre == f"Rango {numero}":
            nombre = predeterminado
        return nombre

    def _confirmar_eliminacion(self, titulo, mensaje):
        """Cartel de advertencia antes de cualquier borrado de rangos."""
        respuesta = QMessageBox.question(
            self,
            titulo,
            mensaje,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return respuesta == QMessageBox.Yes

    def _eliminar_rango(self, padre_id):
        """Elimina un rango puntual (y sus sub-rangos, si tiene)."""
        rango = next(
            (r for r in self.rangos if self._id_rango(r) == padre_id and not r.get("es_subrango")),
            None,
        )
        if rango is None:
            return
        subrangos = [r for r in self.rangos if r.get("padre") == padre_id]
        mensaje = f"¿Eliminar el rango «{self._nombre_rango(rango)}»?"
        if subrangos:
            plural = "sub-rango" if len(subrangos) == 1 else "sub-rangos"
            mensaje += f"\n\nTambién se eliminarán sus {len(subrangos)} {plural}."
        if not self._confirmar_eliminacion("Eliminar rango", mensaje):
            return
        self.eliminarRangosSolicitado.emit([padre_id])

    def _eliminar_subrango(self, sub_id):
        """Elimina un único sub-rango."""
        rango = next((r for r in self.rangos if self._id_rango(r) == sub_id), None)
        nombre = self._nombre_rango(rango) if rango else "este sub-rango"
        mensaje = f"¿Eliminar el sub-rango «{nombre}»?"
        if not self._confirmar_eliminacion("Eliminar sub-rango", mensaje):
            return
        self.eliminarRangosSolicitado.emit([sub_id])

    def _eliminar_subrangos_de(self, padre_id):
        """Elimina de una todos los sub-rangos de un rango padre."""
        ids = [
            self._id_rango(rango)
            for rango in self.rangos
            if rango.get("padre") == padre_id
        ]
        if not ids:
            return
        padre = next((r for r in self.rangos if self._id_rango(r) == padre_id), None)
        nombre_padre = self._nombre_rango(padre) if padre else "este rango"
        plural = "sub-rango" if len(ids) == 1 else "sub-rangos"
        mensaje = f"¿Eliminar los {len(ids)} {plural} de «{nombre_padre}»?"
        if not self._confirmar_eliminacion("Eliminar sub-rangos", mensaje):
            return
        self.eliminarRangosSolicitado.emit(ids)

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
                int(rango["numero"])
                for rango in self.rangos
                if self._id_rango(rango) == identificador
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

    def obtener_rangos_seleccionados(self):
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
        seleccionados = self.obtener_rangos_seleccionados()
        seleccionados_visibles = self._obtener_visibles_seleccionados()
        total = len(self.checkboxes)
        self.lbl_resumen.setText(
            f"{len(seleccionados_visibles)} de {total} rango(s) seleccionados en esta señal."
            if total
            else "No hay rangos marcados."
        )
        self.seleccionRangosCambiada.emit(seleccionados)
        self._actualizar_botones()

    def _eliminar_seleccionados(self):
        seleccionados = self._obtener_visibles_seleccionados()
        if not seleccionados:
            return
        mensaje = (
            f"¿Eliminar los {len(seleccionados)} rango(s)/sub-rango(s) marcados "
            "en esta señal? Los sub-rangos de cualquier rango marcado se pierden también."
        )
        if not self._confirmar_eliminacion("Eliminar rangos", mensaje):
            return
        self.eliminarRangosSolicitado.emit(seleccionados)

    def _eliminar_todos(self):
        if not self.rangos:
            return
        mensaje = (
            "¿Eliminar todos los rangos y sub-rangos de todas las señales? "
            "Esta acción no se puede deshacer."
        )
        if not self._confirmar_eliminacion("Eliminar todos los rangos", mensaje):
            return
        self.limpiarRangosSolicitado.emit()

    def _actualizar_botones(self):
        self.btn_eliminar.setEnabled(bool(self._obtener_visibles_seleccionados()))
        self.btn_limpiar.setEnabled(bool(self.rangos))
        # La potencia se calcula sobre rangos (no sub-rangos): sin ninguno
        # marcado no hay nada que calcular, así que el botón queda gris con la
        # razón en el tooltip.
        hay_seleccion = bool(self._rangos_padre_seleccionados())
        self.btn_aplicar_formula.setEnabled(hay_seleccion)
        self.btn_aplicar_formula.setToolTip(
            "Calcula la potencia en los rangos marcados. Los sub-rangos se "
            "calculan al abrirlos con doble clic."
            if hay_seleccion
            else "Marcá al menos un rango para poder calcular la potencia."
        )

    def mostrar_error_rango(self, mensaje):
        self.lbl_error.setStyleSheet("color: #EF5350;")
        self.lbl_error.setText(mensaje)

    def mostrar_aviso_rango(self, mensaje):
        self.lbl_error.setStyleSheet("color: #66BB6A;")
        self.lbl_error.setText(mensaje)
