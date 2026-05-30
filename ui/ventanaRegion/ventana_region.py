from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFrame,
    QGridLayout
)

from ui.grafica import Grafica

import numpy as np


class VentanaRegion(QWidget):

    def __init__(
        self,
        df,
        columnas_visibles
    ):

        super().__init__()

        self.df = df

        self.columnas_visibles = columnas_visibles

        self.setWindowTitle(
            "Región Seleccionada"
        )

        self.resize(1100, 800)

        # =====================================================
        # LAYOUT PRINCIPAL
        # =====================================================

        layout = QVBoxLayout()

        # =====================================================
        # GRÁFICA
        # =====================================================

        self.plot = Grafica()

        self.plot.graficar(
            df,
            columnas_visibles
        )

        layout.addWidget(
            self.plot
        )

        # =====================================================
        # PANEL DE FÓRMULAS
        # =====================================================

        formulas_frame = QFrame()

        formulas_frame.setObjectName(
            "card"
        )

        formulas_layout = QVBoxLayout()

        # =====================================================
        # TÍTULO
        # =====================================================

        titulo = QLabel(
            "Aplicar Fórmulas"
        )

        titulo.setObjectName(
            "cardTitle"
        )

        formulas_layout.addWidget(
            titulo
        )

        # =====================================================
        # GRID RESULTADOS
        # =====================================================

        grid = QGridLayout()

        # =====================================================
        # OBTENER SEÑAL
        # =====================================================

        señal = list(
            columnas_visibles.keys()
        )[0]

        datos = df[señal].to_numpy()

        # =====================================================
        # CÁLCULOS
        # =====================================================

        maximo = np.max(datos)

        minimo = np.min(datos)

        promedio = np.mean(datos)

        rms = np.sqrt(
            np.mean(datos ** 2)
        )

        potencia = np.mean(
            datos ** 2
        )

        # =====================================================
        # LABELS RESULTADOS
        # =====================================================

        grid.addWidget(
            QLabel("Máximo:"),
            0,
            0
        )

        grid.addWidget(
            QLabel(f"{maximo:.4f}"),
            0,
            1
        )

        grid.addWidget(
            QLabel("Mínimo:"),
            1,
            0
        )

        grid.addWidget(
            QLabel(f"{minimo:.4f}"),
            1,
            1
        )

        grid.addWidget(
            QLabel("Promedio:"),
            2,
            0
        )

        grid.addWidget(
            QLabel(f"{promedio:.4f}"),
            2,
            1
        )

        grid.addWidget(
            QLabel("RMS:"),
            3,
            0
        )

        grid.addWidget(
            QLabel(f"{rms:.4f}"),
            3,
            1
        )

        grid.addWidget(
            QLabel("Potencia:"),
            4,
            0
        )

        grid.addWidget(
            QLabel(f"{potencia:.4f}"),
            4,
            1
        )

        formulas_layout.addLayout(
            grid
        )

        formulas_frame.setLayout(
            formulas_layout
        )

        layout.addWidget(
            formulas_frame
        )

        self.setLayout(
            layout
        )