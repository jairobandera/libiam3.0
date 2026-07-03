from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QComboBox,
    QHeaderView,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QWidget,
    QGroupBox,
    QLineEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from logica.config_db import agregar_alias, guardar_seccion_archivo, listar_secciones_archivo, eliminar_seccion_archivo


class VentanaEditorCSV(QDialog):
    aliasesGuardados = Signal(object)

    def __init__(self, df, db_session, ruta_archivo, parent=None):
        super().__init__(parent)
        self.df = df
        self.db_session = db_session
        self.ruta_archivo = ruta_archivo
        self.setWindowTitle("Editor CSV - Asignar Cabeceras")
        self.resize(1200, 700)
        self.cambios_pendientes = []
        self.secciones_pendientes = []
        self.fila_seleccionada = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        lbl_instruccion = QLabel(
            "Para archivos con cabeceras apiladas, seleccione la fila de cabecera, "
            "ingrese fila cabecera y fila fin, y use 'Marcar como nueva sección'. "
            "La sección original (fila 0) se incluye automáticamente. "
            "Las filas marcadas se resaltan en verde. "
            "Opcional: doble click en una celda para asignar tipo/eje manualmente (se muestra en amarillo)."
        )
        lbl_instruccion.setWordWrap(True)
        layout.addWidget(lbl_instruccion)

        # Controles de secciones
        self.seccion_controles = self.crear_controles_secciones()
        layout.addWidget(self.seccion_controles)

        # Lista de secciones definidas
        self.seccion_lista = self.crear_lista_secciones()
        layout.addWidget(self.seccion_lista)

        self.tabla = QTableWidget()
        self.tabla.setRowCount(len(self.df))
        self.tabla.setColumnCount(len(self.df.columns))
        self.tabla.setHorizontalHeaderLabels([str(c) for c in self.df.columns])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.verticalHeader().setVisible(True)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla.cellClicked.connect(self._al_click_fila)

        self._llenar_tabla()
        self._resaltar_cabeceras()

        self.tabla.cellDoubleClicked.connect(self._al_doble_click_celda)

        layout.addWidget(self.tabla)

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

        self.lista_secciones = QListWidget()
        self.lista_secciones.setFixedHeight(80)
        layout.addWidget(self.lista_secciones)

        btn_eliminar = QPushButton("Eliminar sección seleccionada")
        btn_eliminar.setObjectName("btnResetMapeo")
        btn_eliminar.setCursor(Qt.PointingHandCursor)
        btn_eliminar.clicked.connect(self._eliminar_seccion)
        layout.addWidget(btn_eliminar)

        group.setLayout(layout)
        return group

    def _llenar_tabla(self):
        for fila in range(len(self.df)):
            self.tabla.setVerticalHeaderItem(fila, QTableWidgetItem(str(fila)))
            for col in range(len(self.df.columns)):
                valor = self.df.iloc[fila, col]
                item = QTableWidgetItem(str(valor))
                item.setTextAlignment(Qt.AlignCenter)
                self.tabla.setItem(fila, col, item)

    def _es_fila_cabecera(self, fila_idx):
        celdas_texto = 0
        celdas_total = len(self.df.columns)

        for col in range(celdas_total):
            valor = self.df.iloc[fila_idx, col]
            if str(valor).strip() == "":
                continue
            try:
                float(str(valor))
            except ValueError:
                celdas_texto += 1

        return celdas_texto > celdas_total / 2

    def _resaltar_cabeceras(self):
        for fila in range(len(self.df)):
            if self._es_fila_cabecera(fila):
                for col in range(len(self.df.columns)):
                    item = self.tabla.item(fila, col)
                    if item:
                        item.setBackground(QColor(30, 75, 180))
                        item.setForeground(Qt.white)

    def _al_click_fila(self, fila, col):
        self.fila_seleccionada = fila
        self.txt_fila_cabecera.setText(str(fila))
        self.txt_fila_fin.setText(str(fila))

    def _al_doble_click_celda(self, fila, col):
        nombre_columna = self.df.columns[col]
        valor_celda = str(self.df.iloc[fila, col]).strip()

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
        })

        item = self.tabla.item(fila, col)
        if item:
            item.setBackground(QColor(200, 170, 0))
            item.setForeground(Qt.black)

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
            return

        # Extraer nombres de columna de la fila de cabecera
        columnas = []
        for col in range(len(self.df.columns)):
            valor = str(self.df.iloc[fila_cabecera, col]).strip()
            if valor:
                columnas.append(valor)

        if not columnas:
            return

        self.secciones_pendientes.append({
            "fila_inicio": fila_cabecera,
            "fila_fin": fila_fin,
            "columnas": columnas,
        })

        # Resaltar filas de la sección en verde
        for fila in range(fila_cabecera, fila_fin + 1):
            for col in range(len(self.df.columns)):
                item = self.tabla.item(fila, col)
                if item:
                    item.setBackground(QColor(0, 120, 0))
                    item.setForeground(Qt.white)

        self._actualizar_lista_secciones()

    def _actualizar_lista_secciones(self):
        self.lista_secciones.clear()
        for i, sec in enumerate(self.secciones_pendientes):
            cols_str = ", ".join(sec["columnas"][:5])
            if len(sec["columnas"]) > 5:
                cols_str += "..."
            item = QListWidgetItem(f"Sección {i+1}: filas {sec['fila_inicio']}-{sec['fila_fin']} | {cols_str}")
            item.setData(Qt.UserRole, i)
            self.lista_secciones.addItem(item)

    def _eliminar_seccion(self):
        item = self.lista_secciones.currentItem()
        if not item:
            return

        idx = item.data(Qt.UserRole)
        if idx is not None and 0 <= idx < len(self.secciones_pendientes):
            sec = self.secciones_pendientes.pop(idx)
            # Quitar resaltado verde de las filas
            for fila in range(sec["fila_inicio"], sec["fila_fin"] + 1):
                for col in range(len(self.df.columns)):
                    tab_item = self.tabla.item(fila, col)
                    if tab_item and tab_item.background().color() == QColor(0, 120, 0):
                        if self._es_fila_cabecera(fila):
                            tab_item.setBackground(QColor(30, 75, 180))
                            tab_item.setForeground(Qt.white)
                        else:
                            tab_item.setBackground(Qt.white)
                            tab_item.setForeground(Qt.black)
            self._actualizar_lista_secciones()

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

    def _guardar_y_cerrar(self):
        if self.cambios_pendientes:
            for cambio in self.cambios_pendientes:
                agregar_alias(self.db_session, cambio["nombre"], cambio["tipo"], cambio["eje"])

        if self.ruta_archivo and self.secciones_pendientes:
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
