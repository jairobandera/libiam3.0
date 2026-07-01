from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
)
from PySide6.QtCore import Qt, Signal
import os
from logica.cargador_csv import CargadorCSV


class PanelIzquierdo(QFrame):
    archivoCargado = Signal(str, object, object)
    archivoSeleccionado = Signal(str, object, object)
    modoSeleccionRangoCambiado = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setObjectName("panelIzquierdo")
        self.setFixedWidth(280)
        self.cargador = CargadorCSV(self)
        self.archivos_cargados = {}
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
        nombre_archivo, df = self.cargador.seleccionar_y_cargar()

        if nombre_archivo is None:
            return

        # Agregar archivo al arbol
        self.agregar_al_arbol(nombre_archivo, df)

        # Mostrar informacion del archivo
        info = self.cargador.obtener_info(nombre_archivo, df)
        info["columnas_csv"] = list(df.columns)
        self.lbl_nombre_archivo.setText(f"Nombre: {info['nombre']}")
        self.lbl_columnas.setText(f"Columnas: {info['columnas']}")
        self.lbl_tipo_datos.setText(f"Tipo de datos: {info['tipo_datos']}")
        self.lbl_subframes.setText(f"Subframes: {info['tiene_subframes']}")
        self.lbl_registros.setText(f"Registros: {info['registros']}")

        self.archivoCargado.emit(nombre_archivo, df, info)

        # Pasar datos al panel derecho si existe
        if hasattr(self, "panel_derecho_ref"):
            self.panel_derecho_ref.cargar_datos_csv(info)

    def agregar_al_arbol(self, nombre_archivo, df):

        # Guardar el dataframe para uso futuro
        self.archivos_cargados[nombre_archivo] = df

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
        df = self.archivos_cargados[nombre_archivo]
        info = self.cargador.obtener_info(nombre_archivo, df)
        info["columnas_csv"] = list(df.columns)
        self.lbl_nombre_archivo.setText(f"Nombre: {info['nombre']}")
        self.lbl_columnas.setText(f"Columnas: {info['columnas']}")
        self.lbl_tipo_datos.setText(f"Tipo de datos: {info['tipo_datos']}")
        self.lbl_subframes.setText(f"Subframes: {info['tiene_subframes']}")
        self.lbl_registros.setText(f"Registros: {info['registros']}")

        self.archivoSeleccionado.emit(nombre_archivo, df, info)

        # Actualizar panel derecho con los datos del archivo seleccionado
        if hasattr(self, "panel_derecho_ref"):
            self.panel_derecho_ref.cargar_datos_csv(info)
