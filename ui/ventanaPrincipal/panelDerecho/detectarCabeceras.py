from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QCheckBox,
    QPushButton,
    QScrollArea,
    QWidget,
    QInputDialog,
)
from PySide6.QtCore import Qt, Signal

from logica.config_db import agregar_alias


class DetectarCabeceras(QFrame):
    cabecerasActualizadas = Signal()
    aliasesGuardados = Signal(object)

    def __init__(self, db_session=None):
        super().__init__()
        self.setObjectName("detectarCabeceras")
        self.db_session = db_session
        self.df_actual = None
        self.ruta_archivo_actual = None
        self.cabeceras_detectadas = []
        self.cabeceras_sin_asignar = []
        self.secciones_pendientes = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.lbl_titulo = QLabel("Detectar Cabeceras")
        self.lbl_titulo.setObjectName("tituloPanel")

        self.seccion_detectadas = self.crear_seccion_detectadas()
        layout.addWidget(self.seccion_detectadas)

        self.seccion_sin_asignar = self.crear_seccion_sin_asignar()
        layout.addWidget(self.seccion_sin_asignar)

        self.seccion_botones = self.crear_seccion_botones()
        layout.addWidget(self.seccion_botones)

        layout.addStretch()
        self.setLayout(layout)

    def crear_seccion_detectadas(self):
        frame = QFrame()
        frame.setObjectName("seccionDeteccion")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        lbl_titulo = QLabel("Cabeceras detectadas")
        lbl_titulo.setObjectName("tituloSeccionMapeo")

        self.lbl_contador_detectadas = QLabel("0 cabeceras reconocidas")
        self.lbl_contador_detectadas.setObjectName("lblDeteccion")

        self.contenedor_detectadas = QWidget()
        self.layout_detectadas = QVBoxLayout()
        self.layout_detectadas.setContentsMargins(0, 0, 0, 0)
        self.layout_detectadas.setSpacing(6)
        self.contenedor_detectadas.setLayout(self.layout_detectadas)

        self.scroll_detectadas = QScrollArea()
        self.scroll_detectadas.setWidget(self.contenedor_detectadas)
        self.scroll_detectadas.setWidgetResizable(True)
        self.scroll_detectadas.setFrameShape(QFrame.NoFrame)
        self.scroll_detectadas.setFixedHeight(500)
        self.scroll_detectadas.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(lbl_titulo)
        layout.addWidget(self.lbl_contador_detectadas)
        layout.addWidget(self.scroll_detectadas)

        frame.setLayout(layout)
        return frame

    def crear_seccion_sin_asignar(self):
        frame = QFrame()
        frame.setObjectName("seccionMapeo")

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        lbl_titulo = QLabel("Cabeceras sin asignar")
        lbl_titulo.setObjectName("tituloSeccionMapeo")

        self.lbl_contador_sin_asignar = QLabel("0 cabeceras pendientes")
        self.lbl_contador_sin_asignar.setObjectName("lblDeteccionWarn")

        self.contenedor_sin_asignar = QWidget()
        self.layout_sin_asignar = QVBoxLayout()
        self.layout_sin_asignar.setContentsMargins(0, 0, 0, 0)
        self.layout_sin_asignar.setSpacing(6)
        self.contenedor_sin_asignar.setLayout(self.layout_sin_asignar)

        self.scroll_sin_asignar = QScrollArea()
        self.scroll_sin_asignar.setWidget(self.contenedor_sin_asignar)
        self.scroll_sin_asignar.setWidgetResizable(True)
        self.scroll_sin_asignar.setFrameShape(QFrame.NoFrame)
        self.scroll_sin_asignar.setFixedHeight(200)
        self.scroll_sin_asignar.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        layout.addWidget(lbl_titulo)
        layout.addWidget(self.lbl_contador_sin_asignar)
        layout.addWidget(self.scroll_sin_asignar)

        frame.setLayout(layout)
        return frame

    def crear_seccion_botones(self):
        frame = QFrame()
        frame.setObjectName("seccionBotonesAccion")

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.btn_abrir_editor = QPushButton("Abrir CSV en editor")
        self.btn_abrir_editor.setObjectName("btnAplicarMapeo")
        self.btn_abrir_editor.setCursor(Qt.PointingHandCursor)
        self.btn_abrir_editor.clicked.connect(self.abrir_editor_csv)

        layout.addWidget(self.btn_abrir_editor)

        frame.setLayout(layout)
        return frame

    def cargar_datos(self, info):
        print(f"[DEBUG] DetectarCabeceras.cargar_datos: info keys={list(info.keys()) if info else 'None'}")
        self.df_actual = info.get("df", None)
        self.ruta_archivo_actual = info.get("ruta_archivo", None)
        deteccion = info.get("deteccion", {})

        print(f"[DEBUG] DetectarCabeceras.cargar_datos: df_actual={'si' if self.df_actual is not None else 'no'}, ruta={self.ruta_archivo_actual}")
        print(f"[DEBUG] DetectarCabeceras.cargar_datos: deteccion={deteccion}")

        self.cabeceras_detectadas = []
        self.cabeceras_sin_asignar = []

        mapeo = deteccion.get("mapeo", {})
        columnas_mapeadas = set()

        for tipo, ejes in mapeo.items():
            if isinstance(ejes, dict):
                for eje, columna in ejes.items():
                    columnas_mapeadas.add(columna)
                    self.cabeceras_detectadas.append({
                        "nombre": columna,
                        "tipo": tipo,
                        "eje": eje,
                    })
            else:
                columnas_mapeadas.add(ejes)
                self.cabeceras_detectadas.append({
                    "nombre": ejes,
                    "tipo": tipo,
                    "eje": "ninguno",
                })

        cabeceras_extra = deteccion.get("cabeceras_extra", [])
        for cab in cabeceras_extra:
            self.cabeceras_detectadas.append({
                "nombre": cab["nombre"],
                "tipo": cab["tipo"],
                "eje": cab["eje"],
            })

        no_reconocidas = deteccion.get("no_reconocidas", [])
        for col in no_reconocidas:
            if col not in columnas_mapeadas and str(col).lower().strip() not in ("nan", "", "none"):
                self.cabeceras_sin_asignar.append(col)

        self.renderizar_detectadas()
        self.renderizar_sin_asignar()

    def renderizar_detectadas(self):
        while self.layout_detectadas.count():
            hijo = self.layout_detectadas.takeAt(0)
            if hijo.widget():
                hijo.widget().deleteLater()

        for cab in self.cabeceras_detectadas:
            fila = self.crear_fila_detectada(cab)
            self.layout_detectadas.addWidget(fila)

        self.lbl_contador_detectadas.setText(
            f"{len(self.cabeceras_detectadas)} cabeceras reconocidas"
        )

    def crear_fila_detectada(self, cab):
        frame = QFrame()
        frame.setObjectName("filaMapeo")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.setEnabled(False)

        label = QLabel(f"{cab['tipo']} {cab['eje'].replace('eje_', '').upper() if cab['eje'] != 'ninguno' else ''}")
        label.setObjectName("lblEje")
        label.setMinimumWidth(80)

        nombre = QLabel(cab["nombre"])
        nombre.setObjectName("lblColumnaCSV")

        layout.addWidget(checkbox)
        layout.addWidget(label)
        layout.addWidget(nombre, 1)

        frame.setLayout(layout)
        return frame

    def renderizar_sin_asignar(self):
        while self.layout_sin_asignar.count():
            hijo = self.layout_sin_asignar.takeAt(0)
            if hijo.widget():
                hijo.widget().deleteLater()

        for col in self.cabeceras_sin_asignar:
            fila = self.crear_fila_sin_asignar(col)
            self.layout_sin_asignar.addWidget(fila)

        self.lbl_contador_sin_asignar.setText(
            f"{len(self.cabeceras_sin_asignar)} cabeceras pendientes"
        )

    def crear_fila_sin_asignar(self, nombre_columna):
        frame = QFrame()
        frame.setObjectName("filaMapeo")

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label_nombre = QLabel(nombre_columna)
        label_nombre.setObjectName("lblColumnaCSV")
        label_nombre.setMinimumWidth(100)

        cmb_tipo = QComboBox()
        cmb_tipo.setObjectName("cmbTipo")
        cmb_tipo.addItem("Seleccionar tipo...")
        cmb_tipo.addItem("Fuerza")
        cmb_tipo.addItem("Momento")
        cmb_tipo.addItem("COP")
        cmb_tipo.addItem("Tiempo")
        cmb_tipo.addItem("Frame")

        cmb_eje = QComboBox()
        cmb_eje.setObjectName("cmbEje")
        cmb_eje.addItem("Seleccionar eje...")
        cmb_eje.addItem("X")
        cmb_eje.addItem("Y")
        cmb_eje.addItem("Z")
        cmb_eje.addItem("Ninguno")

        btn_guardar = QPushButton("Guardar")
        btn_guardar.setObjectName("btnAplicarMapeo")
        btn_guardar.setCursor(Qt.PointingHandCursor)
        btn_guardar.setFixedWidth(70)
        btn_guardar.clicked.connect(
            lambda checked, col=nombre_columna, ct=cmb_tipo, ce=cmb_eje:
            self.guardar_alias(col, ct, ce)
        )

        layout.addWidget(label_nombre)
        layout.addWidget(cmb_tipo, 1)
        layout.addWidget(cmb_eje, 1)
        layout.addWidget(btn_guardar)

        frame.setLayout(layout)
        return frame

    def guardar_alias(self, nombre_columna, cmb_tipo, cmb_eje):
        tipo = cmb_tipo.currentText()
        eje = cmb_eje.currentText()

        print(f"[DEBUG] guardar_alias: columna={nombre_columna}, tipo={tipo}, eje={eje}")

        if tipo == "Seleccionar tipo..." or eje == "Seleccionar eje...":
            print("[DEBUG] guardar_alias: tipo o eje no seleccionado, saliendo")
            return

        eje_map = {
            "X": "eje_x",
            "Y": "eje_y",
            "Z": "eje_z",
            "Ninguno": "ninguno",
        }

        agregar_alias(self.db_session, nombre_columna, tipo, eje_map[eje])

        if nombre_columna in self.cabeceras_sin_asignar:
            self.cabeceras_sin_asignar.remove(nombre_columna)
            self.cabeceras_detectadas.append({
                "nombre": nombre_columna,
                "tipo": tipo,
                "eje": eje_map[eje],
            })

        self.renderizar_detectadas()
        self.renderizar_sin_asignar()
        self.aliasesGuardados.emit(self.secciones_pendientes)

    def reasignar_alias(self, nombre_columna):
        tipos = ["Fuerza", "Momento", "COP", "Tiempo", "Frame"]
        tipo, ok = QInputDialog.getItem(
            self, "Re-asignar Cabecera",
            f"Cabecera: {nombre_columna}\n\nSeleccione el nuevo tipo:",
            tipos, 0, False
        )

        if not ok or not tipo:
            return

        ejes = ["X", "Y", "Z", "Ninguno"]
        eje, ok2 = QInputDialog.getItem(
            self, "Re-asignar Eje",
            f"Cabecera: {nombre_columna}\nTipo: {tipo}\n\nSeleccione el nuevo eje:",
            ejes, 0, False
        )

        if not ok2 or not eje:
            return

        eje_map = {"X": "eje_x", "Y": "eje_y", "Z": "eje_z", "Ninguno": "ninguno"}

        agregar_alias(self.db_session, nombre_columna, tipo, eje_map[eje])

        for i, cab in enumerate(self.cabeceras_detectadas):
            if cab["nombre"] == nombre_columna:
                self.cabeceras_detectadas[i] = {
                    "nombre": nombre_columna,
                    "tipo": tipo,
                    "eje": eje_map[eje],
                }
                break

        self.renderizar_detectadas()
        self.aliasesGuardados.emit(self.secciones_pendientes)

    def abrir_editor_csv(self):
        print(f"[DEBUG] abrir_editor_csv: df_actual={'si' if self.df_actual is not None else 'no'}, ruta={self.ruta_archivo_actual}")
        if self.df_actual is not None and self.ruta_archivo_actual:
            import pandas as pd
            df_raw = pd.read_csv(self.ruta_archivo_actual, sep=None, engine="python", header=None)
            from ui.ventanaPrincipal.panelDerecho.ventanaEditorCSV import VentanaEditorCSV
            editor = VentanaEditorCSV(df_raw, self.db_session, self.ruta_archivo_actual, self)
            editor.aliasesGuardados.connect(self._on_aliases_guardados)
            editor.show()
        else:
            print("[DEBUG] abrir_editor_csv: df_actual o ruta_archivo es None")

    def _on_aliases_guardados(self, secciones):
        print(f"[DEBUG] DetectarCabeceras._on_aliases_guardados: secciones={secciones}")
        self.secciones_pendientes = secciones
        self.aliasesGuardados.emit(secciones)
