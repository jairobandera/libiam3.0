"""Diálogos simples para seleccionar y confirmar una exportación."""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from logica import exportacion


def _cantidad_legible(cantidad, singular, plural=None):
    cantidad = int(cantidad or 0)
    plural = plural or f"{singular}s"
    numero = f"{cantidad:,}".replace(",", ".")
    return f"{numero} {singular if cantidad == 1 else plural}"


class ExportarDialog(QDialog):
    """Lista tradicional de opciones de exportación con botones de radio."""

    def __init__(
        self,
        parent=None,
        nombre_archivo="",
        cantidad_frames=0,
        cantidad_senales=0,
        cantidad_intervalos=0,
        intervalos=None,
        cantidad_resultados=0,
        nombre_formula="",
        hay_filtros=False,
        hay_curvas_formula=False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Exportar análisis")
        self.setModal(True)
        self.resize(680, 760)
        self.setMinimumSize(600, 620)
        self.setObjectName("dialogoExportar")

        self.nombre_archivo = str(nombre_archivo or "Archivo sin nombre")
        self.cantidad_frames = int(cantidad_frames or 0)
        self.cantidad_senales = int(cantidad_senales or 0)
        self.intervalos = [dict(intervalo) for intervalo in intervalos or ()]
        self.cantidad_intervalos = (
            len(self.intervalos)
            if intervalos is not None
            else int(cantidad_intervalos or 0)
        )
        self.cantidad_resultados = int(cantidad_resultados or 0)
        self.nombre_formula = str(nombre_formula or "").strip()
        self.hay_filtros = bool(hay_filtros)
        self.hay_curvas_formula = bool(hay_curvas_formula)

        self.grupo = QButtonGroup(self)
        self.grupo_alcance = QButtonGroup(self)
        self._radios = {}
        self._definiciones = self._crear_definiciones()
        self._init_ui()

    def _crear_definiciones(self):
        detalle_datos = (
            "Valores originales y filtrados."
            if self.hay_filtros
            else "Valores originales."
        )
        return {
            exportacion.MODO_DATOS: {
                "titulo": "Datos de las señales",
                "formato": "CSV",
                "detalle": detalle_datos,
                "disponible": self.cantidad_senales > 0,
                "motivo": "No hay señales disponibles.",
                "resumen": (
                    f"{_cantidad_legible(self.cantidad_frames, 'fila')} y "
                    f"{_cantidad_legible(self.cantidad_senales, 'señal', 'señales')}."
                ),
            },
            exportacion.MODO_INTERVALOS: {
                "titulo": "Muestras por intervalo",
                "formato": "CSV",
                "detalle": "Muestras, límites y notas.",
                "disponible": self.cantidad_intervalos > 0,
                "motivo": "Todavía no se creó ningún intervalo.",
                "resumen": _cantidad_legible(
                    self.cantidad_intervalos,
                    "intervalo o subintervalo",
                    "intervalos o subintervalos",
                )
                + ".",
            },
            exportacion.MODO_RESULTADOS: {
                "titulo": "Resumen de fórmulas",
                "formato": "CSV",
                "detalle": "Promedio, máximo y frame del máximo.",
                "disponible": self.cantidad_resultados > 0,
                "motivo": "Primero aplicá una fórmula a uno o más intervalos.",
                "resumen": _cantidad_legible(
                    self.cantidad_resultados, "resultado"
                )
                + ".",
            },
            exportacion.MODO_COMPLETO: {
                "titulo": "Análisis completo",
                "formato": "ZIP",
                "detalle": "Datos, intervalos y resultados.",
                "disponible": True,
                "motivo": "",
                "resumen": "Todos los elementos disponibles.",
            },
        }

    def _init_ui(self):
        principal = QVBoxLayout()
        principal.setContentsMargins(24, 22, 24, 20)
        principal.setSpacing(12)

        titulo = QLabel("Exportar análisis")
        titulo.setObjectName("tituloDialogoExportar")
        principal.addWidget(titulo)

        archivo = QLabel(self._texto_archivo())
        archivo.setObjectName("archivoSimpleExportacion")
        archivo.setToolTip(self.nombre_archivo)
        archivo.setWordWrap(True)
        principal.addWidget(archivo)

        principal.addWidget(self._crear_separador())

        lbl_contenido = QLabel("Contenido")
        lbl_contenido.setObjectName("seccionDialogoExportar")
        principal.addWidget(lbl_contenido)

        for clave, definicion in self._definiciones.items():
            radio = QRadioButton(
                f"{definicion['titulo']}  ·  {definicion['formato']}"
            )
            radio.setObjectName("opcionExportacion")
            radio.setEnabled(definicion["disponible"])
            radio.setCursor(
                Qt.PointingHandCursor
                if definicion["disponible"]
                else Qt.ArrowCursor
            )
            self.grupo.addButton(radio)
            self._radios[clave] = radio
            principal.addWidget(radio)

            texto_detalle = (
                definicion["detalle"]
                if definicion["disponible"]
                else definicion["motivo"]
            )
            detalle = QLabel(texto_detalle)
            detalle.setObjectName(
                "detalleOpcionExportacion"
                if definicion["disponible"]
                else "detalleOpcionExportacionDeshabilitada"
            )
            detalle.setWordWrap(True)
            detalle.setContentsMargins(27, 0, 0, 4)
            principal.addWidget(detalle)

        principal.addWidget(self._crear_separador())
        self._agregar_selector_alcance(principal)

        principal.addStretch()

        principal.addWidget(self._crear_separador())
        principal.addLayout(self._crear_botones())
        self.setLayout(principal)

        predeterminada = (
            exportacion.MODO_DATOS
            if self._definiciones[exportacion.MODO_DATOS]["disponible"]
            else exportacion.MODO_COMPLETO
        )
        self._radios[predeterminada].setChecked(True)
        self._actualizar_alcance()

    def _agregar_selector_alcance(self, principal):
        titulo = QLabel("Alcance")
        titulo.setObjectName("seccionDialogoExportar")
        principal.addWidget(titulo)

        self.radio_todo = QRadioButton("Todo el archivo")
        self.radio_todo.setObjectName("opcionAlcanceExportacion")
        self.radio_recortes = QRadioButton("Intervalos seleccionados")
        self.radio_recortes.setObjectName("opcionAlcanceExportacion")
        self.radio_recortes.setEnabled(bool(self.intervalos))
        self.grupo_alcance.addButton(self.radio_todo)
        self.grupo_alcance.addButton(self.radio_recortes)
        self.radio_todo.setChecked(True)
        principal.addWidget(self.radio_todo)
        principal.addWidget(self.radio_recortes)

        acciones = QHBoxLayout()
        self.btn_todos_recortes = QPushButton("Todos")
        self.btn_todos_recortes.setObjectName("btnAlcanceExportacion")
        self.btn_ningun_recorte = QPushButton("Ninguno")
        self.btn_ningun_recorte.setObjectName("btnAlcanceExportacion")
        self.btn_todos_recortes.clicked.connect(
            lambda: self._marcar_recortes(True)
        )
        self.btn_ningun_recorte.clicked.connect(
            lambda: self._marcar_recortes(False)
        )
        acciones.addWidget(self.btn_todos_recortes)
        acciones.addWidget(self.btn_ningun_recorte)
        acciones.addStretch()
        principal.addLayout(acciones)

        total = len(self.intervalos)
        self.lbl_catalogo_recortes = QLabel(
            _cantidad_legible(
                total,
                "intervalo o subintervalo",
                "intervalos o subintervalos",
            )
        )
        self.lbl_catalogo_recortes.setObjectName("catalogoCompletoExportacion")
        self.lbl_catalogo_recortes.setWordWrap(True)
        principal.addWidget(self.lbl_catalogo_recortes)

        self.lista_recortes = QListWidget()
        self.lista_recortes.setObjectName("listaRecortesExportacion")
        self.lista_recortes.setSelectionMode(QAbstractItemView.NoSelection)
        # Antes el layout podía comprimir la lista hasta dejar visible una sola
        # fila, lo que parecía un filtrado por la señal activa. Se reserva un
        # área suficiente y el resto continúa accesible con su barra de scroll.
        self.lista_recortes.setMinimumHeight(170)
        self.lista_recortes.setMaximumHeight(240)
        for intervalo in self.intervalos:
            identificador = intervalo.get("id")
            if identificador is None:
                continue
            es_sub = bool(intervalo.get("es_subintervalo"))
            nombre = intervalo.get("nombre") or (
                f"Sub-intervalo {intervalo.get('numero', '')}"
                if es_sub
                else f"Intervalo {intervalo.get('numero', '')}"
            )
            senal = intervalo.get("senal") or intervalo.get("columna") or "Señal"
            prefijo = "↳ " if es_sub else ""
            item = QListWidgetItem(
                f"{prefijo}{senal} · {nombre} "
                f"({intervalo.get('desde', '')}–{intervalo.get('hasta', '')})"
            )
            item.setData(Qt.UserRole, identificador)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setForeground(
                QBrush(QColor(intervalo.get("color") or "#E8E8E8"))
            )
            self.lista_recortes.addItem(item)
        self.lista_recortes.itemChanged.connect(self._recorte_cambiado)
        principal.addWidget(self.lista_recortes)

        self.lbl_alcance = QLabel("")
        self.lbl_alcance.setObjectName("detalleAlcanceExportacion")
        self.lbl_alcance.setWordWrap(True)
        principal.addWidget(self.lbl_alcance)

        self.radio_todo.toggled.connect(self._actualizar_alcance)
        self.radio_recortes.toggled.connect(self._actualizar_alcance)

    def _marcar_recortes(self, activo):
        estado = Qt.Checked if activo else Qt.Unchecked
        self.lista_recortes.blockSignals(True)
        for indice in range(self.lista_recortes.count()):
            self.lista_recortes.item(indice).setCheckState(estado)
        self.lista_recortes.blockSignals(False)
        self._actualizar_alcance()

    def _recorte_cambiado(self, *_args):
        """Al tocar la lista, activa su alcance sin depender de otro panel."""
        if self.intervalos and not self.radio_recortes.isChecked():
            self.radio_recortes.setChecked(True)
        self._actualizar_alcance()

    def _actualizar_alcance(self, *_args):
        usa_recortes = bool(
            hasattr(self, "radio_recortes") and self.radio_recortes.isChecked()
        )
        if not hasattr(self, "lista_recortes"):
            return
        seleccionados = sum(
            self.lista_recortes.item(indice).checkState() == Qt.Checked
            for indice in range(self.lista_recortes.count())
        )
        # Siempre se puede recorrer la lista completa. Si se marca o desmarca
        # una fila, `_recorte_cambiado` activa automáticamente el alcance por
        # intervalos.
        self.lista_recortes.setEnabled(bool(self.intervalos))
        self.btn_todos_recortes.setEnabled(usa_recortes)
        self.btn_ningun_recorte.setEnabled(usa_recortes)
        if usa_recortes:
            self.lbl_alcance.setText(
                f"{seleccionados} seleccionado(s)."
                if seleccionados
                else "Elegí al menos un recorte."
            )
        else:
            self.lbl_alcance.setText("Todo el contenido disponible.")
        if hasattr(self, "btn_continuar"):
            self.btn_continuar.setEnabled(not usa_recortes or seleccionados > 0)

    def _texto_archivo(self):
        nombre = self.nombre_archivo.replace("\\", "/").rsplit("/", 1)[-1]
        cantidades = (
            _cantidad_legible(self.cantidad_senales, "señal", "señales"),
            _cantidad_legible(self.cantidad_intervalos, "intervalo"),
            _cantidad_legible(self.cantidad_resultados, "resultado"),
        )
        return f"Archivo: {nombre}\n{' · '.join(cantidades)}"

    @staticmethod
    def _crear_separador():
        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setObjectName("separadorDialogo")
        return separador

    def _crear_botones(self):
        botones = QHBoxLayout()
        botones.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnDialogoSecundario")
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)

        self.btn_continuar = QPushButton("Elegir ubicación")
        self.btn_continuar.setObjectName("btnDialogoPrimario")
        self.btn_continuar.setCursor(Qt.PointingHandCursor)
        self.btn_continuar.setDefault(True)
        self.btn_continuar.clicked.connect(self.accept)

        botones.addWidget(btn_cancelar)
        botones.addWidget(self.btn_continuar)
        return botones

    def modo_seleccionado(self):
        for clave, radio in self._radios.items():
            if radio.isChecked():
                return clave
        return exportacion.MODO_DATOS

    def titulo_modo_seleccionado(self):
        return self._definiciones[self.modo_seleccionado()]["titulo"]

    def resumen_modo_seleccionado(self):
        return self._definiciones[self.modo_seleccionado()]["resumen"]

    def ids_intervalos_seleccionados(self):
        """None representa todo; una lista representa los recortes elegidos."""
        if not self.radio_recortes.isChecked():
            return None
        return [
            self.lista_recortes.item(indice).data(Qt.UserRole)
            for indice in range(self.lista_recortes.count())
            if self.lista_recortes.item(indice).checkState() == Qt.Checked
        ]


class ExportacionCompletadaDialog(QDialog):
    """Confirma el archivo creado y ofrece abrirlo o mostrar su carpeta."""

    def __init__(self, parent, ruta, titulo_modo, resumen=""):
        super().__init__(parent)
        self.ruta = Path(ruta).absolute()
        self.setWindowTitle("Exportación completada")
        self.setModal(True)
        self.resize(590, 330)
        self.setMinimumWidth(540)
        self.setObjectName("dialogoExportacionCompletada")

        principal = QVBoxLayout()
        principal.setContentsMargins(24, 23, 24, 20)
        principal.setSpacing(16)
        principal.addLayout(self._crear_encabezado())
        principal.addWidget(self._crear_ficha_archivo(titulo_modo, resumen))

        self.lbl_estado_apertura = QLabel("")
        self.lbl_estado_apertura.setObjectName("estadoAperturaExportacion")
        self.lbl_estado_apertura.setWordWrap(True)
        self.lbl_estado_apertura.hide()
        principal.addWidget(self.lbl_estado_apertura)

        principal.addStretch()
        principal.addWidget(ExportarDialog._crear_separador())
        principal.addLayout(self._crear_botones())
        self.setLayout(principal)

    def _crear_encabezado(self):
        encabezado = QHBoxLayout()
        encabezado.setSpacing(14)

        icono = QLabel("✓")
        icono.setObjectName("iconoExportacionCompletada")
        icono.setAlignment(Qt.AlignCenter)
        icono.setFixedSize(46, 46)
        encabezado.addWidget(icono, 0, Qt.AlignTop)

        titulo = QLabel("Exportación completada")
        titulo.setObjectName("tituloExportacionCompletada")
        encabezado.addWidget(titulo, 1)
        return encabezado

    def _crear_ficha_archivo(self, titulo_modo, resumen):
        ficha = QFrame()
        ficha.setObjectName("fichaArchivoExportado")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 13, 15, 14)
        layout.setSpacing(6)

        fila_tipo = QHBoxLayout()
        nombre_modo = QLabel(str(titulo_modo or "Archivo exportado"))
        nombre_modo.setObjectName("tipoArchivoExportado")
        fila_tipo.addWidget(nombre_modo)
        fila_tipo.addStretch()
        formato = QLabel(self.ruta.suffix.lstrip(".").upper() or "ARCHIVO")
        formato.setObjectName("formatoArchivoExportado")
        fila_tipo.addWidget(formato)
        layout.addLayout(fila_tipo)

        nombre = QLabel(self.ruta.name)
        nombre.setObjectName("nombreArchivoExportado")
        nombre.setWordWrap(True)
        layout.addWidget(nombre)

        detalle = resumen.strip() if resumen else ""
        tamano = self._tamano_legible()
        if tamano:
            detalle = f"{detalle} · " if detalle else ""
            detalle += f"Tamaño: {tamano}"
        if detalle:
            lbl_detalle = QLabel(detalle)
            lbl_detalle.setObjectName("detalleArchivoExportado")
            lbl_detalle.setWordWrap(True)
            layout.addWidget(lbl_detalle)

        ruta = QLineEdit(str(self.ruta))
        ruta.setObjectName("rutaArchivoExportado")
        ruta.setReadOnly(True)
        ruta.setCursorPosition(0)
        layout.addWidget(ruta)

        ficha.setLayout(layout)
        return ficha

    def _crear_botones(self):
        botones = QHBoxLayout()

        btn_carpeta = QPushButton("Abrir carpeta")
        btn_carpeta.setObjectName("btnDialogoSecundario")
        btn_carpeta.setCursor(Qt.PointingHandCursor)
        btn_carpeta.clicked.connect(lambda: self._abrir(self.ruta.parent, "carpeta"))
        botones.addWidget(btn_carpeta)

        btn_archivo = QPushButton("Abrir archivo")
        btn_archivo.setObjectName("btnDialogoSecundario")
        btn_archivo.setCursor(Qt.PointingHandCursor)
        btn_archivo.clicked.connect(lambda: self._abrir(self.ruta, "archivo"))
        botones.addWidget(btn_archivo)

        botones.addStretch()
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btnDialogoPrimario")
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.setDefault(True)
        btn_cerrar.clicked.connect(self.accept)
        botones.addWidget(btn_cerrar)
        return botones

    def _tamano_legible(self):
        try:
            tamano = float(self.ruta.stat().st_size)
        except OSError:
            return ""
        unidades = ("B", "KB", "MB", "GB")
        indice = 0
        while tamano >= 1024 and indice < len(unidades) - 1:
            tamano /= 1024
            indice += 1
        if indice == 0:
            return f"{int(tamano)} {unidades[indice]}"
        return f"{tamano:.1f}".replace(".", ",") + f" {unidades[indice]}"

    def _abrir(self, ruta, tipo):
        if QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta))):
            self.lbl_estado_apertura.hide()
            return
        self.lbl_estado_apertura.setText(
            f"No se pudo abrir {tipo}."
        )
        self.lbl_estado_apertura.show()
