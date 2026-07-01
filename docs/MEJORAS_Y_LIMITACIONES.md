# Pendiente y mejoras identificadas — extractor maestro

Lista canónica de lo que **falta** y de **todas las mejoras** detectadas a lo
largo del desarrollo. Estado base: el motor de **plan** (extracción nuevo+antiguo,
validación V0–V18, salidas) y la **capa de seguimiento** (S1–S4) están completos
y validados (38 planes + 55 seguimientos, golden files + paridad, 30 pruebas).

Prioridad: 🔴 alta · 🟠 media · 🟢 baja.

---

## A. Trabajo pendiente (fases)

| # | Pendiente | Prio | Notas |
|---|---|:---:|---|
| A1 | **Fase 8 — Migración** de los 9 aplicativos al maestro | 🔴 | Reemplazar cada extractor legado por la librería, comparando salida vs golden antes de retirar. |
| A2 | **Empaquetado**: `pip install`, **CLI** (`python -m extractor_pa archivo.xlsx`), versionado/publicación interna | 🔴 | Necesario para que los apps lo consuman. |
| A3 | **Tablero único de cumplimiento por política** (cruza plan + seguimiento + semáforo en un HTML/Excel navegable) | 🟠 | Piezas ya listas (`cruzar_con_plan`, `consolidar`, `semaforo_de`); falta el ensamblado. |
| A4 | **Adaptador a ORM relacional versionado** (modelo de `seguimiento-pp-sdis`) | 🟢 | Hoy hay JSON/CSV/Excel/DataFrame; falta persistencia en BD. |

## B. Alertas del catálogo aún no implementadas (19 de 70)

| # | Alertas | Prio | Por qué falta |
|---|---|:---:|---|
| B1 | ✅ **V4** `sector_no_oficial`/`entidad_no_oficial` + normalización difusa (v0.9.10) | — | **Opcional**: `extraer_plan_accion(..., catalogo_oficial=CatalogoOficial())`. Sin catálogo no se ejecuta. |
| B2 | ✅ `objetivo_sin_resultados`, `jerarquia_ip` (v0.9.11) | — | **`Objetivo`** como entidad (capturada aunque no tenga IR) + validación de jerarquía N.N.N⊂N.N. 74 planes reales: 0 espurios. |
| B3 | `formato_no_compatible`, `metadatos` (gate de plantilla del plan) | 🟢 | Bloqueo de plantillas incompatibles + nombre de política del formato antiguo. |
| B4 | **Operativas** (`sispp-sdis`): vencimiento, sin responsable, sin seguimiento, rezago, sobrecumplimiento, variación anómala, CRP sobreasignado | 🟠 | **Dependen del contexto de operación** (períodos, usuarios, BD), no de un archivo → pertenecen a la app, no al extractor. |
| B5 | **Cualitativas** (RN-CUL): justificación obligatoria de rezago/sobrecumplimiento | 🟢 | Requieren el reporte cualitativo en contexto de operación. |
| B6 | **Q001–Q003** (calidad declarativa de `sistema-seguimiento-v3`) | 🟢 | Reglas de cierre/ajuste; dependen de estado del sistema. |

## C. Exactitud del extractor de PLAN

| # | Mejora | Prio | Detalle |
|---|---|:---:|---|
| C1 | ✅ **Nombre de política robusto** (v0.9.5): busca "Política Pública" en cabecera si la celda fija trae Decreto/CONPES/"No aplica"/vacío | — | Hecho. 0 sospechosos en 38 planes. |
| C2 | ✅ **Parser de fechas** (v0.9.2): año 2 dígitos, serial Excel, formato US | — | Hecho. Las inválidas reales quedan como `fecha_invalida`. |
| C3 | ⏸️ **Ascensión de fila vigente** para metas/meta_final | 🟢 | Diferido: no afecta la huella; requiere verdad de campo para validar el cambio. |
| C4 | ✅ **Conservar metas no numéricas** (v0.9.7): el maestro guarda el texto crudo de metas como `'más 0.01 punto'` | — | Hecho. Detectado por la auditoría de migración (95 casos). |
| C5 | ✅ **Escala mezclada** (v0.9.2): alerta `escala_mezclada` para confusión ×100 (0-1 vs 0-100), conservadora | — | Hecho. |

## D. Extractor de SEGUIMIENTO

| # | Mejora | Prio | Detalle |
|---|---|:---:|---|
| D1 | **Fallback a layout fijo** si no se encuentran las anclas (algunos `.xlsb` podrían variar) | 🟢 | Diferido: en los 51 `.xlsb` reales las anclas siempre se encontraron. |
| D2 | ✅ **Metadatos de período/año desde columnas** (v0.9.5): `corte`→período, año de reporte→año cuando el nombre no los trae | — | Hecho. `BTI.xlsb` → Q4/2025. |
| D3 | **Normalizar escala** de avances/% del seguimiento de forma consistente (fracción vs %) | 🟢 | Diferido: hoy el semáforo normaliza; unificar criterio. |

## E. Robustez / rendimiento / infraestructura

| # | Mejora | Prio | Detalle |
|---|---|:---:|---|
| E1 | Apertura **sin `read_only`** del plan → lenta en libros de 50+ hojas | 🟢 | Evaluar leer solo la hoja del plan o cachear; el motivo es acceder a celdas combinadas de encabezado. |
| E2 | ✅ Ignorar archivos temporales **`~$`** en todos los scripts de lote (v0.9.2) | — | Hecho y verificado. |
| E3 | ✅ **Golden completo** (97 huellas, todas las políticas) + unit tests por etapa (v0.9.4) | — | Hecho. `pytest -m slow` para la regresión exhaustiva. |
| E4 | ✅ **Métricas de extracción** en `Metadatos` (`n_ir`/`n_ip`/`n_alertas`/`pct_ir_con_linea_base`) (v0.9.2) | — | Hecho. Tipado fuerte queda para H2. |

## F. Funcionalidades de valor (heredables de los legados)

| # | Mejora | Prio | Origen |
|---|---|:---:|---|
| F1 | ✅ **Triage persistente de alertas** (v0.9.12): `gobernanza.py` — clave estable por hash, estados nueva/en_gestion/resuelta/descartada, `reconciliar` con autocierre, store JSON atómico + auditoría JSONL | — | `sispp-gobierno` (gobernanza del dato). |
| F2 | ✅ **Reaplicar correcciones humanas aprobadas** (v0.9.13): `decisiones.py` — `RegistroDecisiones` (store JSON + auditoría, acciones aprobar/nombre_nuevo/ignorar/eliminar) + `aplicar_decisiones` (reaplica sobre IR/IP) + puente `aprobar_sugerencias` desde B1 | — | `sispp-gobierno`. Cierra el flujo B1→F2. |
| F3 | **Normalización difusa de entidades/sectores** (RapidFuzz) contra catálogo oficial | 🟠 | `sispp-gobierno` (paso 3) → habilita B1. |
| F4 | **Reportes adicionales**: inconsistencias por política (ya en el CSV), hoja de vida del indicador, brechas/avance agregado | 🟢 | `generador-seguimiento`, `alertas-seguimientos`. |

## G. Estado de lo YA resuelto (referencia)

- ✅ Extracción plan **nuevo + antiguo** (bloque financiero) con detección por anclas configurables.
- ✅ Celdas combinadas (4 capas + ascensión), año de vigencia, escala % por `number_format`.
- ✅ **Fichas técnicas** (5 convenciones de nombre).
- ✅ Reglas de negocio **V0–V18** + consistencia (inconsistencia IR, IP duplicado).
- ✅ **Catálogo consolidado** (70 tipos) como fuente única de niveles.
- ✅ **Salidas** JSON/CSV/Excel/DataFrame (por archivo y consolidado).
- ✅ **Seguimiento** S1–S4 (extracción `.xlsb`, cruce con plan, consolidación por período, 15 alertas de consistencia + semáforo, salidas).
- ✅ **Regresión (golden) + paridad** con legados (plan 8/8, seguimiento 6/6).
- ✅ **Reportes accionables por política** (plan, seguimiento, fichas/unidad).
