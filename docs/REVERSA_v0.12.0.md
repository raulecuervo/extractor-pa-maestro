# Cómo volver atrás desde v0.12.0

La v0.12.0 cambia resultados de cálculo (correcciones A, B y C — ver el
`CHANGELOG.md`). Este documento explica cómo regresar al comportamiento
anterior, total o parcialmente, y qué se rompe en cada caso.

**Versión anterior estable:** `v0.11.1`

---

## Opción 1 — Volver toda la librería (lo más rápido)

No hay que tocar código: basta con que las aplicaciones vuelvan a apuntar al
tag anterior. En `requirements.txt` de cada consumidor:

```bash
pip install 'extractor-pa[xlsb] @ git+https://github.com/raulecuervo/extractor-pa-maestro.git@v0.11.1'
```

Consumidores conocidos que hay que revertir a la vez, para que no queden
calculando distinto entre sí:

- `alertas-seguimientos` — `requirements.txt`
- `sispp-gobierno`, `sispp-sdis` — revisar su pin antes de mover nada

Después de revertir, en `alertas-seguimientos` hay que **recargar los archivos**
o recalcular las métricas almacenadas: `seguimientos.pct_hasta_vig` y
`trayectoria_ideal` quedaron guardados con las fórmulas nuevas.

---

## Opción 2 — Revertir una sola corrección

Las tres son independientes en el código pero **no en el resultado**. Antes de
revertir una sola, leer esto:

| Se revierte | Qué pasa |
|---|---|
| Solo **C** | 135 indicadores aparecen sobre-ejecutados de forma espuria: con A aplicado, la meta se prorratea desde cero. **No hacer.** |
| Solo **A** | La meta del período vuelve a ser igual a la meta anual en semestrales y anuales, y el prorrateo de B nunca ocurre: B queda inerte. |
| Solo **B** | Válido. El cálculo de la aplicación sigue corregido; solo el validador de discrepancia vuelve a comparar contra la meta anual entera. Sube el ruido de `ADVERTENCIA_DISCREPANCIA_PCT` (de 3 a ~19 en Trabajo Decente 2026 S1). |

Es decir: **B se puede revertir sola; A y C solo juntas.**

### Ubicación exacta de cada corrección

| | Archivo | Función |
|---|---|---|
| **A** | `extractor_pa/seguimiento/metricas.py` | `calc_mes` |
| **B** | `extractor_pa/seguimiento/validacion_seg.py` | `_validar_discrepancia_pct` (+ el import de `calc_mes`, `calc_meta_periodo`, `lb_de_indicador`) |
| **C** | `extractor_pa/seguimiento/metricas.py` | `metricas_corte`, bloque `if t != "SUMA" and meta_prev in (None, 0)` |

### Código original

**A — `calc_mes` antes:**

```python
def calc_mes(trimestre: int, periodicidad: Any) -> int:
    """Trimestre → mes de corte según periodicidad (§10.1; = JS getMes)."""
    p = (str(periodicidad) if periodicidad is not None else "").lower()
    if "anual" in p:
        return 12
    if "semest" in p:
        return min(trimestre * 6, 12)
    return min(trimestre * 3, 12)   # trimestral (default)
```

**C — en `metricas_corte`, eliminar este bloque** (el de arriba,
`meta_prev = next(...)` con `if meta_anual is None`, se conserva):

```python
    if t != "SUMA" and meta_prev in (None, 0):
        meta_prev = next(
            (s["meta_anual"] for s in reversed(segs_todos)
             if s["anio"] < anio and s.get("meta_anual") not in (None, 0)), None)
        if meta_prev is None:
            meta_prev = meta_anual if t == "CONSTANTE" else lb
```

**B — `_validar_discrepancia_pct` antes:**

```python
def _validar_discrepancia_pct(ind, politica, archivo):
    out = []
    year, _ = parse_period(ind.corte, ind.anio_reporte)
    if year is None:
        return out

    acum_rep = safe_float(ind.acumulados.get(str(year)))
    meta_anual = safe_float(ind.metas.get(str(year)))
    pct_rep = safe_float(ind.pct_vigencia.get(str(year)))

    if acum_rep is None or meta_anual is None or meta_anual == 0 or pct_rep is None:
        return out

    pct_calc = acum_rep / meta_anual
    if round(pct_rep, 3) != round(pct_calc, 3):
        out.append(_finding("ADVERTENCIA_DISCREPANCIA_PCT", ind, politica, archivo,
                            campo=f"% Avance Vigencia {year}",
                            val_base=f"Calculado={round(pct_calc, 3):.3f} (acum={acum_rep}/meta={meta_anual})",
                            val_nuevo=f"Reportado={round(pct_rep, 3):.3f}",
                            periodo=str(year),
                            detalle=(f"El % avance reportado en el archivo ({round(pct_rep, 3):.3f}) "
                                     f"difiere del calculado acumulado/meta ({round(pct_calc, 3):.3f}) "
                                     f"para la vigencia {year}")))
    return out
```

Al revertir B, el import vuelve a `from .metricas import safe_float`.

### Tests que hay que devolver

`tests/test_seguimiento_capa2.py`:

| Test | Valor con v0.12.0 | Valor al revertir |
|---|---|---|
| `test_metricas_corte_creciente_con_lb` | `ma == 75`, `phv == 1.5` | `ma == 50`, `phv is None` |
| `test_discrepancia_pct` | `Calculado=1.000 (suma de reportes=50/meta del periodo=50)` | `Calculado=0.500` |
| `test_calc_mes_lo_define_el_corte` + `test_periodicidad_no_altera_el_mes` | — | volver a `test_calc_mes_por_periodicidad` |
| `test_discrepancia_pct_no_usa_notacion_cientifica` | — | borrar si se revierte el `:g` |

---

## Opción 3 — Revertir solo en `alertas-seguimientos`, sin tocar la librería

Existió un mecanismo para esto: `services/formulas_correcciones.py`, que
parcheaba la librería en caliente desde `db.py`. Se retiró al publicar la
v0.12.0 porque ya no hacía falta. Si en algún momento se necesita el camino
inverso —la librería corregida pero una aplicación con el cálculo viejo— ese
archivo está en el historial de `alertas-seguimientos`:

```bash
git log --all --oneline -- services/formulas_correcciones.py
```

No es el camino recomendado: reintroduce la divergencia entre la aplicación y
SISPP, que es justamente lo que la v0.12.0 vino a cerrar.

---

## Cómo verificar que la reversa quedó bien

```bash
python -m pytest tests/ -q
```

Los dos fallos de `tests/test_catalogo_oficial.py` (`test_sugerencia_fuzzy` y
`test_normalizacion_aplica`) son **anteriores** a la v0.12.0 y no indican un
problema con la reversa.

Casos de control para comparar a mano:

| Indicador | Tipo | v0.11.1 | v0.12.0 |
|---|---|---|---|
| `Cultura Ciudadana 2.1.1` | CRECIENTE | `meta_prev = None` | `meta_prev = 1.0`, PHV 100 % |
| `Trabajo Decente 4.1.4` | CONSTANTE | MP interpola desde LB=12 | MP = 2.0 (su propia meta) |
| `Trabajo Decente 1.1.2` | SUMA | MP = 33.075, PHV 129,36 % | MP = 16.537,5, PHV 155,13 % |
