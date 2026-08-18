import os
import shutil

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from ui.cabecera.cabeceraPrincipal.cabecera import Cabecera
from ui.cabecera.cabeceraPrincipal.cargarProyecto import CargarProyectoDialog
from ui.cabecera.cabeceraPrincipal.exportar import (
    ExportarDialog,
    ExportacionCompletadaDialog,
)
from ui.cabecera.subCabecera.seleccionarRango import SeleccionarRango

from ui.ventanaPrincipal.areaCentralGraficas import AreaCentralGraficas
from ui.ventanaPrincipal.panelizquierdo import PanelIzquierdo
from ui.ventanaPrincipal.panelDerecho.panelDerecho import PanelDerecho
from ui.ventanaPrincipal.barraBotones import BarraBotones
from logica import app_info, exportacion, proyecto


class VentanaPrincipal(QWidget):

    def __init__(self, db_session=None):
        super().__init__()

        self.db_session = db_session
        self.setWindowTitle(app_info.NOMBRE)
        self.resize(1600, 900)

        self.init_ui()

    def init_ui(self):

        # Layout principal vertical
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Cabecera principal
        self.cabecera = Cabecera()
        layout.addWidget(self.cabecera)

        # Subcabecera
        self.subcabecera = SeleccionarRango()
        layout.addWidget(self.subcabecera)

        # Layout horizontal para el contenido principal
        layout_contenido = QHBoxLayout()
        layout_contenido.setContentsMargins(0, 0, 0, 0)
        layout_contenido.setSpacing(0)

        # Panel izquierdo
        self.panel_izquierdo = PanelIzquierdo(db_session=self.db_session)
        layout_contenido.addWidget(self.panel_izquierdo)

        # Área central de gráficas
        self.area_central = AreaCentralGraficas()
        layout_contenido.addWidget(self.area_central, 1)

        # Panel derecho colapsable
        self.panel_derecho = PanelDerecho(db_session=self.db_session)
        layout_contenido.addWidget(self.panel_derecho)

        # Barra de botones derecha
        self.barra_botones = BarraBotones(self.panel_derecho)
        layout_contenido.addWidget(self.barra_botones)

        layout.addLayout(layout_contenido)

        self.setLayout(layout)

        # Conectar la configuración de la cabecera con el área de gráficas
        self.cabecera.superposicionRangosCambiada.connect(
            self.area_central.set_superposicion_habilitada
        )
        self.cabecera.noPreguntarSuperposicionCambiada.connect(
            self.area_central.set_no_preguntar_superposicion
        )
        # El área central repinta con la paleta que ya sincronizó
        # «logica.accesibilidad»; los paneles que muestran esos colores
        # (leyenda de filtros) se refrescan después.
        self.cabecera.accesibilidadCambiada.connect(
            self.area_central.aplicar_accesibilidad
        )
        self.cabecera.accesibilidadCambiada.connect(
            lambda: self.panel_derecho.filtros.aplicar_paleta()
        )
        self.cabecera.guardarSolicitado.connect(self._guardar_proyecto)
        self.cabecera.cargarSolicitado.connect(self._cargar_proyecto)
        self.cabecera.exportarSolicitado.connect(self._exportar)

        # Conectar panel izquierdo con panel derecho
        self.panel_izquierdo.panel_derecho_ref = self.panel_derecho

        # Conectar carga de datos y selección de rango con las gráficas
        self.panel_izquierdo.archivoCargado.connect(self.area_central.cargar_dataframe)
        self.panel_izquierdo.archivoSeleccionado.connect(self.area_central.cargar_dataframe)
        self.panel_izquierdo.modoSeleccionRangoCambiado.connect(
            self.area_central.set_modo_seleccion_rango
        )

        self.panel_derecho.config_columnas.mapeoAplicado.connect(
            self.area_central.actualizar_mapeo
        )

        self.subcabecera.rangoManualSolicitado.connect(
            self.area_central.seleccionar_rango_manual
        )

        self.panel_derecho.filtros.filtroSolicitado.connect(
            self.area_central.aplicar_filtro
        )
        self.panel_derecho.filtros.restaurarSolicitado.connect(
            self.area_central.restaurar_datos_originales
        )
        self.panel_derecho.filtros.frecuenciaCambiada.connect(
            self.area_central.set_frecuencia_grafica
        )
        self.area_central.filtroEstadoCambiado.connect(
            self.panel_derecho.filtros.actualizar_estado
        )
        self.area_central.senalesDisponiblesCambiaron.connect(
            self.panel_derecho.filtros.cargar_senales
        )
        self.area_central.variablesFormulaCambiaron.connect(
            self.panel_derecho.formulas.cargar_variables_formula
        )

        self.area_central.rangosCambiados.connect(
            self.panel_derecho.formulas.cargar_rangos
        )
        self.area_central.rangoRechazado.connect(
            self.panel_derecho.formulas.mostrar_error_rango
        )
        self.area_central.rangoAjustado.connect(
            self.panel_derecho.formulas.mostrar_aviso_rango
        )
        self.panel_derecho.formulas.aplicarATodasCambiado.connect(
            self.area_central.set_aplicar_corte_todas
        )
        self.panel_derecho.formulas.notaGuardada.connect(
            self.area_central.set_nota
        )
        self.panel_derecho.formulas.eliminarRangosSolicitado.connect(
            self.area_central.eliminar_rangos
        )

        # --- Fórmulas ---
        self.panel_derecho.formulas.formulaSolicitada.connect(
            self.area_central.aplicar_formula
        )
        self.panel_derecho.formulas.quitarFormulaSolicitado.connect(
            self.area_central.quitar_formula
        )
        self.area_central.formulaEstadoCambiado.connect(
            self.panel_derecho.formulas.actualizar_estado_formula
        )
        self.area_central.resultadosFormulaCambiaron.connect(
            self.panel_derecho.formulas.mostrar_resultados_formula
        )
        self.panel_izquierdo.variablesCambiaron.connect(
            self.area_central.set_variables_sujeto
        )
        self.panel_derecho.formulas.fuenteCalculoCambiada.connect(
            self.area_central.set_fuente_calculo
        )
        self.area_central.fuenteDatosCambiada.connect(
            self.panel_derecho.formulas.set_hay_filtro
        )
        self.panel_derecho.formulas.formulasCambiaron.connect(
            self.area_central.actualizar_formulas_abiertas
        )

    def _exportar(self):
        """Exporta el estado actual sin alterar el proyecto guardado."""
        area = self.area_central
        if area.df_grafica_original is None or area.columna_x is None:
            QMessageBox.warning(
                self, "Exportar", "Primero cargá un archivo CSV para poder exportar."
            )
            return

        columnas = [
            columna
            for columna in area._obtener_columnas_a_graficar()
            if columna in area.df_grafica_original.columns
        ]
        if not columnas:
            columnas = [
                columna
                for columna in area.graficas_por_columna
                if columna in area.df_grafica_original.columns
            ]
        rangos = area.rangos_para_exportar()
        resultados_formulas = area.resultados_formulas_para_exportar()
        cantidad_resultados = sum(
            len(datos.get("resultados") or ()) for datos in resultados_formulas
        )
        nombres_formulas = list(
            dict.fromkeys(
                datos.get("nombre", "")
                for datos in resultados_formulas
                if datos.get("nombre")
            )
        )
        nombre_formula = (
            nombres_formulas[0]
            if len(nombres_formulas) == 1
            else f"{len(nombres_formulas)} fórmulas aplicadas"
            if nombres_formulas
            else ""
        )
        curvas_formula = self._curvas_formula_para_exportar(columnas)

        dialogo = ExportarDialog(
            self,
            nombre_archivo=area.nombre_archivo,
            cantidad_frames=len(area.df_grafica_original),
            cantidad_senales=len(columnas),
            cantidad_rangos=len(rangos),
            cantidad_resultados=cantidad_resultados,
            nombre_formula=nombre_formula,
            hay_filtros=bool(set(columnas) & set(area.columnas_filtradas)),
            hay_curvas_formula=bool(curvas_formula),
        )
        if dialogo.exec() != ExportarDialog.Accepted:
            return

        modo = dialogo.modo_seleccionado()
        titulo_modo = dialogo.titulo_modo_seleccionado()
        resumen_modo = dialogo.resumen_modo_seleccionado()
        extension = exportacion.EXTENSIONES_MODO[modo]
        base = exportacion.nombre_base(area.nombre_archivo)
        sufijos = {
            exportacion.MODO_DATOS: "datos",
            exportacion.MODO_RANGOS: "rangos",
            exportacion.MODO_RESULTADOS: "resultados",
            exportacion.MODO_COMPLETO: "analisis",
        }
        sugerido = f"{base}_{sufijos[modo]}{extension}"
        filtro = (
            "Archivo ZIP (*.zip)"
            if extension == ".zip"
            else "CSV compatible con Excel (*.csv)"
        )
        ruta, _ = QFileDialog.getSaveFileName(
            self, f"Guardar {titulo_modo.lower()}", sugerido, filtro
        )
        if not ruta:
            return
        ruta = exportacion.asegurar_extension(ruta, extension)

        try:
            if modo == exportacion.MODO_DATOS:
                tabla_datos = self._tabla_datos_para_exportar(columnas)
                exportacion.escribir_csv(ruta, tabla_datos)
            elif modo == exportacion.MODO_RANGOS:
                tabla_muestras = exportacion.preparar_muestras_rangos(
                    rangos,
                    area.df_grafica_original,
                    area.df_grafica,
                    area.columna_x,
                    area.columnas_filtradas,
                )
                exportacion.escribir_csv(ruta, tabla_muestras)
            elif modo == exportacion.MODO_RESULTADOS:
                tabla_resultados = exportacion.preparar_resultados_formulas(
                    resultados_formulas
                )
                exportacion.escribir_csv(ruta, tabla_resultados)
            else:
                tabla_datos = self._tabla_datos_para_exportar(columnas)
                tabla_rangos = exportacion.preparar_rangos(rangos)
                tabla_muestras = exportacion.preparar_muestras_rangos(
                    rangos,
                    area.df_grafica_original,
                    area.df_grafica,
                    area.columna_x,
                    area.columnas_filtradas,
                )
                tabla_resultados = exportacion.preparar_resultados_formulas(
                    resultados_formulas
                )
                informacion = exportacion.preparar_informacion(
                    area.nombre_archivo,
                    area.columna_x,
                    columnas,
                    area.unidades,
                    area.frecuencia_grafica,
                    area.filtros_por_columna,
                    resultados_formulas,
                    nombres=self._nombres_senales_para_exportar(columnas),
                )
                tablas = {"datos.csv": tabla_datos}
                if len(tabla_rangos):
                    tablas["rangos.csv"] = tabla_rangos
                    tablas["muestras_rangos.csv"] = tabla_muestras
                if len(tabla_resultados):
                    tablas["resultados_formula.csv"] = tabla_resultados
                exportacion.escribir_paquete(ruta, tablas, informacion)
        except PermissionError as exc:
            QMessageBox.critical(
                self,
                "No se puede sobrescribir",
                str(exc),
            )
            return
        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Error al exportar",
                "No se pudo completar la exportación.\n\n"
                f"Detalle: {exc}",
            )
            return

        ExportacionCompletadaDialog(
            self,
            os.path.normpath(ruta),
            titulo_modo,
            resumen_modo,
        ).exec()

    def _tabla_datos_para_exportar(self, columnas):
        area = self.area_central
        return exportacion.preparar_datos(
            area.df_grafica_original,
            area.df_grafica,
            area.columna_x,
            columnas,
            area.columnas_filtradas,
            self._curvas_formula_para_exportar(columnas),
            nombres=self._nombres_senales_para_exportar(columnas),
            unidades=area.unidades,
        )

    def _nombres_senales_para_exportar(self, columnas):
        """Usa los títulos visibles sin perder la referencia a la señal."""
        nombres = {}
        for columna in columnas:
            grafica = self.area_central.graficas_por_columna.get(columna)
            if grafica is not None and grafica.nombre_senal:
                nombres[columna] = grafica.nombre_senal
        return nombres

    def _curvas_formula_para_exportar(self, columnas):
        """Toma cada fórmula por separado, aunque convivan en una gráfica."""
        return self.area_central.curvas_formulas_para_exportar(columnas)

    def _guardar_proyecto(self):
        """Guarda una copia del CSV y sus rangos/notas en la carpeta del proyecto.

        Se dispara solo desde el botón «Guardar» de la cabecera. Pide el nombre
        con un cuadro de diálogo propio (no el de Windows) y escribe todo dentro
        de ``<proyecto>/archivos``.
        """
        archivo = getattr(self.panel_izquierdo, "archivo_actual", {}) or {}
        ruta_original = archivo.get("ruta")
        df_original = self.area_central.df_original
        if not ruta_original and df_original is None:
            QMessageBox.warning(
                self, "Guardar", "Primero cargá un archivo CSV para poder guardar."
            )
            return

        sugerido = ""
        if archivo.get("nombre"):
            sugerido = os.path.splitext(archivo["nombre"])[0]

        nombre, ok = QInputDialog.getText(
            self,
            "Guardar proyecto",
            "Nombre del archivo (se guardará como .csv):",
            text=sugerido,
        )
        if not ok:
            return

        nombre = proyecto.sanear_nombre(nombre)
        if not nombre:
            QMessageBox.warning(self, "Guardar", "Ingresá un nombre de archivo válido.")
            return

        proyecto.asegurar_carpeta()
        ruta_csv = proyecto.ruta_csv(nombre)
        ruta_anotaciones = proyecto.ruta_anotaciones(nombre)

        try:
            # Copia del CSV original (o del DataFrame si no está la ruta).
            if ruta_original and os.path.exists(ruta_original):
                shutil.copyfile(ruta_original, ruta_csv)
            else:
                df_original.to_csv(ruta_csv, index=False)

            # Rangos, sub-rangos y notas trabajados.
            anotaciones = self.area_central.exportar_anotaciones()
            proyecto.escribir_anotaciones(ruta_anotaciones, anotaciones)
        except OSError as exc:
            QMessageBox.critical(self, "Guardar", f"No se pudo guardar:\n{exc}")
            return

        QMessageBox.information(
            self,
            "Guardar",
            "Proyecto guardado en la carpeta «archivos»:\n\n"
            f"• {os.path.basename(ruta_csv)} (copia del CSV)\n"
            f"• {os.path.basename(ruta_anotaciones)} "
            f"({len(anotaciones)} rango(s)/sub-rango(s) con sus notas)",
        )

    def _cargar_proyecto(self):
        """Abre un proyecto de la carpeta «archivos» con sus rangos y notas.

        El diálogo solo lista esa carpeta: no se puede navegar a otra ruta,
        porque un CSV de cualquier otro lado no tiene anotaciones asociadas.
        La asociación es por nombre (``<nombre>.csv`` ↔
        ``<nombre>_anotaciones.csv``); no se usa la base de datos.
        """
        dialogo = CargarProyectoDialog(self)
        if dialogo.exec() != CargarProyectoDialog.Accepted:
            return

        datos = dialogo.proyecto_seleccionado()
        if not datos:
            return

        if self.panel_izquierdo.cargar_archivo_desde_ruta(datos["ruta"]) is None:
            return

        # El CSV ya está graficado: recién ahora se pueden reponer los rangos,
        # porque cargar_dataframe() limpia los gestores.
        try:
            anotaciones = proyecto.leer_anotaciones(datos["ruta_anotaciones"])
        except OSError as exc:
            QMessageBox.warning(
                self, "Cargar", f"No se pudieron leer las anotaciones:\n{exc}"
            )
            return

        if not anotaciones:
            QMessageBox.information(
                self,
                "Cargar",
                f"Se cargó «{datos['nombre']}».\n\n"
                "El proyecto no tenía rangos ni notas guardados.",
            )
            return

        restaurados, descartados = self.area_central.importar_anotaciones(anotaciones)

        mensaje = (
            f"Se cargó «{datos['nombre']}» con "
            f"{restaurados} rango(s)/sub-rango(s) y sus notas."
        )
        if descartados:
            mensaje += (
                f"\n\nQuedaron {descartados} sin restaurar: su señal no está "
                "graficada en este archivo. Revisá el mapeo de columnas."
            )
        QMessageBox.information(self, "Cargar", mensaje)
