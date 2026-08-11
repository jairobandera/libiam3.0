# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**ABS 3.0** (Analysis of Biomechanical Signals) is a PySide6 desktop app for loading, visualizing, filtering, and analyzing biomechanical signals (force / moment / center-of-pressure) exported as CSV. Built for the LIBiAM lab at UTEC. Codebase, comments, UI strings, and identifiers are all in **Spanish** — match that when writing new code.

## Commands

```bash
# Setup (Windows)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Run the app
python main.py

# Run the full test suite (unittest, no pytest config in repo)
python -m unittest tests.test_logica

# Run a single test case / method
python -m unittest tests.test_logica.TestFiltro
python -m unittest tests.test_logica.TestRangos.test_ajusta_inicio_ocupado_al_primer_frame_libre
```

No linter or build step is configured. Tests cover only `logica/` (CSV reading, Butterworth filters, range validation); the `ui/` layer has none.

### Verifying UI changes without a display

The `ui/` layer can still be exercised headlessly, which is the fastest way to check a change end to end:

```bash
QT_QPA_PLATFORM=offscreen PYTHONIOENCODING=utf-8 python -c "..."
```

`PYTHONIOENCODING=utf-8` matters because the console is cp1252 and UI strings contain glyphs (`☰ ▾ ✕ ＋ ↳`) that otherwise raise `UnicodeEncodeError` on print. To drive flows that open dialogs, stub them before importing UI modules:

```python
import PySide6.QtWidgets as W
W.QInputDialog.getText = staticmethod(lambda *a, **k: ("", True))
W.QMessageBox.question = staticmethod(lambda *a, **k: W.QMessageBox.Yes)
```

When checking widget geometry, **load the real `.qss` files first** (as `main.py` does) — stylesheet padding changes widget widths, so measurements without it are misleading.

## Architecture

Two-layer split: **`logica/`** is pure, UI-free, testable business logic; **`ui/`** is the PySide6 widget tree. Keep new algorithmic code in `logica/` (and covered by `tests/`) rather than embedding it in widgets.

### Data flow

1. **`main.py`** — entry point. Initializes the SQLite config DB, concatenates the `.qss` stylesheets from `utilidades/estilos/`, and shows `VentanaPrincipal`.
2. **`PanelIzquierdo`** (left) — file tree, load button, and the "Variables" section. Emits `archivoCargado` / `archivoSeleccionado` carrying `(nombre, dataframe, info)`.
3. **`AreaCentralGraficas`** (center) — the hub. Builds one `GraficaSenal` (a `pg.PlotWidget`) per signal and owns all filtering, range, sub-range and note state. Largest and most central UI file.
4. **`PanelDerecho`** (right) — `QStackedWidget` with four panels: `ConfigColumnas` (mapping), `Filtros`, `Formulas` (ranges), `DetectarCabeceras`. `BarraBotones` toggles visibility.
5. **`Cabecera`** (top) — Inicio / Guardar / Exportar / Configurar / Acerca de. Owns the session config dialog and the save action.

Widgets are wired **entirely by Qt signals connected in `VentanaPrincipal.init_ui()`** — that method is the single source of truth for cross-panel communication. Add new interactions there rather than reaching into sibling widgets.

### CSV reading (`logica/lector_csv.py`)

Biomechanical exports are messy: metadata rows before the header, a units row after it, unusual delimiters, subframes. `leer_csv_rapido()` auto-detects the delimiter, locates the real header row heuristically, strips the units row into `metadatos["unidades"]`, extracts the declared sampling frequency, and returns `(df, metadatos)` with metadata also on `df.attrs`. It reads only the first ~120 rows to decide, then loads the numeric block with the pandas C engine so columns stay numeric. `leer_csv_crudo()` reads everything header-less for the manual-section editor.

### Column mapping (DB-driven, user-reorderable)

Column-name → signal-type mapping is **learned and persisted in SQLite** (`libiam_config.db`, schema in `logica/config_db.py`). `AliasColumna` maps a lowercased name to `(tipo, eje)`; the DB is seeded on first run and `_migrar_db` handles additive changes. `buscar_alias()` does exact-match then longest-substring fallback. **The `.db` file is committed** — be deliberate about changes.

`ConfigColumnas` renders the mapping as a drag-reorderable `QListWidget` (`InternalMove`). On "Aplicar Mapeo" it injects an **`orden` integer** into each entry, and `AreaCentralGraficas._entradas_mapeo_ordenadas()` sorts graphs by it. Entries without `orden` fall back to dict insertion order, so older callers keep working.

### Filtering

`logica/filtros_senales.py` is the real, tested implementation: `aplicar_butterworth()` (4th-order, zero-phase `filtfilt`), validating cutoffs against Nyquist, interpolating over NaNs before filtering and restoring them after. Filtered curves are overlaid (original blue, filtered orange) — filtering never replaces the original. `logica/procesamiento_filtros.py` is an older, untested duplicate; prefer `filtros_senales.py`.

### Formulas: potencia and impulso

`logica/formulas.py` is the engine, UI-free and tested. Both formulas derive from **the vertical force**, the standard force-plate method:

```
a(t) = (Fz(t) − m·g) / m      aceleracion()  — the plate already reads m·g at rest,
v(t) = ∫ a(t) dt              velocidad()      so only the excess accelerates the subject
P(t) = Fz(t) · v(t)           potencia()     — instantaneous, in W
J(t) = ∫ (Fz(t) − m·g) dt     impulso()      — accumulated, in N·s
```

`_integrar_acumulado()` is the **single trapezoidal integrator** behind both `velocidad()` and `impulso()` — change the integration rule there and both follow.

**Integration runs once over the whole record, not per range** (`integra_en_registro: True`). It starts from zero at the CSV's first frame, which is captured with the subject still; a marked range only *slices* the result and never resets the initial condition. This is the single most important invariant in the module:

- **Potencia** needs absolute velocity, so it depends on that first frame really being at rest.
- **Impulso** does not. By the impulse-momentum theorem `J = m·Δv`, so a range's **net impulse is the difference between the ends of its slice** — `valores[-1] − valores[0]`, never `valores[-1]`. On real data the gap is large (a range measuring 12.9 N·s sits at 60.9 N·s of accumulated curve), so getting this wrong is silently, badly wrong rather than slightly off.

`detalles_impulso()` returns the per-range values the panel shows: net impulse, Δv, and the **propulsive/braking split** (the net force clipped by sign and integrated separately — at plate sampling rates the zero-crossing trapezoid error is negligible). It is wired in through the registry's optional **`detalles` hook**, which `computar_formula()` calls per range via `_detalles_de()`. Formulas without it (potencia) are described well enough by the resumen's peak and mean; accumulated curves need their own numbers, and each entry carries its own unit so N·s and m/s can share a block.

`FORMULAS` is the registry, and **adding a formula there is the whole job** — `PanelCalculo` builds its combo straight from it, so the UI needs no changes at all. Each entry declares `nombre`, `articulo`, `expresion`, `unidad`, `salida_rol`, `requiere_roles`, `requiere` (blocking checks with their messages), `computar`, and optionally `integra_en_registro` and `detalles`.

`articulo` ("la" / "el") exists because messages are built as `nombre_con_articulo()`; hardcoding "la" produced *«se calculó la impulso»* the moment a masculine name joined the registry.

`_validar_parametros()` gates on mass, gravity and sampling rate, each with a message naming what's missing. `TestPotencia` and `TestImpulso` each cover a constant-force case checkable by hand: 2·m·g for 1 s gives exactly 10 m/s, 14 000 W and 700 N·s. `TestImpulso.test_el_neto_del_rango_resta_los_extremos_del_recorte` is the regression guard for the slicing rule — it puts an impulse *before* the range so taking the last value would be visibly wrong.

**Formulas are computed on parent ranges only, never on sub-ranges.** Sub-ranges get their own calculation later, inside the `VentanaRegion` that opens on double-click — that's where they're actually visible. `Formulas._rangos_padre_seleccionados()` filters them out for both the request and the Aplicar button's enabled state, and `_rangos_seleccionados()` in `AreaCentralGraficas` drops `es_subrango` again so the rule holds even if another caller appears.

**Formulas are computed on ranges, not on the whole signal.** `Formulas._solicitar_formula()` sends the IDs currently checked plus the `clave` of the formula picked in `PanelCalculo`, so the Todos/Pares/Impares/Ninguno buttons drive what gets calculated. `_marcar_modo_seleccion()` stores the active mode and sets an `activo` property that `#btnResetMapeo[activo="true"]` styles with a blue border. With nothing selected the Aplicar button is disabled and says why in its tooltip.

**`PanelCalculo` (`ui/ventanaPrincipal/panelDerecho/panelCalculo.py`) is the shared UI block** — source combo, formula combo, Aplicar/Quitar, status, results, warnings. Both the right panel (inside `Formulas`) and `VentanaRegion` embed the same widget, so neither duplicates the layout. It knows nothing about ranges or maths: it emits `calcularSolicitado` and renders whatever results it's handed.

`AreaCentralGraficas.aplicar_formula()` (the `clave` key selects which; `formula_predeterminada()` when absent):

- Resolves the formula's `requiere_roles` against `_roles_disponibles()`; it refuses with an explanatory message when a needed signal isn't mapped or is hidden.
- `_calcular_por_intervalos()` is the shared engine for both parent ranges and the sub-range window, so the two paths can't drift.
- Draws on the graph of the formula's `salida_rol`; every other graph gets `limpiar_curva_formula()`.
- Re-applies itself after `_crear_graficas()` / `_actualizar_datos_graficas()`, since `set_datos()` rebuilds the curves. Mass and gravity arrive from `PanelIzquierdo.variablesCambiaron`.
- Each result row carries `detalles` (empty for potencia). `PanelCalculo._bloque_valores()` renders those instead of pico/media when present, because the peak of an *accumulated* curve says little on its own.

**Filtering is deliberately NOT required to calculate.** A low-pass flattens peaks, so gating the calculation behind a filter would bias every reported peak downward. What matters instead is **provenance**: `fuente_calculo` ("filtrada"/"original") is user-selectable in the panel, `_fuente_de_columna()` reports what was *actually* used, and `filtros_por_columna` keeps each signal's filter description. `fuente` is the same vocabulary the ranges use and is persisted as a column in the annotations CSV (additive; older files read back as `""`).

In `GraficaSenal`:

- `set_curva_formula(x, y, ...)` takes explicit `x` because the curve now covers only the marked stretches. **A NaN between segments plus `connect="finite"`** draws the ranges separately instead of joining them with a line that doesn't exist.
- `picos` carries one point per range, each with its own summary; the hover box shows the values of the range you're pointing at.
- The curve goes on a **second right-hand ViewBox** (`vb_formula`) when it can't share the signal's axis — watts or N·s against newtons never can. `_necesita_eje_propio()` decides on **scale, not just unit**: if either curve would occupy less than `FRACCION_MINIMA_EJE_COMPARTIDO` of the combined span, it gets its own axis.
- **Never call `vb_formula.autoRange()`**: it reframes X too, and since that ViewBox is X-linked to the main one it would drag the signal's view to the range stretch and desynchronise it from the other graphs. Only `enableAutoRange(axis="y")`.
- `_actualizar_caja_valor()` shows a `pg.TextItem` box **only while the cursor is over a peak or the curve**, and hides it on leaving. It carries the whole summary (peak, min, mean, RMS), so `_anclaje_caja()` compares the box's **real pixel height** (converted through `viewBox.viewPixelSize()`) against the free space on each side instead of using a fixed threshold.
- Don't measure a `TextItem`'s on-screen rect with `mapRectToScene()`: it ignores transformations, so the mapped rect comes back shrunk and useless. Compare `boundingRect().height()` (already in pixels) scaled by `viewPixelSize()`.

### Ranges, sub-ranges and notes

`GestorRangos` (`logica/rangos.py`) manages integer frame ranges (inclusive endpoints; sharing an endpoint counts as overlap). `listar()` returns them from left to right and assigns a visual `orden`; the stable `numero` remains the internal identity used by notes, sub-ranges and delete actions. Automatic names and colors follow `orden`, while custom names survive reordering. `agregar_ajustado()` snaps to the free stretch in the gesture's direction — this is the default behavior. `hay_superposicion()` and `agregar(..., permitir_superposicion=True)` support the opt-in overlap mode.

`GestorRangos(prefijo_nombre=...)` decides how unnamed ranges are called. Sub-gestores are built with `GestorRangos("Sub-rango")` so the panel, the notes and the annotations CSV all distinguish them from their parent. Projects saved before that change carry `Rango N` on their sub-ranges; `Formulas._crear_checkbox()` relabels those on display.

`AreaCentralGraficas` holds the state in three dicts, all keyed by string IDs:

- `gestores_rangos[columna]` — parent ranges, ID `"{columna}::{numero}"`
- `subgestores[(columna, numero_padre)]` — sub-ranges, ID `"{columna}::{padre}::sub::{numero}"`
- `notas[id]` — free-text note for any range or sub-range

`_rangos_para_panel()` flattens all of it into the flat list of dicts the `Formulas` panel consumes; each row carries `es_subrango`, `padre` and `nota`, and `Formulas` rebuilds the hierarchy (indented children, collapsible via a `▾/▸` toggle). Sub-ranges are created by **double-clicking a colored range** on a graph, which opens `VentanaRegion` (`ui/ventanaRegion/`) showing only that range's slice. Deleting a parent cascades to its sub-ranges and their notes.

Overlap settings live in `Cabecera` (session-only) and are pushed to `AreaCentralGraficas` via `set_superposicion_habilitada` / `set_no_preguntar_superposicion`; they apply to both ranges and sub-ranges.

### Colors and the colorblind mode

**All plot colors come from `logica/paleta.py`** — never hardcode a hex in `ui/` for a curve, a range or the selection preview. It holds two palettes (`estandar` and `daltonico`, the latter using the Okabe-Ito series) and a module-level active mode, toggled from `Configurar` → "Paleta accesible para daltonismo" (session-only, like the overlap settings).

The key invariant: **a range's visible color is a pure function of its left-to-right `orden`** (`paleta.color_rango(orden)`), while its internal `numero` stays stable. Saved annotations don't store colors for the same reason.

`AreaCentralGraficas.set_modo_daltonico()` is the entry point: it recolors every gestor and subgestor, then repaints via `GraficaSenal.aplicar_paleta()` — which re-pens the existing `curva_original`/`curva_filtrada` items instead of re-plotting, so the user's zoom survives. Open `VentanaRegion` windows are repainted too (each one carries a `clave_subgestor` for that). `Filtros.aplicar_paleta()` refreshes its color legend separately, wired in `VentanaPrincipal.init_ui()`.

Success/error feedback in `Filtros.actualizar_estado()` prefixes a `✓`/`✕` so the state doesn't depend on the green/red distinction alone.

### Persistence model — three distinct places

Be deliberate about which one a new setting belongs in:

| Where | What | Lifetime |
|---|---|---|
| `libiam_config.db` (SQLite) | column aliases, manual sections, **per-file mass** (`VariableArchivo`, keyed by `ruta_archivo`) | permanent, committed to repo |
| In-memory session state | gravity constant (`PanelIzquierdo.GRAVEDAD_TIERRA`, default 9.8), overlap settings | resets to defaults on restart — intentional |
| `archivos/` folder | `Guardar` writes `<nombre>.csv` (copy of the original) + `<nombre>_anotaciones.csv` (ranges, sub-ranges, notes) | user's work product |

`logica/proyecto.py` owns the `archivos/` folder: path helpers, `sanear_nombre()`, `listar_proyectos()`, and the read/write of the annotations sidecar (`CAMPOS_ANOTACIONES` is the fixed header). **Projects are not recorded in the DB at all** — the only thing linking a saved CSV to the user's work is the filename pairing `<nombre>.csv` ↔ `<nombre>_anotaciones.csv`. That is why the name is sanitized on save and the folder is not user-selectable.

- **Save** — `VentanaPrincipal._guardar_proyecto()`. Uses `QInputDialog` for the filename (deliberately **not** the native Windows file dialog).
- **Clean up** — `Configurar` → "Archivos guardados" → `LimpiarArchivosDialog` (`ui/cabecera/cabeceraPrincipal/limpiarArchivos.py`). The period combo (`proyecto.PERIODOS`) is only a *shortcut that pre-checks* matching rows; the list stays editable, so "a specific file" is just manual checking. Deletion goes through `proyecto.eliminar_proyectos()`, which removes both files of each pair and refuses any path whose parent isn't `archivos/`. Nothing is deleted without a `QMessageBox.question` listing the names.
- **Load** — `VentanaPrincipal._cargar_proyecto()`, from the `Cargar` header button. `CargarProyectoDialog` (`ui/cabecera/cabeceraPrincipal/cargarProyecto.py`) lists *only* `archivos/` with no way to navigate elsewhere. It then loads the CSV through `PanelIzquierdo.cargar_archivo_desde_ruta()` (so tree, info and right panel update as with a normal load) and **afterwards** calls `AreaCentralGraficas.importar_anotaciones()` — order matters, because `cargar_dataframe()` wipes the range state.

`importar_anotaciones()` rebuilds parents before children and uses `GestorRangos.restaurar()`, which keeps the internal number and skips overlap validation — it was already decided when the range was created. Visual order, automatic names and colors are recalculated from the horizontal position. Rows whose column isn't plotted in the current file are counted as discarded and reported to the user.

Note `archivos/` is **not** in `.gitignore`.

### Subframes

When a CSV has a `SubFrame` column, samples in the same frame are averaged (`groupby(frame).mean()`) in `AreaCentralGraficas` before plotting. `Filtros.fs_control` always represents the original frequency (detected or typed manually); `calcular_frecuencia_efectiva()` divides it by the subframes per frame and that effective value is sent to filters and formulas.

## Qt gotchas found in this codebase

These cost real debugging time; check them before reaching for a workaround:

- **`QCheckBox` cannot shrink below its text.** Its `minimumSizeHint()` equals its `sizeHint()`, so in the narrow right panel a long label pushes trailing buttons out of the viewport (horizontal scrollbars are disabled there). `Formulas` handles this by truncating labels with `…` (full text in the tooltip) *and* setting an explicit `setMaximumWidth`. `setMinimumWidth(0)` does **not** work; `QSizePolicy.Ignored` shrinks it but collapses the text.
- **`QListWidget` + `InternalMove` discards `setItemWidget` widgets.** A drag moves the `QListWidgetItem`, so item data (text, `UserRole`, check state) survives but embedded widgets do not. `ConfigColumnas` therefore uses native items with `Qt.ItemIsUserCheckable` instead of embedded rows.
- Items in a reorderable list should clear `Qt.ItemIsDropEnabled` so drops land *between* rows rather than onto one.
- Block `itemChanged` while populating a checkable list, or the initial `setCheckState` calls fire the handler.
- **pyqtgraph: remove an item from the same container you added it to.** `PlotWidget.addItem()` and `viewBox.addItem()` keep *separate* bookkeeping, so `self.removeItem(item)` silently does nothing for an item added via `vb.addItem(item)` — it stays on screen forever. `GraficaSenal` stores `_vista_items` at creation for exactly this. A leaked item is worse than a stray pixel: it still counts for `autoRange()`, so one orphaned peak marker at 1138 N kept the Fx axis pinned to 0–1200 and flattened the real signal.
- Decorations that shouldn't influence the view (markers, hover boxes) must be added with `addItem(item, ignoreBounds=True)`.
- `TextItem` is clipped by its ViewBox: anchoring a tooltip box *above* a point puts it off-screen at the highest peak. `_anclaje_caja()` places it below by default and only flips up near the floor.
- `%g` renders typical force values as `1.14e+03`. Use `formulas.formatear_valor()` for anything a user reads.
- **`QLabel` rich text drops `margin-bottom` on a `<div>` whose children are all `<div>`s** — a wrapper around an entry separates nothing, and `<p>` margins are ignored too. Put the margin on the entry's **last leaf div** (that's what `Formulas._divs_con_separacion()` does). Verify with `heightForWidth()`, not by eye: the offscreen renderer has no fonts, so spacing can't be judged from a screenshot.

## Conventions

- **App identity is centralized in `logica/app_info.py`** — version, authors, institution and the suggested citation all derive from `VERSION`. Change the version there only.
- Custom pyqtgraph subclasses live at the top of `areaCentralGraficas.py`: `EjeDecimal` (axis without `×1e-6` SI-prefix factors) and `ViewBoxZoom` (horizontal wheel zoom).
- Widget styling goes in the `.qss` files (matched by `setObjectName`), not inline `setStyleSheet`, except where a per-row dynamic color is needed (range checkboxes use the range's own color).
- **The whole app is dark.** `ventana.qss` opens with a blanket `QWidget { background-color: #333337; color: #FFFFFF; }`, so dialogs are dark too — including the light-looking header. A new dialog should inherit that background and only style its controls (`#252526` lists, `#1E1E1E` inputs, `#3E3E42` borders, `#1976D2` accent). Styling one light produces white-on-white labels, since inline `font-size`-only styles keep the inherited white text.
- Icons are stroke-only SVGs in `utilidades/icons/`, 24×24, `stroke-width="2"`, colored `#374151` for the light header and `#8A8A8A`/`#42A5F5` for the dark right panel. QSS cannot recolor an SVG icon, so a button with two visual states needs **two files** (e.g. `nota_agregar.svg` / `nota_editar.svg` on the range note button) rather than a `color:` rule.
- Sample/test CSVs live in `utilidades/resources/`; `tests/` references `Carlos Bigolotti Americano CM Fuerza solo.csv`.
- Several modules still contain `print("[DEBUG] ...")` calls; match or remove them deliberately rather than by accident.
