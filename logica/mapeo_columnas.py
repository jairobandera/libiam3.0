class MapeoColumnas:
    """Maneja el mapeo de columnas del CSV a variables internas."""

    def __init__(self):
        self.mapeo_usuario = {}
        self.mapeo_automatico = {}
        self.ejes_activos = {}
        self.columnas_csv = []

    def inicializar(self, deteccion, columnas):
        """Inicializa el mapeo con la deteccion automatica y las columnas del CSV."""
        self.columnas_csv = list(columnas)
        self.mapeo_automatico = deteccion.get("mapeo", {})
        self.mapeo_usuario = {}
        self.ejes_activos = {}

        for tipo, ejes in self.mapeo_automatico.items():
            if isinstance(ejes, dict):
                for eje, columna in ejes.items():
                    self.ejes_activos[(tipo, eje)] = True

    def obtener_columnas_csv(self):
        """Retorna lista de todas las columnas del CSV."""
        return self.columnas_csv

    def obtener_tipos_detectados(self):
        """Retorna lista de tipos de datos detectados en el CSV."""
        return list(self.mapeo_automatico.keys())

    def obtener_ejes_para_tipo(self, tipo_dato):
        """Retorna los ejes disponibles para un tipo de dato."""
        mapeo = self.mapeo_automatico.get(tipo_dato, {})
        if isinstance(mapeo, dict):
            return mapeo
        return {}

    def obtener_columna_mapeada(self, tipo_dato, eje):
        """Retorna la columna mapeada para un tipo y eje.

        Prioriza la configuracion del usuario, sino usa la deteccion automatica.
        """
        clave = (tipo_dato, eje)

        if clave in self.mapeo_usuario:
            return self.mapeo_usuario[clave]

        ejes = self.mapeo_automatico.get(tipo_dato, {})
        if isinstance(ejes, dict):
            return ejes.get(eje)

        return None

    def aplicar_mapeo_usuario(self, tipo_dato, eje, columna):
        """Guarda la seleccion manual del usuario."""
        clave = (tipo_dato, eje)
        self.mapeo_usuario[clave] = columna

    def toggle_eje(self, tipo_dato, eje, activo):
        """Activa o desactiva un eje."""
        clave = (tipo_dato, eje)
        self.ejes_activos[clave] = activo

    def es_eje_activo(self, tipo_dato, eje):
        """Retorna True si el eje esta habilitado."""
        clave = (tipo_dato, eje)
        return self.ejes_activos.get(clave, True)

    def obtener_mapeo_completo(self):
        """Retorna el mapeo completo combinando automatico + usuario + ejes activos.

        Formato:
        {
            "Fuerza": {
                "eje_x": {"columna": "Fx_N", "activo": True},
                "eje_y": {"columna": "Fy_N", "activo": True},
            },
            ...
        }
        """
        resultado = {}

        for tipo, ejes in self.mapeo_automatico.items():
            if not isinstance(ejes, dict):
                continue

            resultado[tipo] = {}

            for eje, columna_auto in ejes.items():
                columna = self.mapeo_usuario.get((tipo, eje), columna_auto)
                activo = self.ejes_activos.get((tipo, eje), True)

                resultado[tipo][eje] = {
                    "columna": columna,
                    "activo": activo,
                }

        return resultado

    def resetear_mapeo(self):
        """Vuelve a la deteccion automatica."""
        self.mapeo_usuario = {}
