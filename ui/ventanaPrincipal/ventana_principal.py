from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QFrame,
    QSplitter,
)

from PySide6.QtCore import Qt

from ui.grafica import Grafica
from ui.arbol_senales import ArbolSenales
from ui.ventanaRegion.ventana_region import VentanaRegion
from ui.cabecera.cabeceraPrincipal.cabecera import Cabecera

from logica.cargador_csv import cargar_csv
from logica.detector_dispositivo import detectar_dispositivo
from logica.clasificador_senales import clasificar_senales


class VentanaPrincipal(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("LIBiAM 3.0")

        self.resize(1600, 950)

        self.df = None

        self.init_ui()

    def init_ui(self):

        main_layout = QVBoxLayout()

        main_layout.setContentsMargins(
            12,
            12,
            12,
            12
        )

        main_layout.setSpacing(12)

        self.header = Cabecera()

        main_layout.addWidget(
            self.header
        )

        splitter = QSplitter(Qt.Horizontal)

        sidebar = QFrame()

        sidebar.setObjectName("sidebar")

        sidebar.setMinimumWidth(320)

        sidebar_layout = QVBoxLayout()

        sidebar_layout.setSpacing(18)

        controles_frame = QFrame()

        controles_frame.setObjectName(
            "card"
        )

        controles_layout = QVBoxLayout()

        controles_title = QLabel(
            "Controles"
        )

        controles_title.setObjectName(
            "cardTitle"
        )

        self.button = QPushButton(
            "Cargar CSV"
        )

        self.button.clicked.connect(
            self.load_csv
        )

        self.region_button = QPushButton(
            "Seleccionar rango"
        )

        self.region_button.clicked.connect(
            self.activar_region
        )

        controles_layout.addWidget(
            controles_title
        )

        controles_layout.addWidget(
            self.button
        )

        controles_layout.addWidget(
            self.region_button
        )

        controles_frame.setLayout(
            controles_layout
        )

        dispositivo_frame = QFrame()

        dispositivo_frame.setObjectName(
            "card"
        )

        dispositivo_layout = QVBoxLayout()

        dispositivo_title = QLabel(
            "Dispositivo Detectado"
        )

        dispositivo_title.setObjectName(
            "cardTitle"
        )

        self.device_label = QLabel(
            "No detectado"
        )

        self.device_label.setObjectName(
            "deviceLabel"
        )

        dispositivo_layout.addWidget(
            dispositivo_title
        )

        dispositivo_layout.addWidget(
            self.device_label
        )

        dispositivo_frame.setLayout(
            dispositivo_layout
        )

        senales_frame = QFrame()

        senales_frame.setObjectName(
            "card"
        )

        senales_layout = QVBoxLayout()

        senales_title = QLabel(
            "Señales"
        )

        senales_title.setObjectName(
            "cardTitle"
        )

        self.tree = ArbolSenales()

        self.tree.itemChanged.connect(self.actualizar_grafica)

        senales_layout.addWidget(senales_title)

        senales_layout.addWidget(self.tree)

        senales_frame.setLayout(senales_layout)

        sidebar_layout.addWidget(controles_frame)

        sidebar_layout.addWidget(dispositivo_frame)

        sidebar_layout.addWidget(senales_frame)

        sidebar_layout.addStretch()

        sidebar.setLayout(sidebar_layout)

        grafica_frame = QFrame()

        grafica_frame.setObjectName(
            "graphFrame"
        )

        grafica_layout = QVBoxLayout()

        self.plot = Grafica()

        self.plot.set_callback_region(self.abrir_region)

        grafica_layout.addWidget(self.plot)

        grafica_frame.setLayout(grafica_layout)

        splitter.addWidget(sidebar)

        splitter.addWidget(grafica_frame)

        splitter.setSizes([320, 1280])

        splitter.setChildrenCollapsible(False)

        main_layout.addWidget(splitter)

        self.setLayout(main_layout)


    def activar_region(self):

        self.plot.activar_seleccion()


    def load_csv(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar CSV",
            "",
            "CSV Files (*.csv)"
        )

        if not file_path:
            return

        self.df = cargar_csv(file_path)

        dispositivo = detectar_dispositivo(self.df)

        self.device_label.setText(dispositivo)

        grupos = clasificar_senales(self.df)

        self.tree.cargar_grupos(grupos)

        self.actualizar_grafica()


    def actualizar_grafica(self):

        if self.df is None:
            return

        visibles = (self.tree.obtener_seleccionadas())

        self.plot.graficar(self.df,visibles)


    def abrir_region(self, inicio, fin, señal):

        if self.df is None:
            return

        import numpy as np
        import pandas as pd

        col_tiempo = self.df.columns[0]

        # =====================================================
        # TIEMPO ORIGINAL
        # =====================================================

        tiempo_original = self.df[col_tiempo].to_numpy()

        # =====================================================
        # NUEVO RANGO EXACTO
        # =====================================================

        cantidad_puntos = 1000

        nuevo_tiempo = np.linspace(
            inicio,
            fin,
            cantidad_puntos
        )

        # =====================================================
        # NUEVO DATAFRAME
        # =====================================================

        df_nuevo = pd.DataFrame()

        df_nuevo[col_tiempo] = nuevo_tiempo

        # =====================================================
        # INTERPOLAR SEÑAL
        # =====================================================

        señal_original = self.df[señal].to_numpy()

        señal_interpolada = np.interp(
            nuevo_tiempo,
            tiempo_original,
            señal_original
        )

        df_nuevo[señal] = señal_interpolada

        # =====================================================
        # MOSTRAR SOLO ESA SEÑAL
        # =====================================================

        visibles = {
            señal: [señal]
        }

        self.ventana_region = VentanaRegion(
            df_nuevo,
            visibles
        )

        self.ventana_region.show()