# -*- coding: utf-8 -*-
"""
Métricas oficiales de seguimiento (capa 2 de la convergencia SISPP ↔ Alertas).

Port PURO (sin BD ni IO) de las fórmulas en producción de
``alertas-seguimientos/db.py`` — MP, MA, PHV, trayectoria, PAF, TID, brecha y
línea base ficticia para DECRECIENTES — alineadas con el CONTEXTO MAESTRO de
SISPP (§10) y con ``FORMULAS.md`` de Alertas-Seguimientos.

CONVENCIÓN DE ESCALA (regla de la librería):
    Todo porcentaje se calcula y retorna como **FRACCIÓN 0–1** (0.5 = 50 %),
    la misma escala del ``.xlsb`` y de la BD de Alertas-Seguimientos. Cada
    aplicación convierte en SU borde: SISPP multiplica ×100 (CONTEXTO §10.4);
    Alertas usa la fracción tal cual. La conversión explícita a 0–100 es
    ``validacion_seg.a_porcentaje``.

CONVENCIÓN DE TIPO:
    ``tipo`` es el tipo de anualización — 'SUMA' | 'CRECIENTE' | 'DECRECIENTE'
    | 'CONSTANTE'. Las funciones lo normalizan a MAYÚSCULAS internamente.

IMPORTANTE (paridad): ``safe_float`` replica la conversión ESTRICTA de
producción (``float()`` directo). NO sustituirlo por ``utilidades.a_float``
(tolerante con comas/%/$): cambiaría el resultado de las validaciones y
rompería el gate de paridad con Alertas-Seguimientos.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional


# ─────────────────────────── conversión numérica ───────────────────────────

def safe_float(val: Any) -> Optional[float]:
    """``float(val)`` o ``None``. Réplica exacta de ``extractor.safe_float``
    de Alertas-Seguimientos (estricta: '1,5' o '50%' NO son numéricos)."""
    try:
        return float(val)
    except Exception:
        return None


def parse_lb(val: Any) -> float:
    """Línea base (texto con coma decimal admitido) → float; 0.0 si no parsea.
    Réplica de ``db._parse_lb``."""
    try:
        return float(str(val or "").replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def anio_de_serial_excel(serial: Any) -> Optional[int]:
    """Año de una fecha serial de Excel (base 1899-12-30, bug de 1900 ya
    corregido). ``None`` si el valor no es una fecha válida."""
    try:
        s = float(serial)
        if s <= 0:
            return None
        return (datetime(1899, 12, 30) + timedelta(days=s)).year
    except Exception:
        return None


def _tipo(tipo: Any) -> str:
    return (str(tipo) if tipo is not None else "").upper().strip()


# ─────────────────────────── fórmulas §10.1–§10.4 ───────────────────────────

def calc_mes(trimestre: int, periodicidad: Any) -> int:
    """Trimestre → mes de corte según periodicidad (§10.1; = JS getMes)."""
    p = (str(periodicidad) if periodicidad is not None else "").lower()
    if "anual" in p:
        return 12
    if "semest" in p:
        return min(trimestre * 6, 12)
    return min(trimestre * 3, 12)   # trimestral (default)


def calc_meta_periodo(tipo, meta_anual, meta_prev, mes) -> Optional[float]:
    """Meta del período MP (§10.1; = JS getMetaPeriodo).
    SUMA:  MV × mes/12 · otros: (MV − MV_año_anterior) × mes/12 + MV_año_anterior."""
    if meta_anual is None:
        return None
    if _tipo(tipo) == "SUMA":
        return meta_anual * mes / 12
    prev = meta_prev or 0.0
    return (meta_anual - prev) * (mes / 12) + prev


def calc_meta_acum(tipo, mp, sum_metas_prev) -> Optional[float]:
    """Meta acumulada MA (§10.2; = JS getMetaAcum).
    SUMA: Σ metas de años anteriores + MP · otros: MP."""
    if mp is None:
        return None
    return (sum_metas_prev or 0.0) + mp if _tipo(tipo) == "SUMA" else mp


def calc_sum_metas_prev(metas: dict, hasta_anio: int, anio_min: int = 2018) -> float:
    """Σ de metas anuales de los años ANTERIORES a ``hasta_anio``.
    Réplica de ``db._calc_sum_metas_prev`` con ``anio_min`` parametrizado
    (Alertas usaba la constante ANOS=2018..2025)."""
    return sum(
        safe_float((metas or {}).get(str(y))) or 0.0
        for y in range(anio_min, hasta_anio)
    )


def calc_pct_hasta_vig(tipo, av_acum, ma, lb) -> Optional[float]:
    """PHV — % de avance hasta la vigencia, FRACCIÓN 0–1 (§10.4).
    CRECIENTE/DECRECIENTE: (AV − LB)/(MA − LB) · CONSTANTE/SUMA: AV/MA."""
    if av_acum is None or ma is None:
        return None
    if _tipo(tipo) in ("CRECIENTE", "DECRECIENTE"):
        den = ma - lb
        return None if den == 0 else (av_acum - lb) / den
    return None if ma == 0 else av_acum / ma


# ─────────────────────────── fórmulas §10.5 ───────────────────────────

def calc_trayectoria_ideal(tipo, mp, ma, meta_final, lb) -> Optional[float]:
    """Trayectoria ideal del período vs meta final (fracción 0–1).
    CRECIENTE/DECRECIENTE: (MP − LB)/(meta_final − LB) · CONSTANTE/SUMA: MA/meta_final."""
    if mp is None or meta_final is None:
        return None
    if _tipo(tipo) in ("CRECIENTE", "DECRECIENTE"):
        den = meta_final - lb
        return None if den == 0 else (mp - lb) / den
    eff_ma = ma if ma is not None else mp
    return None if meta_final == 0 else eff_ma / meta_final


def calc_paf(tipo, av_acum, meta_final, lb) -> Optional[float]:
    """PAF — % de avance acumulado vs meta final (§10.5, fracción 0–1).
    CRECIENTE/DECRECIENTE: (AV − LB)/(meta_final − LB) · CONSTANTE/SUMA: AV/meta_final."""
    if meta_final in (None, 0) or av_acum is None:
        return None
    if _tipo(tipo) in ("CRECIENTE", "DECRECIENTE"):
        den = meta_final - lb
        return None if den == 0 else (av_acum - lb) / den
    return av_acum / meta_final


def calc_tid(tipo, ma, meta_final, lb) -> Optional[float]:
    """TID — trayectoria ideal vs meta final (§10.5, fracción 0–1).
    CRECIENTE/DECRECIENTE: (MA − LB)/(meta_final − LB) · CONSTANTE/SUMA: MA/meta_final."""
    if meta_final in (None, 0) or ma is None:
        return None
    if _tipo(tipo) in ("CRECIENTE", "DECRECIENTE"):
        den = meta_final - lb
        return None if den == 0 else (ma - lb) / den
    return ma / meta_final


def calc_brecha(paf, tid) -> Optional[float]:
    """Brecha = PAF − TID (§10.5). Negativa = rezago; positiva = adelanto."""
    if paf is None or tid is None:
        return None
    return paf - tid


# ─────────────────────────── línea base (RN-CUA-009) ───────────────────────────

def calc_lb_ficticia_decreciente(metas: dict, meta_final=None,
                                 anio_fin: Optional[int] = None) -> Optional[float]:
    """LB ficticia para DECRECIENTES sin línea base (RN-CUA-009 de SISPP):
    ``(MetaInicial − MetaFinal) / (AñoFinal − AñoInicial + 1) + MetaInicial``.

    ``anio_fin`` permite fijar el año final de la vigencia (p. ej. derivado de
    ``fecha_fin`` con :func:`anio_de_serial_excel`); si no se pasa, se usa el
    último año con meta anual numérica."""
    if not isinstance(metas, dict):
        return None
    years = []
    for k, v in metas.items():
        if str(k).strip().lower() == "final":
            continue
        try:
            y = int(k)
        except (TypeError, ValueError):
            continue
        mv = safe_float(v)
        if mv is None:
            continue
        years.append((y, mv))
    if not years:
        return None
    years.sort(key=lambda t: t[0])
    anio_ini, meta_ini = years[0]
    ult_anio, meta_fin_anual = years[-1]
    fin = anio_fin if anio_fin is not None else ult_anio
    meta_fin = safe_float(meta_final)
    if meta_fin is None:
        meta_fin = meta_fin_anual
    den = fin - anio_ini + 1
    if den == 0:
        return None
    return (meta_ini - meta_fin) / den + meta_ini


def lb_de_indicador(linea_base, tipo, metas: Optional[dict] = None,
                    meta_final=None, anio_fin: Optional[int] = None) -> float:
    """Línea base numérica del indicador. Versión PURA de ``db._get_lb_for_ind``
    de Alertas (recibe las metas como dict en vez de consultar la BD).

    - LB explícita → :func:`parse_lb`.
    - DECRECIENTE sin LB → :func:`calc_lb_ficticia_decreciente` (RN-CUA-009).
    - Otros tipos sin LB → 0.0."""
    raw = str(linea_base or "").strip()
    if raw:
        return parse_lb(raw)
    if _tipo(tipo) != "DECRECIENTE":
        return 0.0
    fict = calc_lb_ficticia_decreciente(metas or {}, meta_final, anio_fin)
    return fict if fict is not None else 0.0


# ─────────────────────────── núcleo al corte ───────────────────────────

def _suma_metas_prev_suma(segs_al_corte, segs_todos, anio: int,
                          metas_plan: Optional[dict] = None) -> float:
    """SUMA: Σ meta_anual por año calendario < ``anio``. Por año se usa lo
    reportado en seguimiento si existe; si no, la meta del plan solo cuando
    ``max(año en seguimientos) > año``. Sin imputación sintética hacia atrás.
    Réplica de ``db._suma_metas_prev_suma_merged``."""
    por_anio = {}
    for s in segs_al_corte:
        if s["anio"] >= anio:
            continue
        mv_seg = safe_float(s.get("meta_anual"))
        if mv_seg is not None:
            por_anio[s["anio"]] = mv_seg

    plan = dict(metas_plan or {})
    if plan:
        max_seg_anio = max((s["anio"] for s in segs_todos), default=None)
        if max_seg_anio is not None:
            for key, raw in plan.items():
                if str(key).strip().lower() == "final":
                    continue
                try:
                    y = int(key)
                except (TypeError, ValueError):
                    continue
                if y >= anio or max_seg_anio <= y:
                    continue
                mv = safe_float(raw)
                if mv is None:
                    continue
                por_anio.setdefault(y, mv)

    total = 0.0
    for y, v in por_anio.items():
        if y >= anio:
            continue
        fv = safe_float(v)
        if fv is not None:
            total += fv
    return total


def metricas_corte(tipo, periodicidad, lb, segs_al_corte, segs_todos,
                   anio: int, trimestre: int,
                   metas_plan: Optional[dict] = None) -> dict:
    """Núcleo de métricas de un indicador al corte (año, trimestre). Port de
    ``db._calc_metricas_indicador`` de Alertas-Seguimientos.

    ``segs_al_corte`` / ``segs_todos``: listas de dicts con las claves
    ``anio, trimestre, meta_anual, meta_final, acumulado, valor_avance``,
    ordenadas por (anio, trimestre); la primera filtrada al período ≤ corte,
    la segunda con toda la historia. ``metas_plan``: metas por año del plan
    base (solo se usa en SUMA).

    Retorna dict con ``av_acum, meta_anual, meta_prev, meta_final, mp, ma,
    sum_metas_prev, phv, tray, paf, tid, brecha, periodo_str`` — porcentajes
    en FRACCIÓN 0–1."""
    t = _tipo(tipo)

    # meta_final: del seguimiento más reciente que la tenga (toda la historia)
    meta_final = next(
        (s["meta_final"] for s in reversed(segs_todos)
         if s.get("meta_final") is not None), None)

    # meta_anual: del año seleccionado; fallback al más reciente disponible.
    # Para SUMA no hay fallback: la meta anual es un incremento, no un nivel.
    meta_anual = next(
        (s["meta_anual"] for s in segs_todos
         if s["anio"] == anio and s.get("meta_anual") not in (None, 0)), None)
    if meta_anual is None and t != "SUMA":
        meta_anual = next(
            (s["meta_anual"] for s in reversed(segs_todos)
             if s.get("meta_anual") not in (None, 0)), None)

    # meta_prev: meta anual del año anterior al seleccionado
    meta_prev = next(
        (s["meta_anual"] for s in reversed(segs_todos)
         if s["anio"] == anio - 1 and s.get("meta_anual") not in (None, 0)), None)
    if meta_anual is None and t != "SUMA":
        meta_anual = meta_prev

    if t == "SUMA":
        sum_metas_prev = _suma_metas_prev_suma(
            segs_al_corte, segs_todos, anio, metas_plan)
        # Priorizar el acumulado explícito más reciente al corte; si no existe
        # (datos legacy), reconstruir con acumulado del año previo + reportes.
        acum_sel = next(
            (
                s["acumulado"] for s in reversed(segs_al_corte)
                if s.get("acumulado") is not None
                and (s["anio"] < anio or (s["anio"] == anio and s["trimestre"] <= trimestre))
            ),
            None,
        )
        if acum_sel is not None:
            av_acum = float(acum_sel)
        else:
            acum_prev = next(
                (s["acumulado"] for s in reversed(segs_al_corte)
                 if s["anio"] == anio - 1 and s.get("acumulado") is not None),
                0.0) or 0.0
            running_av = sum(
                (s["valor_avance"] or 0.0) for s in segs_al_corte
                if s["anio"] == anio and s["trimestre"] <= trimestre
                and s.get("valor_avance") is not None)
            av_acum = acum_prev + running_av
    else:
        sum_metas_prev = 0.0
        av_acum = next(
            (s["valor_avance"] for s in reversed(segs_al_corte)
             if s.get("valor_avance") is not None), lb)

    mes = calc_mes(trimestre, periodicidad)
    # SUMA sin meta anual en el año seleccionado: MP=0, MA=sum_metas_prev
    # (el indicador sigue participando con su acumulado y sus metas previas).
    meta_anual_mp = meta_anual if meta_anual is not None else (0.0 if t == "SUMA" else None)
    mp = calc_meta_periodo(t, meta_anual_mp, meta_prev, mes)
    ma = calc_meta_acum(t, mp, sum_metas_prev)
    phv = calc_pct_hasta_vig(t, av_acum, ma, lb)
    tray = calc_trayectoria_ideal(t, mp, ma, meta_final, lb)
    paf = calc_paf(t, av_acum, meta_final, lb)
    tid = calc_tid(t, ma, meta_final, lb)

    return dict(
        av_acum=av_acum, meta_anual=meta_anual, meta_prev=meta_prev, meta_final=meta_final,
        mp=mp, ma=ma, sum_metas_prev=sum_metas_prev,
        phv=phv, tray=tray, paf=paf, tid=tid, brecha=calc_brecha(paf, tid),
        periodo_str=f"{anio} Q{trimestre}",
    )
