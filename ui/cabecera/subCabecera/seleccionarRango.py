# Seleccionar rango
# NabBar de tipo de dato (todos, fuerza, EMG, etc)
# posible zoom

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QLineEdit
)

from PySide6.QtGui import QDoubleValidator


class SeleccionarRango(QFrame):

    def __init__(self):

        super().__init__()

        self.setObjectName("subHeader")

        self.variables = {
            "Fuerza": ["Fx", "Fy", "Fz"],
            "Momento": ["Mx", "My", "Mz"],
            "COP": ["COPx", "COPy"]
        }

        self.init_ui()

    def init_ui(self):

        layout = QHBoxLayout()

        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(10)

        # Desplaza los controles hacia el centro-derecha
        layout.addSpacing(300)

        # VARIABLE
      
        layout.addWidget(QLabel("Variable:"))

        self.combo_variable = QComboBox()
        self.combo_variable.addItems(self.variables.keys())
        self.combo_variable.setFixedWidth(120)

        layout.addWidget(self.combo_variable)

        # SEÑAL

        layout.addWidget(QLabel("Señal:"))

        self.combo_senal = QComboBox()
        self.combo_senal.setFixedWidth(100)

        layout.addWidget(self.combo_senal)

        # DESDE

        layout.addWidget(QLabel("Desde:"))

        self.input_desde = QLineEdit()
        self.input_desde.setPlaceholderText("Ej: 0.000")
        self.input_desde.setFixedWidth(90)

        validador_desde = QDoubleValidator()
        self.input_desde.setValidator(validador_desde)

        layout.addWidget(self.input_desde)

        # HASTA

        layout.addWidget(QLabel("Hasta:"))

        self.input_hasta = QLineEdit()
        self.input_hasta.setPlaceholderText("Ej: 10.500")
        self.input_hasta.setFixedWidth(90)

        validador_hasta = QDoubleValidator()
        self.input_hasta.setValidator(validador_hasta)

        layout.addWidget(self.input_hasta)

        # BOTÓN APLICAR

        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_aplicar.setFixedWidth(100)

        layout.addWidget(self.btn_aplicar)

        # Espacio libre a la derecha
        layout.addStretch()

        self.setLayout(layout)

        # EVENTOS
        self.combo_variable.currentTextChanged.connect(
            self.actualizar_senales
        )

        self.actualizar_senales()

    def actualizar_senales(self):

        categoria = self.combo_variable.currentText()

        self.combo_senal.clear()

        self.combo_senal.addItems(
            self.variables[categoria]
        )