"""Modelo independiente de la interfaz para los intervalos de cálculo."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from logica import paleta


# Los colores salen de la paleta activa (ver ``logica/paleta.py``), que cambia
# si se activa el modo daltónico. Se sigue exportando el nombre histórico para
# los usos que solo necesitan la lista estándar.
COLORES_INTERVALOS = paleta.PALETAS[paleta.MODO_ESTANDAR]["intervalos"]


class IntervaloSuperpuestoError(ValueError):
    def __init__(self, intervalo_existente):
        self.intervalo_existente = intervalo_existente
        numero_visible = intervalo_existente.orden or intervalo_existente.numero
        super().__init__(
            f"El intervalo se superpone con el intervalo {numero_visible} "
            f"({intervalo_existente.desde}–{intervalo_existente.hasta})."
        )


@dataclass(frozen=True)
class IntervaloCalculo:
    numero: int
    desde: int
    hasta: int
    color: str
    nombre: str = ""
    # ``numero`` es la identidad interna estable. ``orden`` es la posición
    # visible de izquierda a derecha y puede cambiar al agregar otro recorte.
    orden: int = 0
    nombre_personalizado: bool = False
    # Cuando varios intervalos nacen de una misma réplica, comparten este
    # índice de paleta aunque cada gráfica tenga un orden diferente.
    indice_color: int = 0

    def como_dict(self) -> dict:
        return asdict(self)


class GestorIntervalos:
    """Colección de intervalos de una señal.

    ``prefijo_nombre`` es cómo se llaman los intervalos sin nombre propio. Los
    sub-gestores usan «Sub-intervalo» para que se distingan del intervalo que los
    contiene en el panel, en las notas y en el archivo de anotaciones.
    """

    def __init__(self, prefijo_nombre: str = "Intervalo"):
        self._intervalos: list[IntervaloCalculo] = []
        self._siguiente_numero = 1
        self._prefijo_nombre = prefijo_nombre

    def listar(self) -> list[IntervaloCalculo]:
        """Devuelve los intervalos ordenados y numerados de izquierda a derecha.

        La identidad interna (``numero``) no cambia. Esto permite reordenar lo
        que ve el usuario sin romper notas, sub-intervalos ni botones que ya
        apuntan al recorte. Los nombres automáticos y los colores normales
        siguen la posición visible; los replicados conservan su índice de color
        compartido y los nombres escritos por el usuario se mantienen.
        """
        ordenados = sorted(
            self._intervalos,
            key=lambda intervalo: (intervalo.desde, intervalo.hasta, intervalo.numero),
        )
        resultado = []
        for orden, intervalo in enumerate(ordenados, start=1):
            nombre = (
                intervalo.nombre
                if intervalo.nombre_personalizado
                else f"{self._prefijo_nombre} {orden}"
            )
            resultado.append(
                replace(
                    intervalo,
                    orden=orden,
                    color=paleta.color_intervalo(
                        intervalo.indice_color or orden
                    ),
                    nombre=nombre,
                )
            )
        return resultado

    def _intervalo_visible(self, numero: int) -> IntervaloCalculo | None:
        return next(
            (intervalo for intervalo in self.listar() if intervalo.numero == int(numero)),
            None,
        )

    def hay_superposicion(self, desde: int, hasta: int) -> bool:
        """Indica si el intervalo se superpone con algún intervalo existente."""
        desde, hasta = sorted((int(desde), int(hasta)))
        return any(
            desde <= existente.hasta and hasta >= existente.desde
            for existente in self._intervalos
        )

    def agregar(
        self,
        desde: int,
        hasta: int,
        nombre: str = "",
        permitir_superposicion: bool = False,
        indice_color: int | None = None,
    ) -> IntervaloCalculo:
        desde, hasta = sorted((int(desde), int(hasta)))
        if desde == hasta:
            raise ValueError("El intervalo debe contener al menos dos frames.")

        if not permitir_superposicion:
            for existente in self._intervalos:
                # Los extremos son inclusivos: compartir un frame también cuenta
                # como superposición para evitar duplicarlo en los cálculos.
                if desde <= existente.hasta and hasta >= existente.desde:
                    raise IntervaloSuperpuestoError(
                        self._intervalo_visible(existente.numero) or existente
                    )

        numero = self._siguiente_numero
        try:
            indice_color = int(indice_color or 0)
        except (TypeError, ValueError):
            indice_color = 0
        indice_color = indice_color if indice_color > 0 else 0
        color = paleta.color_intervalo(indice_color or numero)
        nombre = nombre.strip()
        nombre_personalizado = bool(nombre)
        nombre = nombre or f"{self._prefijo_nombre} {numero}"
        intervalo = IntervaloCalculo(
            numero=numero,
            desde=desde,
            hasta=hasta,
            color=color,
            nombre=nombre,
            orden=numero,
            nombre_personalizado=nombre_personalizado,
            indice_color=indice_color,
        )
        self._intervalos.append(intervalo)
        self._siguiente_numero += 1
        return intervalo

    def agregar_ajustado(
        self,
        inicio: int,
        fin: int,
        nombre: str = "",
        indice_color: int | None = None,
    ) -> tuple[IntervaloCalculo, bool]:
        """Agrega el tramo libre recorrido por el gesto del usuario.

        El primer punto actúa como ancla y el segundo indica la dirección. Si
        el ancla cae dentro de un intervalo existente, se desplaza al primer frame
        libre en esa dirección. Si el gesto encuentra otro intervalo, termina en
        el frame inmediatamente anterior. Los extremos son inclusivos.
        """
        inicio_original = int(inicio)
        fin_original = int(fin)
        if inicio_original == fin_original:
            raise ValueError("El intervalo debe contener al menos dos frames.")

        direccion = 1 if fin_original > inicio_original else -1
        inicio_ajustado = inicio_original
        intervalos_ordenados = sorted(self._intervalos, key=lambda intervalo: intervalo.desde)

        for existente in intervalos_ordenados:
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
            for existente in intervalos_ordenados:
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
            for existente in reversed(intervalos_ordenados):
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

        intervalo = self.agregar(
            inicio_ajustado,
            fin_ajustado,
            nombre,
            indice_color=indice_color,
        )
        fue_ajustado = (
            inicio_ajustado != inicio_original or fin_ajustado != fin_original
        )
        return intervalo, fue_ajustado

    def restaurar(
        self,
        numero: int,
        desde: int,
        hasta: int,
        nombre: str = "",
        indice_color: int | None = None,
    ) -> IntervaloCalculo:
        """Reinserta un intervalo ya existente conservando su número original.

        Se usa al abrir un proyecto guardado: los intervalos vienen del archivo de
        anotaciones, así que no se renumeran ni se revalida la superposición
        (ya se decidió cuando se crearon). Si existe un índice de color
        compartido también se restaura; los proyectos anteriores derivan el
        color del número como antes.
        """
        numero = int(numero)
        if numero < 1:
            raise ValueError("El número de intervalo debe ser mayor o igual a 1.")

        desde, hasta = sorted((int(desde), int(hasta)))
        if desde == hasta:
            raise ValueError("El intervalo debe contener al menos dos frames.")

        try:
            indice_color = int(indice_color or 0)
        except (TypeError, ValueError):
            indice_color = 0
        indice_color = indice_color if indice_color > 0 else 0
        color = paleta.color_intervalo(indice_color or numero)
        nombre = (nombre or "").strip()
        nombre_personalizado = bool(nombre) and nombre != (
            f"{self._prefijo_nombre} {numero}"
        )
        nombre = nombre or f"{self._prefijo_nombre} {numero}"
        intervalo = IntervaloCalculo(
            numero=numero,
            desde=desde,
            hasta=hasta,
            color=color,
            nombre=nombre,
            orden=numero,
            nombre_personalizado=nombre_personalizado,
            indice_color=indice_color,
        )

        self._intervalos = [
            existente for existente in self._intervalos if existente.numero != numero
        ]
        self._intervalos.append(intervalo)
        self._intervalos.sort(
            key=lambda existente: (
                existente.desde,
                existente.hasta,
                existente.numero,
            )
        )
        self._siguiente_numero = max(self._siguiente_numero, numero + 1)
        return intervalo

    def eliminar(self, numeros) -> None:
        numeros = {int(numero) for numero in numeros}
        self._intervalos = [intervalo for intervalo in self._intervalos if intervalo.numero not in numeros]

    def recolorear(self) -> None:
        """Reasigna los colores de todos los intervalos según la paleta activa.

        Se llama al prender o apagar el modo daltónico. Los intervalos
        replicados conservan su índice compartido al cambiar de paleta.
        """
        self._intervalos = [
            replace(
                intervalo,
                color=paleta.color_intervalo(
                    intervalo.indice_color or intervalo.numero
                ),
            )
            for intervalo in self._intervalos
        ]

    def limpiar(self) -> None:
        self._intervalos.clear()
        self._siguiente_numero = 1
