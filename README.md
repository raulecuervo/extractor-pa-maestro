# extractor-pa — Extractor maestro de planes de acción

Librería Python independiente que extrae, desde los Excel de **planes de acción
de política pública** (formato SDP/SDIS), un **modelo de datos canónico** único
(política → objetivos → indicadores de resultado/producto → metas anuales), para
que todos los aplicativos (validador de reglas, alertas de seguimiento,
dashboards) consuman el mismo contrato sin importar la plantilla de origen.

Diseñada combinando lo mejor de los 7 extractores existentes
(ver `../_codigo_extraido_pp/PLAN_EXTRACTOR_MAESTRO.md`).

## Instalación

Desarrollo (editable, desde el repo):
```bash
pip install -e .              # núcleo (planes .xlsx)
pip install -e ".[xlsb]"      # + seguimiento .xlsb (pyxlsb); el .xlsx no lo necesita
pip install -e ".[xlsb,pandas,dev]"   # todo + DataFrame + pruebas
```

Para los **aplicativos que la consumen**, fijar un tag. El repositorio es
público; las versiones son los tags `vX.Y.Z` y cada uno trae su Release con el
wheel adjunto (lo publica `.github/workflows/release.yml`):
```bash
pip install "extractor-pa @ git+https://github.com/raulecuervo/extractor-pa-maestro.git@vX.Y.Z"
pip install "extractor-pa[xlsb] @ git+https://github.com/raulecuervo/extractor-pa-maestro.git@vX.Y.Z"  # si lee .xlsb
# o el wheel del Release, en entornos sin git:
pip install https://github.com/raulecuervo/extractor-pa-maestro/releases/download/vX.Y.Z/extractor_pa-X.Y.Z-py3-none-any.whl
```
En `requirements.txt` de cada app, fijar `extractor-pa @ git+…@vX.Y.Z` (o `extractor-pa[xlsb] @ …`).

## Consumidores y versiones

Cada aplicativo fija su propio tag, y las fórmulas del seguimiento (PAF, TID,
PAV, MES, AV) han cambiado entre versiones: **dos aplicativos con pines distintos
muestran cifras distintas para el mismo indicador.** Para verlo:
```bash
python scripts/pines_consumidores.py     # tag que fija cada app vecina frente a la versión actual
```
Qué aplicativo usa qué funcionalidad, con sus archivos de entrada:
[`docs/CONSUMIDORES.md`](docs/CONSUMIDORES.md).

Las versiones que mueven cifras llevan la marca **«Cambia cifras»** en
`CHANGELOG.md` (índice al inicio). Subir el pin de una app por encima de una de
ellas cambia lo que esa app muestra: conviene subir juntas las apps que se comparan
entre sí.

### Estabilidad por capa

| Capa | Estabilidad | La usan |
|---|---|---|
| `extraer_plan_accion` y el modelo canónico (`ResultadoExtraccion`, IR, IP, `Objetivo`) | Estable | validador, extractor-planes-accion, creador, seguimiento-pp-sdis, sispp-gobierno, sispp-SDP, sispp-sdis |
| `extractor_pa.seguimiento`: extracción, cruce, `metricas`, `validacion_seg` | Estable. Lo que importan los aplicativos está fijado en `tests/test_contrato_consumidores.py` | alertas-seguimientos, generador-seguimiento, sispp-gobierno, sispp-SDP, sispp-sdis |
| Reglas V0–V18, catálogo oficial (V4), gobernanza, decisiones, exportadores, tablero y CLI | Disponibles, sin aplicativos que las usen: pueden cambiar entre versiones menores | scripts de este repo |

Antes de renombrar o mover algo de las dos primeras filas, búsquelo en
`tests/test_contrato_consumidores.py`: esa prueba falla si desaparece un nombre que
usa un aplicativo.

## Catálogo oficial / V4 (opcional)

La validación de **sector/entidad oficial** (regla V4) y la **normalización difusa**
son opt-in: solo se activan si se inyecta un catálogo.
```python
from extractor_pa import extraer_plan_accion, CatalogoOficial, sugerencias_normalizacion
res = extraer_plan_accion("plan.xlsx", incluir_reglas_negocio=True,
                          catalogo_oficial=CatalogoOficial())   # dispara V4
sugerencias_normalizacion(res)   # [{'campo':'sector_responsable','original':'GestiónPública','sugerido':'Gestión Pública'},…]
```
El fuzzy requiere `pip install extractor-pa[fuzzy]` (RapidFuzz). Sin catálogo, V4 no se ejecuta.

**Reaplicar correcciones aprobadas (F2)**: una vez que un humano aprueba las
sugerencias, se persisten y se reaplican determinista en cada corrida (sin fuzzy):
```python
from extractor_pa import RegistroDecisiones, aplicar_decisiones
reg = RegistroDecisiones("decisiones/entidades.json")
reg.aprobar_sugerencias(sugerencias_normalizacion(res, CatalogoOficial()))  # o reg.guardar(...)
aplicar_decisiones(res, reg)   # reescribe sector_responsable/entidad_responsable de IR/IP
```

## Gobernanza / triage de alertas (opcional)

Las reglas regeneran las alertas en cada corrida. Para que las decisiones humanas
sobrevivan, cada alerta tiene una **clave estable** (hash de sus campos
identitarios, no de la redacción) cuyo estado vive en un store JSON con bitácora.
```python
from extractor_pa import extraer_plan_accion, RegistroGobernanza
res = extraer_plan_accion("plan.xlsx", incluir_reglas_negocio=True)
reg = RegistroGobernanza("decisiones/alertas_estado.json")   # ruta inyectable
rec = reg.reconciliar(res.alertas)         # clasifica por clave + estado
reg.set_estado([rec.items[0].clave], "en_gestion", nota="oficio 123")
rec.pendientes()       # nueva | en_gestion
rec.desaparecidas      # claves abiertas que ya no aparecen → autocierre
```
Estados: `nueva → en_gestion → resuelta | descartada`. La clave es **byte-idéntica**
a la de `sispp-gobierno`, así que interoperan. Solo stdlib (sin dependencias extra).

## CLI

```bash
extractor-pa --version
extractor-pa plan PLAN.xlsx --reglas --anio 2026 --json salida.json --excel salida.xlsx
extractor-pa seguimiento SEG.xlsb --csv carpeta_salida     # o SEG.xlsx (formato 3.4)
extractor-pa validar PLAN.xlsx --anio 2026      # lista hallazgos V0–V18 por tipo
```
(equivalente: `python -m extractor_pa ...`). Salidas: `--json`, `--csv` (carpeta,
varias tablas), `--excel` (varias hojas). Código de salida ≠0 si la extracción falla.

## Qué hace

- **Carga** del libro (con acceso a celdas combinadas).
- **Localización flexible** de la hoja del plan (exacto → fuzzy → matriz → >40 col).
- **Detección de formato** (nuevo / antiguo).
- **Resolución de columnas por encabezado** con resolución de celdas combinadas,
  **fallback posicional** y anclas **configurables**. Las filas de encabezado se
  ubican por el ancla «Resultado esperado»: 9–11 en la plantilla vigente, 10–12 en
  los planes 2021–2025 y 24–26 cuando la cabecera lista los corresponsables.
- **Pre-filtro** de filas espurias (totales) antes del forward-fill.
- **Normalización avanzada de celdas combinadas (Fase 2):** 4 capas
  (ffill libre de identificadores → `peso_objetivo` por objetivo → campos IR por
  resultado) **+ ascensión de la fila vigente** (si la 1ª fila del IR es histórica
  No Vigente y la vigente está abajo, gana la vigente). Evita la contaminación
  entre IR distintos.
- **Escala de %**: las metas con `number_format` de porcentaje se normalizan
  (`0.0736` → `7.36`).
- **Año de vigencia (Fase 3):** `anio_vigencia` / `anio_vigencia_anterior` y
  `meta_vigencia_actual` / `meta_vigencia_anterior` por indicador, con prioridad
  (año explícito → año actual → anterior más cercano → primero). Sin
  `anio_vigencia` se usa el año del reloj; el usado queda en
  `metadatos.anio_corte`, y pasarlo de nuevo reproduce la extracción.
- **Fichas técnicas (Fase 4a):** lee las hojas de ficha («Ficha técnica IR#/IP#»,
  «F IR#/IP#», «R./P.», «IR_/IP_» o el código solo) y completa `metodologia`,
  `unidad_medida`, `fuente_datos`, `dias_rezago`, `descripcion`, `observaciones`.
  La unidad es la opción pegada a la casilla marcada con «x» en la cuadrícula
  (tres opciones por fila, cada una con su casilla a la derecha); «otro» marcado,
  o ninguna marca, remite a lo escrito en «¿Cuál?» (unidad libre).
- **Formato antiguo / bloque financiero (Fase 4b):** detecta la variante con
  bloque financiero (`MAPEO_ANTIGUO`), resuelve IR/IP **por ancla** y extrae el
  bloque financiero (`RegistroFinanciero`: costo, recurso, fuente, proyecto, por año).
  Los grupos de cada año se reconocen por sus encabezados («Costo Estimado» o
  «Costo», con o sin código de proyecto).
- **Deduplicación de IR** y extracción de IP, con **alertas de extracción**.
- **Consistencia (Fase 5):** detecta inconsistencias entre las filas de un mismo
  IR (`inconsistencia_en_ir`) y códigos de IP duplicados (`codigo_ip_duplicado`).
- **Catálogo consolidado de alertas** (`catalogo.py`, tipos de los 9 aplicativos)
  como única fuente de nivel/descripción. Doc regenerable: `docs/CATALOGO_ALERTAS.md`
  (`python scripts/gen_catalogo.py`).
- **No lanza por el contenido del archivo:** un fallo inesperado queda como la
  alerta fatal `error_extraccion`; si falla una etapa opcional (fichas o reglas),
  queda como `error_etapa_opcional` y el plan se conserva.
- **Motor de reglas de negocio V0–V18** (`validar_reglas(resultado)`):
  ponderación, tipología, fechas, metas, línea base, códigos. Opt-in en el
  pipeline con `incluir_reglas_negocio=True`.
- **Modelo canónico** serializable (`to_dict()` → JSON, objetivos incluidos).
- **Adaptadores de salida (Fase 6):** JSON, CSV, Excel y DataFrame (pandas),
  por plan o **consolidado multi-plan** (`exportar_*` / `exportar_*_consolidado`),
  con una tabla por entidad: metadatos, IR, IP, objetivos, alertas y financiero.

- **Capa de seguimiento** (`extractor_pa/seguimiento/`):
  - **S1** — extrae el `.xlsb` o el `.xlsx` (Avance Cuantitativo/Cualitativo) al
    modelo canónico (histórico indicador×año×trimestre), detección por anclas. El
    formato se reconoce por el contenido, no por la extensión.
  - **S2** — `cruzar_con_plan(seg, plan)` empareja por código IR/IP; `consolidar`
    consolida los avances por período (Q/S/Anual, respeta SUMA).
  - **S3** — `validar_consistencia(base, nuevo)` (15 alertas: estabilidad,
    retroactividad, escala, avance vs meta…) y `semaforo_de(pct)` (rojo/amarillo/
    verde/naranja).

```python
from extractor_pa.seguimiento import extraer_seguimiento, cruzar_con_plan, consolidar
seg = extraer_seguimiento("Seguimiento a Productos PP BTI S1-25.xlsb")
cruzar_con_plan(seg, plan)            # plan = extraer_plan_accion(...)
filas = consolidar(seg, 2024, "Anual")
```

- **Regresión + paridad (Fase 7):** golden files (`tests/golden/`) + paridad
  contra los extractores legados (plan 8/8, seguimiento 6/6). Ver
  `docs/REGRESION_Y_PARIDAD.md`.

Estado y pendientes: `ESTADO.md`. Planes de trabajo anteriores: `docs/historico/`.

> Limitación conocida (Fase 2): la ascensión corrige los campos de identidad del IR
> (nombre, vigencia, peso, sector…); las **metas anuales** y `meta_final` se siguen
> leyendo de la primera fila física (se respeta su escala %). Lo mismo hace el
> extractor original de sispp-gobierno. Se afina en una fase posterior si hace falta.

## Uso

```python
from extractor_pa import extraer_plan_accion

# anio_vigencia: año de corte para meta_vigencia_actual/_anterior (opcional).
res = extraer_plan_accion("ruta/al/plan.xlsx", anio_vigencia=2026)

print(res.metadatos.nombre_politica, res.metadatos.formato_detectado)
for ir in res.indicadores_resultado:
    print(ir.codigo_ir, ir.nombre_indicador, ir.metas_por_anio,
          ir.anio_vigencia, ir.meta_vigencia_actual)
for a in res.alertas:
    print(a.nivel, a.tipo, a.descripcion)

datos = res.to_dict()   # dict apto para JSON
```

Anclas personalizadas (otra variante de plantilla):

```python
from extractor_pa import extraer_plan_accion, MapeoColumnas

mapeo = MapeoColumnas(hoja="Matriz PPMYEG", fila_datos=12)
res = extraer_plan_accion("plan_mujer.xlsx", mapeo=mapeo)
```

## Estructura

```
extractor_pa/
  __init__.py            API pública
  modelo.py              dataclasses canónicas (+ niveles de alerta)
  config.py              MapeoColumnas (anclas configurables)
  utilidades.py          _norm, a_float (europeo), extraer_codigo, leer_celda_escala (%)
  alertas.py             constructor de alertas
  loader.py              apertura del workbook
  localizador_hoja.py    selección flexible de hoja
  detector_formato.py    nuevo / antiguo
  resolutor_columnas.py  columnas por encabezado + celdas combinadas + fallback
  lector_filas.py        lectura, pre-filtro, forward-fill
  normalizador.py        celdas combinadas: 4 capas + ascensión de fila vigente (Fase 2)
  vigencia.py            año de vigencia y metas comparables (Fase 3)
  lector_fichas.py       fichas técnicas: metodología, unidad, días de rezago (Fase 4a)
  consistencia.py        inconsistencias entre filas del IR + IP duplicados (Fase 5)
  catalogo.py            catálogo consolidado de alertas (fuente única)
  catalogo_oficial.py    sectores/entidades oficiales: regla V4 + normalización difusa
  validacion.py          motor de reglas de negocio V0–V18 sobre el modelo canónico
  gobernanza.py          triage persistente de alertas: clave estable + estados + reconciliación/autocierre + auditoría
  decisiones.py          decisiones humanas de entidad/sector: store + auditoría + reaplicación (puente desde B1)
  exportadores.py        salidas: JSON/CSV/Excel/DataFrame + consolidado multi-plan
  tablero.py             tablero HTML de cumplimiento por política
  regresion.py           huellas estables para golden files y paridad
  seguimiento/           SUB-PAQUETE de seguimiento (.xlsb/.xlsx): loader, resolutor
                         por anclas, metadatos, extractor → ResultadoSeguimiento
  estrategias/
    base.py              interfaz EstrategiaExtraccion
    nuevo.py             motor único de extracción (nuevo y antiguo)
    antiguo.py           subclase con otro nombre: el formato antiguo solo cambia el MapeoColumnas
  pipeline.py            orquestador extraer_plan_accion()
tests/
  test_smoke.py                  end-to-end con Excel sintético
  test_contrato_consumidores.py  nombres que importan los aplicativos
  test_golden*.py                regresión contra planes y seguimientos reales
scripts/                         lotes, reportes, golden y pines_consumidores.py
```

## Pruebas

```bash
python -m pytest -q          # rápida; los golden se saltan si los archivos reales no están
python -m pytest -m slow -q  # regresión completa sobre todas las políticas reales
ruff check extractor_pa scripts tests
```
CI (`.github/workflows/ci.yml`) corre ruff y las pruebas en Python 3.10–3.14.
