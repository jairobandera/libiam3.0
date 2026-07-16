import numpy as np
import pandas as pd
import pyqtgraph as pg

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

class ViewBoxZoom(pg.ViewBox):
    """ViewBox con zoom horizontal centrado en la posicion del cursor."""

    def wheelEvent(self, ev, axis=None):
        delta = ev.delta() if hasattr(ev, "delta") else ev.angleDelta().y()
        factor = 0.85 if delta > 0 else 1.15
        centro = self.mapSceneToView(ev.scenePos())
        self.scaleBy(x=factor, y=1.0, center=centro)
        ev.accept()


class GraficaSenal(pg.PlotWidget):
    rangoSeleccionado = Signal(object, str, object, object, float, float)

    #Deja el objeto listo para trabajar, inicializando todos los atributos que se necesitará mas adelante.
    def __init__(self, nombre_senal, parent=None):
        super().__init__(parent=parent, viewBox=ViewBoxZoom())
        self.nombre_senal = nombre_senal
        self.x = None
        self.y = None
        self.modo_seleccion_rango = False
        self.x_inicio = None
        self.linea_inicio = None
        self.linea_preview = None
        self.region_preview = None
        self.region_rango = None
        
        # Configuración inicial de la gráfica (como el tamaño, color de fondo, titulo, etc)
        self.setMinimumHeight(210)
        self.setBackground("#1E1E1E")
        self.setTitle(nombre_senal, color="#FFFFFF", size="11pt")
        self.setLabel("bottom", "Frame")
        self.setLabel("left", nombre_senal)
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setMouseEnabled(x=True, y=False)
        self.getViewBox().setMenuEnabled(False)
        self.scene().sigMouseClicked.connect(self._manejar_click)
        self.scene().sigMouseMoved.connect(self._manejar_mouse_movido)

    #Responsable de cargar los datos de la señal en la gráfica, limpiando cualquier selección previa y ajustando el rango de visualización.
    def set_datos(self, x, y):
        self.x = np.asarray(x, dtype=float)
        self.y = np.asarray(y, dtype=float)
        self.clear() #Deja grafica limpia
        #Reinicia variables.
        self.linea_inicio = None 
        self.linea_preview = None
        self.region_preview = None
        self.region_rango = None
        self.x_inicio = None

        self.plot(self.x, self.y, pen=pg.mkPen("#4FC3F7", width=1.5))
        self.enableAutoRange(axis="y", enable=True)
        self.autoRange()
    
    #Permite activar o desactivar el modo de selección de rango en la gráfica. Cuando está activo, el cursor cambia a una cruz y se pueden seleccionar rangos de datos haciendo clic y arrastrando. 
    #Si se desactiva, se limpia cualquier selección previa y se restablece el cursor a su estado normal.
    def set_modo_seleccion_rango(self, activo):
        self.modo_seleccion_rango = activo
        self.setCursor(Qt.CrossCursor if activo else Qt.ArrowCursor)
        if not activo:
            self.x_inicio = None
            self._limpiar_preview()
            if self.linea_inicio is not None:
                self.removeItem(self.linea_inicio)
                self.linea_inicio = None

    #Maneja el movimiento del mouse sobre la gráfica cuando el modo de selección de rango está activo. 
    #Si se ha iniciado una selección (es decir, si x_inicio no es None), calcula la posición actual del mouse en el eje x y actualiza la vista previa del rango seleccionado.
    def _manejar_mouse_movido(self, posicion):
        if not self.modo_seleccion_rango or self.x_inicio is None:
            return

        view_box = self.plotItem.vb
        if not view_box.sceneBoundingRect().contains(posicion):
            return

        x_actual = self._normalizar_x_click(float(view_box.mapSceneToView(posicion).x()))
        x_inicio = min(self.x_inicio, x_actual)
        x_fin = max(self.x_inicio, x_actual)
        self._mostrar_preview(x_inicio, x_fin, x_actual)

    #Maneja los clics del mouse sobre la gráfica cuando el modo de selección de rango está activo.
    def _manejar_click(self, event):
        if not self.modo_seleccion_rango or event.button() != Qt.LeftButton:
            return
        
        view_box = self.plotItem.vb
        if not view_box.sceneBoundingRect().contains(event.scenePos()):
            return

        x_click = self._normalizar_x_click(float(view_box.mapSceneToView(event.scenePos()).x()))
        if self.x is None or len(self.x) == 0:
            return

        if self.x_inicio is None:
            self._limpiar_rango()
            self.x_inicio = x_click
            self.linea_inicio = pg.InfiniteLine(
                pos=x_click,
                angle=90,
                movable=False,
                pen=pg.mkPen("#FFB74D", width=2),
            )
            self.addItem(self.linea_inicio)
            event.accept()
            return

        x_fin = x_click
        x_inicio = min(self.x_inicio, x_fin)
        x_fin = max(self.x_inicio, x_fin)
        self.x_inicio = None
        self._limpiar_preview()

        if x_inicio == x_fin:
            event.accept()
            return

        self._mostrar_rango(x_inicio, x_fin)
        self.rangoSeleccionado.emit(self, self.nombre_senal, self.x, self.y, x_inicio, x_fin)
        event.accept()

    #Verifica que el valor X para que nunca salga de los limites de la señal.
    def _normalizar_x_click(self, x_click):
        x_finito = self.x[np.isfinite(self.x)] if self.x is not None else np.array([])
        if len(x_finito) == 0:
            return x_click

        x_min = float(np.min(x_finito))
        if x_click < x_min:
            return x_min

        x_max = float(np.max(x_finito))
        if x_click > x_max:
            return x_max

        return x_click

    #Dibuja el rango definitivo seleccionado por el usuario sobre la gráfica
    #Dibuha la region transparente, dibuja las dos lineas verticales de los extremos, agrega esa region a la grafica.
    def _mostrar_rango(self, x_inicio, x_fin):
        self._limpiar_rango()
        self.region_rango = pg.LinearRegionItem(
            values=[x_inicio, x_fin],
            movable=False,
            brush=(25, 118, 210, 90),
        )
        self.region_rango.setZValue(-10)
        for linea in self.region_rango.lines:
            linea.setPen(pg.mkPen("#FFB74D", width=2))
        self.addItem(self.region_rango)

    #Muestra y actualiza la vista previa de la selección de rango mientras el usuario mueve el mouse después del primer clic. 
    #Dibuja una región semitransparente y una línea vertical punteada que sigue la posición actual del cursor.
    def _mostrar_preview(self, x_inicio, x_fin, x_actual):
        if self.region_preview is None:
            self.region_preview = pg.LinearRegionItem(
                values=[x_inicio, x_fin],
                movable=False,
                brush=(25, 118, 210, 45),
            )
            self.region_preview.setZValue(-20)
            for linea in self.region_preview.lines:
                linea.setPen(pg.mkPen("#64B5F6", width=1))
            self.addItem(self.region_preview)
        else:
            self.region_preview.setRegion([x_inicio, x_fin])

        if self.linea_preview is None:
            self.linea_preview = pg.InfiniteLine(
                pos=x_actual,
                angle=90,
                movable=False,
                pen=pg.mkPen("#64B5F6", width=1.5, style=Qt.DashLine),
            )
            self.addItem(self.linea_preview)
        else:
            self.linea_preview.setPos(x_actual)

    #Elimina de la gráfica todos los elementos temporales que se utilizan para mostrar la vista previa de una selección de rango.
    def _limpiar_preview(self):
        if self.linea_preview is not None:
            self.removeItem(self.linea_preview)
            self.linea_preview = None
        if self.region_preview is not None:
            self.removeItem(self.region_preview)
            self.region_preview = None

    #El método limpiar_seleccion_rango() elimina cualquier selección de rango existente y deja la gráfica preparada para comenzar una nueva selección desde cero.
    def limpiar_seleccion_rango(self):
        self.x_inicio = None
        self._limpiar_preview()
        self._limpiar_rango()

    #El método _limpiar_rango() elimina todos los elementos gráficos asociados a un rango seleccionado
    def _limpiar_rango(self):
        if self.linea_inicio is not None:
            self.removeItem(self.linea_inicio)
            self.linea_inicio = None
        self._limpiar_preview()
        if self.region_rango is not None:
            self.removeItem(self.region_rango)
            self.region_rango = None

    #NUEVO!
    #El método seleccionar_rango() permite seleccionar un rango de forma manual.
    def seleccionar_rango(self, x_inicio, x_fin):
        if self.x is None or len(self.x) == 0:
            return

        x_inicio = self._normalizar_x_click(x_inicio)
        x_fin = self._normalizar_x_click(x_fin)

        if x_inicio > x_fin:
            x_inicio, x_fin = x_fin, x_inicio

        if x_inicio == x_fin:
            return

        self._mostrar_rango(x_inicio, x_fin)

        self.rangoSeleccionado.emit(self,self.nombre_senal,self.x,self.y,x_inicio,x_fin)
#-----------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------
class VentanaRangoModal(QDialog):
    #Construir la ventana modal que muestra una visualización ampliada del rango seleccionado, preparando todos sus componentes (título, gráfica y botón de cierre).
    def __init__(self, nombre_senal, x, y, x_inicio, x_fin, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{nombre_senal} | Frame {x_inicio:.2f} - {x_fin:.2f}")
        self.setModal(True)
        self.resize(900, 520)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        titulo = QLabel(f"{nombre_senal} | Rango seleccionado")
        titulo.setStyleSheet("font-size: 15px; font-weight: 600; color: #FFFFFF;")
        layout.addWidget(titulo)

        x_rango, y_rango = self._recortar_rango(x, y, x_inicio, x_fin)

        grafica = pg.PlotWidget(viewBox=ViewBoxZoom())
        grafica.setBackground("#1E1E1E")
        grafica.setLabel("bottom", "Frame")
        grafica.setLabel("left", nombre_senal)
        grafica.showGrid(x=True, y=True, alpha=0.25)
        grafica.setMouseEnabled(x=True, y=False)
        grafica.getViewBox().setMenuEnabled(False)

        if len(x_rango) > 0:
            grafica.plot(x_rango, y_rango, pen=pg.mkPen("#4FC3F7", width=1.8))
            grafica.autoRange()
            grafica.setXRange(x_inicio, x_fin, padding=0)
            self._marcar_limites(grafica, x_inicio, x_fin)

        layout.addWidget(grafica, 1)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

        self.setLayout(layout)

    #Extraer los datos correspondientes al rango seleccionado, eliminando valores inválidos y asegurando que el rango incluya correctamente sus límites.
    def _recortar_rango(self, x, y, x_inicio, x_fin):
        mascara_finita = np.isfinite(x) & np.isfinite(y)
        x = x[mascara_finita]
        y = y[mascara_finita]

        if len(x) == 0:
            return x, y

        orden = np.argsort(x)
        x = x[orden]
        y = y[orden]

        mascara = (x >= x_inicio) & (x <= x_fin)
        x_rango = x[mascara]
        y_rango = y[mascara]

        puntos_x = []
        puntos_y = []
        x_min = float(x[0])
        x_max = float(x[-1])

        if x_min <= x_inicio <= x_max and not np.any(np.isclose(x_rango, x_inicio)):
            puntos_x.append(x_inicio)
            puntos_y.append(float(np.interp(x_inicio, x, y))) #IMPORTANTE: Interpolación lineal para obtener el valor de y correspondiente a x_inicio

        puntos_x.extend(x_rango.tolist())
        puntos_y.extend(y_rango.tolist())

        if x_min <= x_fin <= x_max and not np.any(np.isclose(x_rango, x_fin)):
            puntos_x.append(x_fin)
            puntos_y.append(float(np.interp(x_fin, x, y))) #IMPORTANTE: Interpolación lineal para obtener el valor de y correspondiente a x_fin

        if not puntos_x:
            return np.array([]), np.array([])

        orden_rango = np.argsort(puntos_x)
        return np.asarray(puntos_x)[orden_rango], np.asarray(puntos_y)[orden_rango]

    #Dibuja sobre la gráfica del diálogo una región sombreada que indica visualmente cuáles son los límites del rango seleccionado.
    def _marcar_limites(self, grafica, x_inicio, x_fin):
        region = pg.LinearRegionItem(
            values=[x_inicio, x_fin],
            movable=False,
            brush=(25, 118, 210, 45),
        )
        region.setZValue(-10)
        for linea in region.lines:
            linea.setPen(pg.mkPen("#FFB74D", width=2))
        grafica.addItem(region)
#------------------------------------------------------------------------------------------------------

#------------------------------------------------------------------------------------------------------
class AreaCentralGraficas(QFrame):
    # Su responsabilidad es inicializar todos los atributos que la clase necesitará para administrar las gráficas y luego llamar al método que construye la interfaz gráfica.
    def __init__(self):
        super().__init__()
        self.setObjectName("areaCentralGraficas")
        self.nombre_archivo = None
        self.df_original = None
        self.df_grafica = None
        self.columna_x = None
        self.mapeo_actual = None
        self.modo_seleccion_rango = False
        self.graficas = []
        self.graficas_por_columna = {}

        self._init_ui()

    # Su responsabilidad es construir la interfaz gráfica del área central, creando todos los componentes visuales (layouts, placeholder, área de scroll y contenedor de gráficas) y organizándolos dentro del QFrame.
    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        self.stack = QStackedWidget()

        self.placeholder = QWidget()
        layout_placeholder = QVBoxLayout()
        layout_placeholder.setContentsMargins(0, 0, 0, 0)
        layout_placeholder.addStretch()

        self.lbl_estado = QLabel("Carga un archivo .CSV para visualizar las senales")
        self.lbl_estado.setObjectName("estadoGraficas")
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        self.lbl_estado.setStyleSheet("color: #B0B0B0; font-size: 15px;")
        layout_placeholder.addWidget(self.lbl_estado)
        layout_placeholder.addStretch()
        self.placeholder.setLayout(layout_placeholder)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.contenedor = QWidget()
        self.layout_graficas = QVBoxLayout()
        self.layout_graficas.setContentsMargins(0, 0, 0, 0)
        self.layout_graficas.setSpacing(12)
        self.contenedor.setLayout(self.layout_graficas)
        self.scroll.setWidget(self.contenedor)

        self.stack.addWidget(self.placeholder)
        self.stack.addWidget(self.scroll)

        layout.addWidget(self.stack, 1)
        self.setLayout(layout)
      
    # Recibir el DataFrame cargado desde el CSV, prepararlo para ser graficado, obtener el mapeo de las señales, crear las gráficas y actualizar cuáles deben mostrarse al usuario
    def cargar_dataframe(self, nombre_archivo, df, info):
        print(f"[DEBUG] cargar_dataframe: archivo={nombre_archivo}")
        self.nombre_archivo = nombre_archivo
        self.df_original = df
        self.df_grafica, self.columna_x = self._preparar_dataframe(df)
        self.mapeo_actual = self._mapeo_desde_info(info)
        print(f"[DEBUG] cargar_dataframe: columna_x={self.columna_x}")
        print(f"[DEBUG] cargar_dataframe: mapeo_actual={self.mapeo_actual}")
        self._crear_graficas()
        self._actualizar_visibilidad()

    # Guardar el nuevo mapeo de señales y actualizar la visibilidad de las gráficas ya existentes.
    def actualizar_mapeo(self, mapeo):
        print(f"[DEBUG] actualizar_mapeo: recibido mapeo={mapeo}")
        self.mapeo_actual = mapeo
        if self.df_grafica is not None:
            print("[DEBUG] actualizar_mapeo: llamando a _actualizar_visibilidad")
            self._actualizar_visibilidad()
        else:
            print("[DEBUG] actualizar_mapeo: df_grafica es None, no se grafica")

    # Activar o desactivar el modo de selección de rango en todas las gráficas que existen en el área central.
    def set_modo_seleccion_rango(self, activo):
        self.modo_seleccion_rango = activo
        for grafica in self.graficas:
            grafica.set_modo_seleccion_rango(activo)

    # Es responsable de limpiar, adaptar y preparar el DataFrame para que pueda ser representado correctamente en las gráficas, determinando además cuál será la columna utilizada como eje X.
    def _preparar_dataframe(self, df):
        # Convertir columnas a numerico, forzando errores a NaN
        # Esto maneja cabeceras intercaladas que pandas lee como datos
        df = df.copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        frame_col = self._buscar_columna(df, "frame")
        subframe_col = self._buscar_columna(df, "subframe", "sub_frame") #Si cambia el nombre del encabezado? Si hay dos encabezados?

        if frame_col and subframe_col:
            columnas_numericas = list(df.select_dtypes(include=[np.number]).columns)
            columnas_promedio = [col for col in columnas_numericas if col != frame_col]
            if columnas_promedio:
                return df.groupby(frame_col, as_index=False)[columnas_promedio].mean(), frame_col #ACA PROMEDIO!!

        if frame_col:
            return df.copy(), frame_col

        tiempo_col = self._buscar_columna(df, "time", "time_s", "tiempo")
        if tiempo_col:
            return df.copy(), tiempo_col

        df_indice = df.copy()
        df_indice["Indice"] = np.arange(len(df_indice), dtype=float)
        return df_indice, "Indice"

    # Busca dentro del DataFrame una columna cuyo nombre coincida con alguno de los nombres recibidos como parámetro
    def _buscar_columna(self, df, *nombres):
        nombres_normalizados = {nombre.lower().strip() for nombre in nombres}
        for columna in df.columns:
            if str(columna).lower().strip() in nombres_normalizados:
                return columna
        return None

    # Transforma la información recibida desde el detector de cabeceras al formato que utiliza el sistema para gestionar qué señales existen y si deben mostrarse o no.
    def _mapeo_desde_info(self, info):
        deteccion = info.get("deteccion", {}) if info else {}
        mapeo = deteccion.get("mapeo", {})
        resultado = {}

        for tipo, ejes in mapeo.items():
            if not isinstance(ejes, dict):
                continue
            resultado[tipo] = {}
            for eje, columna in ejes.items():
                resultado[tipo][eje] = {"columna": columna, "activo": True}

        return resultado

    # Genera la lista de todas las columnas válidas del mapeo que pueden utilizarse para crear las gráficas.
    def _obtener_todas_columnas_mapeo(self):
        """Retorna todas las columnas del mapeo, sin importar si estan activas o no."""
        columnas = []
        if self.mapeo_actual:
            for ejes in self.mapeo_actual.values():
                if not isinstance(ejes, dict):
                    continue
                for config in ejes.values():
                    if isinstance(config, dict):
                        columna = config.get("columna")
                    else:
                        columna = config
                    if columna and columna not in columnas:
                        columnas.append(columna)

        columnas_validas = [
            col for col in columnas
            if col in self.df_grafica.columns and col != self.columna_x and self._es_numerica(col)
        ]
        return columnas_validas

    #Determina qué señales deben visualizarse actualmente según el estado del mapeo.
    def _obtener_columnas_a_graficar(self):
        """Retorna solo las columnas marcadas como activas en el mapeo."""
        columnas = []
        if self.mapeo_actual:
            for ejes in self.mapeo_actual.values():
                if not isinstance(ejes, dict):
                    continue
                for config in ejes.values():
                    if isinstance(config, dict):
                        columna = config.get("columna")
                        activo = config.get("activo", True)
                    else:
                        columna = config
                        activo = True
                    if activo and columna and columna not in columnas:
                        columnas.append(columna)

            columnas_validas = [
                col for col in columnas
                if col in self.df_grafica.columns and col != self.columna_x and self._es_numerica(col)
            ]
            return columnas_validas

        columnas_numericas = [
            col for col in self.df_grafica.select_dtypes(include=[np.number]).columns
            if col != self.columna_x and str(col).lower().strip() not in {"subframe", "sub_frame"}
        ]
        return columnas_numericas

    #Verificar si una columna del DataFrame contiene datos numéricos.
    def _es_numerica(self, columna):
        return np.issubdtype(self.df_grafica[columna].dtype, np.number)

    #Generar las etiquetas (títulos) que se mostrarán en las gráficas a partir del mapeo actual, asociando cada columna con su tipo de señal y eje correspondiente.
    def _obtener_labels_columnas(self):
        """Retorna un dict columna -> 'Tipo Eje' basado en el mapeo actual."""
        labels = {}
        if self.mapeo_actual:
            for tipo, ejes in self.mapeo_actual.items():
                if not isinstance(ejes, dict):
                    continue
                for eje, config in ejes.items():
                    if isinstance(config, dict):
                        columna = config.get("columna")
                    else:
                        columna = config
                    if columna:
                        eje_str = eje.replace("eje_", "").upper() if eje != "ninguno" else ""
                        if eje_str:
                            labels[columna] = f"{tipo} {eje_str}"
                        else:
                            labels[columna] = tipo
        return labels

    #Este método es el encargado de crear todas las gráficas a partir del DataFrame preparado. Se ejecuta cuando se carga un archivo CSV y genera una instancia de GraficaSenal para cada columna que deba visualizarse.
    def _crear_graficas(self):
        """Crea todas las grficas una sola vez al cargar el CSV."""
        print("[DEBUG] _crear_graficas: iniciando creacion")
        self._limpiar_graficas()

        if self.df_grafica is None or self.columna_x not in self.df_grafica.columns:
            print("[DEBUG] _crear_graficas: df_grafica None o columna_x no encontrada")
            self._mostrar_placeholder("No hay datos disponibles para graficar.")
            return

        columnas = self._obtener_todas_columnas_mapeo()
        print(f"[DEBUG] _crear_graficas: columnas del mapeo={columnas}")
        if not columnas:
            columnas = [
                col for col in self.df_grafica.select_dtypes(include=[np.number]).columns
                if col != self.columna_x and str(col).lower().strip() not in {"subframe", "sub_frame"}
            ]
            print(f"[DEBUG] _crear_graficas: fallback columnas numericas={columnas}")

        if not columnas:
            print("[DEBUG] _crear_graficas: no hay columnas, mostrando placeholder")
            self._mostrar_placeholder("No se encontraron columnas numericas para graficar.")
            return

        self.stack.setCurrentWidget(self.scroll)

        labels = self._obtener_labels_columnas()
        x = self.df_grafica[self.columna_x].to_numpy(dtype=float)
        for columna in columnas:
            y = self.df_grafica[columna].to_numpy(dtype=float)
            mascara = np.isfinite(x) & np.isfinite(y)
            if not mascara.any():
                print(f"[DEBUG] _crear_graficas: columna {columna} sin datos validos, saltando")
                continue

            label = labels.get(columna)
            titulo = f"{label} - {columna}" if label else str(columna)
            grafica = GraficaSenal(titulo)
            grafica.set_datos(x[mascara], y[mascara])
            grafica.set_modo_seleccion_rango(self.modo_seleccion_rango)
            grafica.rangoSeleccionado.connect(self._abrir_rango_modal)
            self.layout_graficas.addWidget(grafica)
            self.graficas.append(grafica)
            self.graficas_por_columna[columna] = grafica
            print(f"[DEBUG] _crear_graficas: grafica creada para columna={columna}, titulo={titulo}")

        self.layout_graficas.addStretch()
        print(f"[DEBUG] _crear_graficas: fin. graficas_por_columna={list(self.graficas_por_columna.keys())}")

    # El método _actualizar_visibilidad() recorre todas las gráficas que ya fueron creadas y decide si cada una debe mostrarse o esconderse de acuerdo con las columnas que están activas en el mapeo.
    def _actualizar_visibilidad(self):
        """Muestra u oculta las graficas existentes segun el mapeo actual."""
        print(f"[DEBUG] _actualizar_visibilidad: graficas_por_columna={list(self.graficas_por_columna.keys())}")
        if not self.graficas_por_columna:
            print("[DEBUG] _actualizar_visibilidad: no hay graficas creadas, saliendo")
            return

        columnas_activas = set(self._obtener_columnas_a_graficar())
        print(f"[DEBUG] _actualizar_visibilidad: columnas_activas={columnas_activas}")

        hay_visibles = False
        for columna, grafica in self.graficas_por_columna.items():
            visible = columna in columnas_activas
            print(f"[DEBUG] _actualizar_visibilidad: columna={columna}, visible={visible}")
            grafica.setVisible(visible)
            if visible:
                hay_visibles = True

        if hay_visibles:
            print("[DEBUG] _actualizar_visibilidad: hay graficas visibles, mostrando scroll")
            self.stack.setCurrentWidget(self.scroll)
        else:
            print("[DEBUG] _actualizar_visibilidad: ninguna visible, mostrando placeholder")
            self._mostrar_placeholder("No hay columnas activas para graficar.")

    #Eliminar todas las gráficas existentes y limpiar las estructuras de datos asociadas, dejando el área de gráficos preparada para cargar un nuevo conjunto de señales.
    def _limpiar_graficas(self):
        self.graficas = []
        self.graficas_por_columna = {}
        while self.layout_graficas.count():
            item = self.layout_graficas.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    #Cambia el texto del mensaje informativo y muestra la pantalla de espera (placeholder) en lugar del área donde normalmente se muestran las gráficas.
    def _mostrar_placeholder(self, texto):
        self.lbl_estado.setText(texto)
        self.stack.setCurrentWidget(self.placeholder)

    #Crea y muestra la ventana emergente que contiene la gráfica ampliada del rango seleccionado. Cuando el usuario cierra esa ventana, elimina la selección realizada sobre la gráfica original.
    def _abrir_rango_modal(self, grafica_senal, nombre_senal, x, y, x_inicio, x_fin):
        ventana = VentanaRangoModal(nombre_senal, x, y, x_inicio, x_fin, self)
        ventana.exec()
        grafica_senal.limpiar_seleccion_rango()

    #NUEVOOO
    #Busca la gráfica correspondiente a una señal determinada y le indica que seleccione un rango utilizando los valores ingresados manualmente.
    def seleccionar_rango_manual(self, categoria, senal, desde, hasta):

        if self.mapeo_actual is None:
            return

        if categoria not in self.mapeo_actual:
            return

        eje = f"eje_{senal[-1].lower()}"

        config = self.mapeo_actual[categoria].get(eje)

        if config is None:
            return

        columna = config["columna"]

        grafica = self.graficas_por_columna.get(columna)

        if grafica is None:
            return

        grafica.seleccionar_rango(desde, hasta)
#---------------------------------------