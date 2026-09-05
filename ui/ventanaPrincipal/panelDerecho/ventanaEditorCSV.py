from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QAbstractItemView,
    QTableView,
    QPushButton,
    QLabel,
    QComboBox,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QWidget,
    QGroupBox,
    QLineEdit,
    QFrame,
    QStyle,
)
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor, QIcon

PALETA_COLORES = [
    QColor(0, 120, 0),
    QColor(120, 70, 0),
    QColor(100, 50, 150),
    QColor(0, 100, 120),
    QColor(150, 50, 50),
    QColor(60, 80, 140),
    QColor(80, 120, 40),
    QColor(120, 40, 100),
]

COLOR_FONDO_TABLA = QColor(45, 45, 48)
COLOR_CABECERA = QColor(30, 75, 180)
COLOR_ASIGNADA = QColor(200, 170, 0)

from logica.config_db import (
    agregar_alias,
    guardar_seccion_archivo,
    listar_secciones_archivo,
    eliminar_seccion_archivo,
    desactivar_secciones_archivo,
    guardar_cabecera_asignada,
    desactivar_cabeceras_archivo,
    desactivar_cabecera,
    listar_cabeceras_asignadas,
)


class ModeloCSV(QAbstractTableModel):
    """Modelo virtualizado: Qt solicita únicamente las celdas visibles."""

    def __init__(self, df, parent=None):
        super().__init__(parent)
        self.df = df
        self.secciones = []
        self.celdas_asignadas = set()
        self._cache_filas_cabecera = {}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.df)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.df.columns)

    @staticmethod
    def _valor_a_str(valor):
        texto = str(valor).strip()
        return "" if texto.lower() in {"nan", "none"} else texto

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        fila, columna = index.row(), index.column()
        if role == Qt.DisplayRole:
            return self._valor_a_str(self.df.iat[fila, columna])
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        if role == Qt.BackgroundRole:
            if (fila, columna) in self.celdas_asignadas:
                return COLOR_ASIGNADA
            for indice, seccion in enumerate(self.secciones):
                if seccion["fila_inicio"] <= fila <= seccion["fila_fin"]:
                    return PALETA_COLORES[indice % len(PALETA_COLORES)]
            if self.es_fila_cabecera(fila):
                return COLOR_CABECERA
            return COLOR_FONDO_TABLA
        if role == Qt.ForegroundRole:
            return Qt.black if (fila, columna) in self.celdas_asignadas else Qt.white
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self.df.columns[section])
        return str(section)

    def es_fila_cabecera(self, fila):
        if fila in self._cache_filas_cabecera:
            return self._cache_filas_cabecera[fila]

        celdas_texto = 0
        celdas_total = len(self.df.columns)
        for columna in range(celdas_total):
            valor = self._valor_a_str(self.df.iat[fila, columna])
            if not valor:
                continue
            try:
                float(valor)
            except ValueError:
                celdas_texto += 1

        resultado = celdas_texto > celdas_total / 2
        self._cache_filas_cabecera[fila] = resultado
        return resultado

    def actualizar_resaltado(self, secciones=None, celdas_asignadas=None):
        if secciones is not None:
            self.secciones = list(secciones)
        if celdas_asignadas is not None:
            self.celdas_asignadas = set(celdas_asignadas)
        if self.rowCount() and self.columnCount():
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(self.rowCount() - 1, self.columnCount() - 1),
                [Qt.BackgroundRole, Qt.ForegroundRole],
            )


class VentanaEditorCSV(QDialog):
    aliasesGuardados = Signal(object)

    def __init__(self, df, db_session, ruta_archivo, parent=None):
        super().__init__(parent)
        self.df = df
        self.db_session = db_session
        self.ruta_archivo = ruta_archivo
        self.setWindowTitle("Editor CSV - Asignar Cabeceras")
        self.resize(1200, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.cambios_pendientes = []
        self.secciones_pendientes = []
        self.fila_seleccionada = None
        self.click_numero = 0
        self.celdas_asignadas = set()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addStretch()

        self.btn_ayuda = QPushButton("Ayuda")
        self.btn_ayuda.setObjectName("btnAyuda")
        self.btn_ayuda.setCursor(Qt.PointingHandCursor)
        self.btn_ayuda.setIcon(QIcon(self.style().standardIcon(QStyle.SP_DialogHelpButton)))
        self.btn_ayuda.setToolTip("Cómo usar el editor")
        self.btn_ayuda.clicked.connect(self._mostrar_ayuda)
        header_layout.addWidget(self.btn_ayuda)

        layout.addLayout(header_layout)

        # Controles de secciones
        self.seccion_controles = self.crear_controles_secciones()
        layout.addWidget(self.seccion_controles)

        # Secciones definidas + Cabeceras asignadas, lado a lado
        paneles_layout = QHBoxLayout()
        paneles_layout.setSpacing(8)

        self.seccion_lista = self.crear_lista_secciones()
        paneles_layout.addWidget(self.seccion_lista, 3)

        self.cambios_lista = self.crear_lista_cambios()
        paneles_layout.addWidget(self.cambios_lista, 2)

        layout.addLayout(paneles_layout)

        self.tabla = QTableView()
        self.modelo_tabla = ModeloCSV(self.df, self.tabla)
        self.tabla.setModel(self.modelo_tabla)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tabla.horizontalHeader().setDefaultSectionSize(120)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.verticalHeader().setVisible(True)
        self.tabla.verticalHeader().setDefaultSectionSize(24)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.clicked.connect(self._al_click_fila)
        self.tabla.doubleClicked.connect(self._al_doble_click_celda)

        layout.addWidget(self.tabla, 1)

        botones_layout = QHBoxLayout()
        botones_layout.addStretch()

        self.btn_guardar_cerrar = QPushButton("Guardar y cerrar")
        self.btn_guardar_cerrar.setObjectName("btnAplicarMapeo")
        self.btn_guardar_cerrar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar_cerrar.clicked.connect(self._guardar_y_cerrar)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnResetMapeo")
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self.close)

        botones_layout.addWidget(self.btn_guardar_cerrar)
        botones_layout.addWidget(self.btn_cancelar)

        layout.addLayout(botones_layout)
        self.setLayout(layout)

        self._cargar_secciones_existentes()

    def crear_controles_secciones(self):
        group = QGroupBox("Definir nueva sección")
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(QLabel("Fila cabecera:"))
        self.txt_fila_cabecera = QLineEdit()
        self.txt_fila_cabecera.setFixedWidth(60)
        layout.addWidget(self.txt_fila_cabecera)

        layout.addWidget(QLabel("Fila fin:"))
        self.txt_fila_fin = QLineEdit()
        self.txt_fila_fin.setFixedWidth(60)
        layout.addWidget(self.txt_fila_fin)

        self.btn_marcar_seccion = QPushButton("Marcar como nueva sección")
        self.btn_marcar_seccion.setObjectName("btnAplicarMapeo")
        self.btn_marcar_seccion.setCursor(Qt.PointingHandCursor)
        self.btn_marcar_seccion.clicked.connect(self._marcar_seccion)
        layout.addWidget(self.btn_marcar_seccion)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def crear_lista_secciones(self):
        group = QGroupBox("Secciones definidas")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        header_secciones = QHBoxLayout()
        header_secciones.setContentsMargins(0, 0, 0, 0)
        header_secciones.addStretch()

        self.btn_quitar_todos = QPushButton("Quitar todos")
        self.btn_quitar_todos.setCursor(Qt.PointingHandCursor)
        self.btn_quitar_todos.setFixedWidth(120)
        self.btn_quitar_todos.setIcon(QIcon(self.style().standardIcon(QStyle.SP_BrowserStop)))
        self.btn_quitar_todos.setStyleSheet(
            "QPushButton { background-color: #C62828; color: white; border: none; padding: 4px 10px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #B71C1C; }"
            "QPushButton:pressed { background-color: #8E0000; }"
        )
        self.btn_quitar_todos.clicked.connect(self._quitar_todas_secciones)
        header_secciones.addWidget(self.btn_quitar_todos)

        layout.addLayout(header_secciones)

        self.scroll_secciones = QScrollArea()
        self.scroll_secciones.setWidgetResizable(True)
        self.scroll_secciones.setFrameShape(QFrame.NoFrame)
        self.scroll_secciones.setFixedHeight(160)

        self.contenedor_secciones = QWidget()
        self.layout_secciones = QVBoxLayout()
        self.layout_secciones.setContentsMargins(0, 0, 0, 0)
        self.layout_secciones.setSpacing(4)
        self.contenedor_secciones.setLayout(self.layout_secciones)
        self.scroll_secciones.setWidget(self.contenedor_secciones)

        layout.addWidget(self.scroll_secciones)

        group.setLayout(layout)
        return group

    def crear_lista_cambios(self):
        group = QGroupBox("Cabeceras asignadas")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        header_cambios = QHBoxLayout()
        header_cambios.setContentsMargins(0, 0, 0, 0)
        header_cambios.addStretch()

        self.btn_quitar_todos_cambios = QPushButton("Quitar todos")
        self.btn_quitar_todos_cambios.setCursor(Qt.PointingHandCursor)
        self.btn_quitar_todos_cambios.setFixedWidth(120)
        self.btn_quitar_todos_cambios.setIcon(QIcon(self.style().standardIcon(QStyle.SP_BrowserStop)))
        self.btn_quitar_todos_cambios.setStyleSheet(
            "QPushButton { background-color: #C62828; color: white; border: none; padding: 4px 10px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #B71C1C; }"
            "QPushButton:pressed { background-color: #8E0000; }"
        )
        self.btn_quitar_todos_cambios.clicked.connect(self._quitar_todos_cambios)
        header_cambios.addWidget(self.btn_quitar_todos_cambios)

        layout.addLayout(header_cambios)

        self.scroll_cambios = QScrollArea()
        self.scroll_cambios.setWidgetResizable(True)
        self.scroll_cambios.setFrameShape(QFrame.NoFrame)
        self.scroll_cambios.setFixedHeight(160)

        self.contenedor_cambios = QWidget()
        self.layout_cambios = QVBoxLayout()
        self.layout_cambios.setContentsMargins(0, 0, 0, 0)
        self.layout_cambios.setSpacing(4)
        self.contenedor_cambios.setLayout(self.layout_cambios)
        self.scroll_cambios.setWidget(self.contenedor_cambios)

        layout.addWidget(self.scroll_cambios)

        group.setLayout(layout)
        return group

    def _valor_a_str(self, valor):
        s = str(valor).strip()
        if s.lower() == "nan":
            return ""
        return s

    def _es_fila_cabecera(self, fila_idx):
        return self.modelo_tabla.es_fila_cabecera(fila_idx)

    def _resaltar_cabeceras(self):
        self.modelo_tabla.actualizar_resaltado(
            self.secciones_pendientes, self.celdas_asignadas
        )

    def _al_click_fila(self, indice, col=None):
        fila = indice.row() if isinstance(indice, QModelIndex) else int(indice)
        self.fila_seleccionada = fila

        if self.click_numero == 0:
            self.txt_fila_cabecera.setText(str(fila))
            self.txt_fila_fin.clear()
            self.click_numero = 1
        elif self.click_numero == 1:
            fila_cabecera = int(self.txt_fila_cabecera.text().strip()) if self.txt_fila_cabecera.text().strip() else fila
            if fila >= fila_cabecera:
                self.txt_fila_fin.setText(str(fila))
            else:
                self.txt_fila_cabecera.setText(str(fila))
                self.txt_fila_fin.clear()
            self.click_numero = 2
        else:
            self.txt_fila_cabecera.setText(str(fila))
            self.txt_fila_fin.clear()
            self.click_numero = 1

    def _al_doble_click_celda(self, indice, col=None):
        if isinstance(indice, QModelIndex):
            fila, col = indice.row(), indice.column()
        else:
            fila, col = int(indice), int(col)
        nombre_columna = self.df.columns[col]
        valor_celda = self._valor_a_str(self.df.iloc[fila, col])

        if not valor_celda:
            return

        tipos = ["Fuerza", "Momento", "COP", "Tiempo", "Frame"]
        tipo, ok = QInputDialog.getItem(
            self, "Asignar Cabecera",
            f"Columna: {nombre_columna}\nValor: {valor_celda}\n\nSeleccione el tipo:",
            tipos, 0, False
        )

        if not ok or not tipo:
            return

        ejes = ["X", "Y", "Z", "Ninguno"]
        eje, ok2 = QInputDialog.getItem(
            self, "Asignar Eje",
            f"Columna: {nombre_columna}\nTipo: {tipo}\n\nSeleccione el eje:",
            ejes, 0, False
        )

        if not ok2 or not eje:
            return

        eje_map = {"X": "eje_x", "Y": "eje_y", "Z": "eje_z", "Ninguno": "ninguno"}

        self.cambios_pendientes.append({
            "nombre": valor_celda,
            "tipo": tipo,
            "eje": eje_map[eje],
            "fila": fila,
            "columna_indice": col,
        })

        self.celdas_asignadas.add((fila, col))
        self._reaplicar_resaltado()

        self._actualizar_lista_cambios()

    def _marcar_seccion(self):
        fila_cabecera_text = self.txt_fila_cabecera.text().strip()
        fila_fin_text = self.txt_fila_fin.text().strip()

        if not fila_cabecera_text or not fila_fin_text:
            return

        try:
            fila_cabecera = int(fila_cabecera_text)
            fila_fin = int(fila_fin_text)
        except ValueError:
            return

        if fila_cabecera < 0 or fila_fin >= len(self.df) or fila_cabecera > fila_fin:
            QMessageBox.warning(self, "Filas inválidas",
                "Las filas ingresadas no son válidas.\n"
                "La fila cabecera debe ser menor o igual que la fila fin\n"
                "y ambas dentro del rango del archivo.")
            return

        for i, sec in enumerate(self.secciones_pendientes):
            if fila_cabecera <= sec["fila_fin"] and sec["fila_inicio"] <= fila_fin:
                QMessageBox.warning(self, "Sección superpuesta",
                    f"La sección que intenta marcar (filas {fila_cabecera}-{fila_fin})\n"
                    f"se superpone con la Sección {i+1} (filas {sec['fila_inicio']}-{sec['fila_fin']}).\n\n"
                    f"Las secciones no pueden superponerse. La nueva sección\n"
                    f"debe empezar a partir de la fila {sec['fila_fin'] + 1}.")
                return

        # Extraer nombres de columna de la fila de cabecera
        columnas = []
        for col in range(len(self.df.columns)):
            valor = self._valor_a_str(self.df.iloc[fila_cabecera, col])
            if valor:
                columnas.append(valor)

        if not columnas:
            return

        todas_numericas = True
        for col_nombre in columnas:
            try:
                float(col_nombre)
            except ValueError:
                todas_numericas = False
                break

        if todas_numericas:
            QMessageBox.warning(self, "Sección inválida",
                "No se puede asignar una sección que contiene solo datos numéricos.\n"
                "La fila de cabecera debe contener nombres de variables (ej. Fuerza).")
            return

        self.secciones_pendientes.append({
            "fila_inicio": fila_cabecera,
            "fila_fin": fila_fin,
            "columnas": columnas,
        })

        self._reaplicar_resaltado()
        self._actualizar_lista_secciones()

    def _actualizar_lista_secciones(self):
        while self.layout_secciones.count():
            hijo = self.layout_secciones.takeAt(0)
            widget = hijo.widget()
            if widget is not None:
                widget.setParent(None)

        for i, sec in enumerate(self.secciones_pendientes):
            color = PALETA_COLORES[i % len(PALETA_COLORES)]
            fila = self._crear_fila_seccion(i, sec, color)
            self.layout_secciones.addWidget(fila)

        self.layout_secciones.addStretch()

    def _crear_fila_seccion(self, idx, sec, color):
        frame = QFrame()
        frame.setObjectName("filaSeccion")
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        indicador = QLabel("    ")
        indicador.setFixedWidth(20)
        indicador.setStyleSheet(f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border-radius: 3px;")

        cols_str = ", ".join(sec["columnas"][:5])
        if len(sec["columnas"]) > 5:
            cols_str += "..."

        lbl = QLabel(f"Sección {idx+1}: filas {sec['fila_inicio']}-{sec['fila_fin']} | {cols_str}")
        lbl.setObjectName("lblSeccion")

        btn_quitar = QPushButton("Quitar")
        btn_quitar.setCursor(Qt.PointingHandCursor)
        btn_quitar.setFixedWidth(80)
        btn_quitar.setIcon(QIcon(self.style().standardIcon(QStyle.SP_DialogDiscardButton)))
        btn_quitar.setStyleSheet(
            "QPushButton { background-color: #E85D04; color: white; border: none; padding: 4px 10px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #D14E00; }"
            "QPushButton:pressed { background-color: #B03D00; }"
        )
        btn_quitar.clicked.connect(lambda checked, i=idx: self._eliminar_seccion(i))

        layout.addWidget(indicador)
        layout.addWidget(lbl, 1)
        layout.addWidget(btn_quitar)

        frame.setLayout(layout)
        return frame

    def _eliminar_seccion(self, idx):
        if idx is not None and 0 <= idx < len(self.secciones_pendientes):
            self.secciones_pendientes.pop(idx)
            self._reaplicar_resaltado()
            self._actualizar_lista_secciones()

    def _quitar_todas_secciones(self):
        if not self.secciones_pendientes:
            return
        self.secciones_pendientes.clear()
        self._reaplicar_resaltado()
        self._actualizar_lista_secciones()

    def _actualizar_lista_cambios(self):
        while self.layout_cambios.count():
            hijo = self.layout_cambios.takeAt(0)
            widget = hijo.widget()
            if widget is not None:
                widget.setParent(None)

        for i, cambio in enumerate(self.cambios_pendientes):
            fila = self._crear_fila_cambio(i, cambio)
            self.layout_cambios.addWidget(fila)

        self.layout_cambios.addStretch()

    def _crear_fila_cambio(self, idx, cambio):
        frame = QFrame()
        frame.setObjectName("filaCambio")
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        eje_str = cambio["eje"].replace("eje_", "").upper() if cambio["eje"] != "ninguno" else "-"
        lbl = QLabel(f"{cambio['nombre']}  →  {cambio['tipo']} {eje_str}")
        lbl.setObjectName("lblCambio")
        lbl.setWordWrap(True)

        btn_quitar = QPushButton("Quitar")
        btn_quitar.setCursor(Qt.PointingHandCursor)
        btn_quitar.setFixedWidth(80)
        btn_quitar.setIcon(QIcon(self.style().standardIcon(QStyle.SP_DialogDiscardButton)))
        btn_quitar.setStyleSheet(
            "QPushButton { background-color: #E85D04; color: white; border: none; padding: 4px 10px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #D14E00; }"
            "QPushButton:pressed { background-color: #B03D00; }"
        )
        btn_quitar.clicked.connect(lambda checked, i=idx: self._eliminar_cambio(i))

        layout.addWidget(lbl, 1)
        layout.addWidget(btn_quitar)

        frame.setLayout(layout)
        return frame

    def _eliminar_cambio(self, idx):
        if idx is not None and 0 <= idx < len(self.cambios_pendientes):
            cambio = self.cambios_pendientes.pop(idx)
            if self.ruta_archivo and "id" in cambio:
                desactivar_cabecera(self.db_session, cambio["id"])
            if "fila" in cambio and "columna_indice" in cambio:
                self.celdas_asignadas.discard(
                    (cambio["fila"], cambio["columna_indice"])
                )
                self._reaplicar_resaltado()
            self._actualizar_lista_cambios()

    def _quitar_todos_cambios(self):
        if not self.cambios_pendientes:
            return
        if self.ruta_archivo:
            desactivar_cabeceras_archivo(self.db_session, self.ruta_archivo)
        self.cambios_pendientes.clear()
        self.celdas_asignadas.clear()
        self._reaplicar_resaltado()
        self._actualizar_lista_cambios()

    def _mostrar_ayuda(self):
        QMessageBox.information(self, "Ayuda - Editor CSV",
            "<b>Crear una sección</b><br>"
            "1. Hacé clic en la fila de cabecera (se completa 'Fila cabecera').<br>"
            "2. Hacé clic en la fila fin (se completa 'Fila fin').<br>"
            "3. Un tercer clic reinicia la selección.<br>"
            "4. Presioná 'Marcar como nueva sección'.<br><br>"
            "<b>Secciones</b><br>"
            "- Cada sección se resalta con un color distinto.<br>"
            "- Las secciones no pueden superponerse.<br>"
            "- Usá 'Quitar' para eliminar una sección individual.<br>"
            "- Usá 'Quitar todos' para eliminar todas las secciones.<br><br>"
            "<b>Asignar cabeceras manualmente</b><br>"
            "- Hacé doble clic en una celda para asignarle un tipo (Fuerza, Momento, COP, etc.) y un eje (X, Y, Z).<br>"
            "- La celda se resalta en amarillo.<br>"
            "- Al presionar 'Guardar y cerrar', las asignaciones se guardan<br>"
            "  para detectar automáticamente en futuras cargas de archivos CSV."
        )

    def _reaplicar_resaltado(self):
        """Actualiza solo las celdas visibles mediante el modelo virtualizado."""
        self.modelo_tabla.actualizar_resaltado(
            self.secciones_pendientes, self.celdas_asignadas
        )

    def _cargar_secciones_existentes(self):
        if self.ruta_archivo:
            secciones = listar_secciones_archivo(self.db_session, self.ruta_archivo)
            for sec in secciones:
                self.secciones_pendientes.append({
                    "fila_inicio": sec.fila_inicio,
                    "fila_fin": sec.fila_fin,
                    "columnas": sec.columnas.split(","),
                })
            self._actualizar_lista_secciones()

            cabeceras = listar_cabeceras_asignadas(self.db_session, self.ruta_archivo)
            for cab in cabeceras:
                self.cambios_pendientes.append({
                    "id": cab["id"],
                    "nombre": cab["nombre"],
                    "tipo": cab["tipo"],
                    "eje": cab["eje"],
                })
            self._actualizar_lista_cambios()
            self._reaplicar_resaltado()

    def _guardar_y_cerrar(self):
        if self.ruta_archivo:
            desactivar_cabeceras_archivo(self.db_session, self.ruta_archivo)
            for cambio in self.cambios_pendientes:
                guardar_cabecera_asignada(
                    self.db_session,
                    self.ruta_archivo,
                    cambio["nombre"],
                    cambio["tipo"],
                    cambio["eje"],
                )

            desactivar_secciones_archivo(self.db_session, self.ruta_archivo)
            for sec in self.secciones_pendientes:
                guardar_seccion_archivo(
                    self.db_session,
                    self.ruta_archivo,
                    sec["fila_inicio"],
                    sec["fila_fin"],
                    ",".join(sec["columnas"]),
                )

        self.aliasesGuardados.emit(self.secciones_pendientes)
        self.close()
