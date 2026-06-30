# Plan de lo pendiente — Extractor maestro `extractor_pa`

Estado base (v0.9.12, 124 pruebas): la librería (plan + seguimiento + reglas
V0–V18 + B1/B2/B3 + salidas + tablero + golden/paridad) está completa y validada;
**8 de 8 extractores reales migrados** y activados en rama `migracion-extractor-pa`.
La librería está **publicada y versionada** (repo privado, tags) y las apps están
**pinadas**. Lo que queda es **adopción** (merge → validar en entorno → retirar
legados) y mejoras opcionales.

> **El runbook secuenciado para cerrar todo, incluido el merge, está en
> [`PLAN_CIERRE.md`](PLAN_CIERRE.md).** Esta tabla es el registro de pendientes.

Prioridad: 🔴 alta · 🟠 media · 🟢 baja. Esfuerzo: S ≤1d · M 2–4d · L 1–2sem.

---

## A. Cerrar la adopción (camino crítico)

| # | Pendiente | Prio | Esf. |
|---|---|:--:|:--:|
| A1 | ✅ **Versionar y publicar `extractor-pa`**: repo privado `extractor-pa-maestro` en GitHub, tags `v0.9.x` (último `v0.9.12`), wheel construible. | — | — |
| A2 | ✅ **Fijar la dependencia** en cada app migrada (`requirements.txt` → `extractor-pa @ git+…@v0.9.11`). Subir a `@v0.9.12` es opcional (B3 es aditivo). | — | — |
| A3 | **CI** del maestro: el workflow `.github/workflows/ci.yml` existe; **confirmar que corre verde** en GitHub Actions. | 🟠 | S |
| A8 | ✅ **Merge de las 8 ramas → `main`** hecho y pusheado (`--no-ff`; validador: su `main` era un stub V1 de historia no relacionada → se promovió la rama de migración a `main` conservando LICENSE, con respaldo en tag `pre-maestro-main`). Falta **Fase 3** (ventana de validación en producción) y **Fase 4** (retirar legados). | 🟠 | S |
| A4 | ✅ **`creador-planes-accion`** migrado (adaptador `import_excel_maestro.py`, reconstruye la jerarquía ORM) — **roundtrip 20/20**, activado. | — | — |
| A5 | ✅ **Etapa 04 de seguimiento de `sispp-gobierno`** migrada (v0.9.9 con `metas_acumuladas`); cuant byte-idéntico, 04→05 validadas. | — | — |
| A6 | **Retirar los extractores legados** tras un período de validación en producción (hoy quedan intactos como respaldo; cada migración es reversible con 1 línea). | 🟠 | S |
| A7 | **Correr la suite completa de cada app en su propio entorno** (aquí faltan deps: `bcrypt` en sispp-sdis, deps de creador). Confirmar verde con el adaptador. | 🟠 | S |

## B. Mejoras de funcionalidad del maestro

| # | Pendiente | Prio | Esf. |
|---|---|:--:|:--:|
| B1 | ✅ **Catálogos oficiales + V4 + normalización difusa** (v0.9.10): `CatalogoOficial` + regla V4 **opcional** (`catalogo_oficial=`) + `sugerencias_normalizacion`/`aplicar_normalizacion` (RapidFuzz, extra `[fuzzy]`). | — | — |
| B2 | ✅ **Objetivo como entidad** (v0.9.11): `Objetivo` en el modelo + `objetivo_sin_resultados` (ADVERTENCIA) + `jerarquia_ip` (ERROR, valida N.N.N ⊂ N.N). 74 planes reales: 0 espurios. | — | — |
| B3 | ✅ **Gobernanza de alertas** (v0.9.12): `gobernanza.py` con clave estable por hash (byte-idéntica a sispp-gobierno), estados nueva/en_gestion/resuelta/descartada, `reconciliar` con autocierre, store JSON atómico + auditoría JSONL. Falta el resto de F2 (reaplicar correcciones de catálogo) ligado a B1. | — | — |
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
A1/A2 (publicar + fijar dependencia) y B1/B2/B3 (catálogos/V4 + objetivo +
gobernanza) **ya están hechos**. El camino restante es de **adopción**, detallado
en [`PLAN_CIERRE.md`](PLAN_CIERRE.md): **A7** (validar cada app en su entorno) →
**A8** (merge de ramas) → ventana de validación → **A6** (retirar legados). En
paralelo, cierres opcionales: **F2** (decisiones), **C5** (reportes), **C/D**.

## Definición de "terminado"
- ✅ `extractor-pa` publicado, versionado y consumido por pin en las 8 apps.
- ⏳ Las 8 ramas de migración **mergeadas a `main`** (A8) con sus suites verdes
  en sus entornos (A7).
- ⏳ Legados **retirados** tras la ventana de validación (A6).
