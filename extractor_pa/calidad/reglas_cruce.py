# -*- coding: utf-8 -*-
"""
Reglas de cruce plan ↔ seguimiento (0.29.0, ADR-001).

- ``CRUCE_IND_NO_EN_PLAN``: indicador vigente del seguimiento cuyo código no está
  en el plan (los No Vigentes no se alertan: un indicador retirado en el plan
  2026 sí estaba vigente cuando reportó en 2025).
- ``CRUCE_IND_NO_EN_SEGUIMIENTO``: indicador vigente del plan, con peso y ya
  iniciado al corte, que no aparece en el seguimiento.
- ``CRUCE_PERIODICIDAD_DISTINTA``: la periodicidad del plan no es la del formato.

También entrega :func:`periodicidad_del_plan`, el mapa que usa
``SEG_META_SIN_REPORTE`` cuando manda la periodicidad del plan.
"""

from __future__ import annotations

from ..seguimiento.hallazgos import crear_hallazgo
from ..seguimiento.metricas import periodo_de_fecha, safe_float
from ..seguimiento.validacion_seg import normalise, parse_period
from ..validacion import _es_no_vigente as _plan_no_vigente
from ..validacion import _leer_peso
from .catalogo import APLICA_CRUCE
from .hallazgo import FUENTE_CRUCE, Hallazgo, desde_hallazgo_seguimiento


def _indice_plan(plan) -> dict:
    """{codigo: indicador del plan} (IR por N.N, IP por N.N.N)."""
    idx = {}
    for ir in plan.indicadores_resultado:
        if ir.codigo_ir:
            idx[str(ir.codigo_ir)] = ir
    for ip in plan.indicadores_producto:
        if ip.codigo_ip:
            idx[str(ip.codigo_ip)] = ip
    return idx


def periodicidad_del_plan(plan) -> dict:
    """{codigo: periodicidad del plan} para los indicadores con periodicidad."""
    return {cod: ind.periodicidad for cod, ind in _indice_plan(plan).items()
            if normalise(ind.periodicidad)}


def _corte_de(seguimiento, parametros):
    if parametros.corte:
        return int(parametros.corte[0]), int(parametros.corte[1])
    m = seguimiento.metadatos
    for ind in seguimiento.indicadores:
        y, q = parse_period(ind.corte, ind.anio_reporte)
        if y is not None:
            return y, q or 4
    return (m.anio_reporte, 4) if m.anio_reporte else (None, None)


def _h_seg(tipo, ind, politica, archivo, **kw) -> Hallazgo:
    h = crear_hallazgo(tipo, codigo=ind.codigo, politica=politica, sector=ind.sector,
                       entidad=ind.entidad, nombre=ind.nombre, archivo=archivo, **kw)
    return desde_hallazgo_seguimiento(h, aplica_a=APLICA_CRUCE, fuente=FUENTE_CRUCE)


def hallazgos_cruce(plan, seguimiento, parametros) -> list:
    politica = seguimiento.metadatos.nombre_politica or plan.metadatos.nombre_politica or ""
    archivo = seguimiento.metadatos.archivo_fuente
    idx = _indice_plan(plan)
    en_seg = {}
    out = []

    # Seguimiento → plan.
    for ind in seguimiento.indicadores:
        cod = str(ind.codigo or "")
        if not cod:
            continue
        en_seg[cod] = ind
        vigente = not str(ind.estado or "").strip().lower().startswith("no")
        pl = idx.get(cod)
        if pl is None:
            if vigente:
                out.append(_h_seg("CRUCE_IND_NO_EN_PLAN", ind, politica, archivo,
                                  campo="Código", val_nuevo=cod,
                                  detalle=(f"El seguimiento reporta el indicador '{cod}' "
                                           f"({ind.estado or 'sin estado'}) pero el plan de "
                                           f"acción '{plan.metadatos.archivo_fuente}' no lo "
                                           f"contiene: su avance no se calcula contra el plan.")))
            continue
        p_plan, p_seg = normalise(pl.periodicidad), normalise(ind.periodicidad)
        if p_plan and p_seg and p_plan.lower() != p_seg.lower():
            out.append(_h_seg("CRUCE_PERIODICIDAD_DISTINTA", ind, politica, archivo,
                              campo="Periodicidad", val_base=f"Plan={p_plan}",
                              val_nuevo=f"Seguimiento={p_seg}",
                              detalle=(f"La periodicidad del plan ('{p_plan}') no coincide con la "
                                       f"del formato ('{p_seg}'); la exigencia de reporte usa la "
                                       f"del plan.")))

    # Plan → seguimiento.
    year, q = _corte_de(seguimiento, parametros)
    for cod, pl in idx.items():
        if cod in en_seg or _plan_no_vigente(pl):
            continue
        peso = _leer_peso(pl.peso_pct)[0]
        if peso is None or peso <= 0:
            continue
        ini = periodo_de_fecha(pl.fecha_inicio)
        if year is not None and ini is not None and ini > (year, q or 4):
            continue
        h = crear_hallazgo(
            "CRUCE_IND_NO_EN_SEGUIMIENTO", codigo=cod, politica=politica,
            sector=pl.sector_responsable, entidad=pl.entidad_responsable,
            nombre=pl.nombre_indicador, archivo=archivo, campo="Código", val_base=cod,
            detalle=(f"El indicador '{cod}' del plan (vigente, peso {safe_float(peso):g}, "
                     f"inicio {pl.fecha_inicio}) no aparece en el formato de seguimiento con "
                     f"ese código: ¿se renumeró o no se reporta?"))
        hh = desde_hallazgo_seguimiento(h, aplica_a=APLICA_CRUCE, fuente=FUENTE_CRUCE)
        hh.cod_ir = getattr(pl, "codigo_ir", "") or ""
        hh.cod_ip = getattr(pl, "codigo_ip", "") or ""
        out.append(hh)
    return out
