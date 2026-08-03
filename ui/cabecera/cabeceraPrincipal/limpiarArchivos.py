"""Popup para limpiar la carpeta «archivos».

El desplegable de período es un atajo: marca los proyectos que entran en ese
criterio, pero la lista siempre queda editable, así el usuario puede sacar o
agregar cualquiera antes de borrar. Nada se elimina sin confirmación explícita
y sin ver los nombres.
"""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from logica import proyecto


class LimpiarArchivosDialog(QDialog):
    """Selector de qué copias guardadas eliminar de la carpeta «archivos»."""

    archivosEliminados = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Limpiar archivos guardados")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setObjectName("dialogoLimpiar")
        self.proyectos = []
        self._poblando = False
        self._init_ui()
        self._recargar()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        titulo = QLabel("Limpiar archivos guardados")
        titulo.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(titulo)

        self.lbl_ayuda = QLabel()
        self.lbl_ayuda.setObjectName("dialogoLimpiarAyuda")
        self.lbl_ayuda.setWordWrap(True)
        layout.addWidget(self.lbl_ayuda)

        fila_periodo = QHBoxLayout()
        fila_periodo.setSpacing(8)
        lbl_periodo = QLabel("Qué eliminar:")
        self.combo_periodo = QComboBox()
        self.combo_periodo.setObjectName("comboLimpiar")
        for clave, etiqueta in proyecto.PERIODOS:
            self.combo_periodo.addItem(etiqueta, clave)
        self.combo_periodo.currentIndexChanged.connect(self._aplicar_periodo)
        fila_periodo.addWidget(lbl_periodo)
        fila_periodo.addWidget(self.combo_periodo, 1)
        layout.addLayout(fila_periodo)

        self.lista = QListWidget()
        self.lista.setObjectName("listaLimpiar")
        self.lista.setMinimumHeight(200)
        # Los nombres largos se recortan con «…» (el completo va en el tooltip)
        # en vez de sacar una barra horizontal.
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lista.setTextElideMode(Qt.ElideRight)
        self.lista.itemChanged.connect(self._on_item_cambiado)
        layout.addWidget(self.lista, 1)

        self.lbl_resumen = QLabel()
        self.lbl_resumen.setObjectName("dialogoLimpiarResumen")
        self.lbl_resumen.setWordWrap(True)
        layout.addWidget(self.lbl_resumen)

        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setObjectName("separadorDialogo")
        layout.addWidget(separador)

        botones = QHBoxLayout()
        botones.addStretch()

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setObjectName("btnDialogoSecundario")
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.clicked.connect(self.accept)

        self.btn_eliminar = QPushButton("Eliminar seleccionados")
        self.btn_eliminar.setObjectName("btnDialogoPeligro")
        self.btn_eliminar.setCursor(Qt.PointingHandCursor)
        self.btn_eliminar.clicked.connect(self._eliminar)

        botones.addWidget(btn_cerrar)
        botones.addWidget(self.btn_eliminar)
        layout.addLayout(botones)

        self.setLayout(layout)

    def _recargar(self):
        """Relee la carpeta y repuebla la lista respetando el período elegido."""
        self.proyectos = proyecto.listar_proyectos()

        # Poblar dispara itemChanged por cada setCheckState: hay que silenciarlo.
        self._poblando = True
        self.lista.clear()

        if not self.proyectos:
            item = QListWidgetItem("La carpeta «archivos» está vacía.")
            item.setFlags(Qt.NoItemFlags)
            self.lista.addItem(item)
            self.lbl_ayuda.setText(
                "Todavía no hay copias guardadas para limpiar."
            )
        else:
            total = proyecto.formatear_tamano(
                sum(p["tamano"] for p in self.proyectos)
            )
            self.lbl_ayuda.setText(
                f"La carpeta «archivos» tiene {len(self.proyectos)} proyecto(s), "
                f"{total} en total. Se elimina el CSV y su archivo de "
                "anotaciones. Esta acción no se puede deshacer."
            )
            for datos in self.proyectos:
                item = QListWidgetItem(self._texto_item(datos))
                item.setData(Qt.UserRole, datos)
                item.setToolTip(self._texto_item(datos))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.lista.addItem(item)

        self._poblando = False
        self._aplicar_periodo()

    @staticmethod
    def _texto_item(datos):
        partes = [datos["nombre"]]
        if datos["modificado"]:
            fecha = datetime.fromtimestamp(datos["modificado"])
            partes.append(fecha.strftime("%d/%m/%Y %H:%M"))
        partes.append(proyecto.formatear_tamano(datos["tamano"]))
        if not datos["tiene_anotaciones"]:
            partes.append("sin anotaciones")
        return "   ·   ".join(partes)

    def _aplicar_periodo(self):
        """Marca los proyectos que entran en el período elegido."""
        periodo = self.combo_periodo.currentData()
        coincidentes = {
            p["nombre"]
            for p in proyecto.filtrar_por_periodo(self.proyectos, periodo)
        }

        self._poblando = True
        for indice in range(self.lista.count()):
            item = self.lista.item(indice)
            datos = item.data(Qt.UserRole)
            if not datos:
                continue
            item.setCheckState(
                Qt.Checked if datos["nombre"] in coincidentes else Qt.Unchecked
            )
        self._poblando = False
        self._actualizar_resumen()

    def _on_item_cambiado(self, _item):
        if self._poblando:
            return
        self._actualizar_resumen()

    def _seleccionados(self):
        seleccionados = []
        for indice in range(self.lista.count()):
            item = self.lista.item(indice)
            datos = item.data(Qt.UserRole)
            if datos and item.checkState() == Qt.Checked:
                seleccionados.append(datos)
        return seleccionados

    def _actualizar_resumen(self):
        seleccionados = self._seleccionados()
        self.btn_eliminar.setEnabled(bool(seleccionados))

        if not seleccionados:
            self.lbl_resumen.setText("No hay ningún archivo marcado.")
            return

        tamano = proyecto.formatear_tamano(
            sum(p["tamano"] for p in seleccionados)
        )
        self.lbl_resumen.setText(
            f"Se eliminarán {len(seleccionados)} proyecto(s) · {tamano}"
        )

    def _eliminar(self):
        seleccionados = self._seleccionados()
        if not seleccionados:
            return

        nombres = [p["nombre"] for p in seleccionados]
        listado = "\n".join(f"• {nombre}" for nombre in nombres[:12])
        if len(nombres) > 12:
            listado += f"\n• … y {len(nombres) - 12} más"

        confirmacion = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"Se van a eliminar {len(nombres)} proyecto(s) de la carpeta "
            "«archivos», junto con sus rangos y notas:\n\n"
            f"{listado}\n\nEsta acción no se puede deshacer. ¿Continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return

        eliminados, errores = proyecto.eliminar_proyectos(nombres)
        self._recargar()

        if eliminados:
            self.archivosEliminados.emit(len(eliminados))

        if errores:
            detalle = "\n".join(f"• {error}" for error in errores)
            QMessageBox.warning(
                self,
                "Limpiar archivos",
                f"Se eliminaron {len(eliminados)} proyecto(s).\n\n"
                f"No se pudieron eliminar:\n{detalle}",
            )
        else:
            QMessageBox.information(
                self,
                "Limpiar archivos",
                f"Se eliminaron {len(eliminados)} proyecto(s) de la carpeta "
                "«archivos».",
            )
