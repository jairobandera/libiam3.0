"""Componente reutilizable de cálculo de fórmulas.

Bloque que muestra la fuente de datos (señal filtrada/original), el selector de
fórmula, los botones Aplicar/Quitar, el estado y los resultados por intervalo. Es
**solo interfaz**: no sabe nada de intervalos ni de cálculo. Emite solicitudes y
recibe resultados.

Lo usan tanto el panel derecho de la ventana principal (dentro de ``Formulas``)
como la ventana que se abre sobre un intervalo (``VentanaRegion``), para que ambos
usen exactamente el mismo componente sin duplicar código. La matemática sigue
en ``logica.formulas``.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from logica import formulas as formulas_logica
from logica import paleta


class PanelCalculo(QFrame):
    """Bloque de UI de una fórmula, sin conocimiento del origen de los datos."""

    # Pedido de cálculo: el contenedor decide qué intervalos/parámetros envía.
    calcularSolicitado = Signal()
    quitarFormulaSolicitado = Signal()
    fuenteCalculoCambiada = Signal(str)
    crearFormulaSolicitado = Signal()
    editarFormulaSolicitado = Signal(str)
    eliminarFormulaSolicitado = Signal(str)

    def __init__(self, permitir_gestion=False):
        super().__init__()
        self.permitir_gestion = bool(permitir_gestion)
        self.setObjectName("seccionFormulas")
        self.ultimos_resultados = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # --- Encabezado ---
        titulo = QLabel("Fórmulas")
        titulo.setObjectName("tituloSeccionMapeo")
        layout.addWidget(titulo)

        descripcion = QLabel(
            "En este apartado se calculan las diferentes fórmulas disponibles "
            "para el análisis biomecánico."
        )
        descripcion.setWordWrap(True)
        descripcion.setObjectName("lblDeteccion")
        layout.addWidget(descripcion)

        # --- Fuente de datos ---
        self._agregar_separador(layout)
        layout.addWidget(self._crear_bloque_fuente())
        self.set_hay_filtro(False)

        # --- Fórmula ---
        self._agregar_separador(layout)
        layout.addWidget(self._crear_bloque_formula())

        # --- Acciones ---
        self._agregar_separador(layout)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        self.btn_aplicar_formula = QPushButton("Aplicar")
        self.btn_aplicar_formula.setObjectName("btnAplicarMapeo")
        self.btn_aplicar_formula.setCursor(Qt.PointingHandCursor)
        self.btn_aplicar_formula.clicked.connect(self.calcularSolicitado.emit)
        self.btn_quitar_formula = QPushButton("Quitar")
        self.btn_quitar_formula.setObjectName("btnResetMapeo")
        self.btn_quitar_formula.setCursor(Qt.PointingHandCursor)
        self.btn_quitar_formula.setEnabled(False)
        self.btn_quitar_formula.setToolTip(
            "Quita todas las fórmulas aplicadas de las gráficas."
        )
        self.btn_quitar_formula.clicked.connect(self.quitarFormulaSolicitado.emit)
        fila.addWidget(self.btn_aplicar_formula)
        fila.addWidget(self.btn_quitar_formula)
        layout.addLayout(fila)

        # --- Estado ---
        self._agregar_separador(layout)
        self.lbl_estado_formula = QLabel("")
        self.lbl_estado_formula.setWordWrap(True)
        self.lbl_estado_formula.setObjectName("lblEstadoFormula")
        layout.addWidget(self.lbl_estado_formula)

        # --- Resultados ---
        self._agregar_separador(layout)
        self.lbl_titulo_resultados = QLabel("Resultados")
        self.lbl_titulo_resultados.setObjectName("tituloSeccionFormula")
        self.lbl_titulo_resultados.hide()
        layout.addWidget(self.lbl_titulo_resultados)

        self.lbl_resultados = QLabel("")
        self.lbl_resultados.setWordWrap(True)
        self.lbl_resultados.setObjectName("lblResultadosFormula")
        self.lbl_resultados.hide()
        layout.addWidget(self.lbl_resultados)

        # Advertencias biomecánicas (no bloqueantes): se muestran en ámbar.
        self.lbl_advertencia = QLabel("")
        self.lbl_advertencia.setWordWrap(True)
        self.lbl_advertencia.setObjectName("lblAdvertenciaFormula")
        self.lbl_advertencia.hide()
        layout.addWidget(self.lbl_advertencia)

        self.setLayout(layout)

    @staticmethod
    def _agregar_separador(layout):
        """Línea fina que separa los bloques, en el tono del borde actual."""
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setFixedHeight(1)
        separador.setStyleSheet("background-color: #3E3E42; border: 0;")
        layout.addWidget(separador)

    def _crear_bloque_fuente(self):
        """Selector «Fuente de datos» (señal filtrada/original)."""
        bloque = QWidget()
        bloque_layout = QVBoxLayout()
        bloque_layout.setContentsMargins(0, 0, 0, 0)
        bloque_layout.setSpacing(4)

        lbl = QLabel("Fuente de datos")
        lbl.setObjectName("tituloSeccionFormula")
        bloque_layout.addWidget(lbl)

        # Elegir sobre qué serie se calcula. No se exige filtro para calcular:
        # un pasa-bajos achata los picos, así que forzarlo sesgaría los valores.
        self.cmb_fuente = QComboBox()
        self.cmb_fuente.setObjectName("comboFormula")
        self.cmb_fuente.addItem("Señal filtrada", "filtrada")
        self.cmb_fuente.addItem("Señal original", "original")
        self.cmb_fuente.currentIndexChanged.connect(
            lambda _i: self.fuenteCalculoCambiada.emit(self.cmb_fuente.currentData())
        )
        bloque_layout.addWidget(self.cmb_fuente)

        bloque.setLayout(bloque_layout)
        return bloque

    def _crear_bloque_formula(self):
        """Selector de fórmula. Hoy solo «Potencia»; queda preparado para más."""
        bloque = QWidget()
        bloque_layout = QVBoxLayout()
        bloque_layout.setContentsMargins(0, 0, 0, 0)
        bloque_layout.setSpacing(4)

        lbl = QLabel("Fórmula")
        lbl.setObjectName("tituloSeccionFormula")
        bloque_layout.addWidget(lbl)

        self.cmb_formula = QComboBox()
        self.cmb_formula.setObjectName("comboFormula")
        # El listado sale del registro ``logica.formulas.FORMULAS``: agregar una
        # fórmula allí la muestra sola, sin tocar la interfaz.
        for clave, descripcion in formulas_logica.FORMULAS.items():
            self.cmb_formula.addItem(descripcion["nombre"], clave)
        self.cmb_formula.setCurrentIndex(0)
        self.cmb_formula.currentIndexChanged.connect(
            self._actualizar_formula_seleccionada
        )
        bloque_layout.addWidget(self.cmb_formula)

        self.lbl_expresion_formula = QLabel("")
        self.lbl_expresion_formula.setWordWrap(True)
        self.lbl_expresion_formula.setObjectName("lblExpresionFormula")
        bloque_layout.addWidget(self.lbl_expresion_formula)

        if self.permitir_gestion:
            fila = QHBoxLayout()
            fila.setSpacing(5)
            self.btn_crear_formula = QPushButton("Crear fórmula")
            self.btn_crear_formula.setObjectName("btnAplicarMapeo")
            self.btn_crear_formula.setCursor(Qt.PointingHandCursor)
            self.btn_crear_formula.clicked.connect(self.crearFormulaSolicitado.emit)

            self.btn_editar_formula = QPushButton("Editar")
            self.btn_editar_formula.setObjectName("btnResetMapeo")
            self.btn_editar_formula.setCursor(Qt.PointingHandCursor)
            self.btn_editar_formula.clicked.connect(self._pedir_edicion)

            self.btn_eliminar_formula = QPushButton("Eliminar")
            self.btn_eliminar_formula.setObjectName("btnResetMapeo")
            self.btn_eliminar_formula.setCursor(Qt.PointingHandCursor)
            self.btn_eliminar_formula.clicked.connect(self._pedir_eliminacion)

            fila.addWidget(self.btn_crear_formula, 1)
            fila.addWidget(self.btn_editar_formula)
            fila.addWidget(self.btn_eliminar_formula)
            bloque_layout.addLayout(fila)

        bloque.setLayout(bloque_layout)
        self.recargar_formulas()
        return bloque

    def recargar_formulas(self, seleccionar=None):
        """Actualiza el combo conservando la selección cuando todavía existe."""
        anterior = seleccionar or self.formula_seleccionada()
        self.cmb_formula.blockSignals(True)
        self.cmb_formula.clear()
        for clave, descripcion in formulas_logica.FORMULAS.items():
            nombre = descripcion["nombre"]
            if descripcion.get("personalizada"):
                nombre = f"{nombre} (propia)"
            self.cmb_formula.addItem(nombre, clave)
        indice = self.cmb_formula.findData(anterior)
        self.cmb_formula.setCurrentIndex(indice if indice >= 0 else 0)
        self.cmb_formula.blockSignals(False)
        self._actualizar_formula_seleccionada()

    def _actualizar_formula_seleccionada(self, _indice=None):
        clave = self.formula_seleccionada()
        descripcion = formulas_logica.FORMULAS.get(clave, {})
        expresion = descripcion.get("expresion") or ""
        ayuda = descripcion.get("descripcion") or ""
        texto = expresion
        if ayuda:
            texto = f"{texto}\n{ayuda}" if texto else ayuda
        self.lbl_expresion_formula.setText(texto)
        personalizada = bool(descripcion.get("personalizada"))
        if self.permitir_gestion:
            self.btn_editar_formula.setEnabled(personalizada)
            self.btn_eliminar_formula.setEnabled(personalizada)
            motivo = (
                ""
                if personalizada
                else "Las fórmulas incorporadas no se modifican."
            )
            self.btn_editar_formula.setToolTip(motivo)
            self.btn_eliminar_formula.setToolTip(motivo)

    def _pedir_edicion(self):
        clave = self.formula_seleccionada()
        if formulas_logica.es_formula_personalizada(clave):
            self.editarFormulaSolicitado.emit(clave)

    def _pedir_eliminacion(self):
        clave = self.formula_seleccionada()
        if formulas_logica.es_formula_personalizada(clave):
            self.eliminarFormulaSolicitado.emit(clave)

    def formula_seleccionada(self):
        """Clave de la fórmula elegida (p. ej. ``"potencia"``)."""
        return self.cmb_formula.currentData()

    def fuente_seleccionada(self):
        """Fuente elegida: ``"filtrada"`` o ``"original"``."""
        return self.cmb_fuente.currentData()

    def set_fuente(self, valor):
        """Sincroniza el combo de fuente con el valor aplicado globalmente."""
        indice = self.cmb_fuente.findData(valor)
        if indice >= 0 and indice != self.cmb_fuente.currentIndex():
            self.cmb_fuente.setCurrentIndex(indice)

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

    def set_aplicar_habilitado(self, habilitado, tooltip=""):
        """Habilita/deshabilita el botón Aplicar con su motivo como tooltip."""
        self.btn_aplicar_formula.setEnabled(bool(habilitado))
        self.btn_aplicar_formula.setToolTip(tooltip or "")

    def actualizar_estado(self, exito, mensaje):
        color = "#66BB6A" if exito else "#EF5350"
        if paleta.modo_daltonico_activo():
            color = "#56B4E9" if exito else "#D55E00"
        simbolo = "✓" if exito else "✕"
        self.lbl_estado_formula.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.lbl_estado_formula.setText(f"{simbolo} {mensaje}" if mensaje else "")

    def limpiar_resultados(self):
        """Deja el recuadro como si nunca se hubiera aplicado una fórmula."""
        self.ultimos_resultados = None
        self.lbl_resultados.setText("")
        self.lbl_resultados.hide()
        self.lbl_titulo_resultados.hide()
        self.lbl_estado_formula.setText("")
        self.lbl_advertencia.setText("")
        self.lbl_advertencia.hide()
        self.btn_quitar_formula.setEnabled(False)

    def mostrar_resultados(self, datos):
        """Un bloque por intervalo calculado, con sus valores destacados."""
        if not datos or not datos.get("resultados"):
            self.limpiar_resultados()
            return
        self.ultimos_resultados = datos

        resultados = datos["resultados"]
        unidad = datos.get("unidad") or ""
        sufijo = f" {unidad}" if unidad else ""

        encabezado = [(f"<b>{datos.get('nombre', 'Fórmula')}</b>", "")]
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
        self.lbl_titulo_resultados.show()
        self.btn_quitar_formula.setEnabled(True)
        self._mostrar_advertencias(datos.get("advertencias"))

    def actualizar_advertencias(self, advertencias):
        """Muestra (o limpia) las advertencias del último cálculo sin tocarlo."""
        self._mostrar_advertencias(advertencias)

    def _mostrar_advertencias(self, advertencias):
        """Vuelca las advertencias en ámbar; se ocultan si no hay ninguna."""
        lista = [a for a in (advertencias or []) if a]
        if not lista:
            self.lbl_advertencia.setText("")
            self.lbl_advertencia.hide()
            return
        color = "#E6A23C"
        if paleta.modo_daltonico_activo():
            color = "#E69F00"
        lineas = "".join(f'<div>⚠ {a}</div>' for a in lista)
        self.lbl_advertencia.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.lbl_advertencia.setText(lineas)
        self.lbl_advertencia.show()

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
        """Un intervalo como bloque con salto de línea, no como renglón corrido."""
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

        # La gráfica que posee el intervalo, para no mezclar resultados de señales.
        senal = (resultado.get("senal") or "").strip()
        if senal:
            lineas.insert(1, (f"en {senal}", "color:#8A8A8A; font-size:10px;"))

        if resultado.get("valor") is not None:
            valor = formulas_logica.formatear_valor(resultado["valor"])
            lineas.append((f"resultado <b>{valor}{sufijo}</b>", ""))
        elif pico is None:
            lineas.append(("sin datos válidos", "color:#8A8A8A;"))
        else:
            valor_pico = formulas_logica.formatear_valor(pico)
            valor_minimo = formulas_logica.formatear_valor(resumen.get("minimo"))
            valor_media = formulas_logica.formatear_valor(resumen.get("media"))
            valor_rms = formulas_logica.formatear_valor(resumen.get("rms"))
            lineas.append(
                (
                    f"pico <b>{valor_pico}{sufijo}</b> "
                    f'<span style="color:#8A8A8A;">(frame {resumen["x_pico"]:g})</span>',
                    "",
                )
            )
            lineas.append((f"mínimo <b>{valor_minimo}{sufijo}</b>", ""))
            lineas.append((f"media <b>{valor_media}{sufijo}</b>", ""))
            lineas.append((f"RMS <b>{valor_rms}{sufijo}</b>", ""))

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
