# -*- coding: utf-8 -*-
"""
Motor de calidad: ``evaluar(plan=…, seguimiento=…, base=…)`` → ``list[Hallazgo]``.

Corre las reglas cuyos datos están disponibles: con solo el plan, las del
plan; con el seguimiento, las del archivo (y las de entre cargas si hay
``base``); con plan y seguimiento, también las de cruce. Ninguna regla
modifica los datos: solo los describe. Las fachadas históricas
(``validacion.validar_reglas``, ``seguimiento.validar_archivo`` /
``validar_consistencia``) siguen siendo las implementaciones de las reglas
V0–V18 y de las del seguimiento; el motor las envuelve y les suma las reglas
nuevas (desde la 0.29.0).
"""

from __future__ import annotations

from typing import Iterable, Optional

from ..seguimiento.validacion_seg import validar_archivo, validar_consistencia
from ..validacion import validar_reglas
from .catalogo import (
    APLICA_CRUCE, APLICA_ENTRE_CARGAS, APLICA_ESTRUCTURA_PLAN, APLICA_ESTRUCTURA_SEG,
    APLICA_PLAN, APLICA_SEGUIMIENTO, APLICA_SERIE, CATALOGO_CALIDAD,
)
from .hallazgo import FUENTE_PLAN, FUENTE_SEGUIMIENTO, Hallazgo, desde_alerta, desde_hallazgo_seguimiento
from .parametros import PARAMETROS_POR_DEFECTO, ParametrosCalidad

_APLICA_ESTRUCTURA = (APLICA_ESTRUCTURA_PLAN, APLICA_ESTRUCTURA_SEG)


def _indice_plan(plan) -> dict:
    """{codigo: (sector, entidad, nombre, tipo)} de los indicadores del plan."""
    idx = {}
    for ir in getattr(plan, "indicadores_resultado", []) or []:
        if ir.codigo_ir:
            idx[ir.codigo_ir] = (ir.sector_responsable or "", ir.entidad_responsable or "",
                                 ir.nombre_indicador or "", "resultado")
    for ip in getattr(plan, "indicadores_producto", []) or []:
        if ip.codigo_ip:
            idx[ip.codigo_ip] = (ip.sector_responsable or "", ip.entidad_responsable or "",
                                 ip.nombre_indicador or "", "producto")
    return idx


def _de_alerta_plan(alerta, idx: dict, aplica_a: str) -> Hallazgo:
    codigo = alerta.codigo_ip or alerta.codigo_ir or ""
    sector, entidad, nombre, _tipo = idx.get(codigo, ("", "", "", ""))
    return desde_alerta(alerta, aplica_a=aplica_a, sector=sector, entidad=entidad,
                        nombre=nombre, fuente=FUENTE_PLAN)


def hallazgos_plan(plan, parametros: ParametrosCalidad = PARAMETROS_POR_DEFECTO) -> list:
    """Hallazgos del plan: estructurales (``res.alertas``) + reglas V0–V18."""
    idx = _indice_plan(plan)
    out = []
    if parametros.incluir_estructurales:
        out.extend(_de_alerta_plan(a, idx, APLICA_ESTRUCTURA_PLAN)
                   for a in getattr(plan, "alertas", []) or [])
    alertas = validar_reglas(plan, catalogo_oficial=parametros.catalogo_oficial,
                             tolerancia_peso_pp=parametros.tolerancia_peso_pp,
                             tolerancia_meta_final=parametros.tolerancia_meta_final)
    out.extend(_de_alerta_plan(a, idx, APLICA_PLAN) for a in alertas)
    return out


def hallazgos_seguimiento(seguimiento, base=None,
                          parametros: ParametrosCalidad = PARAMETROS_POR_DEFECTO) -> list:
    """Hallazgos del seguimiento: estructurales + ``validar_archivo`` (o
    ``validar_consistencia`` si hay ``base``)."""
    out = []
    if parametros.incluir_estructurales:
        out.extend(desde_alerta(a, aplica_a=APLICA_ESTRUCTURA_SEG, fuente=FUENTE_SEGUIMIENTO)
                   for a in getattr(seguimiento, "alertas", []) or [])
    kw = dict(anio_min=parametros.anio_min, entidad_sector=parametros.entidad_sector,
              umbrales=parametros.umbrales_semaforo)
    if base is not None:
        hs = validar_consistencia(base, seguimiento, **kw)
    else:
        hs = validar_archivo(seguimiento, **kw)
    out.extend(desde_hallazgo_seguimiento(h) for h in hs)
    return out


def _es_no_vigente(h: Hallazgo, estados: dict) -> bool:
    est = str(estados.get(h.codigo) or "").strip().lower()
    return est.startswith("no")


def filtrar(hallazgos: Iterable[Hallazgo], parametros: ParametrosCalidad = PARAMETROS_POR_DEFECTO,
            *, aplica_a: Optional[Iterable[str]] = None, familias: Optional[Iterable[str]] = None,
            codigos: Optional[Iterable[str]] = None, estados: Optional[dict] = None) -> list:
    """Aplica los filtros de los parámetros (reglas activas, No Vigentes) y los
    del llamador (``aplica_a``, ``familias``, ``codigos`` de regla)."""
    aplica_a = set(aplica_a) if aplica_a else None
    familias = set(familias) if familias else None
    codigos = set(codigos) if codigos else None
    estados = estados or {}
    out = []
    for h in hallazgos:
        r = CATALOGO_CALIDAD.get(h.regla)
        if r is not None and not parametros.activa(r):
            continue
        if aplica_a is not None and h.aplica_a not in aplica_a:
            continue
        if familias is not None and (r is None or r.familia not in familias):
            continue
        if codigos is not None and h.regla not in codigos:
            continue
        if (not parametros.incluir_no_vigentes and h.regla != "SEG_NO_VIGENTE_CON_PESO"
                and h.aplica_a not in _APLICA_ESTRUCTURA and _es_no_vigente(h, estados)):
            continue
        out.append(h)
    return out


def evaluar(*, plan=None, seguimiento=None, base=None, corte=None,
            parametros: Optional[ParametrosCalidad] = None,
            aplica_a: Optional[Iterable[str]] = None, familias: Optional[Iterable[str]] = None,
            codigos: Optional[Iterable[str]] = None) -> list:
    """Evalúa las reglas de calidad sobre lo que se reciba.

    ``plan``: ``ResultadoExtraccion``; ``seguimiento`` / ``base``:
    ``ResultadoSeguimiento``; ``corte``: ``(año, trimestre)`` del análisis
    (``None``: el del archivo); ``parametros``: :class:`ParametrosCalidad`.
    ``aplica_a`` / ``familias`` / ``codigos`` acotan el resultado.
    Devuelve ``list[Hallazgo]`` en el orden de evaluación: estructura, plan,
    seguimiento, cruce."""
    p = parametros or PARAMETROS_POR_DEFECTO
    if corte is not None:
        p = p.con(corte=tuple(corte))
    out: list = []
    if plan is not None:
        out.extend(hallazgos_plan(plan, p))
    estados = {}
    if seguimiento is not None:
        out.extend(hallazgos_seguimiento(seguimiento, base, p))
        estados = {i.codigo: i.estado for i in seguimiento.indicadores if i.codigo}
    if plan is not None and seguimiento is not None:
        out.extend(hallazgos_cruce(plan, seguimiento, p))
    return filtrar(out, p, aplica_a=aplica_a, familias=familias, codigos=codigos, estados=estados)


def hallazgos_cruce(plan, seguimiento, parametros: ParametrosCalidad = PARAMETROS_POR_DEFECTO) -> list:
    """Reglas de cruce plan ↔ seguimiento (se incorporan en la 0.29.0)."""
    return []


__all__ = ["evaluar", "hallazgos_plan", "hallazgos_seguimiento", "hallazgos_cruce", "filtrar",
           "APLICA_PLAN", "APLICA_SEGUIMIENTO", "APLICA_SERIE", "APLICA_ENTRE_CARGAS", "APLICA_CRUCE"]
