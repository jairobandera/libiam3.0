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

### Nuevas Funcionalidades (agregadas en esta fase)
| Componente | Archivo | Estado | Descripcion |
|------------|---------|--------|-------------|
| Panel lateral izquierdo | `ui/ventanaPrincipal/panelizquierdo.py` | **Creado** | Botones, arbol de archivos, informacion del archivo |
| Carga de CSV | `logica/cargador_csv.py` | **Creado** | Dialogo de seleccion, lectura con pandas, deteccion de tipos |
| Estilos panel izquierdo | `utilidades/estilos/panelizquierdo.qss` | **Creado** | Estilos para botones, arbol y seccion de informacion |
| Integracion panel | `ui/ventanaPrincipal/ventana_principal.py` | **Modificado** | Agregado layout horizontal con panel izquierdo |
| Carga de estilos | `main.py` | **Modificado** | Agregada carga de `panelizquierdo.qss` |

#### Detalle de nuevas funcionalidades:
- **Carga de archivos CSV**: Dialogo de seleccion con deteccion automatica del delimitador
- **Deteccion inteligente**: Identificacion automatica de columnas de Fuerza, Momento y COP
- **Deteccion de SubFrames**: Reconocimiento de estructura con multiple mediciones por Frame
- **Arbol de archivos**: Lista visual de archivos cargados con scroll automatico
- **Informacion del archivo**: Nombre, columnas, tipo de datos, subframes y registros
- **Interaccion con arbol**: Doble click para cambiar la informacion mostrada

## Estructura del Proyecto

```
libiam3.0/
├── main.py                 # Punto de entrada (modificado)
├── logica/
│   └── cargador_csv.py     # Logica de carga y deteccion (creado)
├── ui/
│   ├── cabecera/           # Barra superior (existente)
│   └── ventanaPrincipal/   # Ventana principal
│       ├── ventana_principal.py  # Layout (modificado)
│       └── panelizquierdo.py     # Panel lateral (creado)
── utilidades/
    ├── estilos/            # Hojas de estilo QSS
    ├── icons/              # Iconos SVG/PNG
    └── resources/          # Archivos CSV de ejemplo
```

## Dependencias

- PySide6 6.11.0
- pandas 3.0.3
- numpy 2.4.4
- pyqtgraph 0.14.0
- SQLAlchemy 2.0.49

## Estado del Proyecto

Este proyecto esta en desarrollo activo. Las funcionalidades de graficacion y procesamiento de datos se implementaran en fases posteriores.
