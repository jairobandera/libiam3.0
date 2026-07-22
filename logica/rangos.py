"""Modelo independiente de la interfaz para los rangos de cálculo."""

from __future__ import annotations

from dataclasses import asdict, dataclass


COLORES_RANGOS = (
    "#42A5F5",
    "#66BB6A",
    "#FFCA28",
    "#AB47BC",
    "#FF7043",
    "#26C6DA",
    "#EC407A",
    "#9CCC65",
    "#7E57C2",
    "#FFA726",
    "#26A69A",
    "#5C6BC0",
)


class RangoSuperpuestoError(ValueError):
    def __init__(self, rango_existente):
        self.rango_existente = rango_existente
        super().__init__(
            f"El rango se superpone con el rango {rango_existente.numero} "
            f"({rango_existente.desde}–{rango_existente.hasta})."
        )


@dataclass(frozen=True)
class RangoCalculo:
    numero: int
    desde: int
    hasta: int
    color: str
    nombre: str = ""

    def como_dict(self) -> dict:
        return asdict(self)


class GestorRangos:
    def __init__(self):
        self._rangos: list[RangoCalculo] = []
        self._siguiente_numero = 1

    def listar(self) -> list[RangoCalculo]:
        return list(self._rangos)

    def agregar(self, desde: int, hasta: int, nombre: str = "") -> RangoCalculo:
        desde, hasta = sorted((int(desde), int(hasta)))
        if desde == hasta:
            raise ValueError("El rango debe contener al menos dos frames.")

        for existente in self._rangos:
            # Los extremos son inclusivos: compartir un frame también cuenta
            # como superposición para evitar duplicarlo en los cálculos.
            if desde <= existente.hasta and hasta >= existente.desde:
                raise RangoSuperpuestoError(existente)

        numero = self._siguiente_numero
        color = COLORES_RANGOS[(numero - 1) % len(COLORES_RANGOS)]
        nombre = nombre.strip() or f"Rango {numero}"
        rango = RangoCalculo(numero=numero, desde=desde, hasta=hasta, color=color, nombre=nombre)
        self._rangos.append(rango)
        self._siguiente_numero += 1
        return rango

    def agregar_ajustado(
        self, inicio: int, fin: int, nombre: str = ""
    ) -> tuple[RangoCalculo, bool]:
        """Agrega el tramo libre recorrido por el gesto del usuario.

        El primer punto actúa como ancla y el segundo indica la dirección. Si
        el ancla cae dentro de un rango existente, se desplaza al primer frame
        libre en esa dirección. Si el gesto encuentra otro rango, termina en
        el frame inmediatamente anterior. Los extremos son inclusivos.
        """
        inicio_original = int(inicio)
        fin_original = int(fin)
        if inicio_original == fin_original:
            raise ValueError("El rango debe contener al menos dos frames.")

        direccion = 1 if fin_original > inicio_original else -1
        inicio_ajustado = inicio_original
        rangos_ordenados = sorted(self._rangos, key=lambda rango: rango.desde)

        for existente in rangos_ordenados:
            if existente.desde <= inicio_original <= existente.hasta:
                inicio_ajustado = (
                    existente.hasta + 1
                    if direccion > 0
                    else existente.desde - 1
                )
                break

        if direccion > 0:
            if inicio_ajustado >= fin_original:
                raise ValueError(
                    "No queda un intervalo libre de al menos dos frames "
                    "en la dirección seleccionada."
                )
            fin_ajustado = fin_original
            for existente in rangos_ordenados:
                if existente.hasta < inicio_ajustado:
                    continue
                if existente.desde > fin_ajustado:
                    break
                fin_ajustado = existente.desde - 1
                break
        else:
            if inicio_ajustado <= fin_original:
                raise ValueError(
                    "No queda un intervalo libre de al menos dos frames "
                    "en la dirección seleccionada."
                )
            fin_ajustado = fin_original
            for existente in reversed(rangos_ordenados):
                if existente.desde > inicio_ajustado:
                    continue
                if existente.hasta < fin_ajustado:
                    break
                fin_ajustado = existente.hasta + 1
                break

        if inicio_ajustado == fin_ajustado:
            raise ValueError(
                "No queda un intervalo libre de al menos dos frames "
                "en la dirección seleccionada."
            )

        rango = self.agregar(inicio_ajustado, fin_ajustado, nombre)
        fue_ajustado = (
            inicio_ajustado != inicio_original or fin_ajustado != fin_original
        )
        return rango, fue_ajustado

    def eliminar(self, numeros) -> None:
        numeros = {int(numero) for numero in numeros}
        self._rangos = [rango for rango in self._rangos if rango.numero not in numeros]

    def limpiar(self) -> None:
        self._rangos.clear()
        self._siguiente_numero = 1
