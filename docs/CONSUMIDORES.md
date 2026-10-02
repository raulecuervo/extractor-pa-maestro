# Aplicativos que consumen extractor-pa

Inventario al **2026-10-01**, tomado del código de cada repositorio en
`C:\Users\RaulEsteban\Proyectos\`. Lo que cada aplicativo importa está fijado en
[`tests/test_contrato_consumidores.py`](../tests/test_contrato_consumidores.py):
si un nombre desaparece, esa prueba falla aquí antes de que falle en producción.

Para refrescar las versiones fijadas:
```bash
python scripts/pines_consumidores.py
```
Para volver a ubicar los usos:
```bash
grep -rnE "^\s*(from extractor_pa|import extractor_pa)" ../*/ --include=*.py
```

## Resumen

| Aplicativo | Versión fijada | Plan de acción | Seguimiento | Dónde entra |
|---|---|---|---|---|
| alertas-seguimientos | v0.17.0 | — | Extracción, validación y fórmulas | `extractor.py`, `validator.py`, `motor_calculo.py`, `ml_comentarios/` |
| sispp-gobierno | v0.13.0 | Etapa 01 | Etapa 04 | `extraccion_maestro.py`, `extraccion_seg_maestro.py` |
| sispp-SDP | v0.13.0 | Etapa 01 | Etapa 04 | Copia idéntica de sispp-gobierno |
| sispp-sdis (backend) | v0.10.1 | ETL de planes | Importador y fórmulas | `app/etl_maestro.py`, `app/routers/importador.py`, `app/servicios.py` |
| validador_plan_accion | v0.9.11 | Sí | — | `validador/extraccion_maestro.py` |
| extractor-planes-accion | v0.9.11 | Solo formato nuevo | — | `modulo_planes_accion/extractor_maestro.py` |
| creador-planes-accion | v0.9.11 | Sí | — | `app/import_excel_maestro.py` |
| seguimiento-pp-sdis | v0.9.11 | Solo los IR | — | `app/services/plan_accion_import_maestro.py` |
| generador-seguimiento | v0.9.11 | — | Extracción y consolidación | `extractors/parsear_maestro.py` |

Última versión publicada: **v0.18.0**; la 0.19.0 está por etiquetar.

## Qué funcionalidad usa cada uno

### Plan de acción

| Funcionalidad | La usan |
|---|---|
| `extraer_plan_accion(ruta)` con los parámetros por defecto | validador, extractor-planes-accion, creador, seguimiento-pp-sdis, sispp-gobierno, sispp-SDP, sispp-sdis |
| `extraer_plan_accion(ruta, leer_fichas_tecnicas=False)` | extractor-planes-accion (solo el script `auditar_perdidas.py`) |
| `res.exitoso` (descartar el archivo si falló) | validador, extractor-planes-accion, sispp-gobierno, sispp-SDP |
| `res.alertas`, todas, con todos sus campos | validador, extractor-planes-accion, sispp-gobierno, sispp-SDP |
| `res.alertas`, solo las de nivel ERROR (`tipo` y `descripcion`) | sispp-sdis |
| `metadatos`: nombre de la política, sector y entidad líder, objetivo general | validador, extractor-planes-accion, seguimiento-pp-sdis, sispp-gobierno, sispp-SDP, sispp-sdis |
| `metadatos.documento_conpes` | seguimiento-pp-sdis, sispp-gobierno, sispp-SDP, sispp-sdis |
| Indicadores de resultado (IR): identidad, pesos, fórmula, tipo de anualización, periodicidad, línea base, fechas, meta final, metas anuales | Los 7 aplicativos de plan |
| IR: sector/entidad responsable, ODS y meta ODS | validador, extractor-planes-accion, creador, seguimiento-pp-sdis, sispp-gobierno, sispp-SDP (sispp-sdis: solo sector/entidad) |
| Indicadores de producto (IP): identidad, peso, fórmula, tipo, periodicidad, línea base, fechas, meta final, metas anuales, sector/entidad responsable | validador, extractor-planes-accion, creador, sispp-gobierno, sispp-SDP, sispp-sdis |
| IP: dirección responsable y corresponsables (sector, entidad, dirección) | extractor-planes-accion, creador, sispp-gobierno, sispp-SDP (sispp-sdis: solo la dirección responsable) |
| IP: objetivo y meta PDD, proyecto de inversión, enfoques principal y secundario | extractor-planes-accion, creador, sispp-gobierno, sispp-SDP (sispp-sdis: proyecto y enfoques) |
| Campos de ficha técnica: metodología, unidad de medida, fuente de datos, días de rezago, descripción, observaciones | creador, sispp-sdis (sispp-gobierno y sispp-SDP: solo `descripcion` del IP) |
| `escala_pct`, para dividir entre 100 las metas en porcentaje | Los 7 aplicativos de plan |
| `res.financiero` | Nadie en producción: el adaptador de formato antiguo de extractor-planes-accion lo lee, pero el orquestador sigue usando el extractor legado para ese formato |
| `utilidades.extraer_codigo`, parcheado en tiempo de ejecución | sispp-gobierno, sispp-SDP (`dashboard_pp/parche_extractor.py`, para los códigos «P1.1.1» y «R1.1») |

### Seguimiento

| Funcionalidad | La usan |
|---|---|
| `extraer_seguimiento(ruta)` | alertas-seguimientos, sispp-gobierno, sispp-SDP, sispp-sdis, generador-seguimiento |
| Campos del `IndicadorSeguimiento`: identidad, sector, entidad, ponderación, línea base, tipo, periodicidad, fechas, estado, meta final, avances, acumulados, metas, cualitativos, avances por enfoque, % de la vigencia, corte, año de reporte | alertas-seguimientos, sispp-gobierno, sispp-SDP |
| `metas_acumuladas`, `pct_acumulado`, `pct_total` | sispp-gobierno, sispp-SDP |
| Solo `codigo`, `nombre`, `avances`, `cualitativos` (y `avance_enfoques` en generador) | sispp-sdis, generador-seguimiento |
| `consolidar_periodo(ind, anio, periodo)` | generador-seguimiento |
| `validar_consistencia(base, nuevo, anio_min=…, entidad_sector=…, umbrales=…)` con el semáforo propio | alertas-seguimientos |
| `validar_consistencia(base, nuevo)` con los umbrales de la librería (50 % / 125 %) | sispp-sdis |
| `validar_archivo(res, anio_min=…, umbrales=…)` | alertas-seguimientos (`ml_comentarios`) |
| `HallazgoSeguimiento.as_finding()` | alertas-seguimientos, sispp-sdis |
| Construir resultados a mano: `ResultadoSeguimiento`, `MetadatosSeguimiento`, `indicador_desde_dict` / `IndicadorSeguimiento` | alertas-seguimientos (desde dicts), sispp-sdis (desde su base de datos) |
| Fórmulas de `seguimiento.metricas`: 26, entre ellas `metricas_corte`, `calc_paf`, `calc_tid`, `calc_pct_vigencia`, `calc_mes` y la LB ficticia | alertas-seguimientos (`motor_calculo.py` las reexporta todas, incluida la privada `_suma_metas_prev_suma`) |
| `calc_paf`, `calc_tid`, `calc_brecha`, `lb_de_indicador` (en fracción; la app multiplica por 100) | sispp-sdis (`servicios.py`) |
| `safe_float` | alertas-seguimientos, sispp-sdis |
| `parse_period`, `limites_de_semaforo` | alertas-seguimientos (`ml_comentarios/reglas.py`) |
| `extractor_pa.__version__` | alertas-seguimientos: sella con ella las métricas que guarda (`REGLA_METRICAS` en `db.py`) |

### Instalación y empaquetado

| Uso | Dónde |
|---|---|
| `pip install` desde git en su CI | alertas-seguimientos, sispp-gobierno |
| `pip install` desde git en el Dockerfile (por eso la imagen lleva git) | sispp-sdis |
| PyInstaller empaqueta los submódulos y los datos (`data/entidad_sector.json`) | sispp-gobierno, sispp-SDP (`sispp_pipeline.spec`) |
| Comprueba al arrancar que el intérprete tenga `extractor_pa` | sispp-gobierno, sispp-SDP (`app/runner.py`) |

## Lo que ningún aplicativo usa

Existe en la librería, pero ningún aplicativo lo llama:
- `incluir_reglas_negocio=True` y `validar_reglas` (reglas V0–V18): el validador corre sus propias reglas.
- `catalogo_oficial` (V4) y la normalización difusa.
- Gobernanza de alertas (`RegistroGobernanza`) y decisiones humanas (`RegistroDecisiones`).
- Exportadores (`exportar_*`, `tablas`, `a_dataframes`), tablero HTML y CLI.
- `cruzar_con_plan`, `consolidar` y `semaforo_de` del seguimiento.
- `MapeoColumnas` propio, el parámetro `anio_vigencia` y los campos `meta_vigencia_actual` / `_anterior` (sin `anio_vigencia` dependen del año del reloj, pero ningún aplicativo los lee).
- `res.objetivos` y `metadatos.anio_corte`.
- `IndicadorResultado.enfoque`, que extractor-planes-accion deja en `None` porque antes el maestro no lo entregaba.

## Detalle por aplicativo

### alertas-seguimientos (v0.17.0)
- **`extractor.py`**: `extraer_seguimiento` y convierte cada `IndicadorSeguimiento` a sus dicts.
- **`validator.py`**: arma `ResultadoSeguimiento` con `indicador_desde_dict` y llama `validacion_seg.validar_consistencia` con `anio_min`, `entidad_sector` y los `umbrales` de su Parametrización; devuelve `as_finding()`.
- **`motor_calculo.py`**: reexporta las fórmulas de `seguimiento.metricas` con sus nombres y usa `__version__` como versión de las fórmulas.
- **`ml_comentarios/`**: `extraer_seguimiento`, `validar_consistencia`, `validar_archivo`, `safe_float`, `parse_period`, `limites_de_semaforo`.
- **Al subir de versión**: es el aplicativo más sensible. Cada versión marcada «Cambia cifras» en el CHANGELOG mueve sus números.

### sispp-gobierno y sispp-SDP (v0.13.0)
Los tres archivos que tocan la librería son idénticos en los dos repositorios.
- **Etapa 01** (`extraccion_maestro.py`): `extraer_plan_accion`; vuelca las alertas (ADVERTENCIA → WARNING), descarta si no `exitoso` y convierte IR e IP a dicts, incluidos los corresponsables, PDD y enfoques.
- **Etapa 04** (`extraccion_seg_maestro.py`): `extraer_seguimiento`, con todos los campos del indicador, incluidos `metas_acumuladas` y los porcentajes.
- **`dashboard_pp/parche_extractor.py`**: reemplaza `extraer_codigo` en cinco módulos de la librería para aceptar «P1.1.1» y «R1.1». Puede retirarse cuando fijen v0.19.0 o posterior, que ya acepta «P», «R», «O» y «OE».
- **Al subir de versión**: no usa `metricas`, así que las fórmulas no le cambian cifras; sí le llega lo que cambie en la extracción de planes y seguimientos.

### sispp-sdis, backend (v0.10.1)
- **`app/etl_maestro.py`** (`extraer_pa`): plan completo, incluidas las fichas técnicas; solo toma las alertas de nivel ERROR.
- **`app/routers/importador.py`**: `extraer_seguimiento`, `validar_consistencia` con los umbrales por defecto, `safe_float`, y construye `IndicadorSeguimiento` desde su base de datos.
- **`app/servicios.py`**: `calc_paf`, `calc_tid`, `calc_brecha` y `lb_de_indicador`.
- **Al subir de versión**: de las fórmulas que usa, `calc_paf` y `calc_tid` cambiaron en 0.14.0: en CRECIENTE y DECRECIENTE solo quedan vacíos si la meta final es igual a la LB, así que un DECRECIENTE con meta final 0 ahora sí tiene PAF y TID. Las demás correcciones de cifras (0.12.0, 0.13.0, 0.16.0, 0.17.0) están en funciones que sispp-sdis no llama, porque calcula por su cuenta la meta acumulada y el avance; por eso puede diferir de alertas-seguimientos para el mismo indicador.

### validador_plan_accion (v0.9.11)
- **`validador/extraccion_maestro.py`**: `extraer_plan_accion`; vuelca todas las alertas (renombra el campo `formula` → `formula_indicador` y `meta_AAAA` → `meta_ir_AAAA`), descarta si no `exitoso` y convierte IR e IP a dicts. Las reglas V0–V18 son las suyas, no las de la librería.

### extractor-planes-accion (v0.9.11)
- **`modulo_planes_accion/extractor_maestro.py`**: `extraer_plan_nuevo` es el que usa el orquestador. `extraer_plan_antiguo` (que lee `financiero`) existe pero **no está conectado**: el orquestador sigue con `extractor_antiguo.py`, el legado.
- **`auditar_perdidas.py`**: compara el maestro con el legado (`leer_fichas_tecnicas=False`).
- **Oportunidad**: los planes antiguos 2021–2025 conservan metas, línea base y bloque financiero desde v0.19.0, y el IR trae su `enfoque`; con eso se podría activar el adaptador antiguo.

### creador-planes-accion (v0.9.11)
- **`app/import_excel_maestro.py`** (`importar_politica`, llamado desde `app/routers/ui.py`): `extraer_plan_accion` sobre un archivo temporal y reconstrucción de la jerarquía de su ORM (objetivo → resultado → IR → IP) con todos los campos, fichas técnicas incluidas. Los metadatos de la política los lee con su propio código, no los del maestro, y no mira las alertas.

### seguimiento-pp-sdis (v0.9.11)
- **`app/services/plan_accion_import_maestro.py`** (`parse_plan_accion`, llamado desde `run_full_excel_import`): metadatos y **solo los IR**. Los IP y sus fichas siguen entrando por su importador propio (`import_fichas_ip`).

### generador-seguimiento (v0.9.11)
- **`extractors/parsear_maestro.py`** (`parsear_seguimiento_xlsb`, llamado desde `app.py`): `extraer_seguimiento` y `consolidar_periodo` por indicador; lee código, nombre, avances, cualitativos y avances por enfoque. `comparar_datos.py` es un script de comparación.
