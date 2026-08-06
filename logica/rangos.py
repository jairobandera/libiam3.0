"""Modelo independiente de la interfaz para los rangos de cálculo."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from logica import paleta


# Los colores salen de la paleta activa (ver ``logica/paleta.py``), que cambia
# si se activa el modo daltónico. Se sigue exportando el nombre histórico para
# los usos que solo necesitan la lista estándar.
COLORES_RANGOS = paleta.PALETAS[paleta.MODO_ESTANDAR]["rangos"]


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
    """Colección de rangos de una señal.

    ``prefijo_nombre`` es cómo se llaman los rangos sin nombre propio. Los
    sub-gestores usan «Sub-rango» para que se distingan del rango que los
    contiene en el panel, en las notas y en el archivo de anotaciones.
    """

    def __init__(self, prefijo_nombre: str = "Rango"):
        self._rangos: list[RangoCalculo] = []
        self._siguiente_numero = 1
        self._prefijo_nombre = prefijo_nombre

    def listar(self) -> list[RangoCalculo]:
        return list(self._rangos)

    def hay_superposicion(self, desde: int, hasta: int) -> bool:
        """Indica si el intervalo se superpone con algún rango existente."""
        desde, hasta = sorted((int(desde), int(hasta)))
        return any(
            desde <= existente.hasta and hasta >= existente.desde
            for existente in self._rangos
        )

    def agregar(
        self,
        desde: int,
        hasta: int,
        nombre: str = "",
        permitir_superposicion: bool = False,
    ) -> RangoCalculo:
        desde, hasta = sorted((int(desde), int(hasta)))
        if desde == hasta:
            raise ValueError("El rango debe contener al menos dos frames.")

        if not permitir_superposicion:
            for existente in self._rangos:
                # Los extremos son inclusivos: compartir un frame también cuenta
                # como superposición para evitar duplicarlo en los cálculos.
                if desde <= existente.hasta and hasta >= existente.desde:
                    raise RangoSuperpuestoError(existente)

        numero = self._siguiente_numero
        color = paleta.color_rango(numero)
        nombre = nombre.strip() or f"{self._prefijo_nombre} {numero}"
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

    def restaurar(
        self, numero: int, desde: int, hasta: int, nombre: str = ""
    ) -> RangoCalculo:
        """Reinserta un rango ya existente conservando su número original.

        Se usa al abrir un proyecto guardado: los rangos vienen del archivo de
        anotaciones, así que no se renumeran ni se revalida la superposición
        (ya se decidió cuando se crearon). El color se deriva del número, igual
        que en ``agregar``, para que el proyecto se vea igual que al guardarlo.
        """
        numero = int(numero)
        if numero < 1:
            raise ValueError("El número de rango debe ser mayor o igual a 1.")

        desde, hasta = sorted((int(desde), int(hasta)))
        if desde == hasta:
            raise ValueError("El rango debe contener al menos dos frames.")

        color = paleta.color_rango(numero)
        nombre = (nombre or "").strip() or f"{self._prefijo_nombre} {numero}"
        rango = RangoCalculo(
            numero=numero, desde=desde, hasta=hasta, color=color, nombre=nombre
        )

        self._rangos = [
            existente for existente in self._rangos if existente.numero != numero
        ]
        self._rangos.append(rango)
        self._rangos.sort(key=lambda existente: existente.numero)
        self._siguiente_numero = max(self._siguiente_numero, numero + 1)
        return rango

    def eliminar(self, numeros) -> None:
        numeros = {int(numero) for numero in numeros}
        self._rangos = [rango for rango in self._rangos if rango.numero not in numeros]

    def recolorear(self) -> None:
        """Reasigna los colores de todos los rangos según la paleta activa.

        Se llama al prender o apagar el modo daltónico. Como el color depende
        solo del número del rango, apagar el modo devuelve exactamente los
        colores anteriores.
        """
        self._rangos = [
            replace(rango, color=paleta.color_rango(rango.numero))
            for rango in self._rangos
        ]

    def limpiar(self) -> None:
        self._rangos.clear()
        self._siguiente_numero = 1
