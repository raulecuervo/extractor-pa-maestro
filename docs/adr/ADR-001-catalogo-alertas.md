# ADR-001 — Catálogo único de alertas de calidad (plan y seguimiento)

**Estado:** aceptado (1-nov-2026). **Decide:** Esteban Cuervo (OAP / SDP).
**Alcance:** `extractor_pa.calidad` (desde la 0.28.0); consumidores en las fases F3–F4.
**Contexto:** `ANALISIS_ALERTAS_UNIFICADAS.md` (1-nov-2026): la misma regla vivía
hasta en cinco sitios (extractor, `validar_plan` y `observaciones.py` del pipeline de
sispp-gobierno/SDP, el validador de alertas-seguimientos y `ml_comentarios`) con
cuatro tolerancias de peso, seis umbrales de escala y severidades contradictorias.

## Decisión

1. **Una sola fuente:** las reglas viven en `extractor_pa.calidad` (catálogo
   `CATALOGO_CALIDAD`, motor `evaluar`). Los consumidores no reimplementan reglas:
   el pipeline toma `a_observacion()` / `a_alerta()` y la app `as_finding()`.
   Las fachadas `validar_reglas`, `validar_archivo`, `validar_consistencia` y
   `catalogo.CATALOGO` se conservan.
2. **Código canónico + tipo legado.** Cada regla tiene un código estable
   (`PLAN_…`, `SEG_…`, `SERIE_…`, `CARGA_…`, `CRUCE_…`, `EXT_…`) y conserva como
   `Hallazgo.tipo` el tipo legado (`ADVERTENCIA_ESCALA`, `ponderacion_objetivos`…)
   mientras dure la transición: el gate de paridad de la app y el esquema de
   `alertas_planes_accion.csv` no cambian. Las reglas nuevas usan su código canónico
   como tipo.
3. **Tolerancia de las sumas de ponderación: 0,1 puntos porcentuales**
   (`ParametrosCalidad.tolerancia_peso_pp`). Sustituye a 0,01 pp (app), 0,5 pp
   (extractor), 2 pp (`alertas_datos`) y 2 % relativo (`validar_plan`, `observaciones`).
   Rige desde la 0.29.0. La tolerancia de metas anuales contra la meta final (V17)
   sigue en 0,5 absoluto (`tolerancia_meta_final`), acotada al 1 % de la meta para
   que una meta en fracción (0,8 frente a 1) no quede escondida.
4. **Sobre ejecución y escala.** Un avance **> 125 %** de la meta (techo naranja del
   semáforo, configurable con `umbrales_semaforo`) es **sobre ejecución: severidad
   Info**. Un avance **> 250 %** (`umbral_escala`, «el doble de la sobre ejecución»)
   es **posible error de escala: severidad Advertencia**. Sustituye a los umbrales
   150 / 200 / 300 / 500 % y 10× del pipeline. Aplica a las reglas de sobre ejecución
   del año del corte (`SEG_SOBREEJECUCION_PCT`, `SEG_SOBREEJECUCION_VIG`,
   `SEG_PCT_HASTA_VIG_FUERA_RANGO` por arriba, `SEG_ACUMULADO_SOBRE_META_VIG`,
   `SEG_ACUMULADO_SOBRE_META_FINAL`) y a las de la serie histórica
   (`SERIE_SOBREEJECUCION` Info, `SERIE_ESCALA` Advertencia). La incoherencia de
   escala meta 0–1 / reporte > 1 (`SEG_ESCALA`) sigue siendo Advertencia.
   Rige desde la 0.29.0.
5. **Severidad de las reglas del plan.** Son **Error** las reglas «duras», las que
   dejan el indicador o la política sin avance calculable o rompen la agregación:
   pesos que no suman (V0, V1, V2), vigente sin peso y No Vigente con peso (V18),
   códigos duplicados y jerarquía rota, tipo de anualización no reconocido, meta no
   numérica, sin meta final, metas inconsistentes con la meta final según el tipo
   (SUMA, CONSTANTE, última meta), meta final en sentido contrario a la línea base,
   DECRECIENTE sin línea base y fecha de fin anterior a la de inicio. El resto es
   **Advertencia** (periodicidad, fechas no legibles o vacías, brechas de metas,
   metas fuera de la vigencia, metas no monótonas, escala mezclada, LB no numérica,
   vigencia vacía, sin responsable, IR sin productos, objetivo sin resultados) o
   **Info** (LB faltante, código malformado o mal escrito, fecha escrita como texto,
   sector/entidad fuera del listado). El pipeline deja de bajar las V a WARNING.
6. **Exigencia de reporte («meta sin reporte»).** Una sola regla
   (`SEG_META_SIN_REPORTE`) con las funciones vigentes de la 0.27.0:
   `exige_reporte_en` (años con meta programada, `hay_meta`), `trimestre_exigible`,
   `sin_iniciar_al_corte` y `fin_efectivo` (fin del periodo de reporte que contiene la
   fecha de fin). Manda la **periodicidad del plan** cuando se evalúa con plan
   (`periodicidad_de="plan"`); sin plan, la del formato. Es la misma regla que da
   «Sin reporte» en `estado_reporte` del tablero, para que app y tablero no se
   contradigan. Rige desde la 0.29.0 (antes: periodicidad del seguimiento y
   `fecha_fin` cruda).
7. **No Vigentes.** No generan alertas de reporte ni de exigencia (la app las
   descarta con RN-06 y el pipeline no las alerta: 452 falsos positivos). Sí se
   alerta **No Vigente con ponderación > 0**, en el plan (`PLAN_NO_VIGENTE_CON_PESO`)
   y en el seguimiento (`SEG_NO_VIGENTE_CON_PESO`), ambas Error. Con
   `incluir_no_vigentes=False` el motor descarta lo demás.
8. **Meta antes de la fecha de inicio: una sola implementación**
   (`metricas.metas_antes_de_inicio`), en la regla `META_ANTES_INICIO`, que corre
   sobre el plan si lo hay y, si no, sobre las metas del formato de seguimiento.
   Sustituye a `meta_fuera_de_rango` (lado «antes»), `obs_metas_antes_de_inicio` del
   pipeline y `db.alertas_metas_antes_de_inicio` de la app. El lado «después del fin»
   queda en `PLAN_META_DESPUES_FIN`.
9. **Reglas nuevas** (0.29.0): metas no monótonas (`PLAN_METAS_NO_MONOTONAS`),
   CONSTANTE con metas distintas de la meta final (`PLAN_CONSTANTE_METAS_DISTINTAS`),
   SUMA cuyas metas no suman la meta final (`PLAN_SUMA_METAS_VS_MF`, antes dentro de
   V17), fecha vacía (`PLAN_FECHA_VACIA`) y escrita como texto (`PLAN_FECHA_COMO_TEXTO`),
   reporte negativo (`SEG_REPORTE_NEGATIVO`), retroceso del indicador
   (`SERIE_RETROCESO`), reporte en año sin meta en la serie (`SERIE_REPORTE_SIN_META`),
   código mal escrito (`PLAN_CODIGO_MAL_ESCRITO`), vigencia vacía
   (`PLAN_VIGENCIA_VACIA`), producto sin responsable (`PLAN_SIN_RESPONSABLE`),
   periodicidad del plan distinta de la del seguimiento (`CRUCE_PERIODICIDAD_DISTINTA`),
   indicador del plan que no está en el seguimiento (`CRUCE_IND_NO_EN_SEGUIMIENTO`).
10. **Lo que se queda en cada consumidor:** en el pipeline, «política con
    seguimiento y sin plan», «política sin avance calculable» (dependen del conjunto
    de archivos), las observaciones manuales, el responsable (entidad o líder) y el
    filtro lidera/participa; en la app, el cotejo con el Panel SDP, la cobertura de
    cargas, los alias de entidades de Parametrizaciones (se inyectan como
    `entidad_sector`), el semáforo (se inyecta como `umbrales_semaforo`) y
    `ml_comentarios`.
11. **Versionado.** Los cambios de alertas se publican como versiones «Cambia
    alertas» en el CHANGELOG (igual que «Cambia cifras»), y se suben juntos los
    consumidores que se comparan entre sí. 0.28.0: solo esqueleto (mismas alertas);
    0.29.0: decisiones 3–9.

## Correspondencia de códigos

| Canónico | Sustituye a |
|---|---|
| `PLAN_PESO_OBJETIVOS` | `ponderacion_objetivos`, V0, «Pesos de la política no suman 100 %» |
| `PLAN_PESO_CADENA_OBJ_IR` | `ponderacion_ir`, V1, `cadena_objetivo_resultados`, «Pesos del objetivo no cuadran» |
| `PLAN_PESO_CADENA_IR_IP` | `ponderacion_ip`, V2, `cadena_resultado_productos` |
| `PLAN_VIGENTE_SIN_PESO` | `ponderacion_faltante`, `vigencia_ponderacion` (vigente a 0), `indicador_sin_ponderacion`, V18 |
| `PLAN_NO_VIGENTE_CON_PESO` | `vigencia_ponderacion` (No Vigente con peso), «Producto No Vigente con peso» |
| `PLAN_VIGENCIA_VACIA` | `indicador_sin_vigencia` |
| `PLAN_SIN_RESPONSABLE` | `indicador_sin_responsable`, `INDICADOR_SIN_RESPONSABLE`, V4c |
| `PLAN_FECHA_INVALIDA` / `PLAN_FECHA_VACIA` / `PLAN_FECHA_COMO_TEXTO` | `fecha_invalida` (V5) y las reglas «Sin fecha» / «Fecha escrita como texto» del formato 3.4 |
| `PLAN_SUMA_METAS_VS_MF` / `PLAN_CONSTANTE_METAS_DISTINTAS` / `PLAN_ULTIMA_META_VS_MF` | `metas_vs_meta_final` (V17), `EXTRA_META_FINAL_VS_SUMA` |
| `META_ANTES_INICIO` / `PLAN_META_DESPUES_FIN` | `meta_fuera_de_rango` (V15), `obs_metas_antes_de_inicio`, `ADVERTENCIA_META_ANTES_INICIO`, `EXTRA_FECHAS_FIN_CON_META` |
| `PLAN_CODIGO_MAL_ESCRITO` | `utilidades.codigo_mal_escrito` hecho alerta |
| `SEG_ESCALA` / `SERIE_ESCALA` / `SERIE_SOBREEJECUCION` | `ADVERTENCIA_ESCALA`, `obs_escala`, `EXTRA_ESCALA_SERIE`, reglas de escala de `calidad.py` |
| `SEG_META_SIN_REPORTE` | `ADVERTENCIA_META_SIN_REP`, «Sin reporte» de `estado_reporte`, `EXTRA_PERIODICIDAD_SIN_REPORTE` |
| `SEG_REPORTE_SIN_META` / `SERIE_REPORTE_SIN_META` | `ADVERTENCIA_REP_SIN_META`, «meta_anual = 0 con valor reportado» |
| `SEG_REPORTE_NEGATIVO` | «valor_reportado negativo» |
| `SERIE_RETROCESO` | `DISMINUCION_CRECIENTE`, `AUMENTO_DECRECIENTE`, `EXTRA_SENTIDO_CONTRARIO` |
| `CRUCE_IND_NO_EN_PLAN` | `codigo_seguimiento_sin_plan` (pasa a ADVERTENCIA), `indicador_reportado_sin_plan`, «Productos del seguimiento que no están en el plan 2026»; solo indicadores vigentes |
| `CRUCE_IND_NO_EN_SEGUIMIENTO` | `obs_cruce_plan_seguimiento` («Productos del plan que no están en el seguimiento») |
| `CARGA_*` | `ERROR_ESTABILIDAD`, `ERROR_RETROACTIVO`, `ADVERTENCIA_CAMBIO_META`, `INFO_CAMBIO_ESTADO`, `INFO_IND_NUEVO`, `INFO_IND_FALTANTE` |
| `EXT_*` | alertas estructurales de `res.alertas` (plan y seguimiento) |

El catálogo completo, generado desde el código, está en `docs/CATALOGO_CALIDAD.md`.

## Consecuencias

- La app verá más alertas en 0.29.0 (exigencia por `fin_efectivo`, series) y
  cambios de severidad (sobre ejecución a Info); el gate de paridad se actualiza en F4.
- El tablero cambia conteos en «Calidad del dato» (no el esquema) en F3.
- Las tres copias de las reglas del plan (`validar_plan`, `alertas_datos`,
  `observaciones`) se retiran en F3; el validador de la app adopta el catálogo en F5.
