# Changelog — extractor-pa

Formato basado en fases del plan (`../_codigo_extraido_pp/PLAN_EXTRACTOR_MAESTRO.md`).
Capa de seguimiento: ver `../_codigo_extraido_pp/PLAN_EXTRACTOR_SEGUIMIENTO.md`.

## [0.9.9] — Seguimiento: metas acumuladas (migración etapa 04 sispp-gobierno)
### Añadido
- `IndicadorSeguimiento.metas_acumuladas` (`'2024' -> meta acumulada hasta la
  vigencia`); el resolutor detecta el bloque (col_pct_vig − n + i) y el extractor
  lo llena. Habilita la migración de la etapa 04 de seguimiento de `sispp-gobierno`
  (formato largo) con datos cuantitativos byte-idénticos. Suite: 106 pruebas.

## [0.9.8] — Hito 5: Tablero de cumplimiento por política
### Añadido
- `extractor_pa/tablero.py`: ensambla por política PLAN + SEGUIMIENTO (empareja por
  sigla normalizada), cruza indicadores, calcula **semáforo de avance** (% vigencia)
  y conteo de hallazgos V0–V18, y **renderiza un HTML navegable** autocontenido
  (KPIs, leyenda, tabla ordenable + filtro). `construir_tablero` / `render_html`.
- `scripts/gen_tablero.py` → `../_codigo_extraido_pp/TABLERO_CUMPLIMIENTO.html` + csv.
- `tests/test_tablero.py` (emparejamiento + render).

## [0.9.7] — C4: conservar metas no numéricas (auditoría de migración)
### Añadido / Cambiado
- **C4**: `estrategias/nuevo.py` ahora **conserva el texto crudo de las metas no
  numéricas** (`metas_de` / `meta_final_de`): p. ej. `'más 0.01 punto'`,
  `'Publicación (Línea base)'`, `'Levantamiento línea base'`. Antes se descartaban.
  Hace que `meta_no_numerica` (V6/V7) pueda dispararse y que el maestro sea un
  **superconjunto fiel** del legado en metas.
- Efecto: `anios_detectados` puede incluir un año que solo tenía metas de texto
  (columna real del plan). Golden regenerado.
### Auditoría de pérdidas (migración, 37 planes nuevos)
- Método: re-ejecutar el legado **sin forward-fill** para distinguir arrastre vs
  dato genuino (`../extractor-planes-accion/auditar_perdidas.py`).
- Resultado: **103** casos = arrastre (forward-fill) del legado → **maestro
  correcto**; **95** = metas de **texto** que el maestro descartaba → **cerrado
  por C4**; **0** pérdidas numéricas; **0** en otros campos. (Los 50 "numéricos" de
  una corrida previa eran falsos positivos del plan **antiguo** CTI mal clasificado
  como nuevo por el detector del aplicativo.)

## [0.9.6] — Hito 8: Migración (1) + cierre de brecha
### Añadido
- **`direccion_responsable` / `direccion_corresponsable`** en el modelo IP y su
  extracción en el formato nuevo (`estrategias/nuevo.py` lee `dir_resp`/`dir_corresp`,
  ya resueltos por el resolutor). Cierra la brecha detectada al migrar
  `extractor-planes-accion` (campos `dir_responsable`/`dir_corresponsable`).
### Migración (en `../extractor-planes-accion/`)
- Adaptador `extractor_maestro.py` (contrato del legado, vía `extractor_pa`),
  gate de paridad `comparar_maestro.py` y bitácora `MIGRACION_EXTRACTOR_PLANES.md`.
- **Activado**: el orquestador usa el maestro para el formato nuevo. Verificado
  end-to-end (3 planes → CSV+Excel; nombres de política corregidos). Legado intacto.

## [0.9.5] — Hito 3: Exactitud del extractor
### Mejorado
- **C1 — Nombre de política robusto** (`pipeline._es_nombre_politica` /
  `_buscar_nombre_politica`): si la celda fija trae el Decreto/CONPES, "No aplica"
  o está vacía, se busca en la cabecera la celda que **empieza por "Política
  Pública"** (descarta título, objetivo e instrucciones). Corrige 5 planes
  (Acción Climática, LEO, Transparencia, Servicios Públicos, CTI) → **0 nombres
  sospechosos** en los 38, sin romper los 33 ya correctos.
- **D2 — Metadatos de seguimiento desde columnas**: cuando el nombre del `.xlsb`
  no trae período/año (p. ej. `BTI.xlsb`), se derivan del `corte` ("Q4") y de la
  columna de año de reporte (BTI → período Q4, año 2025). `tipo_archivo` se deja
  `None` en archivos combinados (correcto).
### Diferido (documentado, no afecta la huella)
- **C3** (leer metas/meta_final desde la fila vigente promovida) y **C4**
  (conservar `meta_no_numerica` cruda): requieren verdad de campo para validar;
  quedan como refinamiento en `docs/MEJORAS_Y_LIMITACIONES.md`.
### Verificado
- Unit tests de `_es_nombre_politica`; golden regenerado; suite verde.

## [0.9.4] — Hito 2: Endurecer la regresión
### Añadido
- **Golden completo**: 97 huellas (38 planes + 51 seguimientos, + curados),
  descubrimiento automático de todas las políticas (`tests/corpus.py:
  descubrir_planes/descubrir_seguimientos`). `gen_golden.py` genera curado+completo.
- `tests/test_golden_full.py`: regresión exhaustiva por política, marcada `slow`
  (no corre por defecto; `pytest -m slow`). Marcador registrado en `pyproject`
  con `addopts = -m 'not slow'`.
- **Unit tests por etapa** `tests/test_unidades.py` (37): `a_float` (europeo),
  `extraer_codigo`, `es_vigente`/`peso_positivo`, `calcular_vigencia`,
  `codigo_de_hoja_ficha` (5 convenciones).
### Verificado
- Suite: **90 por defecto** (rápida) + **89 `slow`** (golden completo) = 179.

## [0.9.3] — Hito 1: Empaquetado + CLI
### Añadido
- **CLI** `extractor-pa` (`extractor_pa/__main__.py`) con subcomandos `plan`,
  `seguimiento`, `validar`; salidas `--json`/`--csv`/`--excel`; `--version`.
  También `python -m extractor_pa`. Reconfigura stdout a UTF-8 en Windows.
- `pyproject.toml`: `version=0.9.3`, **entry point** `extractor-pa`, keywords;
  extras `xlsb`/`pandas`/`dev` documentados. `pip install -e .` verificado.
- **CI** `.github/workflows/ci.yml` (pytest en Python 3.10–3.12 + verificación CLI).
- Pruebas `tests/test_cli.py`. Suite: **53 pruebas**.

## [0.9.2] — Sprint 0: quick wins (plan de desarrollo)
### Añadido
- **Parser de fechas** robusto (C2): año de 2 dígitos (`31/12/38`), serial de
  Excel (`48944`), formato US `MM/DD/YYYY` (`12/31/2024`). Las fechas inválidas
  reales (`31/06`, `31/02`, basura) siguen marcándose como `fecha_invalida`.
- Alerta **`escala_mezclada`** (C5): confusión de unidades ×100 (proporción 0-1
  vs porcentaje 0-100); conservadora (ratio ≥50) para no marcar conteos pequeños.
- **Métricas de extracción** en `Metadatos` (E4): `n_ir`, `n_ip`, `n_alertas`,
  `pct_ir_con_linea_base`.
- Pruebas `tests/test_fechas.py` (parser + escala). Suite: **48 pruebas**.
- Catálogo: **71 tipos** (52 implementados).
### Verificado
- E2: todos los scripts de lote del repo ignoran `~$`.
- Golden sin regresión (parser/escala solo afectan reglas de negocio).

## [0.8.3] — Seguimiento · Fase S4 (adaptadores de salida)
### Añadido (`extractor_pa/seguimiento/exportadores_seg.py`)
- `tablas_seguimiento(res)`: tablas en **formato largo** (dim + fact): metadatos,
  indicadores, avances_trimestrales, anual, cualitativo, alertas.
- `tabla_consolidado(res, año, periodo)`: la consolidación por período como tabla.
- `tablas_seguimiento_consolidadas([...])`: multi-archivo apilado.
- Export a JSON / CSV / Excel (por archivo y consolidado), reutilizando los
  escritores genéricos de `exportadores.py`.
- `scripts/gen_consolidado_seguimiento.py`.
### Verificado
- Test de tablas + JSON/CSV/Excel sobre `.xlsb` real. Consolidado de los 55
  archivos `.xlsb`. 22 pruebas.

## [0.8.2] — Seguimiento · Fase S3 (alertas de consistencia + semáforo)
### Añadido (`extractor_pa/seguimiento/validacion_seg.py`)
- **15 alertas de consistencia** portadas de `alertas-seguimientos`:
  - Base vs nuevo: `ERROR_ESTABILIDAD`, `ERROR_RETROACTIVO`, `INFO_IND_NUEVO`,
    `INFO_IND_FALTANTE`.
  - Un solo archivo: `ERROR_NO_NUMERICO`, `ADVERTENCIA_ESCALA`,
    `ADVERTENCIA_AVANCE`, `ADVERTENCIA_LIMITE_VIG`, `ADVERTENCIA_ACUM_META_VIG`,
    `ADVERTENCIA_ACUM_META_FIN`, `ADVERTENCIA_META_SIN_REP`,
    `ADVERTENCIA_REP_SIN_META`, `ADVERTENCIA_PCT_HASTA_VIG`,
    `ADVERTENCIA_DISCREPANCIA_PCT`, `ADVERTENCIA_CUAL`.
  - `validar_consistencia(base, nuevo)` y `validar_archivo(nuevo)`.
- **Semáforo/PHV** (de sispp-sdis): `semaforo_de(pct)` / `semaforo_indicador(ind, año)`
  con umbrales rojo≤50 / amarillo≤75 / naranja>125 (acepta fracción o 0-100).
- Las 15 alertas quedan marcadas como **implementadas** en el catálogo (51/70).
### Verificado
- Unitario controlado: estabilidad/retroactividad/nuevo/faltante disparan.
- Real (par BTI base S1-25 vs nuevo S2-25): se ejecuta y aflora avance/% etc.
- Semáforo clasifica ROJO/AMARILLO/VERDE/NARANJA. 21 pruebas.

## [0.8.1] — Seguimiento · Fase S2 (cruce con plan + consolidación por período)
### Añadido (`extractor_pa/seguimiento/`)
- `cruce.py`:
  - `cruzar_con_plan(res_seg, res_plan)`: empareja cada indicador de seguimiento
    con su IR/IP del plan por código numérico (N.N→IR, N.N.N→IP); enriquece
    `en_plan / tipo_plan / nombre_plan` y reporta los códigos sin plan.
  - `consolidar_periodo(ind, anio, periodo)` y `consolidar(res, anio, periodo)`:
    consolidan los avances por período (Q1–Q4 / S1 / S2 / Anual); SUMA suma los
    trimestres, el resto toma el último valor reportado.
- Captura de columnas fijas del `.xlsb` (mejora S1): estado, ponderación, línea
  base, **tipo de anualización**, periodicidad, fechas (seriales → ISO), corte,
  año de reporte.
- Tipo de alerta `codigo_seguimiento_sin_plan` en el catálogo.
### Verificado
- Real: BTI seguimiento × plan → **38/38 emparejados**; consolidación 2024-Anual
  con 33 indicadores (respeta SUMA/Creciente/Constante). 18 pruebas.

## [0.9.1] — Reportes accionables por política
### Añadido (`scripts/` + salidas en `../_codigo_extraido_pp/`)
- `reporte_hallazgos.py` → `REPORTE_HALLAZGOS_POR_POLITICA.md` +
  `hallazgos_por_politica.csv`: hallazgos del plan (V0–V18 + consistencia +
  extracción) por política, con resumen por nivel, por tipo de regla y detalle.
- `reporte_hallazgos_seguimiento.py` → `REPORTE_HALLAZGOS_SEGUIMIENTO_POR_POLITICA.md`
  + csv: consistencia del seguimiento por archivo `.xlsb` (+ pares base→nuevo).
### Resultados (corpus real)
- Plan: **2.771 hallazgos** (278 ERROR, 1.273 ADVERTENCIA, 1.220 INFO).
  Top reglas-error: V17 metas_vs_meta_final (134), V2 ponderacion_ip (40),
  V14 meta_vs_linea_base (37), V3 tipo_anualizacion (29).
- Seguimiento: **6.925 hallazgos** (7 ERROR, 6.918 ADVERTENCIA) en 53 archivos.

## [0.9.0] — Fase 7: Regresión (golden files) + paridad con legados
### Añadido
- `extractor_pa/regresion.py`: huellas estables (`huella_plan`, `huella_seguimiento`,
  `diferencias`) — resumen determinista para regresión/paridad.
- `tests/corpus.py` (corpus representativo) + `scripts/gen_golden.py` (genera
  `tests/golden/*.json`) + `tests/test_golden.py` (8 casos de regresión).
- `scripts/paridad_legados.py`: compara códigos del maestro vs los legados.
- `docs/REGRESION_Y_PARIDAD.md`.
### Verificado
- **Golden**: 5 planes + 3 seguimientos; 30 pruebas en total.
- **Paridad plan** vs `extractor-planes-accion`: 8/8 mismo conteo, 7/8 códigos
  idénticos; la 1 diferencia (Bicicleta `5.1` vs `5`) es el **maestro corrigiendo**
  un código con espacio ("5. 1") → paridad efectiva 8/8.
- **Paridad seguimiento** vs `alertas-seguimientos`: 6/6 códigos idénticos.

## [0.8.0] — Capa de SEGUIMIENTO · Fase S1 (núcleo de extracción .xlsb)
### Revisión + comparativo
- Revisión de los 3 extractores de seguimiento (alertas-seguimientos,
  generador-seguimiento, sispp-gobierno) → `PLAN_EXTRACTOR_SEGUIMIENTO.md`.
### Añadido (sub-paquete `extractor_pa/seguimiento/`)
- `modelo.py`: `IndicadorSeguimiento` (histórico indicador×año×trimestre),
  `MetadatosSeguimiento`, `ResultadoSeguimiento`.
- `loader.py`: lectura `.xlsb` (pyxlsb) + localización flexible de hojas.
- `resolutor.py`: **detección por anclas** (fila de bloques + años) — la técnica
  robusta de generador-seguimiento/sispp-gobierno; mapas por año de trimestres,
  acumulados, metas y % (vigencia/acumulado/total).
- `metadatos.py`: tipo/política/período/año desde el **nombre del archivo**
  (de alertas-seguimientos).
- `extractor.py`: `extraer_seguimiento(ruta)` → histórico cuantitativo + cualitativo.
- Tipos de alerta de extracción de seguimiento en el catálogo (5 nuevos).
### Verificado
- Test de integración con `.xlsb` real. **55 archivos `.xlsb` reales** extraídos
  con **0 problemas** (3.644 indicadores). 16 pruebas en total.

## [0.7.0] — Fase 6: Adaptadores de salida
### Añadido
- **`exportadores.py`**: convierte el modelo canónico a múltiples formatos:
  - `exportar_json` / `exportar_json_consolidado` (stdlib).
  - `exportar_csv` / `exportar_csv_consolidado` (stdlib; una tabla por archivo).
  - `exportar_excel` / `exportar_excel_consolidado` (openpyxl; una hoja por tabla).
  - `a_dataframes` / `a_dataframes_consolidado` (pandas, dependencia opcional).
  - `tablas` / `tablas_consolidadas`: aplanado en **formato ancho** (metas →
    columnas `meta_<año>`) con columnas `politica`/`archivo`.
- **Consolidado multi-plan**: apila IR/IP/alertas/financiero de varias políticas
  en tablas únicas para analizar todo el corpus junto.
- `scripts/gen_consolidado.py`: genera el consolidado de todos los planes
  (ignora archivos temporales `~$` de Excel).
### Verificado
- Tests de exportación (un plan: JSON/CSV/Excel/tablas; consolidado multi-plan).
- Consolidado real de los 38 planes a Excel + CSV + JSON.

## [0.6.0] — Catálogo consolidado + motor de reglas de negocio (V0–V18)
### Revisión
- Inventario de TODOS los chequeos de los 9 aplicativos (alertas, errores,
  reglas). Hallazgos: `generador-seguimiento` usa V0–V18 explícitos;
  `sispp-gobierno` añade `periodicidad_invalida`/`objetivo_sin_resultados`;
  `sispp-sdis` tiene reglas RN por dominio; `alertas-seguimientos` 15 tipos de
  seguimiento; `sistema-seguimiento-v3` Q001–Q003.
### Añadido
- **`catalogo.py`**: catálogo consolidado (64 tipos) como única fuente de verdad,
  con nivel, familia, capa, regla de origen y bandera `implementado`. Helpers
  `nivel_de`, `por_capa`, `por_familia`.
- **`validacion.py`**: motor de **reglas de negocio V0–V18** sobre el modelo
  canónico (`validar_reglas(resultado)`): ponderación (V0/V1/V2/V18), tipología
  (V3 + periodicidad), fechas (V5), metas (V6/V7/V8/V12/V14/V15/V17), línea base
  (V9/V16), códigos (V11/V13). `_parse_fecha` tolera año suelto, `YYYY-MM-DD`,
  `DD/MM/YYYY` y `datetime`.
- Flag `incluir_reglas_negocio` en `extraer_plan_accion(...)` (opt-in) y export
  `validar_reglas` en la API.
- `docs/CATALOGO_ALERTAS.md` regenerable desde el código (`scripts/gen_catalogo.py`).
### Cambiado
- **`crear_alerta(tipo, descripcion, ...)`**: el **nivel se toma del catálogo**
  (centralizado, una sola nomenclatura ERROR/ADVERTENCIA/INFO). Llamadores
  actualizados.
- `ResultadoExtraccion.exitoso`: solo falla por errores FATALES de extracción
  (apertura/hoja/formato/estructura), no por hallazgos de negocio.
### Verificado
- Tests de plan limpio (sin alertas de negocio) y de violaciones (V0/V14/V18) +
  flag del pipeline. Sobre planes reales el motor aflora hallazgos reales
  (BTI 14, Cultos 21, CTI 9 tras ajustar el parseo de fechas año-suelto).

## [0.5.0] — Fase 5: Consistencia y alertas
### Añadido
- Módulo `consistencia.py`:
  - `chequear_consistencia_ir(...)`: detecta cuando el mismo IR aparece en varias
    filas con un valor NO vacío distinto (nombre, vigencia, peso, fórmula, sector,
    entidad, tipo de anualización, periodicidad, línea base, meta final, fechas y
    metas anuales). Se evalúa sobre los valores **originales** (antes de la
    normalización de celdas combinadas). Tolera número vs texto y mayúsculas/espacios.
  - `chequear_duplicados_ip(...)`: detecta códigos de IP repetidos.
- Alertas nuevas: `inconsistencia_en_ir`, `codigo_ip_duplicado` (ADVERTENCIA).
- **Catálogo de alertas** documentado: `docs/CATALOGO_ALERTAS.md`.
### Cambiado
- El motor toma un snapshot de los valores originales por fila antes de normalizar,
  para poder comparar las filas del IR.
### Verificado
- Tests de inconsistencia y duplicado + regresión (el plan limpio no genera estas
  alertas). Sobre los planes reales afloran inconsistencias de dato existentes.

## [0.4.2] — Detección flexible de nombres de ficha técnica
### Corregido
- La detección de hojas de ficha solo reconocía «Ficha técnica IR#/IP#». Los
  planes reales usan muchas convenciones: `R.1.1`/`P.1.1.1` (Cultos),
  `R 1.1 Desc`/`P 1.1.1 Desc` (Salud Mental), `1.1.1. Desc` (LEO), `1.1.10`
  (Hábitat), `IR_1.1`/`IP_1.1.1` con guion bajo (Pobreza, Talento Humano).
  Nueva función `codigo_de_hoja_ficha(nombre)` que las cubre todas y descarta
  hojas no-ficha (plan, desplegables, instructivo, versiones).
### Impacto (planes antes reportados «sin ficha»)
- LEO 0→87/87, Cultos 0→32/32, Hábitat 0→81/86, Salud Mental 0→32/33,
  Migrantes 0→58/59, Pobreza 0→49/49, Talento Humano 7→36 (con ficha y unidad).
### Verificado
- Test unitario de todas las convenciones de nombre. Sin regresión en los
  planes que ya funcionaban (BTI, LGBTI, Discapacidad).

## [0.4.1] — Fase 4b: Formato antiguo (variante con bloque financiero)
### Añadido
- `MAPEO_ANTIGUO` (config) para la variante con bloque financiero y columnas
  reordenadas (p. ej. `plan_accion_pp_cti_v4-25.xlsx`): IR/IP resueltos POR ANCLA.
- Lectura del **bloque financiero** (Costo Estimado / Recurso disponible / Fuente
  de financiación / Código Proyecto, 4 columnas por año) → `RegistroFinanciero`.
- `ResultadoExtraccion.financiero` (lista de `RegistroFinanciero`).
### Cambiado (generalización del motor)
- El **resolutor de columnas** ahora soporta: IP por ancla (`anclas_ip`), anclas
  repetidas genéricas `{texto: (clave_ir, clave_ip)}`, fallback posicional
  desactivable y detección del bloque financiero. Devuelve un 4º valor
  `financiero_cols`.
- El **detector** clasifica como «antiguo» si hay bloque financiero en los
  encabezados (prioridad sobre las anclas nuevas).
- El **pipeline** elige el mapeo automáticamente según el formato (nuevo/antiguo);
  un mapeo pasado por el usuario siempre se respeta. Motor de extracción único.
### Verificado
- `plan_accion_pp_cti`: detectado «antiguo», 8 IR / 32 IP / 342 registros
  financieros, 0 errores; campos de IP (vigencia, nombre) ahora correctos.
- **Sin regresión**: los planes «nuevo» del baseline extraen conteos idénticos.
### Limitación
- Metadatos del formato antiguo (nombre de política) son best-effort: la celda B4
  no siempre trae el nombre; se descartan valores no textuales.
- La variante clásica con datos desde la fila 27 no se ha visto en los repos; si
  aparece, requerirá su propio mapeo (la arquitectura ya lo permite).

## [0.4.0] — Fase 4a: Fichas técnicas
### Añadido
- Módulo `lector_fichas.py` (portado de `sispp-sdis.leer_fichas`, ajustado al
  layout real de los planes SDP de gobierno): lee las hojas «Ficha técnica IR#/IP#»
  y extrae metodología, descripción, unidad de medida, fuentes, días de rezago y
  observaciones; enlaza cada ficha a su IR/IP por código.
- Campos `descripcion` y `observaciones` en el modelo (IR e IP).
- Parámetro `leer_fichas_tecnicas` en `extraer_plan_accion(...)` (por defecto True).
### Ajustes sobre el formato real
- La **unidad de medida** se resuelve por la opción marcada con «x» o por la
  respuesta a «¿Cuál?» (unidad libre, p. ej. «Puntaje», «Componentes»).
- En este formato, **días de rezago y fuentes** solo aparecen en las fichas de IR
  (las de IP normalmente no los traen): el extractor lo refleja fielmente.
### Verificado
- Prueba sintética de fichas (IR + IP) y `leer_fichas_tecnicas=False`.
- Real: BTI 50/53, LGBTI 191/192, Infancia 103/131 indicadores con unidad; 0 errores.
### Pendiente
- **Fase 4b (formato antiguo)**: no hay archivos en formato antiguo en los repos
  (los 39 planes son «nuevo»), por lo que NO se implementa aún por falta de un
  archivo real para validar. Queda a la espera de una muestra.

## [0.3.0] — Fase 3: Año de vigencia
### Añadido
- Módulo `vigencia.py` con `calcular_vigencia(metas, anio_explicito)` (lógica de
  `generador-seguimiento._año_vigencia_para`): determina el año de corte y el
  anterior con prioridad (año explícito → año actual → año anterior más cercano →
  primer año).
- Campos en el modelo: `anio_vigencia`, `anio_vigencia_anterior`,
  `meta_vigencia_actual`, `meta_vigencia_anterior` (IR e IP).
- Parámetro `anio_vigencia` en `extraer_plan_accion(...)` (runtime, no de mapeo).
### Verificado
- Pruebas de vigencia con año explícito y con fallback al año anterior más cercano.
- Sin regresión en los 38 planes reales.

## [0.2.0] — Fase 2: Normalización avanzada de celdas combinadas
### Añadido
- Módulo `normalizador.py` con la estrategia de 4 capas de `sispp-gobierno`:
  ffill libre de identificadores → `peso_objetivo` por objetivo → campos IR por
  resultado → **ascensión de la fila vigente**.
### Cambiado
- `estrategias/nuevo.py` usa `normalizar_celdas_combinadas` en lugar del
  forward-fill global simple.
### Verificado
- 3 pruebas (base, ascensión, no-contaminación). 38 planes reales con 0 errores.
### Limitación conocida
- Las metas anuales y `meta_final` se leen de la primera fila física (para
  respetar la escala %); la ascensión solo corrige los campos de identidad del IR.

## [0.1.0] — Fase 1: Núcleo del formato nuevo
### Añadido
- Pipeline modular: `loader` → `localizador_hoja` → `detector_formato` →
  `resolutor_columnas` → `lector_filas` → `estrategias/nuevo` → `pipeline`.
- Modelo canónico (`modelo.py`), anclas configurables (`config.py`),
  utilidades (`utilidades.py`: `_norm`, `a_float` europeo, `extraer_codigo`,
  `leer_celda_escala` con escala %).
- Localización flexible de hoja, detección de formato (nuevo/antiguo),
  resolución de columnas por encabezado con celdas combinadas + fallback,
  pre-filtro de filas espurias, deduplicación de IR, alertas de extracción.
### Verificado
- Smoke test sintético end-to-end. 38 planes reales con 0 errores.
