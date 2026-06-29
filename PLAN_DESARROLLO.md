# Plan de desarrollo — Extractor maestro de política pública

Hoja de ruta para llevar la librería `extractor_pa` desde su estado actual
(núcleo completo y validado) hasta su **adopción en producción** y la
incorporación de las mejoras identificadas.

## Estado actual (línea base)
- ✅ **Plan**: extracción nuevo+antiguo, normalización de celdas combinadas,
  vigencia, fichas técnicas, reglas **V0–V18**, consistencia, salidas.
- ✅ **Seguimiento (S1–S4)**: extracción `.xlsb`, cruce con plan, consolidación
  por período, 15 alertas de consistencia + semáforo, salidas.
- ✅ **Catálogo consolidado** (70 tipos), **golden files + paridad** con legados,
  **reportes accionables por política**.
- Validado: 38 planes + 55 seguimientos · 30 pruebas.

## Principios
1. **Nada que hoy funciona se rompe**: cada cambio pasa por los golden files.
2. **Migración con paridad**: ningún legado se retira sin demostrar equivalencia.
3. **Una sola fuente de verdad**: modelo canónico + catálogo de alertas.
4. **Lo operativo vive en la app**, lo de archivo vive en la librería.

## Convenciones
Esfuerzo: **S** ≤1 día · **M** 2–4 días · **L** 1–2 semanas. Prio: 🔴 alta · 🟠 media · 🟢 baja.

---

## Sprint 0 — Quick wins ✅ HECHO (v0.9.2)
- ✅ Ignorar archivos `~$` en todos los scripts de lote (E2).
- ✅ Parser de fechas: año 2 dígitos, serial Excel, formato US (C2).
- ✅ Alerta `escala_mezclada` conservadora (ratio ≥50) (C5).
- ✅ Métricas en `Metadatos`: `n_ir`/`n_ip`/`n_alertas`/`pct_ir_con_linea_base` (E4).
- **Resultado**: golden sin regresión; `fecha_invalida` baja de 40 a ~13 (el resto
  son fechas realmente inválidas); 48 pruebas verdes; catálogo 71 tipos.

---

## Hito 1 — Empaquetado y CLI ✅ HECHO (v0.9.3)
- ✅ `pyproject` con entry point; **CLI** `extractor-pa` (= `python -m extractor_pa`)
  con subcomandos `plan`, `seguimiento`, `validar` y salidas `--json/--csv/--excel`.
- ✅ **CI** `.github/workflows/ci.yml` (pytest 3.10–3.12 + verificación CLI).
- ✅ `pip install -e .` y console script verificados; `tests/test_cli.py` (53 pruebas).
- Pendiente menor: build/publicación de wheel a un índice interno (cuando haya repo).

## Hito 2 — Endurecer la regresión ✅ HECHO (v0.9.4)
- ✅ **Golden completo**: 97 huellas (38 planes + 51 seguimientos) — descubrimiento
  automático de todas las políticas; `pytest -m slow` para la regresión exhaustiva.
- ✅ **Unit tests por etapa** (`test_unidades.py`, 37): utilidades, vigencia, fichas.
- **Resultado**: 90 pruebas por defecto + 89 `slow` = 179; corpus golden cubre el 100% de políticas.
- Pendiente menor: tipado fuerte (E4) y unit tests de resolutor/normalizador (cubiertos hoy por golden).

## Hito 3 — Exactitud del extractor ✅ HECHO (v0.9.5)
- ✅ **C1 — Nombre de política** robusto: busca "Política Pública" en cabecera
  cuando la celda fija trae Decreto/CONPES/"No aplica"/vacío → 0 sospechosos en 38.
- ✅ **D2 — Seguimiento**: período/año desde columnas (`corte`, año de reporte)
  cuando el nombre no los trae.
- ✅ **C4** (conservar metas no numéricas, v0.9.7) — detectado por la auditoría de
  migración (95 casos de texto perdido); ahora el maestro los conserva.
- ⏸️ **C3** (ascensión de metas a fila vigente), **D1** (fallback de layout fijo) y
  **D3** (escala unificada): diferidos. La auditoría de migración mostró que no hay
  pérdida numérica ni en otros campos, así que C3 es de bajo impacto. Ver
  `docs/MEJORAS_Y_LIMITACIONES.md`.
- **Resultado**: golden re-aprobado; nombre correcto en todos los planes.

## Hito 4 — Catálogos oficiales + V4 + normalización difusa 🟠 (L)
- Inyectar **catálogo oficial** de sectores/entidades.
- Implementar **V4** (`sector_no_oficial`, `entidad_no_oficial`).
- **Normalización difusa** (RapidFuzz) heredada de `sispp-gobierno` (paso opcional).
- Modelar el **objetivo** como entidad → `objetivo_sin_resultados`, `jerarquia_ip` (B2).
- **Dependencias**: H3. **Aceptación**: V4 corre y sugiere normalizaciones; reportes incluyen entidades no oficiales.

## Hito 5 — Tablero de cumplimiento por política ✅ HECHO (v0.9.8)
- ✅ `extractor_pa/tablero.py`: empareja plan↔seguimiento por sigla, cruza, calcula
  semáforo de avance (% vigencia) + hallazgos V0–V18, y **renderiza HTML navegable**
  (KPIs, leyenda, tabla ordenable + filtro). `scripts/gen_tablero.py` → HTML + CSV.
- Salida: `../_codigo_extraido_pp/TABLERO_CUMPLIMIENTO.html` + `tablero_cumplimiento.csv`.

## Hito 6 — Gobernanza de alertas (triage persistente) 🟠 (M)
- **Triage** con clave estable por hash, estados (nueva/en_gestión/resuelta/descartada),
  autocierre y auditoría (heredar `sispp-gobierno`).
- **Reaplicar correcciones humanas aprobadas** antes de extraer (F2).
- **Dependencias**: H1. **Aceptación**: las decisiones humanas sobreviven re-extracciones.

## Hito 7 — Persistencia / ORM relacional versionado 🟢 (L)
- Adaptador a **modelo relacional** (de `seguimiento-pp-sdis`) con **versionado + diff**.
- **Dependencias**: H1. **Aceptación**: cargar plan/seguimiento a BD con versión e historial.

## Hito 8 — Migración de los aplicativos (Fase 8) 🔴 (L) · *gated por H1, H2*
Por cada aplicativo: envolver el maestro tras la firma legada → comparar salida
vs golden → reemplazar → retirar el legado. Orden sugerido:
1. ✅ **`extractor-planes-accion`** (v0.9.7) — **formato nuevo activado** y
   verificado: adaptador + gate de paridad + brecha `dir_responsable` cerrada +
   **auditoría de pérdidas = 0** (C4 conserva metas de texto). **Formato antiguo
   analizado** (CTI): el maestro mejora núcleo y financiero pero pierde ~276 celdas
   antiguo-específicas → se mantiene el legado antiguo (1 solo plan). Además se
   **corrigió el detector** del aplicativo (clasificaba mal CTI como nuevo → basura);
   ahora CTI enruta al legado antiguo (financiero 333, completo). Ver
   `../extractor-planes-accion/MIGRACION_EXTRACTOR_PLANES.md`.
2. ✅ **`validador-plan-accion`** — adaptador `extraccion_maestro.py` + gate
   `comparar_validador.py`, **activado**; 7/7 tests del app verdes; el maestro
   **mejora** (DRAFE ahora valida; menos falsos `inconsistencia_en_ir`). Ver
   `../validador-plan-accion/MIGRACION_VALIDADOR.md`. (Falta `generador-seguimiento`.)
3. ✅ **`alertas-seguimientos`** — adaptador `extractor_maestro.py` (capa de
   seguimiento `.xlsb`) + gate; **activado**; 57/57 tests; **alertas byte-idénticas**
   (`run_all_validations`: 56=56, 10=10). Ver `../alertas-seguimientos/MIGRACION_ALERTAS_SEG.md`.
4. ◑ **`seguimiento-pp-sdis`** — adaptador `plan_accion_import_maestro.py` + gate
   **listos, NO activados** (el maestro arregla un extractor roto: legado extrae 0
   metas, falla DRAFE, trunca códigos → cambia datos de BD; activar con migración
   de datos). Ver `../seguimiento-pp-sdis/MIGRACION_PLAN_IMPORT.md`.
5. ✅ **`sispp-sdis`** — adaptador `etl_maestro.py` + gate, **activado** (`test_etl`
   10/10; maestro arregla DRAFE, lee más fichas). `MIGRACION_ETL.md`.
6. ✅ **`generador-seguimiento`** — adaptador `parsear_maestro.py`, **activado**;
   salida **byte-idéntica** (datos+resumen+cualitativo 8/8). `MIGRACION_SEGUIMIENTO.md`.
7. ✅ **`sispp-gobierno`** — **activado y validado aguas abajo**: etapa 01 (maestro)
   → CSVs; etapas 02-06 los consumen sin error (fact_metas 34.228); 49 tests passed.
   (Etapa 04 seguimiento sigue en legado, migrable aparte.) `MIGRACION_PIPELINE.md`.
8. ✅ **`creador-planes-accion`** — adaptador `import_excel_maestro.py` (reconstruye
   la jerarquía ORM), **activado**; **roundtrip verificado 20/20**. `MIGRACION_IMPORT.md`.
9. ✖️ **`sistema-seguimiento-v3`** — API/formularios, no extrae de Excel.

**Migración: los 8 extractores reales migrados** (7 activos verificados + creador
20/20). Pendiente menor: etapa 04 (seguimiento) de sispp-gobierno — ver A5 en
`PLAN_PENDIENTE.md`.
- **Aceptación por app**: paridad vs golden + pruebas de la app verdes; legado retirado.

## Hito 9 — Capa operativa/cualitativa (en la app, opcional) 🟢 (L)
- Alertas **operativas** (vencimiento, sin responsable, rezago, sobrecumplimiento,
  variación anómala, CRP) y **cualitativas** (RN-CUL), **dentro de la app de
  operación** (SISPP), consumiendo el modelo canónico + períodos/usuarios.
- **Dependencias**: H8. **Aceptación**: notificaciones operativas en la app destino.

---

## Secuencia recomendada
```
Sprint 0 (quick wins)
   │
   ▼
H1 Empaquetado/CLI ──► H2 Regresión ──► H3 Exactitud ──► H8 Migración (1→5)
   │                         │                │
   │                         │                ├─► H4 Catálogos/V4
   │                         │                └─► H5 Tablero
   ├─► H6 Gobernanza
   └─► H7 ORM
                                                   H9 Operativa (post-migración, en la app)
```
**Camino crítico para producción:** Sprint 0 → H1 → H2 → H3 → H8.
**Valor temprano para gestión:** H5 (tablero) y los reportes ya existentes.

## Riesgos y mitigaciones
| Riesgo | Mitigación |
|---|---|
| Deriva de la plantilla SDP | Anclas configurables + gate de compatibilidad + golden files. |
| Romper un app al migrar | Paridad vs golden por app antes de retirar el legado (H8). |
| Nombres de política inconsistentes | Usar `archivo` como id; H3 mejora el nombre. |
| Falta de `.xlsb`/plantillas nuevas | Corpus de golden + fallback de layout (H3). |
| Catálogo oficial no disponible | V4 queda opcional/inyectable (H4). |

## Métrica de "hecho"
- 100% de las políticas con golden y paridad.
- Todos los aplicativos consumiendo `extractor_pa` (legados retirados).
- Tablero de cumplimiento operativo y reportes por política automatizados.
