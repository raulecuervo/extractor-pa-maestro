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

from dataclasses import replace
from typing import Iterable, Optional

from ..seguimiento.validacion_seg import validar_archivo, validar_consistencia
from ..validacion import validar_reglas
from .catalogo import (
    APLICA_CRUCE, APLICA_ENTRE_CARGAS, APLICA_ESTRUCTURA_PLAN, APLICA_ESTRUCTURA_SEG,
    APLICA_PLAN, APLICA_SEGUIMIENTO, APLICA_SERIE, CATALOGO_CALIDAD,
)
from .hallazgo import FUENTE_PLAN, FUENTE_SEGUIMIENTO, Hallazgo, desde_alerta, desde_hallazgo_seguimiento
from .parametros import PARAMETROS_POR_DEFECTO, ParametrosCalidad
from .reglas_cruce import hallazgos_cruce as _cruce
from .reglas_cruce import periodicidad_del_plan
from .reglas_seguimiento import hallazgos_nuevos as _seg_nuevas

_APLICA_ESTRUCTURA = (APLICA_ESTRUCTURA_PLAN, APLICA_ESTRUCTURA_SEG)
# Reglas que sí se conservan para los No Vigentes con ``incluir_no_vigentes=False``.
_REGLAS_NO_VIGENTE = frozenset({"SEG_NO_VIGENTE_CON_PESO", "PLAN_NO_VIGENTE_CON_PESO",
                                "CARGA_CAMBIO_ESTADO"})


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


def _al_corte(seguimiento, corte):
    """Copia del resultado con los indicadores situados en ``corte`` (año, trimestre):
    las reglas del año del corte leen ``ind.corte`` / ``ind.anio_reporte``."""
    if not corte:
        return seguimiento
    y, q = int(corte[0]), int(corte[1])
    inds = [replace(i, corte=f"Q{q}", anio_reporte=y) for i in seguimiento.indicadores]
    return replace(seguimiento, indicadores=inds)


def hallazgos_seguimiento(seguimiento, base=None,
                          parametros: ParametrosCalidad = PARAMETROS_POR_DEFECTO,
                          plan=None) -> list:
    """Hallazgos del seguimiento: estructurales + ``validar_archivo`` (o
    ``validar_consistencia`` si hay ``base``) + las reglas nuevas (serie, reporte
    negativo, No Vigente con peso, meta antes del inicio sin plan). Con ``plan``
    y ``periodicidad_de="plan"`` la exigencia de reporte usa la periodicidad del
    plan; con ``parametros.corte`` se evalúa en ese corte."""
    out = []
    if parametros.incluir_estructurales:
        out.extend(desde_alerta(a, aplica_a=APLICA_ESTRUCTURA_SEG, fuente=FUENTE_SEGUIMIENTO)
                   for a in getattr(seguimiento, "alertas", []) or [])
    seg = _al_corte(seguimiento, parametros.corte)
    per_plan = (periodicidad_del_plan(plan)
                if plan is not None and parametros.periodicidad_de == "plan" else None)
    kw = dict(anio_min=parametros.anio_min, entidad_sector=parametros.entidad_sector,
              umbrales=parametros.umbrales_semaforo, umbral_escala=parametros.umbral_escala,
              periodicidad_plan=per_plan)
    if base is not None:
        hs = validar_consistencia(base, seg, **kw)
    else:
        hs = validar_archivo(seg, **kw)
    out.extend(desde_hallazgo_seguimiento(h) for h in hs)
    out.extend(_seg_nuevas(seg, parametros, con_plan=plan is not None))
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
        if (not parametros.incluir_no_vigentes and h.regla not in _REGLAS_NO_VIGENTE
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
    estados = _estados(plan, seguimiento)
    if plan is not None:
        out.extend(hallazgos_plan(plan, p))
    if seguimiento is not None:
        out.extend(hallazgos_seguimiento(seguimiento, base, p, plan=plan))
    if plan is not None and seguimiento is not None:
        out.extend(hallazgos_cruce(plan, seguimiento, p))
    return filtrar(out, p, aplica_a=aplica_a, familias=familias, codigos=codigos, estados=estados)


def _estados(plan, seguimiento) -> dict:
    """{codigo: estado} para el filtro de No Vigentes: el del seguimiento manda;
    sin seguimiento, la vigencia del plan."""
    est = {}
    if plan is not None:
        for ind in list(plan.indicadores_resultado) + list(plan.indicadores_producto):
            cod = getattr(ind, "codigo_ip", None) or getattr(ind, "codigo_ir", None)
            if cod:
                est[cod] = ind.es_vigente
    if seguimiento is not None:
        est.update({i.codigo: i.estado for i in seguimiento.indicadores if i.codigo})
    return est


def hallazgos_cruce(plan, seguimiento, parametros: ParametrosCalidad = PARAMETROS_POR_DEFECTO) -> list:
    """Reglas de cruce plan ↔ seguimiento (ver ``reglas_cruce``)."""
    return _cruce(plan, seguimiento, parametros)


# ─────────────────────────── funciones de conveniencia ───────────────────────────

def alertas_plan(plan, parametros: Optional[ParametrosCalidad] = None) -> list:
    """Para el paso 01 del pipeline: ``list[Alerta]`` (esquema de
    ``alertas_planes_accion.csv``) con las estructurales y las reglas del plan."""
    return [h.a_alerta() for h in evaluar(plan=plan, parametros=parametros)]


def hallazgos_app(seguimiento, base=None, parametros: Optional[ParametrosCalidad] = None,
                  plan=None) -> list:
    """Para alertas-seguimientos: los dicts de ``as_finding()`` (tabla ``alertas``),
    con el seguimiento, la base y, si se pasa, el plan (reglas de cruce)."""
    return [h.as_finding() for h in evaluar(plan=plan, seguimiento=seguimiento, base=base,
                                            parametros=parametros)]


_REGLAS_AGRUPADAS = ("CRUCE_IND_NO_EN_PLAN", "CRUCE_IND_NO_EN_SEGUIMIENTO")


def observaciones_desde(plan=None, seguimiento=None, corte=None, *, politica_key: str = "",
                        parametros: Optional[ParametrosCalidad] = None,
                        responsable_por_defecto: str = "", agrupar_cruce: bool = True,
                        base=None) -> list:
    """Para el paso 06 del pipeline: filas de ``observaciones_politica``
    (``COLS_OBSERVACION``) de una política, a partir de su plan y su último
    formato de seguimiento al ``corte``. ``responsable_por_defecto`` (la entidad
    líder) se usa cuando el hallazgo no trae entidad. Con ``agrupar_cruce`` los
    indicadores que no cruzan se resumen en una fila por regla y política, como
    hoy en ``observaciones.obs_cruce_plan_seguimiento``."""
    p = parametros or PARAMETROS_POR_DEFECTO
    hs = evaluar(plan=plan, seguimiento=seguimiento, base=base, corte=corte, parametros=p)
    filas, grupos = [], {}
    for h in hs:
        if agrupar_cruce and h.regla in _REGLAS_AGRUPADAS:
            grupos.setdefault(h.regla, []).append(h)
            continue
        filas.append(h.a_observacion(politica_key=politica_key,
                                     responsable=h.entidad or responsable_por_defecto))
    for regla, lote in grupos.items():
        cods = [h.codigo for h in lote]
        fila = lote[0].a_observacion(politica_key=politica_key, responsable=responsable_por_defecto)
        fila.update(nivel="Política", indicador_key="", codigo="",
                    evidencia=f"{len(cods)} indicador(es): {', '.join(cods[:25])}"
                              f"{' …' if len(cods) > 25 else ''}.")
        filas.append(fila)
    return filas


__all__ = ["evaluar", "hallazgos_plan", "hallazgos_seguimiento", "hallazgos_cruce", "filtrar",
           "alertas_plan", "hallazgos_app", "observaciones_desde",
           "APLICA_PLAN", "APLICA_SEGUIMIENTO", "APLICA_SERIE", "APLICA_ENTRE_CARGAS", "APLICA_CRUCE"]
