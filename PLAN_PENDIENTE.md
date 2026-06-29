# Plan de lo pendiente — Extractor maestro `extractor_pa`

Estado base: la librería (plan + seguimiento + reglas V0–V18 + salidas + tablero +
golden/paridad) está completa y validada; **7 de 7 extractores reales migrados**
(6 activos + sispp-gobierno activado y validado aguas abajo). Quedan cierres de
adopción, mejoras de funcionalidad y endurecimiento.

Prioridad: 🔴 alta · 🟠 media · 🟢 baja. Esfuerzo: S ≤1d · M 2–4d · L 1–2sem.

---

## A. Cerrar la adopción (camino crítico)

| # | Pendiente | Prio | Esf. |
|---|---|:--:|:--:|
| A1 | **Versionar y publicar `extractor-pa`**: `git init` + repo en GitHub, **build de wheel** y publicación a un índice interno (o tag de release). Hoy es `pip install -e`. | 🔴 | M |
| A2 | **Fijar la dependencia** en cada app migrada (`requirements.txt` → `extractor-pa==X.Y.Z`) y dejar de depender del editable. | 🔴 | S |
| A3 | **CI** del maestro (GitHub Actions ya escrito en `.github/workflows/ci.yml`) — activar al crear el repo. | 🟠 | S |
| A4 | ✅ **`creador-planes-accion`** migrado (adaptador `import_excel_maestro.py`, reconstruye la jerarquía ORM) — **roundtrip 20/20**, activado. | — | — |
| A5 | ✅ **Etapa 04 de seguimiento de `sispp-gobierno`** migrada (v0.9.9 con `metas_acumuladas`); cuant byte-idéntico, 04→05 validadas. | — | — |
| A6 | **Retirar los extractores legados** tras un período de validación en producción (hoy quedan intactos como respaldo; cada migración es reversible con 1 línea). | 🟠 | S |
| A7 | **Correr la suite completa de cada app en su propio entorno** (aquí faltan deps: `bcrypt` en sispp-sdis, deps de creador). Confirmar verde con el adaptador. | 🟠 | S |

## B. Mejoras de funcionalidad del maestro

| # | Pendiente | Prio | Esf. |
|---|---|:--:|:--:|
| B1 | **Catálogos oficiales + V4**: inyectar sectores/entidades oficiales, alerta `sector_no_oficial`/`entidad_no_oficial`, y **normalización difusa** (RapidFuzz) — heredar de `sispp-gobierno` (paso 03). Habilita la paridad total de la unidad/entidad. | 🟠 | L |
| B2 | **Objetivo como entidad**: `objetivo_sin_resultados`, `jerarquia_ip` (validar N.N.N ⊂ N.N). | 🟠 | M |
| B3 | **Gobernanza de alertas** (triage persistente): clave estable por hash, estados (nueva/en_gestión/resuelta), autocierre, auditoría; reaplicar correcciones aprobadas — heredar de `sispp-gobierno`. | 🟠 | M |
| B4 | **Alertas operativas/cualitativas** (vencimiento, rezago, sin responsable, RN-CUL, Q001–Q003): viven en la app de operación; implementarlas consumiendo el modelo canónico. | 🟢 | L |
| B5 | **Adaptador ORM** relacional versionado (modelo de `seguimiento-pp-sdis`). | 🟢 | L |

## C. Refinamientos y calidad

| # | Pendiente | Prio | Esf. |
|---|---|:--:|:--:|
| C1 | **C3** (leer metas/meta_final desde la fila vigente promovida): la auditoría mostró 0 pérdida numérica, bajo impacto; cerrar cuando haya verdad de campo. | 🟢 | S |
| C2 | **D1/D3** seguimiento: fallback a layout fijo si faltan anclas; unificar criterio de escala. | 🟢 | S |
| C3 | **Más golden por variante** y unit tests por etapa (resolutor/normalizador) además de los actuales. | 🟢 | S |
| C4 | **Tablero**: aliases de emparejamiento adicionales si aparecen políticas con sigla muy distinta; export a Excel navegable además del HTML. | 🟢 | S |
| C5 | **Reportes accionables**: hoja de vida del indicador, brechas/avance agregado (heredables de `generador-seguimiento`/`alertas-seguimientos`). | 🟢 | M |

## D. Operación / housekeeping
- Resolver el `input()` interactivo de la etapa 03 de `sispp-gobierno` (directorio oficial) con un flag no interactivo, para CI/pipeline desatendido.
- Limpiar seguimientos duplicados en `02_seguimientos/` (aviso de la etapa 06).
- Documentar en cada app cómo instalar `extractor-pa` (extras `[xlsb]` donde aplique).

---

## Secuencia recomendada
**A1 → A2/A3** (publicar + fijar dependencia + CI) desbloquea todo. En paralelo
**A4/A5** (cerrar los 2 extractores restantes) y luego **A6** (retirar legados).
**B1+B3** (catálogos/V4 + gobernanza) es el mayor salto de funcionalidad. El resto
(B/C) es incremental.

## Definición de "terminado"
- `extractor-pa` publicado y consumido por `pip install extractor-pa` en las apps.
- Los 7 extractores activos con sus suites verdes en sus entornos.
- Legados retirados tras validación.
