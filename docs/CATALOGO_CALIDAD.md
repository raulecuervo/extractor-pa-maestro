# Catálogo de reglas de calidad

> Generado desde `extractor_pa/calidad/catalogo.py` (fuente única; ADR-001).
> Severidad: Error · Advertencia · Info (en `observaciones_politica`: Alta · Media · Baja).

**64 reglas** · 64 implementadas · 0 apagadas por defecto.


## Estructura del plan (extracción)

| código | nombre | severidad | nivel | familia | sustituye a | acción | origen |
|---|---|---|---|---|---|---|---|
| `EXT_APERTURA` | El archivo no se pudo abrir | Error | archivo | Estructura | `apertura` | — | extracción |
| `EXT_HOJA_NO_ENCONTRADA` | No se encontró la hoja del plan de acción | Error | archivo | Estructura | `hoja_no_encontrada` | — | extracción |
| `EXT_FORMATO_NO_RECONOCIDO` | El detector no pudo determinar el formato (ni nuevo ni antiguo) | Error | archivo | Estructura | `formato_no_reconocido` | — | extracción |
| `EXT_ESTRUCTURA` | Faltan las anclas obligatorias ('Meta de resultado Final'/'Producto esperado') | Error | archivo | Estructura | `estructura` | — | extracción |
| `EXT_ERROR_EXTRACCION` | Fallo inesperado al extraer el plan (excepción interna); no se entrega ningún in | Error | archivo | Estructura | `error_extraccion` | — | extracción |
| `EXT_ERROR_ETAPA_OPCIONAL` | Falló una etapa opcional (fichas técnicas o reglas de negocio); el resto de la e | Advertencia | archivo | Estructura | `error_etapa_opcional` | — | extracción |
| `EXT_SIN_IR` | No se extrajo ningún Indicador de Resultado | Advertencia | archivo | Estructura | `sin_ir` | — | extracción |
| `EXT_SIN_IP` | No se extrajo ningún Indicador de Producto | Advertencia | archivo | Estructura | `sin_ip` | — | extracción |
| `EXT_IR_SIN_NOMBRE` | Una fila trae código de IR pero sin nombre (se omitió) | Advertencia | archivo | Estructura | `ir_sin_nombre` | — | extracción |
| `EXT_IP_SIN_NOMBRE` | Una fila trae código de IP pero sin nombre (se omitió) | Advertencia | archivo | Estructura | `ip_sin_nombre` | — | extracción |
| `EXT_CODIGO_NO_RECONOCIDO` | La celda de resultado o de producto trae texto pero no un código reconocible (IR | Advertencia | archivo | Estructura | `codigo_no_reconocido` | — | extracción |
| `EXT_CODIGO_IP_DUPLICADO` | Un mismo código de IP aparece más de una vez | Error | archivo | Códigos | `codigo_ip_duplicado` | — | extracción |
| `EXT_INCONSISTENCIA_EN_IR` | El mismo IR aparece en varias filas con un valor no vacío distinto | Advertencia | archivo | Consistencia | `inconsistencia_en_ir` | — | extracción |

## Estructura del seguimiento (extracción)

| código | nombre | severidad | nivel | familia | sustituye a | acción | origen |
|---|---|---|---|---|---|---|---|
| `EXT_APERTURA_SEGUIMIENTO` | No se pudo abrir el archivo de seguimiento (.xlsb o .xlsx) | Error | archivo | Estructura seguimiento | `apertura_seguimiento` | — | extracción |
| `EXT_HOJA_SEGUIMIENTO_NO_ENCONTRADA` | No se encontró la hoja 'Avance Cuantitativo' | Error | archivo | Estructura seguimiento | `hoja_seguimiento_no_encontrada` | — | extracción |
| `EXT_ANCLAS_NO_ENCONTRADAS` | No se encontraron las anclas de bloques en la fila de encabezados | Error | archivo | Estructura seguimiento | `anclas_no_encontradas` | — | extracción |
| `EXT_ANCLAS_PORCENTAJE_AUSENTES` | El archivo no trae los bloques de porcentaje de avance; se leen avances, acumula | Advertencia | archivo | Estructura seguimiento | `anclas_porcentaje_ausentes` | — | extracción |
| `EXT_SIN_INDICADORES_SEGUIMIENTO` | No se extrajo ningún indicador de seguimiento | Advertencia | archivo | Estructura seguimiento | `sin_indicadores_seguimiento` | — | extracción |
| `EXT_INDICADOR_SEGUIMIENTO_SIN_CODIGO` | Fila de seguimiento sin código de indicador reconocible | Info | archivo | Estructura seguimiento | `indicador_seguimiento_sin_codigo` | — | extracción |

## Plan de acción

| código | nombre | severidad | nivel | familia | sustituye a | acción | origen |
|---|---|---|---|---|---|---|---|
| `PLAN_PESO_OBJETIVOS` | Pesos de los objetivos no suman 100 % | Error | politica | Ponderación | `ponderacion_objetivos`, `V0`, `Pesos de la política no suman 100 %` | Solicitar el ajuste del plan de acción ante la SDP. | V0 |
| `PLAN_PESO_CADENA_OBJ_IR` | Pesos de los resultados no cuadran con el objetivo | Error | objetivo | Ponderación | `ponderacion_ir`, `V1`, `cadena_objetivo_resultados`, `Pesos del objetivo no cuadran` | Solicitar el ajuste del plan de acción ante la SDP. | V1 |
| `PLAN_PESO_CADENA_IR_IP` | Pesos de los productos no cuadran con el resultado | Error | resultado | Ponderación | `ponderacion_ip`, `V2`, `cadena_resultado_productos` | Solicitar el ajuste del plan de acción ante la SDP. | V2 |
| `PLAN_VIGENTE_SIN_PESO` | Indicador vigente sin ponderación | Error | indicador | Ponderación | `ponderacion_faltante`, `vigencia_ponderacion`, `V18`, `indicador_sin_ponderacion` | Solicitar el ajuste del plan de acción ante la SDP. | V1/V2/V18 |
| `PLAN_NO_VIGENTE_CON_PESO` | Indicador No Vigente con ponderación | Error | indicador | Ponderación | `vigencia_ponderacion`, `V18`, `Producto No Vigente con peso` | Solicitar ajuste del plan: peso 0 o redistribuirlo. | V18; observaciones.obs_no_vigentes |
| `PLAN_TIPO_ANUALIZACION_INVALIDO` | Tipo de anualización no reconocido | Error | indicador | Tipología | `tipo_anualizacion_invalido`, `V3` | Solicitar el ajuste del plan de acción ante la SDP. | V3 |
| `PLAN_PERIODICIDAD_INVALIDA` | Periodicidad fuera del catálogo | Advertencia | indicador | Tipología | `periodicidad_invalida` | Solicitar el ajuste del plan de acción ante la SDP. | sispp-gobierno |
| `PLAN_SECTOR_NO_OFICIAL` | Sector fuera del listado oficial | Info | indicador | Tipología | `sector_no_oficial`, `V4` | — | V4 |
| `PLAN_ENTIDAD_NO_OFICIAL` | Entidad fuera del listado oficial | Info | indicador | Tipología | `entidad_no_oficial`, `V4` | — | V4 |
| `PLAN_FECHA_INVALIDA` | Fecha no legible | Advertencia | indicador | Fechas | `fecha_invalida`, `V5` | Solicitar el ajuste del plan de acción ante la SDP. | V5 |
| `PLAN_FECHA_INICIO_MAYOR_FIN` | Fecha de fin anterior a la de inicio | Error | indicador | Fechas | `fecha_inicio_mayor_fin`, `V5` | Solicitar el ajuste del plan de acción ante la SDP. | V5 |
| `PLAN_META_NO_NUMERICA` | Meta anual no numérica | Error | indicador | Metas | `meta_no_numerica`, `V6`, `V7` | Solicitar el ajuste del plan de acción ante la SDP. | V6/V7 |
| `PLAN_META_FINAL_FALTANTE` | Sin meta final | Error | indicador | Metas | `meta_final_faltante`, `V8` | Solicitar el ajuste del plan de acción ante la SDP. | V8 |
| `PLAN_BRECHA_EN_METAS` | Faltan metas en años de la vigencia | Advertencia | indicador | Metas | `brecha_en_metas`, `V12` | Solicitar el ajuste del plan de acción ante la SDP. | V12 |
| `PLAN_META_FUERA_VIGENCIA` | Metas fuera de la vigencia | Advertencia | indicador | Metas | `meta_fuera_de_rango`, `V15` | Solicitar el ajuste del plan de acción ante la SDP. | V15 |
| `PLAN_META_VS_LINEA_BASE` | Meta final en sentido contrario a la línea base | Error | indicador | Metas | `meta_vs_linea_base`, `V14` | Solicitar el ajuste del plan de acción ante la SDP. | V14 |
| `PLAN_METAS_VS_META_FINAL` | Metas anuales inconsistentes con la meta final | Error | indicador | Metas | `metas_vs_meta_final`, `V17` | Solicitar el ajuste del plan de acción ante la SDP. | V17 |
| `PLAN_ESCALA_MEZCLADA` | Metas en escalas mezcladas | Advertencia | indicador | Escala | `escala_mezclada` | Solicitar el ajuste del plan de acción ante la SDP. | extractor-pa |
| `PLAN_LINEA_BASE_FALTANTE` | Sin línea base | Info | indicador | Línea base | `linea_base_faltante`, `V9` | — | V9 |
| `PLAN_LINEA_BASE_NO_NUMERICA` | Línea base no numérica | Advertencia | indicador | Línea base | `linea_base_no_numerica`, `V9` | Solicitar el ajuste del plan de acción ante la SDP. | V9 |
| `PLAN_LB_OBLIGATORIA_DECRECIENTE` | DECRECIENTE sin línea base | Error | indicador | Línea base | `lb_obligatoria_decreciente`, `V16` | Solicitar el ajuste del plan de acción ante la SDP. | V16 |
| `PLAN_CODIGO_MALFORMADO` | Código con formato inesperado | Info | indicador | Códigos | `codigo_malformado`, `V13` | — | V13 |
| `PLAN_IR_SIN_PRODUCTOS` | Resultado vigente sin productos | Advertencia | resultado | Códigos | `ir_sin_productos`, `V11`, `resultado_sin_productos` | — | V11 |
| `PLAN_JERARQUIA_ROTA` | Producto sin su resultado | Error | producto | Códigos | `jerarquia_ip`, `producto_sin_resultado` | Solicitar el ajuste del plan de acción ante la SDP. | creador; pipeline |
| `PLAN_OBJETIVO_SIN_RESULTADOS` | Objetivo sin resultados | Advertencia | objetivo | Códigos | `objetivo_sin_resultados` | — | sispp-gobierno |

## Seguimiento: año del corte

| código | nombre | severidad | nivel | familia | sustituye a | acción | origen |
|---|---|---|---|---|---|---|---|
| `SEG_NO_NUMERICO` | Reporte no numérico | Error | indicador | Reporte | `ERROR_NO_NUMERICO` | Solicitar alcance a la entidad para corregir el formato de seguimiento. | alertas-seguimientos |
| `SEG_ESCALA` | Escala del reporte distinta de la meta | Advertencia | indicador | Escala | `ADVERTENCIA_ESCALA`, `Escala: meta en fracción y reporte en 0-100` | Solicitar alcance a la entidad: reportar en la misma escala de la meta. | alertas-seguimientos; observaciones.obs_escala |
| `SEG_SOBREEJECUCION_PCT` | % de avance de la vigencia sobre el umbral de sobre ejecución | Advertencia | indicador | Sobre ejecución | `ADVERTENCIA_AVANCE` | Confirmar con la entidad si es real y dejar la explicación en el cualitativo. | alertas-seguimientos |
| `SEG_SOBREEJECUCION_VIG` | Avance de la vigencia sobre el umbral de sobre ejecución | Advertencia | indicador | Sobre ejecución | `ADVERTENCIA_LIMITE_VIG` | Confirmar con la entidad si es real y dejar la explicación en el cualitativo. | alertas-seguimientos |
| `SEG_ACUMULADO_SOBRE_META_VIG` | Acumulado supera la meta acumulada | Advertencia | indicador | Sobre ejecución | `ADVERTENCIA_ACUM_META_VIG` | — | alertas-seguimientos |
| `SEG_ACUMULADO_SOBRE_META_FINAL` | Acumulado supera la meta final | Advertencia | indicador | Sobre ejecución | `ADVERTENCIA_ACUM_META_FIN` | — | alertas-seguimientos |
| `SEG_META_SIN_REPORTE` | Meta sin reporte exigible | Advertencia | indicador | Exigencia | `ADVERTENCIA_META_SIN_REP`, `Sin reporte`, `Falta reporte exigible` | Solicitar alcance a la entidad para corregir el formato de seguimiento. | alertas-seguimientos; estado_reporte |
| `SEG_REPORTE_SIN_META` | Reporte en año sin meta | Advertencia | indicador | Exigencia | `ADVERTENCIA_REP_SIN_META`, `meta_anual = 0 con valor reportado` | Solicitar el ajuste del plan de acción ante la SDP. | alertas-seguimientos |
| `SEG_PCT_HASTA_VIG_FUERA_RANGO` | % hasta la vigencia fuera del semáforo | Advertencia | indicador | Sobre ejecución | `ADVERTENCIA_PCT_HASTA_VIG` | — | alertas-seguimientos |
| `SEG_DISCREPANCIA_PCT` | % reportado distinto del calculado | Advertencia | indicador | Reporte | `ADVERTENCIA_DISCREPANCIA_PCT` | Solicitar alcance a la entidad para corregir el formato de seguimiento. | alertas-seguimientos |
| `SEG_CUALITATIVO_VACIO` | Cualitativo vacío | Advertencia | indicador | Reporte | `ADVERTENCIA_CUAL` | Solicitar alcance a la entidad para corregir el formato de seguimiento. | alertas-seguimientos |
| `SEG_VIGENTE_SIN_PESO` | Indicador vigente sin ponderación (seguimiento) | Error | indicador | Ponderación | `ERROR_PONDERACION_OBLIGATORIA` | Solicitar alcance a la entidad para corregir el formato de seguimiento. | alertas-seguimientos |
| `SEG_SECTOR_ENTIDAD` | Sector distinto del oficial de la entidad | Advertencia | indicador | Tipología | `ADVERTENCIA_SECTOR_ENTIDAD` | Solicitar alcance a la entidad para corregir el formato de seguimiento. | alertas-seguimientos |

## Seguimiento: entre cargas

| código | nombre | severidad | nivel | familia | sustituye a | acción | origen |
|---|---|---|---|---|---|---|---|
| `CARGA_CAMPO_INMUTABLE` | Campo inmutable modificado entre cargas | Error | indicador | Entre cargas | `ERROR_ESTABILIDAD` | Solicitar alcance a la entidad para corregir el formato de seguimiento. | alertas-seguimientos |
| `CARGA_VALOR_HISTORICO` | Valor histórico modificado | Error | indicador | Entre cargas | `ERROR_RETROACTIVO` | Verificar el alcance que respalda el cambio. | alertas-seguimientos |
| `CARGA_CAMBIO_META` | Meta modificada entre cargas | Advertencia | indicador | Entre cargas | `ADVERTENCIA_CAMBIO_META` | Verificar que el acto administrativo respalde el ajuste. | alertas-seguimientos |
| `CARGA_CAMBIO_ESTADO` | Cambio de estado entre cargas | Info | indicador | Entre cargas | `INFO_CAMBIO_ESTADO` | — | alertas-seguimientos |
| `CARGA_INDICADOR_NUEVO` | Indicador nuevo | Info | indicador | Entre cargas | `INFO_IND_NUEVO` | — | alertas-seguimientos |
| `CARGA_INDICADOR_FALTANTE` | Indicador faltante | Info | indicador | Entre cargas | `INFO_IND_FALTANTE` | — | alertas-seguimientos |

## Cruce plan ↔ seguimiento

| código | nombre | severidad | nivel | familia | sustituye a | acción | origen |
|---|---|---|---|---|---|---|---|
| `CRUCE_IND_NO_EN_PLAN` | Indicador del seguimiento que no está en el plan | Info | indicador | Cruce | `codigo_seguimiento_sin_plan`, `indicador_reportado_sin_plan`, `Productos del seguimiento que no están en el plan 2026` | Verificar la correspondencia de códigos con la entidad y la SDP. | seguimiento.cruzar_con_plan; alertas_datos; observaciones |
