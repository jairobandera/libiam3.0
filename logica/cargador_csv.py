import os
import re
import pandas as pd
import numpy as np
from PySide6.QtWidgets import QFileDialog

from logica.config_db import cargar_aliases, buscar_alias, listar_secciones_archivo


class CargadorCSV:
    """Maneja la carga y lectura de archivos CSV."""

    def __init__(self, parent=None, db_session=None):
        self.parent = parent
        self.db_session = db_session
        self.ruta_archivo_actual = None

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
        self.ruta_archivo_actual = ruta_archivo

        return nombre_archivo, df, ruta_archivo

    def parsear_csv_con_secciones(self, ruta_archivo, secciones):
        """Parsea un CSV con múltiples secciones de cabeceras.

        secciones = [
            {"fila_inicio": 51, "fila_fin": 100, "columnas": ["COPx", "COPy"]},
        ]

        Si la fila 0 no está cubierta por ninguna sección, se agrega automáticamente
        como sección implícita con las columnas originales del CSV.

        Retorna un DataFrame unificado con todas las columnas de todas las secciones.
        """
        if not secciones:
            return pd.read_csv(ruta_archivo, sep=None, engine="python")

        # Leer el CSV completo como texto para poder acceder por filas
        df_raw = pd.read_csv(ruta_archivo, sep=None, engine="python", header=None)

        # Verificar si la fila 0 está cubierta por alguna sección
        fila_0_cubierta = any(sec["fila_inicio"] == 0 for sec in secciones)

        secciones_completas = list(secciones)

        # Si la fila 0 no está cubierta, agregar sección implícita con columnas originales
        if not fila_0_cubierta:
            # Encontrar hasta dónde llega la primera sección marcada
            primera_seccion_inicio = min(sec["fila_inicio"] for sec in secciones)

            # Extraer columnas originales de la fila 0
            columnas_originales = []
            for col in range(len(df_raw.columns)):
                valor = str(df_raw.iloc[0, col]).strip()
                if valor:
                    columnas_originales.append(valor)

            if columnas_originales:
                secciones_completas.insert(0, {
                    "fila_inicio": 0,
                    "fila_fin": primera_seccion_inicio - 1,
                    "columnas": columnas_originales,
                })

        sub_dataframes = []

        for sec in secciones_completas:
            fila_inicio = sec["fila_inicio"]
            fila_fin = sec["fila_fin"]
            columnas = sec["columnas"]

            # Extraer datos de la sección (saltando la fila de cabecera)
            datos = df_raw.iloc[fila_inicio + 1:fila_fin + 1]

            # Crear sub-DataFrame con las columnas de la sección
            sub_df = pd.DataFrame()
            for i, col_nombre in enumerate(columnas):
                if i < len(datos.columns):
                    sub_df[col_nombre] = datos.iloc[:, i].values

            sub_dataframes.append(sub_df)

        # Unir todos los sub-DataFrames
        if sub_dataframes:
            df_unificado = pd.concat(sub_dataframes, ignore_index=True)
            return df_unificado

        return pd.DataFrame()

    def escanear_cabeceras(self, df):
        """Escanea todas las filas del DataFrame buscando filas que parecen cabeceras.

        Una fila se considera cabecera si la mayoria de sus celdas son texto
        (pueden contener numeros como Fx1, pero no son puramente numericas).

        Retorna una lista de nombres de columna unicos encontrados en todo el archivo.
        """
        cabeceras_encontradas = set()

        for _, fila in df.iterrows():
            celdas_texto = 0
            celdas_total = len(fila)

            for valor in fila:
                if pd.isna(valor):
                    continue
                str_val = str(valor).strip()
                if not str_val:
                    continue
                # Verificar si la celda parece texto (no es puramente numerica)
                try:
                    float(str_val)
                    # Es numerico puro
                except ValueError:
                    # Contiene texto (puede tener numeros como Fx1)
                    celdas_texto += 1

            # Si la mayoria son texto, es una fila de cabecera
            if celdas_texto > celdas_total / 2:
                for valor in fila:
                    if pd.isna(valor):
                        continue
                    str_val = str(valor).strip()
                    if str_val:
                        cabeceras_encontradas.add(str_val)

        return list(cabeceras_encontradas)

    def detectar_tipos_datos(self, df, cabeceras_extra=None):
        """Detecta que tipos de datos biomecanicos estan presentes en las columnas.

        Primero hace match exacto contra la BD, luego intenta con patrones.
        Retorna un diccionario con los tipos detectados, el mapeo de columnas
        y las columnas no reconocidas.
        """
        columnas_originales = list(df.columns)
        columnas_df_set = set(columnas_originales)

        aliases_db = cargar_aliases(self.db_session) if self.db_session else {}

        tipos_presentes = []
        mapeo = {}
        no_reconocidas = []

        for col in columnas_originales:
            col_lower = col.lower().strip()
            encontrado = False

            # 1. Match exacto contra BD
            alias_info = buscar_alias(self.db_session, col) if self.db_session else None
            if alias_info:
                tipo = alias_info["tipo"]
                eje = alias_info["eje"]

                if tipo not in tipos_presentes:
                    tipos_presentes.append(tipo)

                if tipo not in mapeo:
                    mapeo[tipo] = {}

                if eje != "ninguno":
                    mapeo[tipo][eje] = col
                else:
                    mapeo[tipo] = col

                encontrado = True

            # 2. Fallback: buscar en aliases por tipo
            if not encontrado and self.db_session:
                for tipo, ejes in aliases_db.items():
                    if isinstance(ejes, dict):
                        for eje, nombres in ejes.items():
                            if eje == "_simple":
                                continue
                            for nombre in nombres:
                                if col_lower == nombre or col_lower.startswith(nombre):
                                    if tipo not in tipos_presentes:
                                        tipos_presentes.append(tipo)
                                    if tipo not in mapeo:
                                        mapeo[tipo] = {}
                                    mapeo[tipo][eje] = col
                                    encontrado = True
                                    break
                            if encontrado:
                                break
                    if encontrado:
                        break

            if not encontrado:
                no_reconocidas.append(col)

        # Detectar cabeceras extra que no son columnas del DataFrame
        cabeceras_extra_detectadas = []
        if cabeceras_extra:
            for cab in cabeceras_extra:
                if cab not in columnas_df_set:
                    cab_lower = cab.lower().strip()
                    alias_info = buscar_alias(self.db_session, cab) if self.db_session else None
                    if alias_info:
                        cabeceras_extra_detectadas.append({
                            "nombre": cab,
                            "tipo": alias_info["tipo"],
                            "eje": alias_info["eje"],
                        })

        return {
            "tipos_presentes": tipos_presentes,
            "mapeo": mapeo,
            "no_reconocidas": no_reconocidas,
            "cabeceras_extra": cabeceras_extra_detectadas,
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
        cabeceras = self.escanear_cabeceras(df)
        deteccion = self.detectar_tipos_datos(df, cabeceras_extra=cabeceras)
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
            "cabeceras_encontradas": cabeceras,
        }
