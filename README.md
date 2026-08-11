# ABS 3.0

ABS 3.0 (Analysis of Biomechanical Signals) es una aplicación de escritorio para cargar, visualizar, filtrar y analizar señales biomecánicas exportadas en archivos CSV. Fue desarrollada para el Laboratorio de Investigación en Biomecánica y Análisis del Movimiento (LIBiAM) de UTEC.

## Instalación y ejecución

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

En GNU/Linux o macOS, la activación del entorno se realiza con:

```bash
source .venv/bin/activate
```

## Funciones implementadas

### Carga de CSV

- Detecta el separador, aunque el archivo use coma, punto y coma, tabulación o barra vertical.
- Localiza la cabecera real cuando el CSV incluye metadatos antes de los datos.
- Separa la fila de unidades para que valores como `N`, `N.mm` y `mm` no se mezclen con las muestras numéricas.
- Conserva la frecuencia de muestreo declarada en la exportación.
- Usa el motor C de pandas y evita recorrer todas las celdas con bucles de Python.
- Reconoce variantes como `SubFrame`, `Sub Frame` y `Sub_Frame`.

Cuando hay subframes, ABS promedia las muestras que pertenecen al mismo frame antes de graficar.

### Gráficas

- Crea una gráfica por señal detectada y mantiene el mapeo entre Fuerza, Momento y COP.
- Muestra la unidad en el eje vertical: `N` para fuerza, `N.mm` para momento y `mm` para centro de presión en el archivo de ejemplo.
- Evita factores automáticos confusos en señales muy pequeñas. Por ejemplo, `Cz` se muestra como `0.000020 mm` en lugar de `20 × 10⁻⁶ mm`.
- Permite zoom horizontal con la rueda del ratón.
- Reduce automáticamente la cantidad de puntos dibujados cuando la vista no necesita mostrarlos todos.

### Filtrado

El panel `Filtro de frecuencias` permite elegir qué señales se procesarán y ofrece tres modos Butterworth de orden 4:

- Por debajo de un límite (pasa-bajos).
- Por encima de un límite (pasa-altos).
- Dentro de un intervalo (pasa-banda).

El campo `Frecuencia usada` se completa con la frecuencia original detectada en el CSV y también permite corregirla o ingresarla manualmente. Cuando los datos contienen subframes y se promedian por frame, el programa divide ese valor automáticamente y muestra la frecuencia efectiva. Por ejemplo, 2000 Hz con 8 subframes se procesa a 250 Hz. El panel también muestra el límite máximo admitido, equivalente a la mitad de la frecuencia efectiva, y bloquea combinaciones matemáticamente inválidas.

El procesamiento se realiza con secciones de segundo orden y hacia adelante y hacia atrás para evitar un desplazamiento temporal apreciable de los eventos. La atenuación fuera de los límites elegidos es gradual; no se presenta como una eliminación perfecta e instantánea de todas las frecuencias exteriores.

El filtrado no reemplaza visualmente los datos: la señal original permanece en azul y la filtrada se superpone en naranja. `Quitar filtro` restaura las señales seleccionadas sin modificar los filtros aplicados a otras. Mientras una curva filtrada está visible, los rangos destinados a cálculos toman sus valores filtrados.

### Rangos para cálculos

- Los límites seleccionados se redondean al frame entero más cercano. Por ejemplo, `30.15` pasa a `30` y `30.76` pasa a `31`.
- Cada rango pertenece únicamente a la gráfica donde se seleccionó y conserva un color propio.
- La lista se ordena de izquierda a derecha. Los nombres automáticos se actualizan según esa posición, sin perder notas ni sub-rangos asociados.
- Los rangos de una misma gráfica no pueden superponerse ni compartir un frame extremo. Si una selección invade un rango existente, se ajusta al tramo libre continuo siguiendo la dirección del gesto. Por ejemplo, con `20–30` ya ocupado, seleccionar `24–50` crea `31–50`.
- La selección ya no abre una ventana modal.
- El panel `Rangos para cálculos` permite elegir la señal y usar todos sus rangos, solo los pares, solo los impares o una combinación manual mediante casillas.
- Cada rango y sub-rango se puede eliminar desde la cruz de su propia fila.

La selección se hace con dos clics sobre una gráfica después de activar `Seleccionar rango`. También se puede ingresar un intervalo entero desde la barra superior.

### Acerca de ABS 3.0

El botón `Acerca de` muestra el nombre del programa, versión, año, institución, laboratorio, descripción y una referencia sugerida que puede copiarse al portapapeles.

Estos datos están centralizados en `logica/app_info.py`. Para publicar otra versión, se modifica `VERSION` una sola vez; el título de la ventana, la cabecera, el diálogo y la referencia se actualizan a partir de ese valor. La autoría registrada es Jairo Bandera, Alan Ceballos y Juan Macchi.

### Editor CSV

El editor usa una tabla virtualizada: mantiene el archivo completo disponible, pero crea visualmente solo las celdas que están en pantalla. Así conserva la selección de filas, el marcado de secciones, los colores y la asignación por doble clic sin construir cientos de miles de elementos de interfaz. También comparte el lector rápido de CSV con el cargador principal.

Con el archivo de prueba de 49.309 filas y 11 columnas, la construcción de la ventana pasó de aproximadamente 23,15 segundos a 0,013 segundos en el entorno de desarrollo. La lectura y apertura completa tarda alrededor de 0,125 segundos; los tiempos pueden variar según el equipo.

## Estructura principal

```text
logica/
├── app_info.py              Datos de versión y referencia
├── cargador_csv.py          Carga y detección de señales
├── filtros_senales.py       Filtro Butterworth
├── lector_csv.py            Lectura rápida y metadatos del CSV
├── mapeo_columnas.py        Mapeo automático y manual
└── rangos.py                Validación de rangos no superpuestos

ui/
├── cabecera/                Barra superior, selección manual y Acerca de
└── ventanaPrincipal/
    ├── areaCentralGraficas.py
    ├── panelizquierdo.py
    └── panelDerecho/        Mapeo, filtros, rangos y cabeceras
```

## Dependencias

- NumPy 2.4.4
- pandas 3.0.3
- PyQtGraph 0.14.0
- PySide6 6.11.0
- SciPy 1.18.0
- SQLAlchemy 2.0.49
