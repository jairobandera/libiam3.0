from PySide6.QtWidgets import QTreeWidget
from PySide6.QtWidgets import QTreeWidgetItem

from PySide6.QtCore import Qt


class ArbolSenales(QTreeWidget):

    def __init__(self):

        super().__init__()

        self.setHeaderLabel("Señales")

    def cargar_grupos(self, grupos):

        self.clear()

        for categoria, señales in grupos.items():

            if not señales:
                continue

            parent = QTreeWidgetItem([categoria])

            self.addTopLevelItem(parent)

            for señal in señales:

                child = QTreeWidgetItem([señal])

                child.setCheckState(
                    0,
                    Qt.Checked
                )

                parent.addChild(child)

            parent.setExpanded(True)

    def obtener_seleccionadas(self):

        seleccionadas = {}

        for i in range(self.topLevelItemCount()):

            parent = self.topLevelItem(i)

            categoria = parent.text(0)

            seleccionadas[categoria] = []

            for j in range(parent.childCount()):

                child = parent.child(j)

                if child.checkState(0) == Qt.Checked:

                    seleccionadas[categoria].append(
                        child.text(0)
                    )

        return seleccionadas