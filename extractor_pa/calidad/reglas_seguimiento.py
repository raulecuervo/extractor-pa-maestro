# -*- coding: utf-8 -*-
"""
Reglas nuevas del seguimiento (0.29.0, ADR-001), sobre ``IndicadorSeguimiento``.

Las reglas históricas de la app siguen en ``seguimiento/validacion_seg.py``;
aquí van las que llegan del pipeline de sispp-gobierno (``observaciones.py``,
``calidad.py``), del formato 3.4 y de ``ml_comentarios``:

- ``SEG_REPORTE_NEGATIVO``: un reporte menor que 0, en toda la serie hasta el corte.
- ``SEG_NO_VIGENTE_CON_PESO``: No Vigente con ponderación > 0 (única alerta que
  se conserva para los No Vigentes).
- ``SERIE_RETROCESO``: CRECIENTE cuyos reportes bajan / DECRECIENTE cuyos suben.
- ``SERIE_REPORTE_SIN_META``: reportes en años cerrados sin meta programada.
- ``SERIE_ESCALA`` / ``SERIE_SOBREEJECUCION``: en años cerrados, avance por
  encima de 250 % de la meta (o meta 0–1 con reporte > 1) / entre el techo
  del semáforo y 250 %.
- ``META_ANTES_INICIO``: metas del formato anteriores a la fecha de inicio
  (solo cuando no hay plan; con plan corre la misma regla sobre el plan).

Todas devuelven ``list[Hallazgo]`` y reciben ``(ind, politica, archivo, parametros)``.
"""

from __future__ import annotations

import re

from ..seguimiento.hallazgos import crear_hallazgo
from ..seguimiento.metricas import hay_meta, metas_antes_de_inicio, safe_float
from ..seguimiento.validacion_seg import parse_period
from .catalogo import APLICA_SEGUIMIENTO, APLICA_SERIE
from .hallazgo import FUENTE_SEGUIMIENTO, desde_hallazgo_seguimiento

_RE_CLAVE = re.compile(r"^(\d{4})_Q(\d)$")


def _h(tipo, ind, politica, archivo, aplica_a, **kw):
    h = crear_hallazgo(tipo, codigo=ind.codigo, politica=politica, sector=ind.sector,
                       entidad=ind.entidad, nombre=ind.nombre, archivo=archivo, **kw)
    return desde_hallazgo_seguimiento(h, aplica_a=aplica_a, fuente=FUENTE_SEGUIMIENTO)


def _corte(ind, parametros):
    if parametros.corte:
        return int(parametros.corte[0]), int(parametros.corte[1])
    return parse_period(ind.corte, ind.anio_reporte)


def _serie_hasta(ind, year, q):
    """``[((año, trimestre), valor)]`` de los reportes numéricos hasta el corte, en orden."""
    out = []
    for clave, v in (ind.avances or {}).items():
        m = _RE_CLAVE.match(str(clave))
        f = safe_float(v)
        if not m or f is None:
            continue
        yq = (int(m.group(1)), int(m.group(2)))
        if year is None or yq <= (year, q or 4):
            out.append((yq, f))
    return sorted(out)


def _es_no_vigente(ind) -> bool:
    return str(ind.estado or "").strip().lower().startswith("no")


def _etq(yq) -> str:
    return f"{yq[0]} Q{yq[1]}"


# ─────────────────────────── reglas ───────────────────────────

def reporte_negativo(ind, politica, archivo, parametros):
    year, q = _corte(ind, parametros)
    neg = [(yq, v) for yq, v in _serie_hasta(ind, year, q) if v < 0]
    if not neg:
        return []
    cortes = tuple(_etq(yq) for yq, _ in neg)
    h = _h("SEG_REPORTE_NEGATIVO", ind, politica, archivo, APLICA_SEGUIMIENTO,
           campo="Avances", val_nuevo="; ".join(f"{_etq(yq)}={v:g}" for yq, v in neg),
           periodo=cortes[-1],
           detalle=f"Reporte negativo en {', '.join(cortes)}: un avance no puede ser menor que 0.")
    h.cortes = cortes
    return [h]


def no_vigente_con_peso(ind, politica, archivo, parametros):
    if not _es_no_vigente(ind):
        return []
    peso = safe_float(ind.ponderacion)
    if peso is None or peso <= 0:
        return []
    return [_h("SEG_NO_VIGENTE_CON_PESO", ind, politica, archivo, APLICA_SEGUIMIENTO,
               campo="Ponderación (%)", val_nuevo=f"{peso:g}",
               detalle=(f"El formato marca el indicador como '{ind.estado}' pero le deja "
                        f"ponderación {peso:g}; ese peso no lo puede cumplir nadie."))]


def retroceso(ind, politica, archivo, parametros):
    tipo = (ind.tipo_anualizacion or "").strip().lower()
    if tipo not in ("creciente", "decreciente"):
        return []
    year, q = _corte(ind, parametros)
    serie = _serie_hasta(ind, year, q)
    quiebres = [(a, b) for a, b in zip(serie, serie[1:])
                if (b[1] < a[1] if tipo == "creciente" else b[1] > a[1])]
    if not quiebres:
        return []
    cortes = tuple(_etq(b[0]) for _, b in quiebres)
    verbo = "baja" if tipo == "creciente" else "sube"
    h = _h("SERIE_RETROCESO", ind, politica, archivo, APLICA_SERIE,
           campo="Avances", periodo=cortes[-1],
           val_nuevo="; ".join(f"{_etq(a[0])}={a[1]:g} → {_etq(b[0])}={b[1]:g}" for a, b in quiebres),
           detalle=(f"Indicador {ind.tipo_anualizacion} cuyo reporte {verbo} en "
                    f"{', '.join(cortes)}. Puede ser un retroceso real o un reporte de "
                    f"otra naturaleza (parcial en vez de acumulado)."))
    h.cortes = cortes
    return [h]


def reporte_sin_meta_serie(ind, politica, archivo, parametros):
    year, q = _corte(ind, parametros)
    if year is None:
        return []
    anios = sorted({yq[0] for yq, _ in _serie_hasta(ind, year, q) if yq[0] < year})
    sin_meta = [a for a in anios
                if not hay_meta((ind.metas or {}).get(str(a)), ind.tipo_anualizacion, ind.meta_final)]
    if not sin_meta:
        return []
    h = _h("SERIE_REPORTE_SIN_META", ind, politica, archivo, APLICA_SERIE,
           campo="Metas", val_base="Meta=0 o no existe",
           val_nuevo="; ".join(f"{a}: reportes {[v for yq, v in _serie_hasta(ind, year, q) if yq[0] == a]}"
                               for a in sin_meta)[:200],
           periodo=str(sin_meta[-1]),
           detalle=(f"Hay reportes en {', '.join(str(a) for a in sin_meta)} pero esos años no "
                    f"tienen meta programada (0 o vacía)."))
    h.cortes = tuple(str(a) for a in sin_meta)
    return [h]


def escala_serie(ind, politica, archivo, parametros):
    """Años cerrados (anteriores al del corte) con avance muy por encima de la meta."""
    year, q = _corte(ind, parametros)
    if year is None:
        return []
    tipo = (ind.tipo_anualizacion or "").strip().lower()
    techo, umbral_escala = parametros.umbral_sobreejecucion, parametros.umbral_escala
    serie = _serie_hasta(ind, year, q)
    out = []
    for a in sorted({yq[0] for yq, _ in serie if yq[0] < year}):
        meta = safe_float((ind.metas or {}).get(str(a)))
        if not hay_meta(meta, ind.tipo_anualizacion, ind.meta_final) or meta <= 0:
            continue
        reps = [v for yq, v in serie if yq[0] == a]
        valor = sum(reps) if tipo == "suma" else reps[-1]
        ratio = valor / meta
        if 0 <= meta <= 1 and any(v > 1 for v in reps):
            tipo_h, detalle = "SERIE_ESCALA", (
                f"En {a} la meta está en escala 0–1 ({meta:g}) y el reporte supera 1 "
                f"({valor:g}): posible confusión entre proporción y porcentaje.")
        elif ratio > umbral_escala:
            tipo_h, detalle = "SERIE_ESCALA", (
                f"En {a} el avance ({valor:g}) es {ratio:.0%} de la meta ({meta:g}), más de "
                f"{umbral_escala:.0%}: posible error de escala o de digitación.")
        elif ratio > techo:
            tipo_h, detalle = "SERIE_SOBREEJECUCION", (
                f"En {a} el avance ({valor:g}) es {ratio:.0%} de la meta ({meta:g}), sobre el "
                f"techo del semáforo ({techo:.0%}).")
        else:
            continue
        h = _h(tipo_h, ind, politica, archivo, APLICA_SERIE, campo=f"Avances {a}",
               val_base=f"Meta={meta:g}", val_nuevo=f"Avance={valor:g} ({ratio:.0%})",
               periodo=str(a), detalle=detalle)
        h.cortes = (str(a),)
        out.append(h)
    return out


def meta_antes_inicio_seguimiento(ind, politica, archivo, parametros):
    anios = metas_antes_de_inicio(ind.metas, ind.fecha_inicio)
    if not anios:
        return []
    lista = ", ".join(str(a) for a in anios)
    h = _h("META_ANTES_INICIO", ind, politica, archivo, APLICA_SEGUIMIENTO,
           campo="Metas", val_base=f"Fecha de inicio={ind.fecha_inicio}",
           val_nuevo="; ".join(f"{a}: {safe_float(ind.metas.get(str(a))):g}" for a in anios),
           periodo=lista,
           detalle=(f"Meta programada antes de la fecha de inicio ({ind.fecha_inicio}) en "
                    f"{lista}: probable error del plan de acción. Esa meta cuenta en la meta "
                    f"acumulada y la trayectoria ideal."))
    h.afecta_avance = "Sí: la meta cuenta en la meta acumulada y la trayectoria ideal"
    return [h]


# Orden de evaluación por indicador. ``META_ANTES_INICIO`` solo sin plan.
REGLAS_SEGUIMIENTO = [reporte_negativo, no_vigente_con_peso, retroceso,
                      reporte_sin_meta_serie, escala_serie]


def hallazgos_nuevos(seguimiento, parametros, *, con_plan: bool = False) -> list:
    politica = seguimiento.metadatos.nombre_politica or ""
    archivo = seguimiento.metadatos.archivo_fuente
    out = []
    for ind in seguimiento.indicadores:
        for fn in REGLAS_SEGUIMIENTO:
            out.extend(fn(ind, politica, archivo, parametros))
        if not con_plan:
            out.extend(meta_antes_inicio_seguimiento(ind, politica, archivo, parametros))
    return out
