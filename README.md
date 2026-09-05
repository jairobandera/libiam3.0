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
- Cada intervalo pertenece a la gráfica donde se seleccionó. Cuando se replica
  en las demás gráficas, todas sus copias comparten el mismo color, aunque las
  listas tengan órdenes diferentes.
- La lista se ordena de izquierda a derecha. Los nombres automáticos se actualizan según esa posición, sin perder notas ni sub-rangos asociados.
- Los rangos de una misma gráfica no pueden superponerse ni compartir un frame extremo. Si una selección invade un rango existente, se ajusta al tramo libre continuo siguiendo la dirección del gesto. Por ejemplo, con `20–30` ya ocupado, seleccionar `24–50` crea `31–50`.
- La selección ya no abre una ventana modal.
- El panel `Intervalos para cálculos` incluye `Calcular sobre: Intervalos |
  Subintervalos`. La lista muestra solamente el nivel elegido.
- En modo `Subintervalos` se reúnen, por grupos, los subintervalos de todos los
  intervalos padre de la señal actual. Así se puede aplicar una fórmula en masa
  sin abrir cada intervalo con doble clic.
- `Todos`, `Pares`, `Impares` y `Ninguno` actúan únicamente sobre el nivel
  visible. Para subintervalos, par o impar se determina dentro de cada padre;
  por ejemplo, se seleccionan A2, B2 y C2.
- Al pulsar `Aplicar` se usan únicamente las casillas marcadas de la señal que
  aparece en el selector. Las selecciones recordadas en otras señales no se
  incluyen hasta que el usuario cambie a ellas.
- Cada rango y sub-rango se puede eliminar desde la cruz de su propia fila.
- `Esc` cancela el primer punto pendiente. Si todavía no se marcó un punto,
  sale del modo de selección.
- Las fórmulas aplicadas a sub-rangos se conservan mientras el CSV siga
  cargado. Al cerrar y volver a abrir su ventana se restauran los resultados,
  las curvas, la fórmula elegida y las casillas calculadas.
- Los cálculos de intervalos y subintervalos permanecen separados. Cambiar el
  selector cambia también las curvas y los resultados visibles; `Aplicar` y
  `Quitar` afectan solo al nivel elegido.
- El doble clic continúa abriendo el detalle de un intervalo para crear,
  revisar o calcular sus subintervalos de forma individual.
- Un intervalo puede aportar los límites de un cálculo aunque se haya marcado
  en otra gráfica. Por ejemplo, un recorte replicado en Fx puede delimitar una
  fórmula de Fz; los valores numéricos siguen tomándose de Fz. La misma curva
  calculada se dibuja en todas las gráficas visibles que contienen una copia de
  ese intervalo, sin recalcularla con Fx, Fy u otra señal.

La selección se hace con dos clics sobre una gráfica después de activar `Seleccionar rango`. También se puede ingresar un intervalo entero desde la barra superior.

### Variables y fórmulas personalizadas

- La masa en kilogramos y la estatura en metros se guardan para cada CSV.
- `masa` y `estatura` están disponibles como datos dentro del constructor de
  fórmulas, junto con gravedad, frecuencia y tiempo.
- Las fórmulas creadas se pueden exportar a un `.txt` e importar en otra copia
  de ABS. Al importar se validan de nuevo, se omiten duplicados exactos y se
  renombran las coincidencias para no reemplazar fórmulas existentes.

### Guardado y reapertura de proyectos

- `Guardar` conserva la copia del CSV y las anotaciones, y agrega un archivo
  de estado con masa, estatura, gravedad, frecuencia, filtros aplicados,
  orden de las gráficas y señales visibles.
- `Cargar` reconstruye ese estado después de abrir el CSV. Los proyectos de
  versiones anteriores, que no tienen archivo de estado, continúan abriendo.
- La ventana principal recuerda su tamaño, posición y estado maximizado. La
  ventana de subintervalos recuerda además el ancho elegido para cada panel.

### Exportación

- Los cálculos se exportan con una fila por fórmula e intervalo: promedio,
  máximo y frame donde ocurrió el máximo. No se agregan como valores de fórmula
  frame por frame dentro del archivo de datos.
- Se incluyen los cálculos de intervalos y sub-intervalos, incluso si la ventana
  de detalle está cerrada.
- El usuario puede exportar todo el registro o marcar recortes específicos. El
  alcance elegido se aplica a los datos, intervalos y resultados incluidos.
- La lista de la ventana Exportar contiene todos los intervalos y sub-intervalos
  existentes de todas las señales. Es independiente de la señal y de las
  casillas activas en `Intervalos para cálculos`.

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
├── formulas.py              Validación y cálculo de fórmulas
├── intercambio_formulas.py Importación y exportación de fórmulas
├── lector_csv.py            Lectura rápida y metadatos del CSV
├── mapeo_columnas.py        Mapeo automático y manual
└── rangos.py                Validación de rangos no superpuestos

ui/
├── cabecera/                Barra superior y Acerca de
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
