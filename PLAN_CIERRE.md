# Plan de cierre — adopción del maestro `extractor_pa` (incluye merge)

Runbook **secuenciado** para llevar la migración de las 8 apps de rama a
producción y retirar los legados. La librería ya está completa y publicada
(v0.9.12); esto es **adopción**, no desarrollo. Cada paso es reversible.

Estado de partida (verificado):

| App | Rama | commits a `main` | archivos | Riesgo merge | Notas |
|---|---|:--:|:--:|:--:|---|
| creador-planes-accion | migracion-extractor-pa | 2 | 6 | 🟢 | roundtrip ORM 20/20 |
| generador-seguimiento | migracion-extractor-pa | 3 | 5 | 🟢 | `.xlsb`, paridad 6/6 |
| alertas-seguimientos | migracion-extractor-pa | 3 | 5 | 🟢 | `.xlsb` |
| seguimiento-pp-sdis | migracion-extractor-pa | 3 | 5 | 🟢 | maestro corrige 0-metas del legado |
| sispp-sdis | migracion-extractor-pa | 3 | 5 | 🟠 | suite necesita `bcrypt` en el entorno |
| extractor-planes-accion | migracion-extractor-pa | 3 | 8 | 🟠 | incluye fix detector H0 |
| validador-plan-accion | migracion-extractor-pa | 5 | 36 | 🔴 | 36 archivos (golden); revisar a fondo |
| sispp-gobierno | migracion-extractor-pa | 4 | 8 | 🔴 | aguas abajo (pipeline 01/04 + seg 04) |

Convención de esfuerzo: S ≤1d · M 2–4d.

---

## Fase 0 — Preparación (S)

1. **Confirmar CI verde del maestro** (A3): revisar GitHub Actions del repo
   `extractor-pa-maestro`; si `ci.yml` no está corriendo, habilitar Actions.
2. **Decidir el pin de merge**: las apps están en `@v0.9.11`. B3 (v0.9.12) es
   aditivo/opt-in → **no es obligatorio** subir. Opción recomendada: mergear con
   `@v0.9.11` (lo ya validado) y subir a `@v0.9.12` en un PR aparte si se quiere
   gobernanza en alguna app.
3. **Etiqueta de respaldo**: en cada app, tag del `main` actual antes de mergear
   (`git tag pre-maestro-main`), por si hay que volver.

## Fase 1 — Validar cada app en su entorno (A7) · gate previo al merge (M)

Por **cada** app, en su entorno real (no el editable del maestro):
```bash
python -m venv .venv && source .venv/Scripts/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt          # instala extractor-pa por el pin
pip install -r requirements-dev.txt 2>/dev/null || true  # deps de prueba si existen
python -m pytest -q                       # suite de la app
python comparar_*.py                      # gate de paridad legado-vs-maestro
```
- **sispp-sdis**: instalar `bcrypt` (falta en el entorno) antes de la suite.
- **creador-planes-accion**: confirmar deps del ORM; correr el roundtrip.
- Registrar el resultado (verde / hallazgos) en el `MIGRACION_*.md` de la app.
- **Criterio de avance**: suite verde **y** gate de paridad sin regresiones
  (las diferencias legado-vs-maestro deben ser solo las mejoras ya documentadas).

> **Estado: Fase 0, 1 y 2 COMPLETADAS** (8/8 apps mergeadas a `main` y pusheadas,
> cada una validada por su gate de paridad/bitácora). Pendiente: Fase 3 (ventana
> de validación en producción) y Fase 4 (retirar legados). validador requirió
> promover la rama de migración a `main` (su `main` era un stub V1 de historia no
> relacionada); LICENSE conservada, respaldo en tag `pre-maestro-main`.

## Fase 2 — Merge de las ramas → `main` (A8) · EL MERGE (S–M) ✅

Orden **de menor a mayor riesgo** (ver tabla). No mergear validador ni
sispp-gobierno hasta que las 🟢/🟠 estén verdes en `main`.

Por cada app (ejemplo con merge directo `--no-ff`, preserva la migración como
unidad revisable y revertible):
```bash
cd <app>
git checkout main && git pull
git merge --no-ff migracion-extractor-pa -m "Adoptar extractor_pa maestro (migración)"
python -m pytest -q          # re-confirmar verde en main
git push origin main
```
Alternativa por **Pull Request** (recomendada si hay revisor): abrir PR
`migracion-extractor-pa → main` en GitHub, adjuntar el `MIGRACION_*.md` y el
output del gate, revisar el diff (sobre todo validador, 36 archivos) y mergear.

**Checklist por merge**
- [ ] Suite de la app verde en `main` tras el merge.
- [ ] Pin correcto en `requirements.txt` (`@v0.9.11` o `@v0.9.12`).
- [ ] `MIGRACION_*.md` incluido en el merge.
- [ ] El extractor **legado sigue presente** (no se borra aún — Fase 4).

**Reversibilidad**: el switch de activación es 1 línea de import; además
`git revert -m 1 <merge_commit>` deshace el merge completo.

## Fase 3 — Ventana de validación en producción (S, + tiempo de observación)

- Correr el pipeline real de cada app con el maestro durante un periodo
  acordado (p. ej. 1–2 corridas/cierres).
- En las apps con gate, ejecutar `comparar_*.py` sobre los datos de producción y
  archivar el reporte. Confirmar 0 regresiones.
- Para sispp-gobierno: validar 01→04→05 aguas abajo (ya hecho una vez; repetir
  sobre datos nuevos).

## Fase 4 — Retirar los extractores legados (A6) (S)

Tras la ventana, por cada app:
1. Eliminar el módulo extractor legado y el switch de import (dejar solo el
   adaptador `*_maestro.py` como única ruta).
2. Quitar del `MIGRACION_*.md` la nota de "reversible con 1 línea".
3. Suite verde + commit `Retirar extractor legado (maestro es la única ruta)`.

## Fase 5 — Cierres de funcionalidad opcionales (paralelizable)

| # | Tarea | Esf. | Nota |
|---|---|:--:|---|
| F2 | **Store de decisiones de entidad aprobadas** + reaplicar (completa B1/B3) | S | JSON estilo `decisiones.py`; reusar `aplicar_normalizacion`. |
| C5 | **Reportes accionables**: hoja de vida del indicador, brechas/avance agregado | M | Heredables de generador-seguimiento/alertas-seguimientos. |
| C1 | Metas/meta_final desde la fila vigente promovida | S | Cerrar con verdad de campo. |
| C2 | Seguimiento: fallback de layout fijo + unificar escala | S | |
| C3 | Más golden por variante + unit tests por etapa | S | |
| C4 | Tablero: aliases extra + export a Excel navegable | S | |
| D | Housekeeping: flag no-interactivo etapa 03 sispp-gobierno; limpiar seguimientos duplicados; doc de instalación por app | S | |
| B4/B5 | Alertas operativas/cualitativas; adaptador ORM | L | **Discutible**: pertenecen a la app de operación, no al extractor. |

## Definición de "terminado"
- ✅ Librería publicada y versionada; 8 apps pinadas.
- ⏳ 8 ramas mergeadas a `main` (Fase 2) con suites verdes en su entorno (Fase 1).
- ⏳ Ventana de validación superada (Fase 3) y legados retirados (Fase 4).
- (Opcional) F2 + C5 cerrados; C/D según prioridad.

## Secuencia y orden de ataque
```
Fase 0 (prep)
  └─ Fase 1 (validar en entorno, A7) ─┐
                                      ├─ Fase 2 (merge, A8: 🟢→🟠→🔴)
                                      │    └─ Fase 3 (ventana) ── Fase 4 (retirar legados, A6)
  Fase 5 (F2, C5, C/D) ── en paralelo, no bloquea la adopción
```
