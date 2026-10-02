# Fase 7 — Regresión (golden files) y paridad con los legados

Asegura que el extractor maestro (a) no sufra **regresiones** entre versiones y
(b) produzca resultados **equivalentes** a los extractores legados — la evidencia
para migrar con confianza.

## A. Golden files (regresión del maestro)

- **Huella estable** por archivo (`extractor_pa/regresion.py`): códigos IR/IP,
  conteos, años y alertas por tipo (sin campos no deterministas como el año de
  vigencia).
- **Corpus** (`tests/corpus.py`): curado (BTI, Educación, LGBTI, CTI,
  Negra-Afro + Adultez en formato antiguo con bloque financiero; 3 seguimientos)
  y completo (todos los planes de `01_planes_accion` y seguimientos de
  `02_seguimientos`, pruebas `slow`).
- **Raíz del corpus**: variable de entorno `EXTRACTOR_PA_CORPUS` (carpeta que
  contiene `sispp-gobierno/` y `alertas-seguimientos/`); sin ella,
  `C:\Users\RaulEsteban\Proyectos`. Sin corpus (p. ej. el CI) las pruebas con
  datos reales se saltan.
- **Golden** en `tests/golden/<clave>.json` (generados con `scripts/gen_golden.py`).
- **Prueba** `tests/test_golden.py`: re-ejecuta el maestro y compara contra la
  huella esperada; falla ante cualquier deriva. La comparación ignora el campo
  `archivo` (un renombrado no es una regresión).

### Claves: la política, no el nombre del archivo

La clave es `plan_<slug>` / `seg_<slug>`, con el slug de la política sacado del
nombre del archivo sin prefijos de catálogo (`29__`, `Decreto_193_de_2022__`),
sin prefijo de tipo (`PA_`, `PA_PP_`, `Plan Accion PP_`) y sin sufijo de versión
(`_V4-26_DP_v1`):

| Archivo | Clave |
|---|---|
| `29__pa_bti_v4-26_dp_v1.xlsx` (antes `PA_BTI_V4-26_DP.xlsx`) | `plan_bti` |
| `Decreto_193_de_2022__pa_trata_v4-26_dp_c_v1.xlsx` | `plan_trata` |
| `Plan Accion PP_Negra-Afro_V3_2025 15.12.2025.xlsx` | `plan_negra_afro` |
| `Acción Climática.xlsb` | `seg_accion_climatica` |

Así un renombrado conserva la clave, y una versión nueva del plan **falla** con
sus diferencias en vez de saltarse: se revisan y se regenera. Si cambia el
nombre de la política misma (Trabajo Digno → Trabajo Decente), se renombra el
golden a mano. Detalle en el docstring de `tests/corpus.py`.

### La regresión no se apaga en silencio

En la suite rápida (`pytest`), sin extraer nada:

- `test_corpus_cubierto_por_golden` **falla** si el corpus existe pero ningún
  archivo tiene golden (lo que pasó al renombrar los planes en 2026-09), y
  advierte de archivos sin golden y de golden huérfanos.
- `test_corpus_claves_unicas` falla si dos archivos dan la misma clave (dos
  versiones del mismo plan en la carpeta).
- Una política curada que falta en un corpus existente falla, no se salta.

### Actualizar tras un cambio intencional

```
python scripts/gen_golden.py --revisar   # qué cambiaría, sin escribir
python scripts/gen_golden.py             # escribe; lista las diferencias con el golden previo
python scripts/gen_golden.py --podar     # además borra los golden huérfanos
```

Una diferencia puede ser una regresión real: revisarla contra el Excel antes de
aceptar el golden nuevo.

## B. Paridad con los extractores legados

`scripts/paridad_legados.py` compara los **conjuntos de códigos** de indicadores
extraídos por el maestro vs el legado, sobre los mismos archivos reales.

### Resultado plan (maestro vs `extractor-planes-accion`)
- **8/8** archivos con el **mismo número** de indicadores.
- **7/8** con conjuntos de códigos **idénticos**.
- 1 diferencia (**PA_Bicicleta**): el maestro extrae `5.1`, el legado `5`. La
  celda real es `"5. 1 Aumento de la productividad…"` (con espacio); el maestro
  **normaliza correctamente** a `5.1` (confirmado porque sus productos son
  `5.1.1`–`5.1.6`), mientras el legado se queda en `5`. → **el maestro es más
  correcto**; paridad efectiva **8/8**.

### Resultado seguimiento (maestro vs `alertas-seguimientos`)
- **6/6** archivos con conjuntos de códigos **idénticos** (maestro por anclas
  dinámicas vs legado por columnas fijas → mismos resultados).

## Conclusión

El maestro **reproduce** los resultados de los extractores legados (e incluso
corrige un caso de código con espacio). Junto con los golden files, esto da la
base para la **Fase 8 — migración**: reemplazar cada extractor legado por la
librería, comparando su salida contra el golden antes de retirarlo.
