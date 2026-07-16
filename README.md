# LIBiAM 3.0

Sistema de Analisis de Senales Biomecanicas para el Laboratorio LIBiAM.

Aplicacion de escritorio desarrollada con PySide6 para la carga, deteccion y visualizacion de datos de plataformas de fuerza.

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Ejecucion

```bash
python main.py
```

## Funcionalidades

### Ya Existian (trabajo previo del equipo)
| Componente | Archivo | Descripcion |
|------------|---------|-------------|
| Barra superior | `ui/cabecera/cabeceraPrincipal/cabecera.py` | Logo, titulo, subtitulo y botones (Proyecto, Guardar, Exportar, Ayuda) |
| Ventana principal | `ui/ventanaPrincipal/ventana_principal.py` | Layout base con cabecera |
| Estilos base | `utilidades/estilos/ventana.qss`, `cabecera.qss` | Tema oscuro y estilos de cabecera |
| Punto de entrada | `main.py` | Carga de estilos QSS y creacion de ventana |
| Panel derecho colapsable | `ui/ventanaPrincipal/panelDerecho/panelDerecho.py` | Panel lateral derecho con animacion de expandir/colapsar y zona de arrastre para redimensionar |

### Nuevas Funcionalidades (agregadas en esta fase)
| Componente | Archivo | Estado | Descripcion |
|------------|---------|--------|-------------|
| Panel lateral izquierdo | `ui/ventanaPrincipal/panelizquierdo.py` | **Implementado** | Botones, arbol de archivos, informacion del archivo |
| Carga de CSV | `logica/cargador_csv.py` | **Implementado** | Dialogo de seleccion, lectura con pandas, deteccion de tipos |
| Estilos panel izquierdo | `utilidades/estilos/panelizquierdo.qss` | **Implementado** | Estilos para botones, arbol y seccion de informacion |
| Panel derecho colapsable | `ui/ventanaPrincipal/panelDerecho/panelDerecho.py` | **Implementado** | Panel con animacion, redimensionable por arrastre |
| Configuracion de columnas | `ui/ventanaPrincipal/panelDerecho/configColumnas.py` | **Implementado** | UI de mapeo con dropdowns, checkboxes, deteccion automatica |
| Logica de mapeo | `logica/mapeo_columnas.py` | **Implementado** | Clase `MapeoColumnas` con mapeo automatico + usuario + ejes activos |
| Area central de graficas | `ui/ventanaPrincipal/areaCentralGraficas.py` | **Implementado** | Graficas por senal con pyqtgraph, zoom y seleccion de rango |
| Barra de botones derecha | `ui/ventanaPrincipal/barraBotones.py` | **Implementado** | 3 toggles (Mapeo, Filtros, Formulas) con hover azul y estado activo |
| Placeholder Filtros | `ui/ventanaPrincipal/panelDerecho/filtros.py` | **Implementado** | Panel "En construccion" con mismo estilo que Mapeo |
| Placeholder Formulas | `ui/ventanaPrincipal/panelDerecho/formulas.py` | **Implementado** | Panel "En construccion" con mismo estilo que Mapeo |
| Estilos panel derecho | `utilidades/estilos/panelderecho.qss` | **Implementado** | Estilos para secciones, mapeo, botones, dropdowns |
| Estilos barra botones | `utilidades/estilos/barrabotones.qss` | **Implementado** | Hover azul, estado activo con propiedad `[activo="true"]` |
| Integracion ventana | `ui/ventanaPrincipal/ventana_principal.py` | **Modificado** | Layout horizontal con panel izquierdo, area central, panel derecho, barra botones |
| Carga de estilos | `main.py` | **Modificado** | Carga de `panelizquierdo.qss`, `panelderecho.qss`, `barrabotones.qss` |

#### Detalle de nuevas funcionalidades:

**Panel Izquierdo:**
- Carga de archivos CSV mediante dialogo de seleccion
- Deteccion automatica del delimitador
- Identificacion automatica de columnas de Fuerza, Momento y COP
- Reconocimiento de estructura con SubFrames (multiple mediciones por Frame)
- Arbol de archivos con scroll automatico
- Informacion del archivo: nombre, columnas, tipo de datos, subframes y registros
- Doble click en el arbol para cambiar la informacion mostrada

**Panel Derecho:**
- Colapsable con animacion suave (250ms, curva InOutCubic)
- Redimensionable por arrastre del borde izquierdo (min 340px, max 800px)
- `QStackedWidget` para alternar entre Mapeo, Filtros y Formulas
- Solo un panel abierto a la vez

**Configuracion de Columnas:**
- Deteccion automatica de columnas biomecanicas (Fuerza, Momento, COP)
- Dropdowns para seleccionar columna por eje (X, Y, Z)
- Checkboxes para activar/desactivar ejes individuales
- Filtro por tipo de dato (Todos, Fuerza, Momento, COP)
- Botones "Aplicar Mapeo" y "Reset"
- Area de mapeo con altura fija de 500px y scroll

**Area Central de Graficas:**
- Visualizacion automatica al cargar o seleccionar un CSV
- Una grafica independiente por senal activa (Fx, Fy, Fz, Mx, etc.)
- Uso de `Frame` como eje X principal
- Promedio por `Frame` cuando el CSV contiene `SubFrame`
- Zoom horizontal con scroll sobre cada grafica
- Seleccion de rango con dos clicks sobre una grafica
- Previsualizacion dinamica del rango antes del segundo click
- Apertura de ventana modal con el rango seleccionado

**Barra de Botones:**
- 3 botones toggle verticales con 12px de espaciado
- Hover azul (`#1976D2`) en todos los botones
- Estado activo persistente (fondo azul) en el boton del panel abierto
- Iconos SVG para estados expandir/colapsar
- Click en el boton activo colapsa el panel

**Placeholder Filtros y Formulas:**
- Mismo fondo `#252526` que el panel de Mapeo
- Spacer de 500px para igualar altura con Mapeo
- Label "En construccion" centrado

## Estructura del Diccionario de Mapeo

El metodo `MapeoColumnas.obtener_mapeo_completo()` devuelve un diccionario que se utiliza como entrada para actualizar las graficas:

```python
mapeo = {
    "Fuerza": {
        "eje_x": {"columna": "Fx_N", "activo": True},
        "eje_y": {"columna": "Fy_N", "activo": True},
        "eje_z": {"columna": "Fz_N", "activo": True}
    },
    "Momento": {
        "eje_x": {"columna": "Mx_Nm", "activo": True},
        "eje_y": {"columna": "My_Nm", "activo": True},
        "eje_z": {"columna": "Mz_Nm", "activo": True}
    },
    "COP": {
        "eje_x": {"columna": "COPx_mm", "activo": True},
        "eje_y": {"columna": "COPy_mm", "activo": True}
    }
}
```

**Campos del diccionario:**
- `columna`: Nombre de la columna en el CSV mapeada a ese eje
- `activo`: Booleano que indica si el eje esta habilitado para graficar

**Uso esperado en graficas:**
```python
# Ejemplo de como se utilizara el mapeo para extraer datos
for tipo, ejes in mapeo.items():
    for eje, config in ejes.items():
        if config["activo"]:
            columna = config["columna"]
            datos = dataframe[columna]  # Extraer serie para graficar con pyqtgraph
```

## Estructura del Proyecto

```
libiam3.0/
├── main.py                         # Punto de entrada (modificado)
├── logica/
│   ├── cargador_csv.py             # Logica de carga y deteccion (implementado)
│   └── mapeo_columnas.py           # Logica de mapeo de columnas (implementado)
├── ui/
│   ├── cabecera/                   # Barra superior (existente)
│   │   └── cabeceraPrincipal/
│   │       ├── cabecera.py         # IMPLEMENTADO
│   │       └── {proyecto,guardar,exportar,ayuda}.py  # EMPTY placeholders
│   └── ventanaPrincipal/           # Ventana principal
│       ├── ventana_principal.py    # Layout (modificado)
│       ├── areaCentralGraficas.py  # Graficas y seleccion de rango (implementado)
│       ├── panelizquierdo.py       # Panel lateral izquierdo (implementado)
│       ├── barraBotones.py         # Barra de toggles derecha (implementado)
│       └── panelDerecho/           # Panel derecho colapsable
│           ├── panelDerecho.py     # Wrapper con animacion (implementado)
│           ├── configColumnas.py   # UI de mapeo (implementado)
│           ├── filtros.py          # Placeholder filtros (implementado)
│           ── formulas.py         # Placeholder formulas (implementado)
└── utilidades/
    ├── estilos/                    # Hojas de estilo QSS
    ├── icons/                      # Iconos SVG/PNG
    └── resources/                  # Archivos CSV de ejemplo
```

## Dependencias

- PySide6 6.11.0
- pandas 3.0.3
- numpy 2.4.4
- pyqtgraph 0.14.0
- SQLAlchemy 2.0.49

## Estado del Proyecto

La estructura UI esta completa con panel izquierdo (carga de CSV), area central de graficas, panel derecho colapsable con 3 secciones (Mapeo, Filtros, Formulas) y barra de toggles con estados visuales. La logica de mapeo de columnas actualiza las senales graficadas y permite activar/desactivar ejes.

**Proximas fases sugeridas:** implementar filtros, formulas y analisis de los rangos seleccionados.
