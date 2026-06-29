# -*- coding: utf-8 -*-
"""
Validación de consistencia del SEGUIMIENTO (Fase S3).

Porta las 15 alertas de consistencia de `alertas-seguimientos/validation/core.py`
al modelo canónico `ResultadoSeguimiento`, más el **semáforo/PHV** de `sispp-sdis`.

Dos grupos:
- **Base vs nuevo** (requieren 2 cargas): ERROR_ESTABILIDAD, ERROR_RETROACTIVO,
  INFO_IND_NUEVO, INFO_IND_FALTANTE.
- **Un solo archivo** (el nuevo): ERROR_NO_NUMERICO, ADVERTENCIA_ESCALA,
  ADVERTENCIA_AVANCE, ADVERTENCIA_LIMITE_VIG, ADVERTENCIA_ACUM_META_VIG,
  ADVERTENCIA_ACUM_META_FIN, ADVERTENCIA_META_SIN_REP, ADVERTENCIA_REP_SIN_META,
  ADVERTENCIA_PCT_HASTA_VIG, ADVERTENCIA_DISCREPANCIA_PCT, ADVERTENCIA_CUAL.

El % de la vigencia (`pct_vigencia`) viene como FRACCIÓN 0-1 en el `.xlsb`; el
umbral de avance es 1.25 (125%).
"""

from __future__ import annotations

import re

from ..alertas import crear_alerta
from ..utilidades import _norm, a_float

UMBRAL_AVANCE = 1.25            # 125% (fracción) para las alertas de avance
UMBRAL_PCT_MIN = 0.50          # piso del % hasta la vigencia

# Semáforo (de sispp-sdis), en PORCENTAJE.
UMBRALES_SEMAFORO = {"rojo": 50.0, "amarillo": 75.0, "naranja": 125.0}

# Campos inmutables del indicador (para ERROR_ESTABILIDAD).
_CAMPOS_ESTABILIDAD = [
    ("indicador_esperado", "Indicador Esperado"),
    ("nombre", "Nombre del Indicador"),
    ("sector", "Sector Responsable"),
    ("entidad", "Entidad Responsable"),
    ("ponderacion", "Ponderación"),
    ("linea_base", "Línea Base"),
    ("tipo_anualizacion", "Tipo de Anualización"),
    ("periodicidad", "Periodicidad"),
    ("fecha_inicio", "Fecha de Inicio"),
    ("fecha_fin", "Fecha de Finalización"),
]


# ─────────────────────────── helpers ───────────────────────────

def _parse_periodo(corte, anio_reporte):
    """(año, trimestre) a partir de 'corte' (Qn) y 'año de reporte'."""
    try:
        year = int(float(str(anio_reporte)))
    except (ValueError, TypeError):
        return None, None
    q = None
    if corte is not None:
        m = re.search(r"Q(\d)", str(corte), re.I)
        if m:
            q = int(m.group(1))
    return year, q


def _es_numerico(v) -> bool:
    if v is None or v == "":
        return True
    return a_float(v) is not None


def _alerta(tipo, ind, descripcion, *, archivo, campo=None, valor=None):
    return crear_alerta(
        tipo, descripcion, archivo_fuente=archivo,
        nombre_politica=None, codigo_ip=ind.codigo or "",
        campo=campo, valor=valor)


def _anio_inicio(ind):
    """Año de inicio para el cálculo de meta acumulada de la vigencia."""
    fi = ind.fecha_inicio
    if fi:
        s = str(fi)
        if len(s) >= 4 and s[:4].isdigit():
            return int(s[:4])
    anios = [int(a) for a in ind.metas if str(a).isdigit()]
    return min(anios) if anios else None


# ─────────────────────────── base vs nuevo ───────────────────────────

def _validar_estabilidad(base, nuevo, archivo):
    out = []
    for attr, etiqueta in _CAMPOS_ESTABILIDAD:
        vb = getattr(base, attr, None)
        vn = getattr(nuevo, attr, None)
        nb, nn = _norm(str(vb)) if vb is not None else "", _norm(str(vn)) if vn is not None else ""
        if nb and nn and nb != nn:
            out.append(_alerta("ERROR_ESTABILIDAD", nuevo,
                               f"{etiqueta} cambió: '{vb}' → '{vn}'",
                               archivo=archivo, campo=etiqueta, valor=f"{vb} | {vn}"))
    return out


def _validar_retroactividad(base, nuevo, archivo):
    out = []
    base_year, base_q = _parse_periodo(base.corte, base.anio_reporte)
    if base_year is None:
        return out
    # Avances de períodos ya cerrados.
    for clave, vb in base.avances.items():
        m = re.match(r"(\d{4})_Q(\d)", clave)
        if not m:
            continue
        ky, kq = int(m.group(1)), int(m.group(2))
        if ky > base_year or (ky == base_year and base_q and kq > base_q):
            continue
        vn = nuevo.avances.get(clave)
        if _norm(str(vb)) != _norm(str(vn)):
            out.append(_alerta("ERROR_RETROACTIVO", nuevo,
                               f"Avance {clave.replace('_', ' ')} histórico modificado: '{vb}' → '{vn}'",
                               archivo=archivo, campo=f"Avance {clave}", valor=f"{vb} | {vn}"))
    # Acumulados de años cerrados.
    for anio in range(2018, base_year + 1):
        vb = base.acumulados.get(str(anio))
        if vb is None:
            continue
        vn = nuevo.acumulados.get(str(anio))
        if _norm(str(vb)) != _norm(str(vn)):
            out.append(_alerta("ERROR_RETROACTIVO", nuevo,
                               f"Acumulado {anio} histórico modificado: '{vb}' → '{vn}'",
                               archivo=archivo, campo=f"Acumulado {anio}", valor=f"{vb} | {vn}"))
    return out


# ─────────────────────────── un solo archivo ───────────────────────────

def _validar_no_numerico(ind, archivo):
    out = []
    year, q = _parse_periodo(ind.corte, ind.anio_reporte)
    if year is None:
        return out
    for qq in range(1, 5):
        v = ind.avances.get(f"{year}_Q{qq}")
        if v is not None and v != "" and not _es_numerico(v):
            out.append(_alerta("ERROR_NO_NUMERICO", ind,
                               f"Avance {year} Q{qq} no es numérico: '{str(v)[:60]}'",
                               archivo=archivo, campo=f"Avance {year} Q{qq}", valor=str(v)[:80]))
    return out


def _validar_escala(ind, archivo):
    out = []
    year, q = _parse_periodo(ind.corte, ind.anio_reporte)
    if year is None or q is None:
        return out
    meta = a_float(ind.metas.get(str(year)))
    if meta is None:
        return out
    meta_pct = 0 <= meta <= 1
    for qq in range(1, q + 1):
        rep = a_float(ind.avances.get(f"{year}_Q{qq}"))
        if rep is None:
            continue
        rep_pct = 0 <= rep <= 1
        if meta_pct and rep > 1:
            out.append(_alerta("ADVERTENCIA_ESCALA", ind,
                               f"Meta en escala 0-1 ({meta}) pero reporte Q{qq}={rep} supera 1",
                               archivo=archivo, campo=f"Avance {year} Q{qq}", valor=rep))
        elif not meta_pct and meta > 1 and rep_pct:
            out.append(_alerta("ADVERTENCIA_ESCALA", ind,
                               f"Meta en valor absoluto ({meta}) pero reporte Q{qq}={rep} en escala 0-1",
                               archivo=archivo, campo=f"Avance {year} Q{qq}", valor=rep))
    return out


def _validar_avance_meta(ind, archivo, umbral=UMBRAL_AVANCE):
    out = []
    year, q = _parse_periodo(ind.corte, ind.anio_reporte)
    if year is None or q is None:
        return out
    meta = a_float(ind.metas.get(str(year)))
    tipo = (ind.tipo_anualizacion or "").lower()
    if meta is None or meta == 0:
        pass
    elif tipo in ("creciente", "decreciente", "constante"):
        ultimo = None
        for qq in range(q, 0, -1):
            v = a_float(ind.avances.get(f"{year}_Q{qq}"))
            if v is not None:
                ultimo = v
                break
        if ultimo is not None and ultimo > meta * umbral:
            out.append(_alerta("ADVERTENCIA_LIMITE_VIG", ind,
                               f"Último reporte {year} ({ultimo}) supera {umbral:.0%} de la meta ({meta})",
                               archivo=archivo, campo=f"Vigencia {year}", valor=ultimo))
    elif tipo == "suma":
        vals = [a_float(ind.avances.get(f"{year}_Q{qq}")) for qq in range(1, q + 1)]
        vals = [v for v in vals if v is not None]
        if vals and sum(vals) > meta * umbral:
            out.append(_alerta("ADVERTENCIA_LIMITE_VIG", ind,
                               f"Suma de reportes {year} ({sum(vals):.4g}) supera {umbral:.0%} de la meta ({meta})",
                               archivo=archivo, campo=f"Vigencia {year}", valor=round(sum(vals), 4)))
    pct = a_float(ind.pct_vigencia.get(str(year)))
    if pct is not None and pct > umbral:
        out.append(_alerta("ADVERTENCIA_AVANCE", ind,
                           f"% Avance de la vigencia ({pct:.1%}) supera {umbral:.0%}",
                           archivo=archivo, campo=f"% Avance Vigencia {year}", valor=f"{pct:.2%}"))
    return out


def _validar_acumulado(ind, archivo):
    out = []
    year, _ = _parse_periodo(ind.corte, ind.anio_reporte)
    if year is None:
        return out
    acum = a_float(ind.acumulados.get(str(year)))
    if acum is None:
        return out
    mf = a_float(ind.meta_final)
    if mf is not None and mf > 0 and acum > mf:
        out.append(_alerta("ADVERTENCIA_ACUM_META_FIN", ind,
                           f"Acumulado {year} ({acum}) supera la meta final ({mf})",
                           archivo=archivo, campo=f"Acumulado {year}", valor=acum))
    ai = _anio_inicio(ind)
    if ai is not None:
        meta_sum = sum(a_float(ind.metas.get(str(y))) or 0 for y in range(ai, year + 1)
                       if a_float(ind.metas.get(str(y))) is not None)
        if meta_sum > 0 and acum > meta_sum:
            out.append(_alerta("ADVERTENCIA_ACUM_META_VIG", ind,
                               f"Acumulado {year} ({acum}) supera la meta acumulada hasta {year} ({meta_sum:.4g})",
                               archivo=archivo, campo=f"Acumulado {year}", valor=acum))
    return out


def _validar_meta_reporte(ind, archivo):
    out = []
    year, q = _parse_periodo(ind.corte, ind.anio_reporte)
    if year is None or q is None:
        return out
    meta = a_float(ind.metas.get(str(year)))
    avances_vig = [ind.avances.get(f"{year}_Q{qq}") for qq in range(1, q + 1)]
    tiene_reporte = any(v is not None and v != "" for v in avances_vig)
    if meta is not None and meta != 0 and not tiene_reporte:
        out.append(_alerta("ADVERTENCIA_META_SIN_REP", ind,
                           f"Existe meta ({meta}) para {year} pero no hay reporte hasta Q{q}",
                           archivo=archivo, campo=f"Avances {year}", valor=meta))
    if (meta is None or meta == 0) and tiene_reporte:
        out.append(_alerta("ADVERTENCIA_REP_SIN_META", ind,
                           f"Hay reporte en {year} pero la meta es 0 o no existe",
                           archivo=archivo, campo=f"Avances {year}"))
    return out


def _validar_pct_hasta_vig(ind, archivo):
    out = []
    year, _ = _parse_periodo(ind.corte, ind.anio_reporte)
    if year is None:
        return out
    pct = a_float(ind.pct_vigencia.get(str(year)))
    if pct is None:
        return out
    if pct < UMBRAL_PCT_MIN or pct > UMBRAL_AVANCE:
        msg = (f"% avance hasta la vigencia ({pct:.1%}) es inferior al 50%"
               if pct < UMBRAL_PCT_MIN else
               f"% avance hasta la vigencia ({pct:.1%}) supera el 125%")
        out.append(_alerta("ADVERTENCIA_PCT_HASTA_VIG", ind, msg,
                           archivo=archivo, campo=f"% Avance Vigencia {year}", valor=f"{pct:.2%}"))
    return out


def _validar_cualitativo(ind, archivo):
    out = []
    if _norm(ind.estado) != "vigente":
        return out
    year, q = _parse_periodo(ind.corte, ind.anio_reporte)
    if year is None or q is None:
        return out
    per = _norm(ind.periodicidad)
    qs = list(range(1, q + 1)) if "trimestral" in per else [q]
    for qq in qs:
        if not ind.cualitativos.get(f"{year}_Q{qq}"):
            out.append(_alerta("ADVERTENCIA_CUAL", ind,
                               f"Indicador Vigente sin reporte cualitativo en {year} Q{qq}",
                               archivo=archivo, campo=f"Cualitativo {year} Q{qq}"))
    return out


def _validar_discrepancia_pct(ind, archivo):
    out = []
    year, _ = _parse_periodo(ind.corte, ind.anio_reporte)
    if year is None:
        return out
    acum = a_float(ind.acumulados.get(str(year)))
    meta = a_float(ind.metas.get(str(year)))
    pct = a_float(ind.pct_vigencia.get(str(year)))
    if acum is None or meta in (None, 0) or pct is None:
        return out
    pct_calc = acum / meta
    if round(pct, 3) != round(pct_calc, 3):
        out.append(_alerta("ADVERTENCIA_DISCREPANCIA_PCT", ind,
                           f"% reportado ({pct:.3f}) difiere del calculado acum/meta ({pct_calc:.3f}) en {year}",
                           archivo=archivo, campo=f"% Avance Vigencia {year}",
                           valor=f"reportado={pct:.3f} calculado={pct_calc:.3f}"))
    return out


_VALIDADORES_ARCHIVO = [
    _validar_no_numerico, _validar_escala, _validar_avance_meta, _validar_acumulado,
    _validar_meta_reporte, _validar_pct_hasta_vig, _validar_cualitativo,
    _validar_discrepancia_pct,
]


# ─────────────────────────── orquestadores ───────────────────────────

def validar_archivo(res_nuevo) -> list:
    """Ejecuta las validaciones de un solo archivo (sin comparar con base)."""
    archivo = res_nuevo.metadatos.archivo_fuente
    alertas = []
    for ind in res_nuevo.indicadores:
        for fn in _VALIDADORES_ARCHIVO:
            alertas.extend(fn(ind, archivo))
    return alertas


def validar_consistencia(res_base, res_nuevo) -> list:
    """Compara base vs nuevo y valida el nuevo. Devuelve la lista de alertas."""
    archivo = res_nuevo.metadatos.archivo_fuente
    base_map = {i.codigo: i for i in res_base.indicadores if i.codigo}
    new_map = {i.codigo: i for i in res_nuevo.indicadores if i.codigo}
    alertas = []

    for code, ind in new_map.items():
        if code not in base_map:
            alertas.append(_alerta("INFO_IND_NUEVO", ind,
                                   f"Indicador {code} nuevo (no estaba en el archivo base).",
                                   archivo=archivo))
    for code, ind in base_map.items():
        if code not in new_map:
            alertas.append(_alerta("INFO_IND_FALTANTE", ind,
                                   f"Indicador {code} estaba en la base y falta en el nuevo.",
                                   archivo=archivo))

    for code, nuevo in new_map.items():
        base = base_map.get(code)
        if base is not None:
            alertas.extend(_validar_estabilidad(base, nuevo, archivo))
            alertas.extend(_validar_retroactividad(base, nuevo, archivo))
        for fn in _VALIDADORES_ARCHIVO:
            alertas.extend(fn(nuevo, archivo))
    return alertas


# ─────────────────────────── semáforo / PHV ───────────────────────────

def _a_porcentaje(pct):
    f = a_float(pct)
    if f is None:
        return None
    return f * 100.0 if 0 <= f <= 1.5 else f


def semaforo_de(pct, umbrales=UMBRALES_SEMAFORO) -> str:
    """ROJO/AMARILLO/VERDE/NARANJA/SIN_DATO según el % (acepta fracción o 0-100)."""
    p = _a_porcentaje(pct)
    if p is None:
        return "SIN_DATO"
    if p <= umbrales["rojo"]:
        return "ROJO"
    if p <= umbrales["amarillo"]:
        return "AMARILLO"
    if p <= umbrales["naranja"]:
        return "VERDE"
    return "NARANJA"


def semaforo_indicador(ind, anio) -> str:
    """Semáforo del indicador para un año, a partir del % de la vigencia reportado."""
    return semaforo_de(ind.pct_vigencia.get(str(anio)))
