# Catálogo CONSOLIDADO de alertas, errores y chequeos

> Consolidado de TODOS los chequeos revisados en los 9 aplicativos de política pública.
> Generado automáticamente desde `extractor_pa/catalogo.py` (única fuente de verdad).
> Niveles unificados: **ERROR** (bloquea / dato inutilizable) · **ADVERTENCIA** (revisar) · **INFO** (informativo).

**71 tipos** catalogados · **52 implementados** en el extractor maestro.

Leyenda `Impl.`: ✅ lo produce el maestro · ⬜ documentado (vive en otro aplicativo o pendiente).

## 1. Extracción / Estructura

Las produce el extractor maestro al leer el Excel.

| tipo | nivel | regla | familia | descripción | Impl. |
|---|---|---|---|---|:---:|
| `apertura` | ERROR | — | Estructura | El archivo no se pudo abrir. | ✅ |
| `hoja_no_encontrada` | ERROR | — | Estructura | No se encontró la hoja del plan de acción. | ✅ |
| `formato_no_reconocido` | ERROR | — | Estructura | El detector no pudo determinar el formato (ni nuevo ni antiguo). | ✅ |
| `formato_no_compatible` | ERROR | sispp-gobierno | Estructura | La plantilla es incompatible con el formato vigente. | ⬜ |
| `estructura` | ERROR | — | Estructura | Faltan las anclas obligatorias ('Meta de resultado Final'/'Producto esperado'). | ✅ |
| `metadatos` | ADVERTENCIA | sispp-gobierno | Estructura | No se pudo identificar el nombre de la política en la cabecera. | ⬜ |
| `sin_ir` | ADVERTENCIA | — | Estructura | No se extrajo ningún Indicador de Resultado. | ✅ |
| `sin_ip` | ADVERTENCIA | — | Estructura | No se extrajo ningún Indicador de Producto. | ✅ |
| `ir_sin_nombre` | ADVERTENCIA | — | Estructura | Una fila trae código de IR pero sin nombre (se omitió). | ✅ |
| `ip_sin_nombre` | ADVERTENCIA | — | Estructura | Una fila trae código de IP pero sin nombre (se omitió). | ✅ |
| `apertura_seguimiento` | ERROR | — | Estructura seguimiento | No se pudo abrir el archivo .xlsb de seguimiento. | ✅ |
| `hoja_seguimiento_no_encontrada` | ERROR | — | Estructura seguimiento | No se encontró la hoja 'Avance Cuantitativo'. | ✅ |
| `anclas_no_encontradas` | ERROR | — | Estructura seguimiento | No se encontraron las anclas de bloques en la fila de encabezados. | ✅ |
| `sin_indicadores_seguimiento` | ADVERTENCIA | — | Estructura seguimiento | No se extrajo ningún indicador de seguimiento. | ✅ |
| `indicador_seguimiento_sin_codigo` | INFO | — | Estructura seguimiento | Fila de seguimiento sin código de indicador reconocible. | ✅ |
| `inconsistencia_en_ir` | ADVERTENCIA | — | Consistencia | El mismo IR aparece en varias filas con un valor no vacío distinto. | ✅ |

## 2. Validación del plan (reglas de negocio V0–V18)

Las produce `validar_reglas()` sobre el modelo canónico.

| tipo | nivel | regla | familia | descripción | Impl. |
|---|---|---|---|---|:---:|
| `codigo_malformado` | INFO | V13 | Códigos | Código con formato inesperado (OBJ=N, IR=N.N, IP=N.N.N). | ✅ |
| `codigo_ip_duplicado` | ERROR | V10 | Códigos | Un mismo código de IP aparece más de una vez. | ✅ |
| `ir_sin_productos` | ADVERTENCIA | V11 | Códigos | Un IR vigente no tiene Indicadores de Producto asociados. | ✅ |
| `objetivo_sin_resultados` | ADVERTENCIA | sispp-gobierno | Códigos | Un objetivo específico no tiene Resultados/IR asociados. | ⬜ |
| `jerarquia_ip` | ERROR | creador | Códigos | El producto N.N.N no cuelga de su resultado N.N (jerarquía rota). | ⬜ |
| `ponderacion_objetivos` | ERROR | V0 | Ponderación | Los pesos de los objetivos no suman 100%. | ✅ |
| `ponderacion_ir` | ERROR | V1 | Ponderación | Los pesos de los IR de un objetivo no igualan el peso del objetivo. | ✅ |
| `ponderacion_ip` | ERROR | V2 | Ponderación | Los pesos de los IP de un IR no igualan el peso del IR. | ✅ |
| `ponderacion_faltante` | ERROR | V1/V2 | Ponderación | Indicador vigente sin ponderación numérica. | ✅ |
| `vigencia_ponderacion` | ERROR | V18 | Ponderación | Incoherencia vigencia↔ponderación (No Vigente debe pesar 0; Vigente >0). | ✅ |
| `tipo_anualizacion_invalido` | ERROR | V3 | Tipología | Tipo de anualización fuera del catálogo (CRECIENTE/DECRECIENTE/CONSTANTE/SUMA). | ✅ |
| `periodicidad_invalida` | ADVERTENCIA | sispp-gobierno | Tipología | Periodicidad fuera del catálogo. | ✅ |
| `sector_no_oficial` | INFO | V4 | Tipología | Sector responsable no reconocido en el catálogo oficial. | ⬜ |
| `entidad_no_oficial` | INFO | V4 | Tipología | Entidad responsable no reconocida en el catálogo oficial. | ⬜ |
| `fecha_invalida` | ADVERTENCIA | V5 | Fechas | Fecha no parseable. | ✅ |
| `fecha_inicio_mayor_fin` | ERROR | V5 | Fechas | La fecha de inicio es posterior a la de finalización. | ✅ |
| `meta_no_numerica` | ERROR | V6/V7 | Metas | Una meta anual no es numérica. | ✅ |
| `meta_final_faltante` | ERROR | V8 | Metas | Falta la meta final del indicador. | ✅ |
| `brecha_en_metas` | ADVERTENCIA | V12 | Metas | Faltan metas en años esperados según la periodicidad/vigencia. | ✅ |
| `meta_fuera_de_rango` | ADVERTENCIA | V15 | Metas | Hay metas en años fuera del rango de vigencia (inicio–fin). | ✅ |
| `meta_vs_linea_base` | ERROR | V14 | Metas | CRECIENTE con meta_final < línea base (o DECRECIENTE al revés). | ✅ |
| `metas_vs_meta_final` | ERROR | V17 | Metas | SUMA: Σ metas anuales ≠ meta_final; resto: última meta ≠ meta_final. | ✅ |
| `escala_mezclada` | ADVERTENCIA | escala | Metas | Las metas anuales del indicador mezclan escalas (fracción 0-1 y valores >1.5), posible error de unidades. | ✅ |
| `linea_base_faltante` | INFO | V9 | Línea base | Línea base (valor y/o año) no registrada. | ✅ |
| `linea_base_no_numerica` | ADVERTENCIA | V9 | Línea base | El valor de línea base no es numérico. | ✅ |
| `lb_obligatoria_decreciente` | ERROR | V16 | Línea base | Indicador DECRECIENTE sin línea base (es obligatoria). | ✅ |

## 3. Consistencia del seguimiento

De `alertas-seguimientos` (capa de seguimiento, fuera del extractor de plan).

| tipo | nivel | regla | familia | descripción | Impl. |
|---|---|---|---|---|:---:|
| `codigo_seguimiento_sin_plan` | INFO | — | Estructura seguimiento | Un código de seguimiento no se encontró en el plan de acción. | ✅ |
| `ERROR_ESTABILIDAD` | ERROR | — | Seguimiento | Campo inmutable del indicador modificado entre cargas. | ✅ |
| `ERROR_RETROACTIVO` | ERROR | — | Seguimiento | Valor histórico (periodo cerrado) modificado. | ✅ |
| `ERROR_NO_NUMERICO` | ERROR | — | Seguimiento | Reporte cuantitativo con valor no numérico. | ✅ |
| `ADVERTENCIA_ESCALA` | ADVERTENCIA | — | Seguimiento | Incoherencia de escala entre la meta y el reporte. | ✅ |
| `ADVERTENCIA_AVANCE` | ADVERTENCIA | — | Seguimiento | El avance supera la meta + 25% (umbral 125%). | ✅ |
| `ADVERTENCIA_LIMITE_VIG` | ADVERTENCIA | — | Seguimiento | El reporte/suma de la vigencia supera el 125% de la meta programada. | ✅ |
| `ADVERTENCIA_ACUM_META_VIG` | ADVERTENCIA | — | Seguimiento | El acumulado supera la meta acumulada de la vigencia. | ✅ |
| `ADVERTENCIA_ACUM_META_FIN` | ADVERTENCIA | — | Seguimiento | El acumulado supera la meta final. | ✅ |
| `ADVERTENCIA_META_SIN_REP` | ADVERTENCIA | — | Seguimiento | Existe meta para la vigencia pero no hay reporte. | ✅ |
| `ADVERTENCIA_REP_SIN_META` | ADVERTENCIA | — | Seguimiento | Hay reporte pero la meta es 0 o no existe. | ✅ |
| `ADVERTENCIA_PCT_HASTA_VIG` | ADVERTENCIA | — | Seguimiento | % de avance hasta la vigencia fuera de rango (<50% o >125%). | ✅ |
| `ADVERTENCIA_DISCREPANCIA_PCT` | ADVERTENCIA | — | Seguimiento | El % reportado difiere del calculado (acumulado/meta anual). | ✅ |
| `ADVERTENCIA_CUAL` | ADVERTENCIA | — | Seguimiento | Indicador Vigente sin reporte cualitativo. | ✅ |
| `INFO_IND_NUEVO` | INFO | — | Seguimiento | Indicador nuevo (no existía en el archivo base). | ✅ |
| `INFO_IND_FALTANTE` | INFO | — | Seguimiento | Indicador presente en la base pero ausente en el nuevo archivo. | ✅ |

## 4. Operativas / temporales

De `sispp-sdis` (notificaciones del ciclo de reporte).

| tipo | nivel | regla | familia | descripción | Impl. |
|---|---|---|---|---|:---:|
| `INDICADOR_SIN_RESPONSABLE` | ADVERTENCIA | RN-ALE-001 | Operativa | Indicador vigente sin ejecutor asignado. | ⬜ |
| `INDICADOR_SIN_SEGUIMIENTO` | ADVERTENCIA | RN-ALE-001 | Operativa | Indicador sin reporte en el período. | ⬜ |
| `PROXIMO_VENCIMIENTO` | ADVERTENCIA | RN-ALE-004 | Operativa | Faltan N días (5/3/1) para la fecha límite y el reporte está pendiente. | ⬜ |
| `REZAGO` | ADVERTENCIA | semáforo | Operativa | Semáforo ROJO/AMARILLO (ejecución baja/media). | ⬜ |
| `SOBRECUMPLIMIENTO` | ADVERTENCIA | semáforo | Operativa | PHV supera el umbral de sobre ejecución (>125%). | ⬜ |
| `DISMINUCION_CRECIENTE` | ADVERTENCIA | RN-CUA-002 | Operativa | Indicador CRECIENTE cuyo valor disminuyó vs período anterior. | ⬜ |
| `AUMENTO_DECRECIENTE` | ADVERTENCIA | RN-CUA-003 | Operativa | Indicador DECRECIENTE cuyo valor aumentó vs período anterior. | ⬜ |
| `CRP_SOBREASIGNADO` | ADVERTENCIA | RN-FIN-004 | Operativa | Un CRP tiene >100% comprometido en una política. | ⬜ |

## 5. Cualitativas

Justificaciones obligatorias (`sispp-sdis`, RN-CUL).

| tipo | nivel | regla | familia | descripción | Impl. |
|---|---|---|---|---|:---:|
| `justificacion_rezago_obligatoria` | ERROR | RN-CUL-003 | Cualitativa | Falta la justificación obligatoria de rezago (semáforo ROJO/AMARILLO). | ⬜ |
| `justificacion_sobrecumplimiento_obligatoria` | ERROR | RN-CUL-003 | Cualitativa | Falta la justificación obligatoria de sobrecumplimiento. | ⬜ |

## 6. Calidad declarativa

De `sistema-seguimiento-v3` (Q001–Q003).

| tipo | nivel | regla | familia | descripción | Impl. |
|---|---|---|---|---|:---:|
| `Q001` | ERROR | Q001 | Calidad | No permitir metas finales negativas. | ⬜ |
| `Q002` | ERROR | Q002 | Calidad | No cerrar la política sin corte final publicado. | ⬜ |
| `Q003` | ADVERTENCIA | Q003 | Calidad | Cada ajuste debe tener justificación. | ⬜ |

## Notas

- El **nivel** y la **descripción** de cada tipo viven en `extractor_pa/catalogo.py`; `crear_alerta(tipo, ...)` toma el nivel de ahí.
- Las capas 3–6 (seguimiento, operativas, cualitativas, calidad) se documentan para el consolidado pero pertenecen a los aplicativos de seguimiento/operación, no al extractor del plan.
