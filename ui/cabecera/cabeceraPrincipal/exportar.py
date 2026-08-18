"""Diálogos simples para seleccionar y confirmar una exportación."""

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
        cantidad_rangos=0,
        cantidad_resultados=0,
        nombre_formula="",
        hay_filtros=False,
        hay_curvas_formula=False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Exportar análisis")
        self.setModal(True)
        self.resize(590, 520)
        self.setMinimumSize(540, 480)
        self.setObjectName("dialogoExportar")

        self.nombre_archivo = str(nombre_archivo or "Archivo sin nombre")
        self.cantidad_frames = int(cantidad_frames or 0)
        self.cantidad_senales = int(cantidad_senales or 0)
        self.cantidad_rangos = int(cantidad_rangos or 0)
        self.cantidad_resultados = int(cantidad_resultados or 0)
        self.nombre_formula = str(nombre_formula or "").strip()
        self.hay_filtros = bool(hay_filtros)
        self.hay_curvas_formula = bool(hay_curvas_formula)

        self.grupo = QButtonGroup(self)
        self._radios = {}
        self._definiciones = self._crear_definiciones()
        self._init_ui()

    def _crear_definiciones(self):
        extras = []
        if self.hay_filtros:
            extras.append("valores filtrados")
        if self.hay_curvas_formula:
            extras.append("curvas calculadas")
        detalle_extra = f" Incluye {' y '.join(extras)}." if extras else ""

        formula = self.nombre_formula or "la fórmula aplicada"
        return {
            exportacion.MODO_DATOS: {
                "titulo": "Datos de las señales",
                "formato": "CSV",
                "detalle": (
                    "Una fila por punto del eje horizontal, con los valores "
                    f"originales.{detalle_extra}"
                ),
                "disponible": self.cantidad_senales > 0,
                "motivo": "No hay señales disponibles.",
                "resumen": (
                    f"{_cantidad_legible(self.cantidad_frames, 'fila')} y "
                    f"{_cantidad_legible(self.cantidad_senales, 'señal', 'señales')}."
                ),
            },
            exportacion.MODO_RANGOS: {
                "titulo": "Muestras por rango",
                "formato": "CSV",
                "detalle": "Muestras, límites y notas de cada rango seleccionado.",
                "disponible": self.cantidad_rangos > 0,
                "motivo": "Todavía no se creó ningún rango.",
                "resumen": _cantidad_legible(
                    self.cantidad_rangos,
                    "rango o subrango",
                    "rangos o subrangos",
                )
                + ".",
            },
            exportacion.MODO_RESULTADOS: {
                "titulo": "Resultados de fórmulas",
                "formato": "CSV",
                "detalle": f"Resultados por rango correspondientes a {formula}.",
                "disponible": self.cantidad_resultados > 0,
                "motivo": "Primero aplicá una fórmula a uno o más rangos.",
                "resumen": _cantidad_legible(
                    self.cantidad_resultados, "resultado"
                )
                + ".",
            },
            exportacion.MODO_COMPLETO: {
                "titulo": "Análisis completo",
                "formato": "ZIP",
                "detalle": (
                    "Datos, rangos, resultados disponibles y un resumen del análisis."
                ),
                "disponible": True,
                "motivo": "",
                "resumen": "Un paquete con todos los elementos disponibles.",
            },
        }

    def _init_ui(self):
        principal = QVBoxLayout()
        principal.setContentsMargins(24, 22, 24, 20)
        principal.setSpacing(12)

        titulo = QLabel("Exportar análisis")
        titulo.setObjectName("tituloDialogoExportar")
        principal.addWidget(titulo)

        subtitulo = QLabel("Seleccioná qué contenido querés guardar.")
        subtitulo.setObjectName("subtituloDialogoExportar")
        principal.addWidget(subtitulo)

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

        principal.addStretch()

        nota = QLabel(
            "Los archivos CSV se guardan en un formato compatible con Excel."
        )
        nota.setObjectName("notaSimpleExportacion")
        nota.setWordWrap(True)
        principal.addWidget(nota)

        principal.addWidget(self._crear_separador())
        principal.addLayout(self._crear_botones())
        self.setLayout(principal)

        predeterminada = (
            exportacion.MODO_DATOS
            if self._definiciones[exportacion.MODO_DATOS]["disponible"]
            else exportacion.MODO_COMPLETO
        )
        self._radios[predeterminada].setChecked(True)

    def _texto_archivo(self):
        nombre = self.nombre_archivo.replace("\\", "/").rsplit("/", 1)[-1]
        cantidades = (
            _cantidad_legible(self.cantidad_senales, "señal", "señales"),
            _cantidad_legible(self.cantidad_rangos, "rango"),
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

        btn_continuar = QPushButton("Elegir ubicación")
        btn_continuar.setObjectName("btnDialogoPrimario")
        btn_continuar.setCursor(Qt.PointingHandCursor)
        btn_continuar.setDefault(True)
        btn_continuar.clicked.connect(self.accept)

        botones.addWidget(btn_cancelar)
        botones.addWidget(btn_continuar)
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


class ExportacionCompletadaDialog(QDialog):
    """Confirma el archivo creado y ofrece abrirlo o mostrar su carpeta."""

    def __init__(self, parent, ruta, titulo_modo, resumen=""):
        super().__init__(parent)
        self.ruta = Path(ruta).absolute()
        self.setWindowTitle("Exportación completada")
        self.setModal(True)
        self.resize(590, 385)
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

        textos = QVBoxLayout()
        textos.setSpacing(4)
        titulo = QLabel("Exportación completada")
        titulo.setObjectName("tituloExportacionCompletada")
        textos.addWidget(titulo)
        subtitulo = QLabel(
            "El archivo se creó correctamente y está listo para usar."
        )
        subtitulo.setObjectName("subtituloExportacionCompletada")
        subtitulo.setWordWrap(True)
        textos.addWidget(subtitulo)
        encabezado.addLayout(textos, 1)
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

        detalle = resumen.strip() if resumen else "Archivo generado por ABS 3.0."
        tamano = self._tamano_legible()
        if tamano:
            detalle = f"{detalle}  Tamaño: {tamano}"
        lbl_detalle = QLabel(detalle)
        lbl_detalle.setObjectName("detalleArchivoExportado")
        lbl_detalle.setWordWrap(True)
        layout.addWidget(lbl_detalle)

        ruta = QLineEdit(str(self.ruta))
        ruta.setObjectName("rutaArchivoExportado")
        ruta.setReadOnly(True)
        ruta.setCursorPosition(0)
        ruta.setToolTip("Podés seleccionar y copiar esta ubicación.")
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
            f"No se pudo abrir {tipo}. La ubicación puede copiarse desde el campo anterior."
        )
        self.lbl_estado_apertura.show()
