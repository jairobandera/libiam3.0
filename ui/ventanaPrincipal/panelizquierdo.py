from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
import os
import pandas as pd
from logica.cargador_csv import CargadorCSV
from logica.config_db import listar_secciones_archivo


class PanelIzquierdo(QFrame):
    archivoCargado = Signal(str, object, object)
    archivoSeleccionado = Signal(str, object, object)
    modoSeleccionRangoCambiado = Signal(bool)

    def __init__(self, db_session=None):
        super().__init__()
        self.setObjectName("panelIzquierdo")
        self.setFixedWidth(280)
        self.db_session = db_session
        self.cargador = CargadorCSV(self, db_session=self.db_session)
        self.archivos_cargados = {}
        self.archivo_actual = {}
        self.alias_signal_conectado = False
        self.init_ui()

    def init_ui(self):

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Seccion superior: botones de accion
        self.seccion_botones = self.crear_seccion_botones()
        layout.addWidget(self.seccion_botones)

        # Espacio vacio reservado para futuras funcionalidades
        layout.addStretch()

        # Seccion central: arbol de archivos (ya no toma espacio extra)
        self.seccion_arbol = self.crear_seccion_arbol()
        layout.addWidget(self.seccion_arbol, 0)

        # Seccion inferior: informacion del archivo
        self.seccion_info = self.crear_seccion_info()
        layout.addWidget(self.seccion_info)

        self.setLayout(layout)

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

        # Boton seleccionar rango
        self.btn_rango = QPushButton("Seleccionar rango")
        self.btn_rango.setObjectName("btnSeleccionarRango")
        self.btn_rango.setCursor(Qt.PointingHandCursor)
        self.btn_rango.setCheckable(True)
        self.btn_rango.toggled.connect(self.modoSeleccionRangoCambiado.emit)

        layout.addWidget(self.btn_cargar)
        layout.addWidget(self.btn_rango)

        frame.setLayout(layout)
        return frame

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
                print(f"[DEBUG] cargar_csv: {len(secciones)} secciones cargadas desde BD para {nombre_archivo}")

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
        self.archivos_cargados[nombre_archivo] = {"df": df, "ruta": ruta_archivo}

        # Si es el primer archivo, limpiar el item vacio
        if self.arbol.topLevelItemCount() == 1:
            primer_item = self.arbol.topLevelItem(0)
            if primer_item.text(0) == "Ningun archivo cargado":
                self.arbol.clear()

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
            df = pd.read_csv(ruta_archivo, sep=None, engine="python")

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
            eje_str = cab["eje"].replace("eje_", "").upper() if cab["eje"] != "ninguno" else ""
            if eje_str:
                detectadas_no_graficadas.append(f"{cab['tipo']} {eje_str} ({cab['nombre']})")
            else:
                detectadas_no_graficadas.append(f"{cab['tipo']} ({cab['nombre']})")

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
