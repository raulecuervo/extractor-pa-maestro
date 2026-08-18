# -*- coding: utf-8 -*-
"""
Validación de consistencia del SEGUIMIENTO — v2 (capa 2 de la convergencia).

Port FIEL de las validaciones EN PRODUCCIÓN de
``alertas-seguimientos/validation/core.py`` sobre el modelo canónico
``ResultadoSeguimiento``, más el semáforo/PHV de ``sispp-sdis``.

v2 (0.10.0) corrige las divergencias del port v1 frente a producción y
enriquece el retorno:

- Retorna ``HallazgoSeguimiento`` (shape completo de ``make_finding`` vía
  ``as_finding()``), no la ``Alerta`` genérica del plan.
- ``avance_meta``: si la meta anual es None/0 se OMITE TODO el chequeo,
  incluido el de ``pct_vigencia`` (early-return de producción).
- Retroactividad: los valores base VACÍOS no generan hallazgo (producción
  salta ``val_base`` falsy distinto de 0).
- Año de inicio (acumulado): ``fecha_inicio`` (serial Excel o 'YYYY-…') con
  fallback a ``anio_min`` — NO a ``min(metas)``.
- Comparaciones de texto con ``normalise`` de producción (colapsa espacios,
  CONSERVA tildes; estabilidad compara en ``upper()``) — no con ``_norm``.
- Numéricos con ``metricas.safe_float`` (``float()`` estricto de producción),
  no con el ``a_float`` tolerante de la librería.
- Etiquetas de campo de producción ('Ponderación (%)', 'Valor Línea Base',
  '% Avance Hasta Vigencia …').

Dos grupos:
- **Base vs nuevo** (2 cargas): ERROR_ESTABILIDAD, ERROR_RETROACTIVO,
  INFO_IND_NUEVO, INFO_IND_FALTANTE.
- **Un solo archivo**: ERROR_NO_NUMERICO, ADVERTENCIA_ESCALA,
  ADVERTENCIA_AVANCE, ADVERTENCIA_LIMITE_VIG, ADVERTENCIA_ACUM_META_VIG,
  ADVERTENCIA_ACUM_META_FIN, ADVERTENCIA_META_SIN_REP, ADVERTENCIA_REP_SIN_META,
  ADVERTENCIA_PCT_HASTA_VIG, ADVERTENCIA_DISCREPANCIA_PCT, ADVERTENCIA_CUAL.

ESCALA: ``pct_vigencia`` viene como FRACCIÓN 0–1 del ``.xlsb``; el umbral de
avance es 1.25 (125 %). ``UMBRALES_SEMAFORO`` está en 0–100 y ``a_porcentaje``
convierte explícitamente (ver README de escala en ``metricas.py``).
"""

from __future__ import annotations

import re

from .hallazgos import (  # noqa: F401  (re-export de UMBRAL_AVANCE)
    HallazgoSeguimiento,
    SEVERIDAD,
    TIPOS_HALLAZGO,
    UMBRAL_AVANCE,
    crear_hallazgo,
)
from ..utilidades import _norm
from .metricas import safe_float
from .modelo import IndicadorSeguimiento

UMBRAL_PCT_MIN = 0.50          # piso del % hasta la vigencia

# Semáforo (de sispp-sdis), en PORCENTAJE 0-100.
UMBRALES_SEMAFORO = {"rojo": 50.0, "amarillo": 75.0, "naranja": 125.0}

# Campos inmutables del indicador (ERROR_ESTABILIDAD), con las etiquetas
# EXACTAS de producción (validation/core.py::validate_stability).
_CAMPOS_ESTABILIDAD = [
    ("indicador_esperado", "Indicador Esperado"),
    ("nombre", "Nombre del Indicador"),
    ("sector", "Sector Responsable"),
    ("entidad", "Entidad Responsable"),
    ("ponderacion", "Ponderación (%)"),
    ("linea_base", "Valor Línea Base"),
    ("tipo_anualizacion", "Tipo de Anualización"),
    ("periodicidad", "Periodicidad"),
    ("fecha_inicio", "Fecha de Inicio"),
    ("fecha_fin", "Fecha de Finalización"),
]


# ─────────────────────────── helpers de producción ───────────────────────────

def normalise(val) -> str:
    """Colapsa espacios y recorta; CONSERVA tildes y mayúsculas.
    Réplica exacta de ``extractor.normalise`` de Alertas-Seguimientos."""
    if val is None:
        return ""
    return re.sub(r"\s+", " ", str(val).strip()).rstrip("\xa0").strip()


def parse_period(corte, anio):
    """(año, trimestre) desde 'corte' (str 'Qn') y 'año de reporte'.
    Réplica de ``extractor.parse_period``."""
    try:
        year = int(float(str(anio)))
    except Exception:
        return None, None
    if isinstance(corte, str):
        m = re.search(r"Q(\d)", corte, re.I)
        if m:
            return year, int(m.group(1))
    return year, None


def infer_anio_inicio(raw, anio_min: int = 2018) -> int:
    """Año de inicio desde ``fecha_inicio`` (serial Excel o 'YYYY-…').
    Réplica de ``extractor._infer_inicio_anio_val`` con el fallback
    parametrizado (producción usa ANOS[0]=2018)."""
    if raw is None or raw == "":
        return anio_min
    try:
        s = float(raw)
        if s > 0:
            from datetime import datetime, timedelta
            dt = datetime(1899, 12, 30) + timedelta(days=s)
            if 1900 <= dt.year <= 2100:
                return dt.year
    except (ValueError, TypeError):
        pass
    s = str(raw).strip()
    if len(s) >= 4 and s[:4].isdigit():
        y = int(s[:4])
        if 1900 <= y <= 2100:
            return y
    return anio_min


def _es_numerico(val) -> bool:
    """Réplica de ``validate.core._is_numeric_value`` (float() estricto)."""
    if val is None or val == "":
        return True
    if isinstance(val, (int, float)):
        return True
    s = str(val).strip()
    if s == "":
        return True
    try:
        float(s)
        return True
    except ValueError:
        return False


def _avances_trimestrales_vigencia(ind, year, hasta_q=None):
    vals = []
    for q in range(1, 5):
        if hasta_q and q > hasta_q:
            break
        v = safe_float(ind.avances.get(f"{year}_Q{q}"))
        if v is not None:
            vals.append(v)
    return vals


def _finding(tipo, ind, politica, archivo, **kw) -> HallazgoSeguimiento:
    """make_finding: los campos identitarios salen del indicador; la política
    del archivo (metadatos) y el archivo es el 'file_nuevo'."""
    return crear_hallazgo(
        tipo, codigo=ind.codigo, politica=politica, sector=ind.sector,
        entidad=ind.entidad, nombre=ind.nombre, archivo=archivo, **kw)


# ─────────────────────────── base vs nuevo ───────────────────────────

def _validar_estabilidad(base, nuevo, politica, archivo):
    out = []
    for attr, etiqueta in _CAMPOS_ESTABILIDAD:
        v_b = normalise(getattr(base, attr, None))
        v_n = normalise(getattr(nuevo, attr, None))
        if v_b and v_n and v_b.upper() != v_n.upper():
            out.append(_finding("ERROR_ESTABILIDAD", base, politica, archivo,
                                campo=etiqueta, val_base=v_b, val_nuevo=v_n))
    return out


# ── Reglas de vigencia (2026-08-15, portadas desde alertas-seguimientos) ──
# Un indicador que pasa a «No Vigente» puede legítimamente cerrar antes: baja su
# ponderación a 0 y ajusta su fecha de finalización. Marcarlo como campo inmutable
# modificado era ruido — en el PA de Mujer copaba la lista de errores. A cambio, un
# «Vigente» SIN ponderación sí es un defecto que antes pasaba inadvertido.

_CAMPO_PONDERACION = "Ponderación (%)"
_CAMPO_FECHA_FIN = "Fecha de Finalización"


def _estado_es(ind, valor) -> bool:
    return str(getattr(ind, "estado", "") or "").strip().lower() == valor


def _cambio_permitido_por_no_vigente(hallazgo, nuevo) -> bool:
    """¿El campo inmutable que cambió es uno que un No Vigente puede cambiar?"""
    if not _estado_es(nuevo, "no vigente"):
        return False
    campo = hallazgo.get("campo") if isinstance(hallazgo, dict) else getattr(hallazgo, "campo", None)
    if campo == _CAMPO_FECHA_FIN:
        return True
    if campo == _CAMPO_PONDERACION:
        pond = safe_float(getattr(nuevo, "ponderacion", None))
        return pond is None or pond == 0
    return False


def _validar_ponderacion_vigente(ind, politica, archivo):
    """Todo indicador vigente debe tener ponderación mayor que 0."""
    if not _estado_es(ind, "vigente"):
        return []
    pond = safe_float(getattr(ind, "ponderacion", None))
    if pond is not None and pond != 0:
        return []
    crudo = getattr(ind, "ponderacion", None)
    return [_finding("ERROR_PONDERACION_OBLIGATORIA", ind, politica, archivo,
                     campo=_CAMPO_PONDERACION,
                     val_nuevo="" if crudo in (None, "") else str(crudo),
                     detalle="Todo indicador vigente debe tener ponderación mayor que 0.")]


def _validar_sector_entidad(ind, politica, archivo, entidad_sector):
    """El sector del archivo no coincide con el oficial de esa entidad.

    Una entidad pertenece a UN solo sector. `entidad_sector` es el mapa curado que
    inyecta la aplicación (normalizado por `normalise().upper()`); si no se inyecta,
    la regla no corre y el comportamiento no cambia.
    """
    if not entidad_sector:
        return []
    ent = _norm(getattr(ind, "entidad", None))
    sec = _norm(getattr(ind, "sector", None))
    oficial = entidad_sector.get(ent)
    if not ent or not sec or not oficial or _norm(oficial) == sec:
        return []
    return [_finding("ADVERTENCIA_SECTOR_ENTIDAD", ind, politica, archivo,
                     campo="Sector Responsable", val_base=oficial,
                     val_nuevo=getattr(ind, "sector", None),
                     detalle=(f"La entidad «{getattr(ind, 'entidad', '')}» pertenece al sector "
                              f"«{oficial}»; el archivo trae «{getattr(ind, 'sector', '')}». "
                              "Se debe corregir en la fuente."))]


def _validar_retroactividad(base, nuevo, politica, archivo, anio_min):
    out = []
    base_year, base_q = parse_period(base.corte, base.anio_reporte)
    if base_year is None:
        return out

    # Avances de períodos ya cerrados (los valores base vacíos NO alertan).
    for clave, val_base in base.avances.items():
        if not val_base and val_base != 0:
            continue
        m = re.match(r"(\d{4})_Q(\d)", clave)
        if not m:
            continue
        ky, kq = int(m.group(1)), int(m.group(2))
        if ky > base_year or (ky == base_year and base_q and kq > base_q):
            continue
        val_nuevo = nuevo.avances.get(clave)
        if normalise(val_base) != normalise(val_nuevo):
            out.append(_finding("ERROR_RETROACTIVO", base, politica, archivo,
                                campo=f"Avance {clave.replace('_', ' ')}",
                                val_base=val_base, val_nuevo=val_nuevo,
                                periodo=clave.replace("_", " ")))

    # Acumulados de años cerrados.
    for anio in range(anio_min, base_year + 1):
        v_b = base.acumulados.get(str(anio))
        if not v_b and v_b != 0:
            continue
        v_n = nuevo.acumulados.get(str(anio))
        if normalise(v_b) != normalise(v_n):
            out.append(_finding("ERROR_RETROACTIVO", base, politica, archivo,
                                campo=f"Acumulado {anio}", val_base=v_b,
                                val_nuevo=v_n, periodo=str(anio)))
    return out


# ─────────────────────────── un solo archivo ───────────────────────────

def _validar_no_numerico(ind, politica, archivo):
    out = []
    year, _q = parse_period(ind.corte, ind.anio_reporte)
    if year is None:
        return out
    for q in range(1, 5):
        val = ind.avances.get(f"{year}_Q{q}")
        if val is not None and val != "" and not _es_numerico(val):
            out.append(_finding("ERROR_NO_NUMERICO", ind, politica, archivo,
                                campo=f"Avance {year} Q{q}",
                                val_nuevo=str(val)[:80],
                                periodo=f"{year} Q{q}",
                                detalle=f"El valor '{str(val)[:60]}' no es numérico en {year} Q{q}"))
    return out


def _validar_escala(ind, politica, archivo):
    out = []
    year, q = parse_period(ind.corte, ind.anio_reporte)
    if year is None or q is None:
        return out
    meta_f = safe_float(ind.metas.get(str(year)))
    if meta_f is None:
        return out
    meta_pct = (0 <= meta_f <= 1)
    for qq in range(1, q + 1):
        rep_f = safe_float(ind.avances.get(f"{year}_Q{qq}"))
        if rep_f is None:
            continue
        rep_pct = (0 <= rep_f <= 1)
        if meta_pct and rep_f > 1:
            out.append(_finding("ADVERTENCIA_ESCALA", ind, politica, archivo,
                                campo=f"Avance {year} Q{qq}",
                                val_base=f"Meta={meta_f} (escala 0-1)",
                                val_nuevo=f"Reporte={rep_f} (valor > 1)",
                                periodo=f"{year} Q{qq}",
                                detalle=f"Meta en escala 0-1 ({meta_f}) pero reporte Q{qq}={rep_f} supera 1"))
        elif not meta_pct and meta_f > 1 and rep_pct:
            out.append(_finding("ADVERTENCIA_ESCALA", ind, politica, archivo,
                                campo=f"Avance {year} Q{qq}",
                                val_base=f"Meta={meta_f} (valor > 1)",
                                val_nuevo=f"Reporte={rep_f} (escala 0-1)",
                                periodo=f"{year} Q{qq}",
                                detalle=f"Meta en valor absoluto ({meta_f}) pero reporte Q{qq}={rep_f} está en escala 0-1"))
    return out


def _validar_avance_meta(ind, politica, archivo, umbral=UMBRAL_AVANCE):
    out = []
    year, q = parse_period(ind.corte, ind.anio_reporte)
    if year is None or q is None:
        return out
    meta_f = safe_float(ind.metas.get(str(year)))
    tipo = (ind.tipo_anualizacion or "").lower()
    if meta_f is None or meta_f == 0:
        # Early-return de PRODUCCIÓN: sin meta anual no se evalúa nada de este
        # chequeo — tampoco el pct_vigencia (divergencia v1 corregida).
        return out

    if tipo in ("creciente", "decreciente", "constante"):
        ultimo = None
        for qq in range(q, 0, -1):
            v = safe_float(ind.avances.get(f"{year}_Q{qq}"))
            if v is not None:
                ultimo = v
                break
        if ultimo is not None and ultimo > meta_f * umbral:
            out.append(_finding("ADVERTENCIA_LIMITE_VIG", ind, politica, archivo,
                                campo=f"Último avance vigencia {year}",
                                val_base=f"Meta={meta_f}",
                                val_nuevo=f"Último reporte={ultimo}",
                                periodo=str(year),
                                detalle=(f"Tipo '{ind.tipo_anualizacion}': último reporte ({ultimo}) "
                                         f"supera {umbral:.0%} de la meta ({meta_f})")))
    elif tipo == "suma":
        vals = _avances_trimestrales_vigencia(ind, year, hasta_q=q)
        if vals:
            total = sum(vals)
            if total > meta_f * umbral:
                out.append(_finding("ADVERTENCIA_LIMITE_VIG", ind, politica, archivo,
                                    campo=f"Suma avances vigencia {year}",
                                    val_base=f"Meta={meta_f}",
                                    val_nuevo=f"Suma={total:.4g}",
                                    periodo=str(year),
                                    detalle=(f"Tipo 'Suma': suma de reportes ({total:.4g}) "
                                             f"supera {umbral:.0%} de la meta ({meta_f})")))

    pct = safe_float(ind.pct_vigencia.get(str(year)))
    if pct is not None and pct > umbral:
        out.append(_finding("ADVERTENCIA_AVANCE", ind, politica, archivo,
                            campo=f"% Avance Vigencia {year}",
                            val_base=str(meta_f), val_nuevo=f"{pct:.2%}",
                            periodo=str(year),
                            detalle=f"% Avance de la vigencia ({pct:.1%}) supera {umbral:.0%} de la meta programada"))
    return out


def _validar_acumulado(ind, politica, archivo, anio_min):
    out = []
    year, _ = parse_period(ind.corte, ind.anio_reporte)
    if year is None:
        return out
    acum_rep = safe_float(ind.acumulados.get(str(year)))
    if acum_rep is None:
        return out

    meta_final = safe_float(ind.meta_final)
    if meta_final is not None and meta_final > 0 and acum_rep > meta_final:
        out.append(_finding("ADVERTENCIA_ACUM_META_FIN", ind, politica, archivo,
                            campo=f"Acumulado {year}",
                            val_base=f"Meta final={meta_final}",
                            val_nuevo=f"Acumulado={acum_rep}",
                            periodo=str(year),
                            detalle=f"El acumulado ({acum_rep}) supera la meta final ({meta_final})"))

    # Año de inicio de PRODUCCIÓN: fecha_inicio (serial/'YYYY-…') con fallback
    # a anio_min — no min(metas) (divergencia v1 corregida).
    anio_inicio = infer_anio_inicio(ind.fecha_inicio, anio_min)
    meta_sum = sum(
        safe_float(ind.metas.get(str(y))) or 0
        for y in range(anio_inicio, year + 1)
        if safe_float(ind.metas.get(str(y))) is not None
    )
    if meta_sum > 0 and acum_rep > meta_sum:
        out.append(_finding("ADVERTENCIA_ACUM_META_VIG", ind, politica, archivo,
                            campo=f"Acumulado {year}",
                            val_base=f"Meta acumulada hasta {year}={meta_sum:.4g}",
                            val_nuevo=f"Acumulado={acum_rep}",
                            periodo=str(year),
                            detalle=(f"El acumulado ({acum_rep}) supera la suma de metas "
                                     f"hasta {year} ({meta_sum:.4g})")))
    return out


def _validar_meta_reporte(ind, politica, archivo):
    out = []
    year, q = parse_period(ind.corte, ind.anio_reporte)
    if year is None or q is None:
        return out

    meta_f = safe_float(ind.metas.get(str(year)))
    avances_vig = [ind.avances.get(f"{year}_Q{qq}") for qq in range(1, q + 1)]
    tiene_reporte = any(v is not None and v != "" for v in avances_vig)

    if meta_f is not None and meta_f != 0 and not tiene_reporte:
        out.append(_finding("ADVERTENCIA_META_SIN_REP", ind, politica, archivo,
                            campo=f"Avances {year}",
                            val_base=f"Meta={meta_f}", val_nuevo="Sin reporte",
                            periodo=str(year),
                            detalle=f"Existe meta ({meta_f}) para {year} pero no hay ningún reporte hasta Q{q}"))

    if (meta_f is None or meta_f == 0) and tiene_reporte:
        rep_vals = [v for v in avances_vig if v is not None and v != ""]
        out.append(_finding("ADVERTENCIA_REP_SIN_META", ind, politica, archivo,
                            campo=f"Avances {year}",
                            val_base="Meta=0 o no existe",
                            val_nuevo=str(rep_vals[0])[:50] if rep_vals else "?",
                            periodo=str(year),
                            detalle=f"No existe meta (o es 0) para {year} pero hay reportes registrados"))
    return out


def _validar_pct_hasta_vig(ind, politica, archivo):
    out = []
    year, _ = parse_period(ind.corte, ind.anio_reporte)
    if year is None:
        return out
    pct = safe_float(ind.pct_vigencia.get(str(year)))
    if pct is None:
        return out
    if pct < UMBRAL_PCT_MIN or pct > UMBRAL_AVANCE:
        msg = (f"% avance hasta la vigencia ({pct:.1%}) es inferior al 50%"
               if pct < UMBRAL_PCT_MIN else
               f"% avance hasta la vigencia ({pct:.1%}) supera el 125%")
        out.append(_finding("ADVERTENCIA_PCT_HASTA_VIG", ind, politica, archivo,
                            campo=f"% Avance Hasta Vigencia {year}",
                            val_nuevo=f"{pct:.2%}", periodo=str(year),
                            detalle=msg))
    return out


def _validar_cualitativo(ind, politica, archivo):
    out = []
    if (ind.estado or "").lower() != "vigente":
        return out
    year, q = parse_period(ind.corte, ind.anio_reporte)
    if year is None or q is None:
        return out
    per = (ind.periodicidad or "").lower()
    qs = list(range(1, q + 1)) if "trimestral" in per else [q]
    for qq in qs:
        clave = f"{year}_Q{qq}"
        if not normalise(ind.cualitativos.get(clave)):
            out.append(_finding("ADVERTENCIA_CUAL", ind, politica, archivo,
                                campo=f"Cualitativo {year} Q{qq}",
                                periodo=f"{year} Q{qq}",
                                detalle=f"Indicador Vigente sin reporte cualitativo en {year} Q{qq}"))
    return out


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


def _validaciones_un_archivo(ind, politica, archivo, anio_min, entidad_sector=None):
    """Las validaciones de un solo archivo, en el ORDEN de producción
    (run_all_validations). Las dos últimas son posteriores a MS-32b."""
    out = []
    out.extend(_validar_no_numerico(ind, politica, archivo))
    out.extend(_validar_escala(ind, politica, archivo))
    out.extend(_validar_avance_meta(ind, politica, archivo))
    out.extend(_validar_acumulado(ind, politica, archivo, anio_min))
    out.extend(_validar_meta_reporte(ind, politica, archivo))
    out.extend(_validar_pct_hasta_vig(ind, politica, archivo))
    out.extend(_validar_cualitativo(ind, politica, archivo))
    out.extend(_validar_discrepancia_pct(ind, politica, archivo))
    out.extend(_validar_ponderacion_vigente(ind, politica, archivo))
    out.extend(_validar_sector_entidad(ind, politica, archivo, entidad_sector))
    return out


# ─────────────────────────── orquestadores ───────────────────────────

def validar_archivo(res_nuevo, *, anio_min: int = 2018, entidad_sector=None) -> list:
    """Validaciones de un solo archivo (sin base). → list[HallazgoSeguimiento].

    `entidad_sector`: mapa {entidad normalizada con `_norm`: sector oficial} para la
    regla ADVERTENCIA_SECTOR_ENTIDAD. Opcional: sin él esa regla no corre.
    """
    politica = res_nuevo.metadatos.nombre_politica or ""
    archivo = res_nuevo.metadatos.archivo_fuente
    alertas = []
    for ind in res_nuevo.indicadores:
        alertas.extend(_validaciones_un_archivo(ind, politica, archivo, anio_min,
                                                entidad_sector))
    return alertas


def validar_consistencia(res_base, res_nuevo, *, anio_min: int = 2018,
                         entidad_sector=None) -> list:
    """Base vs nuevo + validaciones del nuevo. → list[HallazgoSeguimiento].
    Orden y textos de ``run_all_validations`` de producción."""
    politica = res_nuevo.metadatos.nombre_politica or ""
    archivo = res_nuevo.metadatos.archivo_fuente
    base_map = {i.codigo: i for i in res_base.indicadores if i.codigo}
    new_map = {i.codigo: i for i in res_nuevo.indicadores if i.codigo}
    alertas = []

    for code, ind in new_map.items():
        if code not in base_map:
            alertas.append(_finding(
                "INFO_IND_NUEVO", ind, politica, archivo,
                detalle=(f"Indicador {code} presente en este archivo pero no en el "
                         "archivo base cargado. Se creará automáticamente. Para evitar "
                         "esta alerta, recargue el archivo base con la versión actualizada.")))
    for code, ind in base_map.items():
        if code not in new_map:
            alertas.append(_finding(
                "INFO_IND_FALTANTE", ind, politica, archivo,
                detalle="Presente en la base, ausente en el nuevo archivo"))

    for code, nuevo in new_map.items():
        base = base_map.get(code)
        if base is not None:
            alertas.extend(
                h for h in _validar_estabilidad(base, nuevo, politica, archivo)
                if not _cambio_permitido_por_no_vigente(h, nuevo)
            )
            alertas.extend(_validar_retroactividad(base, nuevo, politica, archivo, anio_min))
        alertas.extend(_validaciones_un_archivo(nuevo, politica, archivo, anio_min,
                                                entidad_sector))
    return alertas


# ─────────────────────────── adaptador de dicts ───────────────────────────

def indicador_desde_dict(d: dict) -> IndicadorSeguimiento:
    """Adapta el dict de indicador de Alertas-Seguimientos (BD / extractor
    legado) al modelo canónico. Mapa: ``ind_esperado→indicador_esperado``,
    ``tipo_anual→tipo_anualizacion``, ``metas['final']→meta_final`` (y las
    metas quedan solo con claves de año)."""
    metas = dict(d.get("metas") or {})
    meta_final = metas.pop("final", None)
    return IndicadorSeguimiento(
        codigo=d.get("codigo"),
        indicador_esperado=d.get("ind_esperado"),
        nombre=d.get("nombre"),
        sector=d.get("sector"),
        entidad=d.get("entidad"),
        estado=d.get("estado"),
        ponderacion=d.get("ponderacion"),
        linea_base=d.get("linea_base"),
        tipo_anualizacion=d.get("tipo_anual"),
        periodicidad=d.get("periodicidad"),
        fecha_inicio=d.get("fecha_inicio"),
        fecha_fin=d.get("fecha_fin"),
        corte=d.get("corte"),
        anio_reporte=d.get("anio_reporte"),
        meta_final=meta_final,
        avances=dict(d.get("avances") or {}),
        acumulados=dict(d.get("acumulados") or {}),
        metas=metas,
        pct_vigencia=dict(d.get("pct_vigencia") or {}),
        cualitativos=dict(d.get("cualitativos") or {}),
        avance_enfoques=dict(d.get("avance_enfoques") or {}),
    )


# ─────────────────────────── semáforo / PHV ───────────────────────────

def a_porcentaje(pct):
    """Fracción 0–1 → porcentaje 0–100 (si ya viene en 0–100, se respeta)."""
    f = safe_float(pct)
    if f is None:
        return None
    return f * 100.0 if 0 <= f <= 1.5 else f


# Compatibilidad con consumidores previos (tablero.py).
_a_porcentaje = a_porcentaje


def semaforo_de(pct, umbrales=UMBRALES_SEMAFORO) -> str:
    """ROJO/AMARILLO/VERDE/NARANJA/SIN_DATO según el % (acepta fracción o 0-100)."""
    p = a_porcentaje(pct)
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
