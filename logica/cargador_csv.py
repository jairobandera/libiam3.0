import os
import re
import pandas as pd
from PySide6.QtWidgets import QFileDialog


# Patrones para detectar tipos de datos biomecánicos en los nombres de columnas.
# Cada tipo tiene sub-patrones por eje (x, y, z) para detectar cuales ejes estan presentes.
PATRONES_BIOMECANICOS = {
    "Fuerza": {
        "eje_x": [r"fx", r"force[_\s]?x", r"fuerza[_\s]?x", r"force[_\s]?1", r"fuerza[_\s]?1", r"fx\d*"],
        "eje_y": [r"fy", r"force[_\s]?y", r"fuerza[_\s]?y", r"force[_\s]?2", r"fuerza[_\s]?2", r"fy\d*"],
        "eje_z": [r"fz", r"force[_\s]?z", r"fuerza[_\s]?z", r"force[_\s]?3", r"fuerza[_\s]?3", r"fz\d*"],
    },
    "Momento": {
        "eje_x": [r"mx", r"moment[_\s]?x", r"momento[_\s]?x", r"torque[_\s]?x"],
        "eje_y": [r"my", r"moment[_\s]?y", r"momento[_\s]?y", r"torque[_\s]?y"],
        "eje_z": [r"mz", r"moment[_\s]?z", r"momento[_\s]?z", r"torque[_\s]?z"],
    },
    "COP": {
        "eje_x": [r"copx", r"cop[_\s]?x", r"centro[_\s]?presion[_\s]?x", r"center[_\s]?pressure[_\s]?x"],
        "eje_y": [r"copy", r"cop[_\s]?y", r"centro[_\s]?presion[_\s]?y", r"center[_\s]?pressure[_\s]?y"],
        "eje_z": [r"copz", r"cop[_\s]?z", r"centro[_\s]?presion[_\s]?z", r"center[_\s]?pressure[_\s]?z"],
    },
    "Tiempo": [r"time", r"tiempo", r"t[_\s]?s", r"timestamp"],
    "Frame": [r"frame", r"muestra", r"sample", r"n[_\s]?frame"],
}


class CargadorCSV:
    """Maneja la carga y lectura de archivos CSV."""

    def __init__(self, parent=None):
        self.parent = parent

    def seleccionar_y_cargar(self):
        """Abre dialogo de seleccion y carga el CSV.

        Retorna una tupla (nombre_archivo, dataframe) o (None, None) si se cancela.
        """
        ruta_archivo, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Seleccionar archivo CSV",
            "",
            "Archivos CSV (*.csv);;Todos los archivos (*)"
        )

        if not ruta_archivo:
            return None, None

        nombre_archivo = os.path.basename(ruta_archivo)
        df = pd.read_csv(ruta_archivo, sep=None, engine="python")

        return nombre_archivo, df

    def detectar_tipos_datos(self, df):
        """Detecta que tipos de datos biomecánicos estan presentes en las columnas.

        Retorna un diccionario con los tipos detectados y el mapeo de columnas.
        """
        columnas = [col.lower().strip() for col in df.columns]

        tipos_presentes = []
        mapeo = {}

        for tipo, patrones in PATRONES_BIOMECANICOS.items():

            # Si el tipo tiene sub-ejes (Fuerza, Momento, COP)
            if isinstance(patrones, dict):
                ejes_detectados = {}

                for eje, lista_patrones in patrones.items():
                    for patron in lista_patrones:
                        for i, col in enumerate(columnas):
                            if re.search(patron, col, re.IGNORECASE):
                                # Guardar el nombre original de la columna
                                ejes_detectados[eje] = df.columns[i]
                                break
                        if eje in ejes_detectados:
                            break

                if ejes_detectados:
                    tipos_presentes.append(tipo)
                    mapeo[tipo] = ejes_detectados

            # Si el tipo es simple (Tiempo, Frame)
            else:
                for patron in patrones:
                    for i, col in enumerate(columnas):
                        if re.search(patron, col, re.IGNORECASE):
                            tipos_presentes.append(tipo)
                            mapeo[tipo] = df.columns[i]
                            break
                    if tipo in tipos_presentes:
                        break

        return {
            "tipos_presentes": tipos_presentes,
            "mapeo": mapeo,
        }

    def detectar_subframes(self, df):
        """Detecta si el CSV tiene estructura de subframes."""
        for col in df.columns:
            col_lower = col.lower().strip()
            if "subframe" in col_lower or "sub_frame" in col_lower:
                cantidad_unica = df[col].nunique()
                max_por_frame = df.groupby("Frame")[col].nunique().max() if "Frame" in df.columns else cantidad_unica
                return {
                    "tiene_subframes": True,
                    "columna": col,
                    "cantidad_unica": int(cantidad_unica),
                    "max_por_frame": int(max_por_frame),
                }

        return {"tiene_subframes": False}

    def obtener_info(self, nombre_archivo, df):
        """Retorna un diccionario con la informacion del archivo cargado."""
        deteccion = self.detectar_tipos_datos(df)
        subframes = self.detectar_subframes(df)

        tipos_str = ", ".join(deteccion["tipos_presentes"]) if deteccion["tipos_presentes"] else "Sin reconocer"

        # Info de subframes para mostrar en UI
        if subframes["tiene_subframes"]:
            subframe_info = f"Si (max {subframes['max_por_frame']} por frame)"
        else:
            subframe_info = "No"

        return {
            "nombre": nombre_archivo,
            "columnas": len(df.columns),
            "tipo_datos": tipos_str,
            "registros": len(df),
            "tiene_subframes": subframe_info,
            "deteccion": deteccion,
            "subframes": subframes,
        }
