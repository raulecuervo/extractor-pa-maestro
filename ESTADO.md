# Estado del proyecto — Extractor maestro de planes de acción

Listado de lo realizado y lo pendiente. Hoja de ruta detallada (hitos, esfuerzo,
dependencias, criterios de aceptación): **`PLAN_DESARROLLO.md`**. Mejoras y
limitaciones: **`docs/MEJORAS_Y_LIMITACIONES.md`**.

## ✅ HECHO

### 1. Revisión y extracción de código de los 12 proyectos (`../_codigo_extraido_pp/`)
- Revisión a profundidad de los 12 aplicativos.
- Extracción **comentada** del código de extracción Excel + alertas, un `.md` por
  proyecto de política pública (9) + triage de visores/RAG.
- `00_INDICE_Y_COMPARATIVO.md` (matriz comparativa).
- `PLAN_EXTRACTOR_MAESTRO.md` (análisis a fondo de los 7 extractores + plan por fases).
- ZIP descargable `codigo_extraido_pp.zip`.

### 2. Librería `extractor_pa` (extractor maestro)
- **Fase 1 — Núcleo (formato nuevo):** loader, localización flexible de hoja,
  detector de formato, resolución de columnas **por encabezado** + fallback,
  lector de filas con pre-filtro, modelo canónico serializable.
- **Fase 2 — Celdas combinadas:** normalización en 4 capas + **ascensión de la
  fila vigente**.
- **Fase 3 — Año de vigencia:** `meta_vigencia_actual/_anterior`.
- **Fase 4a — Fichas técnicas:** lectura de hojas de ficha con **5 convenciones
  de nombre** (IR#/IP#, R./P., R /P , código pelado, guion bajo) → metodología,
  unidad de medida, fuentes, días de rezago, descripción, observaciones.
- **Fase 4b — Formato antiguo:** variante con **bloque financiero** (CTI),
  IR/IP por ancla + `RegistroFinanciero`.
- **Fase 5 — Consistencia:** `inconsistencia_en_ir` y `codigo_ip_duplicado`.
- **Catálogo consolidado** (`catalogo.py`, 64 tipos, 6 capas) + **motor de reglas
  de negocio V0–V18** (`validacion.py`) + `crear_alerta` centralizado en el catálogo.
- **Fase 6 — Adaptadores de salida** (`exportadores.py`): JSON, CSV, Excel y
  DataFrame (pandas), por plan o **consolidado multi-plan**.
- **Capa de seguimiento — Fase S1** (`extractor_pa/seguimiento/`): extracción del
  `.xlsb` (Avance Cuantitativo/Cualitativo) al modelo canónico de seguimiento
  (histórico indicador×año×trimestre), detección por anclas + metadatos del nombre.
  Comparativo: `PLAN_EXTRACTOR_SEGUIMIENTO.md`.
- **Validado:** 38 planes `.xlsx` + **55 seguimientos `.xlsb`**, 0 errores · **16 pruebas**.

### 3. Reportes de calidad del dato (`../_codigo_extraido_pp/`)
- `REPORTE_FALTANTES_UNIDAD_FICHA.md` + `faltantes_unidad_ficha.csv`
  (442 sin unidad / 281 sin ficha, depurado).
- `REPORTE_CODIGOS_SIN_FICHA.md` (códigos por política).

### 4. Documentación
- `README.md`, `CHANGELOG.md`, `docs/CATALOGO_ALERTAS.md` (regenerable),
  `docs/MEJORAS_Y_LIMITACIONES.md`.

---

## ⬜ PENDIENTE

### A. Reportes accionables adicionales — ✅ HECHO
- ✅ **Hallazgos del plan por política** (V0–V18 + consistencia + extracción):
  `REPORTE_HALLAZGOS_POR_POLITICA.md` + `hallazgos_por_politica.csv`
  (`scripts/reporte_hallazgos.py`).
- ✅ **Hallazgos del seguimiento por política** (consistencia del reporte + pares
  base→nuevo): `REPORTE_HALLAZGOS_SEGUIMIENTO_POR_POLITICA.md` + csv
  (`scripts/reporte_hallazgos_seguimiento.py`).
- (Ya antes) faltantes de unidad/ficha por política.

### B. Adaptador a ORM relacional (opcional)
- Salida a un **ORM relacional versionado** (modelo de `seguimiento-pp-sdis`).
  Hecho: JSON/CSV/Excel/DataFrame; falta el adaptador a base de datos relacional.

### C. Pendientes menores del extractor
- ~~Ignorar archivos temporales `~$`~~ — hecho en `scripts/gen_consolidado.py`
  (replicar el filtro en los demás scripts de lote).
- Afinar el **parser de fechas** (quedan ~40 `fecha_invalida` por algún formato extra).
- **V4** sector/entidad contra catálogo oficial (requiere inyectar los catálogos).
- `objetivo_sin_resultados` y `jerarquia_ip` (requieren extraer objetivos como
  entidad y validar jerarquía — hoy el código IR se deriva del IP).
- Metadatos del **formato antiguo** (nombre de política no siempre en B4).

### D. Capa de SEGUIMIENTO (en progreso)
- ✅ **S1 — Extracción** del `.xlsb` (Avance Cuantitativo/Cualitativo) → modelo
  canónico (hecho; validado en 55 archivos).
- ✅ **S2 — Match con el plan** (códigos N.N[.N] → IR/IP) + **consolidación por
  período** (Q/S/Anual). Captura además tipo de anualización, ponderación, línea
  base, estado y fechas del `.xlsb` (hecho; validado: BTI 38/38 emparejados).
- ✅ **S3 — Alertas de consistencia** (15 tipos: estabilidad, retroactividad,
  escala, avance vs meta, acumulados, %, cualitativo, nuevo/faltante) +
  **semáforo/PHV** (rojo≤50/amarillo≤75/naranja>125). Hecho y validado.
- ✅ **S4 — Adaptadores de salida** del seguimiento (JSON/CSV/Excel, formato largo
  dim+fact, por archivo y consolidado multi-archivo). Hecho y validado.
- ⬜ **Cualitativas RN-CUL** (justificación obligatoria de rezago/sobrecumplimiento)
  y **operativas** (vencimiento, sin responsable…) — requieren contexto de
  operación (períodos/usuarios), fuera del extractor de archivos.

### E. Aseguramiento y adopción
- ✅ **Fase 7 — Golden files + paridad:** huellas estables + corpus + test de
  regresión (8 golden); paridad maestro vs legados (plan 8/8, seguimiento 6/6).
  Ver `docs/REGRESION_Y_PARIDAD.md`.
- ✅ **Sprint 0 (v0.9.2):** parser de fechas robusto, alerta `escala_mezclada`,
  métricas en `Metadatos`, `~$` en todos los scripts. (`fecha_invalida` 40→14.)
- ✅ **Hito 1 — Empaquetado + CLI (v0.9.3):** `pip install -e .`, console script
  `extractor-pa` (plan/seguimiento/validar), CI, `tests/test_cli.py`.
- ✅ **Hito 2 — Endurecer regresión (v0.9.4):** golden completo (97 huellas, todas
  las políticas, `pytest -m slow`) + unit tests por etapa (`test_unidades.py`).
- ✅ **Hito 3 — Exactitud (v0.9.5–0.9.7):** C1 nombre de política robusto, D2
  metadatos de seguimiento, **C4 metas no numéricas** (detectado por la auditoría
  de migración). C3/D1/D3 diferidos (bajo impacto).
- ✅ **Hito 5 — Tablero de cumplimiento (v0.9.8):** `extractor_pa/tablero.py` +
  `scripts/gen_tablero.py` → `../_codigo_extraido_pp/TABLERO_CUMPLIMIENTO.html`
  (semáforo de avance + hallazgos por política, ordenable y filtrable).
- ✅ **Fase 8 / Hito 8 — Migración de los 9 aplicativos:** 6 migrados (adaptador +
  gate de paridad + bitácora c/u); **5 activados** y verificados:
  - `extractor-planes-accion` (plan nuevo+antiguo) · `validador-plan-accion` (7/7,
    arregla DRAFE) · `alertas-seguimientos` (57/57, alertas byte-idénticas) ·
    `seguimiento-pp-sdis` (3/3, arregla extractor roto) · `sispp-sdis` (test_etl 10/10) ·
    `generador-seguimiento` (**byte-idéntico** 8/8, activado).
  - `sispp-gobierno` (pipeline-fuente) **activado y validado aguas abajo** (etapas
    02-06 consumen los CSVs del maestro; 49 tests passed).
  - **Diferido:** `creador-planes-accion` (extracción entrelazada con ORM, tests no
    corren en este entorno).
  - **N/A:** `sistema-seguimiento-v3` (no extrae de Excel).
- (Detalle histórico de las primeras migraciones:)
- 🔄 **Migración (1/9):** `extractor-planes-accion` migrado y
  **activado** (formato nuevo, v0.9.6), con adaptador + gate de paridad + brecha
  `dir_responsable` cerrada; verificado end-to-end. Faltan los otros 8 aplicativos
  y retirar el legado tras validación.
- Detalle y orden completo en **`PLAN_DESARROLLO.md`**.

---

## Estado por fases (resumen)

| Fase | Descripción | Estado |
|---|---|:---:|
| 0 | Análisis, extracción de código, plan | ✅ |
| 1 | Núcleo formato nuevo | ✅ |
| 2 | Celdas combinadas (4 capas + ascensión) | ✅ |
| 3 | Año de vigencia | ✅ |
| 4a | Fichas técnicas | ✅ |
| 4b | Formato antiguo + financiero | ✅ |
| 5 | Consistencia + catálogo + reglas V0–V18 | ✅ |
| 6 | Adaptadores de salida (JSON/CSV/Excel/DataFrame) | ✅ |
| 7 | Golden files / regresión + paridad con legados | ✅ |
| 8 | Migración de aplicativos | ⬜ |
| S1 | Seguimiento — extracción `.xlsb` (anclas + histórico) | ✅ |
| S2 | Seguimiento — match con plan + consolidación por período | ✅ |
| S3 | Seguimiento — alertas de consistencia (15) + semáforo/PHV | ✅ |
| S4 | Seguimiento — adaptadores de salida | ⬜ |
