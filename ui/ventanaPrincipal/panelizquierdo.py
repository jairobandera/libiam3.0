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
)
from PySide6.QtCore import Qt, Signal, QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
import os
from logica.cargador_csv import CargadorCSV
from logica.config_db import (
    listar_secciones_archivo,
    guardar_variable_archivo,
    obtener_variable_archivo,
)
from logica.lector_csv import leer_csv_rapido


class PanelIzquierdo(QFrame):
    archivoCargado = Signal(str, object, object)
    archivoSeleccionado = Signal(str, object, object)
    modoSeleccionIntervaloCambiado = Signal(bool)
    # Masa del archivo activo y gravedad de la sesión: las usan las fórmulas.
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
        self.init_ui()

    def init_ui(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Seccion superior: botones de accion
        self.seccion_botones = self.crear_seccion_botones()
        layout.addWidget(self.seccion_botones)

        # Seccion de variables (masa por archivo y gravedad)
        self.seccion_variables = self.crear_seccion_variables()
        layout.addWidget(self.seccion_variables)

        # Espacio vacio reservado para futuras funcionalidades
        layout.addStretch()

        # Seccion central: arbol de archivos (ya no toma espacio extra)
        self.seccion_arbol = self.crear_seccion_arbol()
        layout.addWidget(self.seccion_arbol, 0)

        # Seccion inferior: informacion del archivo
        self.seccion_info = self.crear_seccion_info()
        layout.addWidget(self.seccion_info)

        self.setLayout(layout)

        # Sin archivo cargado la masa arranca deshabilitada.
        self._set_masa_habilitada(False)

    def crear_seccion_botones(self):

        frame = QFrame()
        frame.setObjectName("seccionBotones")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Boton cargar archivo CSV
        self.btn_cargar = QPushButton("Cargar archivo CSV")
        self.btn_cargar.setObjectName("btnCargarCSV")
        self.btn_cargar.setCursor(Qt.PointingHandCursor)
        self.btn_cargar.clicked.connect(self.cargar_csv)

        # Boton seleccionar intervalo
        self.btn_intervalo = QPushButton("Seleccionar intervalo")
        self.btn_intervalo.setObjectName("btnSeleccionarIntervalo")
        self.btn_intervalo.setCursor(Qt.PointingHandCursor)
        self.btn_intervalo.setCheckable(True)
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

    def _set_masa_habilitada(self, habilitada):
        """Habilita o no la fila de masa (solo tiene sentido con un CSV cargado)."""
        self.input_masa.setEnabled(habilitada)
        self.btn_guardar_masa.setEnabled(habilitada)
        if not habilitada:
            self.input_masa.clear()
            self.lbl_estado_masa.setText("Cargá un CSV para asignar su masa.")

    def _emitir_variables(self):
        """Avisa la masa y la gravedad vigentes (las fórmulas dependen de esto)."""
        self.variablesCambiaron.emit(
            {"masa": self.masa_actual, "gravedad": self.gravedad}
        )

    def _cargar_masa_archivo(self):
        """Sincroniza el campo de masa con el archivo actualmente activo."""
        ruta = self.archivo_actual.get("ruta") if self.archivo_actual else None
        if not ruta:
            self.masa_actual = None
            self._set_masa_habilitada(False)
            self._emitir_variables()
            return

        self._set_masa_habilitada(True)
        self.lbl_estado_masa.setText("")

        valor = None
        if self.db_session:
            valor = obtener_variable_archivo(self.db_session, ruta, "masa")

        self.masa_actual = valor
        if valor is not None:
            self.input_masa.setText(f"{valor:g}")
            self.lbl_estado_masa.setText(f"Masa guardada: {valor:g} kg")
        else:
            self.input_masa.clear()
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
        except ValueError:
            self.lbl_estado_masa.setText("Valor de masa inválido.")
            return

        guardar_variable_archivo(self.db_session, ruta, "masa", valor)
        self.masa_actual = valor
        self.input_masa.setText(f"{valor:g}")
        self.lbl_estado_masa.setText(f"Masa guardada: {valor:g} kg ✓")
        self._emitir_variables()

        nombre_archivo = self.archivo_actual.get("nombre", "")
        QMessageBox.information(
            self,
            "Masa guardada",
            f"La masa de {valor:g} kg se guardó correctamente"
            + (f" para «{nombre_archivo}»." if nombre_archivo else "."),
        )

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

        # Titulo de la seccion
        titulo = QLabel("Archivos cargados")
        titulo.setObjectName("tituloSeccion")

        # Arbol de archivos
        self.arbol = QTreeWidget()
        self.arbol.setObjectName("arbolArchivos")
        self.arbol.setHeaderHidden(True)
        self.arbol.setIndentation(20)
        self.arbol.setAnimated(True)
        self.arbol.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.arbol.itemDoubleClicked.connect(self.al_seleccionar_archivo)

        # Item de ejemplo (se eliminara cuando se carguen archivos reales)
        item_vacio = QTreeWidgetItem(self.arbol, ["Ningun archivo cargado"])
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

        # Titulo de la seccion
        titulo = QLabel("Informacion del archivo")
        titulo.setObjectName("tituloSeccion")

        # Cuadricula de informacion
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

    def cargar_csv(self):

        # Delegar la carga al cargador CSV
        resultado = self.cargador.seleccionar_y_cargar()

        if resultado[0] is None:
            return

        nombre_archivo, df, ruta_archivo = resultado
        self._procesar_archivo(nombre_archivo, df, ruta_archivo)

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

        try:
            df, _ = leer_csv_rapido(ruta_archivo)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Cargar", f"No se pudo leer el CSV:\n{exc}")
            return None

        nombre_archivo = os.path.basename(ruta_archivo)
        self.cargador.ruta_archivo_actual = ruta_archivo
        self._procesar_archivo(nombre_archivo, df, ruta_archivo)
        return nombre_archivo

    def _procesar_archivo(self, nombre_archivo, df, ruta_archivo):
        """Aplica secciones de la BD, actualiza la UI y avisa al resto de paneles."""

        # Trackear archivo actual
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
                print(f"[DEBUG] _procesar_archivo: {len(secciones)} secciones cargadas desde BD para {nombre_archivo}")

        # Si hay secciones, re-parsear el CSV
        if secciones:
            df = self.cargador.parsear_csv_con_secciones(ruta_archivo, secciones)
            self.archivo_actual["df"] = df

        # Agregar archivo al arbol
        self.agregar_al_arbol(nombre_archivo, df, ruta_archivo)

        # Mostrar informacion del archivo
        info = self.cargador.obtener_info(nombre_archivo, df)
        info["columnas_csv"] = list(df.columns)
        info["df"] = df
        info["ruta_archivo"] = ruta_archivo
        self.lbl_nombre_archivo.setText(f"Nombre: {info['nombre']}")
        self.lbl_columnas.setText(f"Columnas: {info['columnas']}")
        self.lbl_tipo_datos.setText(f"Tipo de datos: {info['tipo_datos']}")
        self.lbl_subframes.setText(f"Subframes: {info['tiene_subframes']}")
        self.lbl_registros.setText(f"Registros: {info['registros']}")

        self.archivoCargado.emit(nombre_archivo, df, info)

        # Cargar la masa guardada de este archivo (o dejar el campo vacío)
        self._cargar_masa_archivo()

        # Mostrar resumen de deteccion al usuario
        self._mostrar_resumen_deteccion(info)

        # Pasar datos al panel derecho si existe
        if hasattr(self, "panel_derecho_ref"):
            self.panel_derecho_ref.cargar_datos_csv(info)
            if not self.alias_signal_conectado:
                self.panel_derecho_ref.detectar_cabeceras.aliasesGuardados.connect(
                    lambda _: self._re_detectar_archivo_actual()
                )
                self.alias_signal_conectado = True

    def agregar_al_arbol(self, nombre_archivo, df, ruta_archivo=None):

        # Guardar el dataframe y ruta para uso futuro
        ya_estaba = nombre_archivo in self.archivos_cargados
        self.archivos_cargados[nombre_archivo] = {"df": df, "ruta": ruta_archivo}

        # Si es el primer archivo, limpiar el item vacio
        if self.arbol.topLevelItemCount() == 1:
            primer_item = self.arbol.topLevelItem(0)
            if primer_item.text(0) == "Ningun archivo cargado":
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
                print(f"[DEBUG] al_seleccionar_archivo: {len(secciones)} secciones cargadas desde BD para {nombre_archivo}")

        if secciones and ruta_archivo:
            df = self.cargador.parsear_csv_con_secciones(ruta_archivo, secciones)
            self.archivo_actual["df"] = df
            self.archivos_cargados[nombre_archivo]["df"] = df

        info = self.cargador.obtener_info(nombre_archivo, df)
        info["columnas_csv"] = list(df.columns)
        info["df"] = df
        info["ruta_archivo"] = ruta_archivo
        self.lbl_nombre_archivo.setText(f"Nombre: {info['nombre']}")
        self.lbl_columnas.setText(f"Columnas: {info['columnas']}")
        self.lbl_tipo_datos.setText(f"Tipo de datos: {info['tipo_datos']}")
        self.lbl_subframes.setText(f"Subframes: {info['tiene_subframes']}")
        self.lbl_registros.setText(f"Registros: {info['registros']}")

        self.archivoSeleccionado.emit(nombre_archivo, df, info)

        # Cargar la masa guardada del archivo seleccionado
        self._cargar_masa_archivo()

        # Actualizar panel derecho con los datos del archivo seleccionado
        if hasattr(self, "panel_derecho_ref"):
            self.panel_derecho_ref.cargar_datos_csv(info)

    def _re_detectar_archivo_actual(self):
        """Re-detecta el archivo actualmente seleccionado con los nuevos aliases."""
        if not self.archivo_actual:
            print("[DEBUG] _re_detectar_archivo_actual: no hay archivo actual")
            return

        nombre_archivo = self.archivo_actual["nombre"]
        df = self.archivo_actual["df"]
        ruta_archivo = self.archivo_actual["ruta"]

        print(f"[DEBUG] _re_detectar_archivo_actual: archivo={nombre_archivo}, ruta={ruta_archivo}")

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
        self.lbl_columnas.setText(f"Columnas: {info['columnas']}")
        self.lbl_tipo_datos.setText(f"Tipo de datos: {info['tipo_datos']}")
        self.lbl_subframes.setText(f"Subframes: {info['tiene_subframes']}")
        self.lbl_registros.setText(f"Registros: {info['registros']}")

        self.archivoCargado.emit(nombre_archivo, df, info)

        if hasattr(self, "panel_derecho_ref"):
            self.panel_derecho_ref.cargar_datos_csv(info)

    def _mostrar_resumen_deteccion(self, info):
        """Muestra un popup con el resumen de variables detectadas y no reconocidas."""
        deteccion = info.get("deteccion", {})
        mapeo = deteccion.get("mapeo", {})
        no_reconocidas = deteccion.get("no_reconocidas", [])
        cabeceras_extra = deteccion.get("cabeceras_extra", [])

        reconocidas = []
        for tipo, ejes in mapeo.items():
            if tipo in ("Frame", "Tiempo"):
                continue
            if isinstance(ejes, dict):
                for eje, columna in ejes.items():
                    eje_str = eje.replace("eje_", "").upper() if eje != "ninguno" else ""
                    if eje_str:
                        reconocidas.append(f"{tipo} {eje_str} ({columna})")
                    else:
                        reconocidas.append(f"{tipo} ({columna})")
            else:
                reconocidas.append(f"{tipo} ({ejes})")

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

        mensaje = ""

        if reconocidas:
            mensaje += "<b>Se graficaron las siguientes variables automáticamente:</b><br>"
            mensaje += "<br>".join(f"• {r}" for r in reconocidas)
            mensaje += "<br><br>"

        if detectadas_no_graficadas:
            mensaje += "<b>Se detectaron variables que NO se graficaron y requieren asignación manual de secciones:</b><br>"
            mensaje += "<br>".join(f"• {d}" for d in detectadas_no_graficadas)
            mensaje += "<br><br>Estas variables están en el archivo pero fuera de la cabecera principal.<br>"
            mensaje += "Para graficarlas, abrí el panel «Detectar Cabeceras»,<br>"
            mensaje += "usá el botón «Abrir CSV en editor» y marcá las secciones correspondientes."
            mensaje += "<br><br>"

        if no_reconocidas:
            mensaje += "<b>Se detectaron columnas no reconocidas que requieren asignación manual:</b><br>"
            mensaje += "<br>".join(f"• {col}" for col in no_reconocidas)
            mensaje += "<br><br>Para asignarlas, abrí el panel «Detectar Cabeceras»<br>"
            mensaje += "y usá el botón «Abrir CSV en editor»."

        if not reconocidas and not detectadas_no_graficadas and not no_reconocidas:
            mensaje = "No se detectaron variables en el archivo."

        if mensaje:
            QMessageBox.information(self, "Detección de cabeceras", mensaje)
