from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QApplication,
)
from PySide6.QtCore import Qt, Signal, QRegularExpression, QThread, QTimer, Slot
from PySide6.QtGui import QRegularExpressionValidator
import os
from logica.cargador_csv import CargadorCSV
from logica.config_db import (
    eliminar_variable_archivo,
    listar_secciones_archivo,
    guardar_variable_archivo,
    obtener_variable_archivo,
)
from logica.lector_csv import leer_csv_rapido
from ui.ventanaPrincipal.cargaCSV import CargaCSVDialog, TrabajadorCargaCSV


class PanelIzquierdo(QFrame):
    archivoCargado = Signal(str, object, object)
    archivoSeleccionado = Signal(str, object, object)
    modoSeleccionIntervaloCambiado = Signal(bool)
    # Masa y estatura del archivo activo, más gravedad de la sesión: las usan
    # las fórmulas creadas por el usuario.
    variablesCambiaron = Signal(object)

    # Gravedad en la superficie terrestre. Es una constante de sesión: se puede
    # editar mientras el programa está abierto pero nunca se guarda en la BD, así
    # al reabrir siempre vuelve a este valor.
    GRAVEDAD_TIERRA = 9.8

    def __init__(self, db_session=None):
        super().__init__()
        self.setObjectName("panelIzquierdo")
        self.setFixedWidth(280)
        self.db_session = db_session
        self.cargador = CargadorCSV(self, db_session=self.db_session)
        self.archivos_cargados = {}
        self.archivo_actual = {}
        self.alias_signal_conectado = False
        self.gravedad = self.GRAVEDAD_TIERRA
        self.masa_actual = None
        self.estatura_actual = None
        self._dialogo_carga = None
        self._hilo_carga = None
        self._trabajador_carga = None
        self._ruta_carga = None
        self._resultado_carga = None
        self._info_resultado_carga = None
        self._error_carga = None
        self.init_ui()

    def init_ui(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.seccion_botones = self.crear_seccion_botones()
        layout.addWidget(self.seccion_botones)

        self.seccion_variables = self.crear_seccion_variables()
        layout.addWidget(self.seccion_variables)

        layout.addStretch()

        self.seccion_arbol = self.crear_seccion_arbol()
        layout.addWidget(self.seccion_arbol, 0)

        self.seccion_info = self.crear_seccion_info()
        layout.addWidget(self.seccion_info)

        self.setLayout(layout)

        # Sin archivo cargado las variables propias del CSV están deshabilitadas.
        self._set_variables_archivo_habilitadas(False)

    def crear_seccion_botones(self):

        frame = QFrame()
        frame.setObjectName("seccionBotones")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.btn_cargar = QPushButton("Cargar archivo CSV")
        self.btn_cargar.setObjectName("btnCargarCSV")
        self.btn_cargar.setCursor(Qt.PointingHandCursor)
        self.btn_cargar.clicked.connect(self.cargar_csv)

        self.btn_intervalo = QPushButton("Seleccionar intervalo")
        self.btn_intervalo.setObjectName("btnSeleccionarIntervalo")
        self.btn_intervalo.setCursor(Qt.PointingHandCursor)
        self.btn_intervalo.setCheckable(True)
        self.btn_intervalo.setToolTip(
            "Esc cancela el punto pendiente o sale de la selección."
        )
        self.btn_intervalo.toggled.connect(self.modoSeleccionIntervaloCambiado.emit)

        layout.addWidget(self.btn_cargar)
        layout.addWidget(self.btn_intervalo)

        frame.setLayout(layout)
        return frame

    def crear_seccion_variables(self):

        frame = QFrame()
        frame.setObjectName("seccionVariables")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        titulo = QLabel("Variables")
        titulo.setObjectName("tituloSeccion")
        layout.addWidget(titulo)

        # --- Masa (por archivo, se guarda en la BD) ---
        fila_masa = QHBoxLayout()
        fila_masa.setSpacing(6)

        lbl_masa = QLabel("Masa")
        lbl_masa.setObjectName("varLabel")
        lbl_masa.setFixedWidth(60)

        self.input_masa = QLineEdit()
        self.input_masa.setObjectName("varInput")
        self.input_masa.setPlaceholderText("kg")
        self.input_masa.setValidator(self._crear_validador_numerico())
        self.input_masa.returnPressed.connect(self.guardar_masa)

        self.btn_guardar_masa = QPushButton("Guardar")
        self.btn_guardar_masa.setObjectName("btnGuardarVar")
        self.btn_guardar_masa.setCursor(Qt.PointingHandCursor)
        self.btn_guardar_masa.clicked.connect(self.guardar_masa)

        fila_masa.addWidget(lbl_masa)
        fila_masa.addWidget(self.input_masa, 1)
        fila_masa.addWidget(self.btn_guardar_masa)
        layout.addLayout(fila_masa)

        self.lbl_estado_masa = QLabel("")
        self.lbl_estado_masa.setObjectName("varEstado")
        self.lbl_estado_masa.setWordWrap(True)
        layout.addWidget(self.lbl_estado_masa)

        # --- Estatura (por archivo, en metros, se guarda en la BD) ---
        fila_estatura = QHBoxLayout()
        fila_estatura.setSpacing(6)

        lbl_estatura = QLabel("Estatura")
        lbl_estatura.setObjectName("varLabel")
        lbl_estatura.setFixedWidth(60)

        self.input_estatura = QLineEdit()
        self.input_estatura.setObjectName("varInput")
        self.input_estatura.setPlaceholderText("m")
        self.input_estatura.setValidator(self._crear_validador_numerico())
        self.input_estatura.returnPressed.connect(self.guardar_estatura)

        self.btn_guardar_estatura = QPushButton("Guardar")
        self.btn_guardar_estatura.setObjectName("btnGuardarVar")
        self.btn_guardar_estatura.setCursor(Qt.PointingHandCursor)
        self.btn_guardar_estatura.clicked.connect(self.guardar_estatura)

        fila_estatura.addWidget(lbl_estatura)
        fila_estatura.addWidget(self.input_estatura, 1)
        fila_estatura.addWidget(self.btn_guardar_estatura)
        layout.addLayout(fila_estatura)

        self.lbl_estado_estatura = QLabel("")
        self.lbl_estado_estatura.setObjectName("varEstado")
        self.lbl_estado_estatura.setWordWrap(True)
        layout.addWidget(self.lbl_estado_estatura)

        # --- Gravedad (constante de sesión, no se guarda en la BD) ---
        fila_gravedad = QHBoxLayout()
        fila_gravedad.setSpacing(6)

        lbl_gravedad = QLabel("Gravedad")
        lbl_gravedad.setObjectName("varLabel")
        lbl_gravedad.setFixedWidth(60)

        self.input_gravedad = QLineEdit(f"{self.GRAVEDAD_TIERRA:g}")
        self.input_gravedad.setObjectName("varInput")
        self.input_gravedad.setValidator(self._crear_validador_numerico())
        self.input_gravedad.setReadOnly(True)
        self.input_gravedad.returnPressed.connect(self._confirmar_gravedad)

        self.btn_editar_gravedad = QPushButton("Editar")
        self.btn_editar_gravedad.setObjectName("btnEditarVar")
        self.btn_editar_gravedad.setCursor(Qt.PointingHandCursor)
        self.btn_editar_gravedad.clicked.connect(self._toggle_editar_gravedad)

        fila_gravedad.addWidget(lbl_gravedad)
        fila_gravedad.addWidget(self.input_gravedad, 1)
        fila_gravedad.addWidget(self.btn_editar_gravedad)
        layout.addLayout(fila_gravedad)

        frame.setLayout(layout)
        return frame

    def _crear_validador_numerico(self):
        """Valida el tecleo de un número decimal aceptando '.' y ',' por igual.

        QDoubleValidator usa el separador decimal del locale del sistema, lo que
        bloquea uno de los dos símbolos según el idioma configurado. El valor
        final igual se normaliza (replace "," -> ".") y se revalida al guardar.
        """
        expresion = QRegularExpression(r"^\d{0,7}([.,]\d{0,6})?$")
        return QRegularExpressionValidator(expresion, self)

    def _set_variables_archivo_habilitadas(self, habilitada):
        """Habilita masa y estatura únicamente cuando hay un CSV activo."""
        self.input_masa.setEnabled(habilitada)
        self.btn_guardar_masa.setEnabled(habilitada)
        self.input_estatura.setEnabled(habilitada)
        self.btn_guardar_estatura.setEnabled(habilitada)
        if not habilitada:
            self.input_masa.clear()
            self.input_estatura.clear()
            self.lbl_estado_masa.clear()
            self.lbl_estado_estatura.clear()

    def _emitir_variables(self):
        """Avisa las variables vigentes de las que dependen las fórmulas."""
        self.variablesCambiaron.emit(
            {
                "masa": self.masa_actual,
                "estatura": self.estatura_actual,
                "gravedad": self.gravedad,
            }
        )

    @staticmethod
    def _valor_positivo(texto, predeterminado=None):
        try:
            valor = float(str(texto).strip().replace(",", "."))
        except (TypeError, ValueError):
            return predeterminado
        return valor if valor > 0 else predeterminado

    def variables_para_proyecto(self):
        """Toma también valores válidos escritos aunque no se pulsara Guardar."""
        self.masa_actual = self._valor_positivo(
            self.input_masa.text(), self.masa_actual
        )
        self.estatura_actual = self._valor_positivo(
            self.input_estatura.text(), self.estatura_actual
        )
        self.gravedad = self._valor_positivo(
            self.input_gravedad.text(), self.gravedad
        )
        self._emitir_variables()
        return {
            "masa": self.masa_actual,
            "estatura": self.estatura_actual,
            "gravedad": self.gravedad,
        }

    def restaurar_variables_proyecto(self, variables):
        """Restaura las variables y las asocia silenciosamente al CSV cargado."""
        if not isinstance(variables, dict) or not self.archivo_actual:
            return

        masa = self._valor_positivo(variables.get("masa"))
        estatura = self._valor_positivo(variables.get("estatura"))
        gravedad = self._valor_positivo(
            variables.get("gravedad"), self.GRAVEDAD_TIERRA
        )
        self.masa_actual = masa
        self.estatura_actual = estatura
        self.gravedad = gravedad

        self.input_masa.setText(f"{masa:g}" if masa is not None else "")
        self.input_estatura.setText(
            f"{estatura:g}" if estatura is not None else ""
        )
        self.input_gravedad.setText(f"{gravedad:g}")
        self.input_gravedad.setReadOnly(True)
        self.btn_editar_gravedad.setText("Editar")
        self.lbl_estado_masa.setText(
            f"Masa restaurada: {masa:g} kg" if masa is not None else ""
        )
        self.lbl_estado_estatura.setText(
            f"Estatura restaurada: {estatura:g} m"
            if estatura is not None else ""
        )

        ruta = self.archivo_actual.get("ruta")
        if self.db_session and ruta:
            for nombre, valor in (("masa", masa), ("estatura", estatura)):
                if valor is None:
                    eliminar_variable_archivo(
                        self.db_session, ruta, nombre
                    )
                else:
                    guardar_variable_archivo(
                        self.db_session, ruta, nombre, valor
                    )
        self._emitir_variables()

    def _cargar_variables_archivo(self):
        """Sincroniza masa y estatura con el archivo actualmente activo."""
        ruta = self.archivo_actual.get("ruta") if self.archivo_actual else None
        if not ruta:
            self.masa_actual = None
            self.estatura_actual = None
            self._set_variables_archivo_habilitadas(False)
            self._emitir_variables()
            return

        self._set_variables_archivo_habilitadas(True)
        self.lbl_estado_masa.setText("")
        self.lbl_estado_estatura.setText("")

        masa = None
        estatura = None
        if self.db_session:
            masa = obtener_variable_archivo(self.db_session, ruta, "masa")
            estatura = obtener_variable_archivo(
                self.db_session, ruta, "estatura"
            )

        self.masa_actual = masa
        if masa is not None:
            self.input_masa.setText(f"{masa:g}")
            self.lbl_estado_masa.setText(f"Masa guardada: {masa:g} kg")
        else:
            self.input_masa.clear()

        self.estatura_actual = estatura
        if estatura is not None:
            self.input_estatura.setText(f"{estatura:g}")
            self.lbl_estado_estatura.setText(
                f"Estatura guardada: {estatura:g} m"
            )
        else:
            self.input_estatura.clear()
        self._emitir_variables()

    def guardar_masa(self):
        """Guarda la masa del archivo actual en la BD (crea o actualiza)."""
        ruta = self.archivo_actual.get("ruta") if self.archivo_actual else None
        if not ruta or not self.db_session:
            return

        texto = self.input_masa.text().strip().replace(",", ".")
        if not texto:
            self.lbl_estado_masa.setText("Ingresá un valor de masa.")
            return

        try:
            valor = float(texto)
            if valor <= 0:
                raise ValueError
        except ValueError:
            self.lbl_estado_masa.setText("Valor de masa inválido.")
            return

        guardar_variable_archivo(self.db_session, ruta, "masa", valor)
        self.masa_actual = valor
        self.input_masa.setText(f"{valor:g}")
        self.lbl_estado_masa.setText(f"Masa guardada: {valor:g} kg ✓")
        self._emitir_variables()

    def guardar_estatura(self):
        """Guarda en metros la estatura asociada al archivo actual."""
        ruta = self.archivo_actual.get("ruta") if self.archivo_actual else None
        if not ruta or not self.db_session:
            return

        texto = self.input_estatura.text().strip().replace(",", ".")
        if not texto:
            self.lbl_estado_estatura.setText("Ingresá un valor de estatura.")
            return

        try:
            valor = float(texto)
            if valor <= 0:
                raise ValueError
        except ValueError:
            self.lbl_estado_estatura.setText("Valor de estatura inválido.")
            return

        guardar_variable_archivo(self.db_session, ruta, "estatura", valor)
        self.estatura_actual = valor
        self.input_estatura.setText(f"{valor:g}")
        self.lbl_estado_estatura.setText(
            f"Estatura guardada: {valor:g} m ✓"
        )
        self._emitir_variables()

    def _toggle_editar_gravedad(self):
        """Alterna entre editar la gravedad y fijarla como constante."""
        if self.input_gravedad.isReadOnly():
            self.input_gravedad.setReadOnly(False)
            self.input_gravedad.setFocus()
            self.input_gravedad.selectAll()
            self.btn_editar_gravedad.setText("Aceptar")
        else:
            self._confirmar_gravedad()

    def _confirmar_gravedad(self):
        """Valida y fija la gravedad editada. Si es inválida vuelve a la de la Tierra."""
        if self.input_gravedad.isReadOnly():
            return

        texto = self.input_gravedad.text().strip().replace(",", ".")
        try:
            valor = float(texto)
            if valor <= 0:
                raise ValueError
        except ValueError:
            valor = self.GRAVEDAD_TIERRA

        self.gravedad = valor
        self.input_gravedad.setText(f"{valor:g}")
        self.input_gravedad.setReadOnly(True)
        self.btn_editar_gravedad.setText("Editar")
        self._emitir_variables()

    def crear_seccion_arbol(self):

        frame = QFrame()
        frame.setObjectName("seccionArbol")
        frame.setMaximumHeight(300)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(6)

        titulo = QLabel("Archivos cargados")
        titulo.setObjectName("tituloSeccion")

        self.arbol = QTreeWidget()
        self.arbol.setObjectName("arbolArchivos")
        self.arbol.setHeaderHidden(True)
        self.arbol.setIndentation(20)
        self.arbol.setAnimated(True)
        self.arbol.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.arbol.itemDoubleClicked.connect(self.al_seleccionar_archivo)

        item_vacio = QTreeWidgetItem(self.arbol, ["Ningún archivo cargado"])
        item_vacio.setFlags(Qt.NoItemFlags)

        layout.addWidget(titulo)
        layout.addWidget(self.arbol)

        frame.setLayout(layout)
        return frame

    def crear_seccion_info(self):

        frame = QFrame()
        frame.setObjectName("seccionInfo")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        titulo = QLabel("Información del archivo")
        titulo.setObjectName("tituloSeccion")

        grid = QVBoxLayout()
        grid.setSpacing(4)

        self.lbl_nombre_archivo = QLabel("Nombre: ---")
        self.lbl_nombre_archivo.setObjectName("infoLabel")

        self.lbl_columnas = QLabel("Columnas: ---")
        self.lbl_columnas.setObjectName("infoLabel")

        self.lbl_tipo_datos = QLabel("Tipo de datos: ---")
        self.lbl_tipo_datos.setObjectName("infoLabel")

        self.lbl_subframes = QLabel("Subframes: ---")
        self.lbl_subframes.setObjectName("infoLabel")

        self.lbl_registros = QLabel("Registros: ---")
        self.lbl_registros.setObjectName("infoLabel")

        grid.addWidget(self.lbl_nombre_archivo)
        grid.addWidget(self.lbl_columnas)
        grid.addWidget(self.lbl_tipo_datos)
        grid.addWidget(self.lbl_subframes)
        grid.addWidget(self.lbl_registros)

        layout.addWidget(titulo)
        layout.addLayout(grid)

        frame.setLayout(layout)
        return frame

    @staticmethod
    def _texto_cantidad_columnas(info):
        texto = f"Columnas: {info['columnas']}"
        omitidas = info.get("cantidad_columnas_ignoradas", 0)
        if omitidas:
            texto += f" · {omitidas} omitidas"
        return texto

    def cargar_csv(self):
        ruta_archivo = self.cargador.seleccionar_archivo()
        if not ruta_archivo:
            return
        self.cargar_archivo_desde_ruta(ruta_archivo)

    def cargar_archivo_desde_ruta(self, ruta_archivo):
        """Carga un CSV cuya ruta ya se conoce, sin abrir el diálogo de archivos.

        Lo usa «Cargar» de la cabecera, que elige el archivo dentro de la
        carpeta «archivos». Devuelve el nombre cargado o ``None`` si falló.
        """
        if not ruta_archivo or not os.path.isfile(ruta_archivo):
            QMessageBox.warning(
                self, "Cargar", "No se encontró el archivo:\n" + str(ruta_archivo)
            )
            return None

        nombre_archivo = os.path.basename(ruta_archivo)
        dialogo = CargaCSVDialog(ruta_archivo, self.window())
        hilo = QThread(self)
        trabajador = TrabajadorCargaCSV(ruta_archivo)
        trabajador.moveToThread(hilo)

        self._dialogo_carga = dialogo
        self._hilo_carga = hilo
        self._trabajador_carga = trabajador
        self._ruta_carga = ruta_archivo
        self._resultado_carga = None
        self._info_resultado_carga = None
        self._error_carga = None

        hilo.started.connect(trabajador.ejecutar)
        trabajador.progresoCambiado.connect(dialogo.actualizar)
        trabajador.cargaCompletada.connect(self._completar_carga_csv)
        trabajador.cargaFallida.connect(self._fallar_carga_csv)
        trabajador.cargaCompletada.connect(hilo.quit)
        trabajador.cargaFallida.connect(hilo.quit)
        trabajador.cargaCompletada.connect(trabajador.deleteLater)
        trabajador.cargaFallida.connect(trabajador.deleteLater)

        QTimer.singleShot(0, hilo.start)
        dialogo.exec()
        hilo.quit()
        hilo.wait()
        hilo.deleteLater()

        resultado = self._resultado_carga
        info = self._info_resultado_carga
        error = self._error_carga
        self._dialogo_carga = None
        self._hilo_carga = None
        self._trabajador_carga = None
        self._ruta_carga = None

        if error:
            QMessageBox.critical(
                self,
                "Cargar CSV",
                f"No se pudo cargar el archivo:\n{error}",
            )
            return None
        if resultado and info:
            self._mostrar_resumen_deteccion(info)
        return resultado

    @Slot(object, object)
    def _completar_carga_csv(self, df, metadatos):
        dialogo = self._dialogo_carga
        if dialogo is None:
            return

        ruta_archivo = self._ruta_carga
        nombre_archivo = os.path.basename(ruta_archivo)
        try:
            dialogo.actualizar(82, "Analizando las señales…")
            dialogo.mostrar_columnas_omitidas(
                metadatos.get("cantidad_columnas_ignoradas", 0)
            )
            QApplication.processEvents()
            self.cargador.ruta_archivo_actual = ruta_archivo
            info = self._procesar_archivo(
                nombre_archivo,
                df,
                ruta_archivo,
                progreso=dialogo.actualizar,
                mostrar_resumen=False,
            )
        except Exception as exc:
            self._error_carga = str(exc)
            dialogo.finalizar(False)
            return

        self._resultado_carga = nombre_archivo
        self._info_resultado_carga = info
        dialogo.actualizar(100, "Archivo listo.")
        QApplication.processEvents()
        dialogo.finalizar(True)

    @Slot(str)
    def _fallar_carga_csv(self, mensaje):
        self._error_carga = mensaje
        if self._dialogo_carga is not None:
            self._dialogo_carga.finalizar(False)

    def _procesar_archivo(
        self,
        nombre_archivo,
        df,
        ruta_archivo,
        progreso=None,
        mostrar_resumen=True,
    ):
        """Aplica secciones de la BD, actualiza la UI y avisa al resto de paneles."""

        self.archivo_actual = {"nombre": nombre_archivo, "df": df, "ruta": ruta_archivo}

        # Limpiar secciones del archivo anterior y cargar las de este archivo desde la BD
        secciones = []
        if hasattr(self, "panel_derecho_ref"):
            self.panel_derecho_ref.detectar_cabeceras.secciones_pendientes = []

        if self.db_session:
            secciones_db = listar_secciones_archivo(self.db_session, ruta_archivo)
            if secciones_db:
                secciones = [
                    {
                        "fila_inicio": sec.fila_inicio,
                        "fila_fin": sec.fila_fin,
                        "columnas": sec.columnas.split(","),
                    }
                    for sec in secciones_db
                ]
                if hasattr(self, "panel_derecho_ref"):
                    self.panel_derecho_ref.detectar_cabeceras.secciones_pendientes = secciones

        if secciones:
            df = self.cargador.parsear_csv_con_secciones(ruta_archivo, secciones)
            self.archivo_actual["df"] = df

        if progreso:
            progreso(85, "Detectando señales…")
            QApplication.processEvents()

        self.agregar_al_arbol(nombre_archivo, df, ruta_archivo)

        info = self.cargador.obtener_info(nombre_archivo, df)
        info["columnas_csv"] = list(df.columns)
        info["df"] = df
        info["ruta_archivo"] = ruta_archivo
        self.lbl_nombre_archivo.setText(f"Nombre: {info['nombre']}")
        self.lbl_columnas.setText(self._texto_cantidad_columnas(info))
        self.lbl_tipo_datos.setText(f"Tipo de datos: {info['tipo_datos']}")
        self.lbl_subframes.setText(f"Subframes: {info['tiene_subframes']}")
        self.lbl_registros.setText(f"Registros: {info['registros']}")

        if progreso:
            progreso(90, "Preparando las gráficas…")
            QApplication.processEvents()

        self.archivoCargado.emit(nombre_archivo, df, info)

        # Cargar masa y estatura guardadas (o dejar sus campos vacíos).
        self._cargar_variables_archivo()

        if mostrar_resumen:
            self._mostrar_resumen_deteccion(info)

        if hasattr(self, "panel_derecho_ref"):
            if progreso:
                progreso(97, "Actualizando los paneles…")
                QApplication.processEvents()
            self.panel_derecho_ref.cargar_datos_csv(info)
            if not self.alias_signal_conectado:
                self.panel_derecho_ref.detectar_cabeceras.aliasesGuardados.connect(
                    lambda _: self._re_detectar_archivo_actual()
                )
                self.alias_signal_conectado = True
        return info

    def agregar_al_arbol(self, nombre_archivo, df, ruta_archivo=None):

        ya_estaba = nombre_archivo in self.archivos_cargados
        self.archivos_cargados[nombre_archivo] = {"df": df, "ruta": ruta_archivo}

        if self.arbol.topLevelItemCount() == 1:
            primer_item = self.arbol.topLevelItem(0)
            if primer_item.text(0) == "Ningún archivo cargado":
                self.arbol.clear()

        # Si el archivo ya estaba en el arbol solo se vuelve a seleccionar,
        # asi recargarlo no duplica la fila.
        if ya_estaba:
            for indice in range(self.arbol.topLevelItemCount()):
                item = self.arbol.topLevelItem(indice)
                if item.text(0) == nombre_archivo:
                    self.arbol.setCurrentItem(item)
                    return

        # Crear item del archivo
        item_archivo = QTreeWidgetItem(self.arbol, [nombre_archivo])
        item_archivo.setFlags(item_archivo.flags() | Qt.ItemIsSelectable)

        # Seleccionar el nuevo item
        self.arbol.setCurrentItem(item_archivo)

    def al_seleccionar_archivo(self, item, columna):
        nombre_archivo = item.text(0)

        if nombre_archivo not in self.archivos_cargados:
            return

        # Actualizar la informacion del archivo
        datos_archivo = self.archivos_cargados[nombre_archivo]
        df = datos_archivo["df"]
        ruta_archivo = datos_archivo.get("ruta")

        # Trackear archivo actual
        self.archivo_actual = {"nombre": nombre_archivo, "df": df, "ruta": ruta_archivo}

        # Limpiar secciones del archivo anterior y cargar las de este archivo desde la BD
        secciones = []
        if hasattr(self, "panel_derecho_ref"):
            self.panel_derecho_ref.detectar_cabeceras.secciones_pendientes = []

        if self.db_session and ruta_archivo:
            secciones_db = listar_secciones_archivo(self.db_session, ruta_archivo)
            if secciones_db:
                secciones = [
                    {
                        "fila_inicio": sec.fila_inicio,
                        "fila_fin": sec.fila_fin,
                        "columnas": sec.columnas.split(","),
                    }
                    for sec in secciones_db
                ]
                if hasattr(self, "panel_derecho_ref"):
                    self.panel_derecho_ref.detectar_cabeceras.secciones_pendientes = secciones

        if secciones and ruta_archivo:
            df = self.cargador.parsear_csv_con_secciones(ruta_archivo, secciones)
            self.archivo_actual["df"] = df
            self.archivos_cargados[nombre_archivo]["df"] = df

        info = self.cargador.obtener_info(nombre_archivo, df)
        info["columnas_csv"] = list(df.columns)
        info["df"] = df
        info["ruta_archivo"] = ruta_archivo
        self.lbl_nombre_archivo.setText(f"Nombre: {info['nombre']}")
        self.lbl_columnas.setText(self._texto_cantidad_columnas(info))
        self.lbl_tipo_datos.setText(f"Tipo de datos: {info['tipo_datos']}")
        self.lbl_subframes.setText(f"Subframes: {info['tiene_subframes']}")
        self.lbl_registros.setText(f"Registros: {info['registros']}")

        self.archivoSeleccionado.emit(nombre_archivo, df, info)

        # Cargar masa y estatura guardadas del archivo seleccionado.
        self._cargar_variables_archivo()

        # Actualizar panel derecho con los datos del archivo seleccionado
        if hasattr(self, "panel_derecho_ref"):
            self.panel_derecho_ref.cargar_datos_csv(info)

    def _re_detectar_archivo_actual(self):
        """Re-detecta el archivo actualmente seleccionado con los nuevos aliases."""
        if not self.archivo_actual:
            return

        nombre_archivo = self.archivo_actual["nombre"]
        df = self.archivo_actual["df"]
        ruta_archivo = self.archivo_actual["ruta"]

        # Obtener secciones del panel derecho directamente
        secciones = None
        if hasattr(self, "panel_derecho_ref"):
            secciones = self.panel_derecho_ref.detectar_cabeceras.secciones_pendientes

        # Re-parsear el CSV: con secciones si hay, o crudo si no hay
        if secciones and ruta_archivo:
            df = self.cargador.parsear_csv_con_secciones(ruta_archivo, secciones)
        elif ruta_archivo:
            df, _ = leer_csv_rapido(ruta_archivo)

        self.archivo_actual["df"] = df
        self.archivos_cargados[nombre_archivo]["df"] = df

        info = self.cargador.obtener_info(nombre_archivo, df)
        info["columnas_csv"] = list(df.columns)
        info["df"] = df
        info["ruta_archivo"] = ruta_archivo
        self.lbl_nombre_archivo.setText(f"Nombre: {info['nombre']}")
        self.lbl_columnas.setText(self._texto_cantidad_columnas(info))
        self.lbl_tipo_datos.setText(f"Tipo de datos: {info['tipo_datos']}")
        self.lbl_subframes.setText(f"Subframes: {info['tiene_subframes']}")
        self.lbl_registros.setText(f"Registros: {info['registros']}")

        self.archivoCargado.emit(nombre_archivo, df, info)

        if hasattr(self, "panel_derecho_ref"):
            self.panel_derecho_ref.cargar_datos_csv(info)

    def _mostrar_resumen_deteccion(self, info):
        """Muestra un popup con el resumen de variables detectadas y no reconocidas."""
        deteccion = info.get("deteccion", {})
        no_reconocidas = deteccion.get("no_reconocidas", [])
        cabeceras_extra = deteccion.get("cabeceras_extra", [])

        no_reconocidas = [
            col for col in no_reconocidas
            if str(col).lower().strip() not in ("nan", "", "none")
        ]

        detectadas_no_graficadas = []
        for cab in cabeceras_extra:
            if cab["tipo"] in ("Frame", "Tiempo"):
                continue
            if cab["nombre"] not in detectadas_no_graficadas:
                detectadas_no_graficadas.append(cab["nombre"])

        pendientes = list(dict.fromkeys(
            detectadas_no_graficadas + no_reconocidas
        ))
        if pendientes:
            dialogo = QMessageBox(self.window())
            dialogo.setIcon(QMessageBox.Warning)
            dialogo.setWindowTitle("Columnas pendientes")
            dialogo.setText(
                f"{len(pendientes)} columna(s) requieren asignación."
            )
            dialogo.setInformativeText("Revisá «Detectar cabeceras».")
            dialogo.setDetailedText("\n".join(map(str, pendientes)))
            dialogo.setStandardButtons(QMessageBox.Ok)
            dialogo.exec()
