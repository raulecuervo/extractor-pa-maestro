# -*- coding: utf-8 -*-
"""
Motor de reglas de negocio del plan de acción (V0–V18).

Opera sobre el MODELO CANÓNICO ya extraído (`ResultadoExtraccion`) y produce
alertas usando el catálogo consolidado. Es independiente de la extracción: se
invoca con `validar_reglas(resultado)`.

Consolida las reglas de `validador-plan-accion` (V0–V18, la referencia),
`generador-seguimiento` (mismas V0–V18) y los extras de `sispp-gobierno`
(periodicidad). Las reglas de catálogo de sector/entidad (V4) quedan disponibles
pero requieren inyectar los catálogos oficiales.

Nomenclatura de reglas (familia → código):
  Ponderación  V0/V1/V2/V18   Tipología V3/V4   Fechas V5
  Metas        V6/V7/V8/V12/V14/V15/V17          Línea base V9/V16
  Códigos      V11/V13
"""

from __future__ import annotations

import datetime as _dt
import re
from collections import defaultdict
from typing import Optional

from .alertas import crear_alerta
from .seguimiento.metricas import hay_meta, metas_antes_de_inicio
from .utilidades import _norm, a_float, codigo_mal_escrito, elegir_peso_objetivo, fecha_de_valor

# Tolerancia de las sumas de ponderación, en puntos porcentuales (ADR-001: 0,1 pp
# desde la 0.29.0; antes 0,5).
TOLERANCIA_PESO_PP = 0.1
# Tolerancia absoluta entre las metas anuales y la meta final (V17).
TOLERANCIA_META_FINAL = 0.5
EPSILON = TOLERANCIA_PESO_PP  # nombre histórico; se conserva por compatibilidad

TIPOS_ANUALIZACION_VALIDOS = {"CRECIENTE", "DECRECIENTE", "CONSTANTE", "SUMA"}
PERIODICIDADES_VALIDAS = {
    "ANUAL", "SEMESTRAL", "TRIMESTRAL", "MENSUAL", "BIMESTRAL",
    "CUATRIMESTRAL", "BIENAL", "TRIENAL", "QUINQUENAL",
}
# Intervalo (en años) entre metas esperadas según periodicidad (para V12).
INTERVALO_PERIODICIDAD = {
    "anual": 1, "semestral": 1, "trimestral": 1, "mensual": 1,
    "bienal": 2, "trienal": 3, "cuatrienal": 4, "quinquenal": 5,
}
_NULOS = {"", "nan", "none", "nd", "n/a", "n.a.", "n.a", "na", "_", "-"}
_RE_OBJ = re.compile(r"^\d+$")
_RE_IR = re.compile(r"^\d+\.\d+$")
_RE_IP = re.compile(r"^\d+\.\d+\.\d+$")
_RE_ANIO = re.compile(r"^(19|20)\d\d(\.0+)?$")


# ─────────────────────────── helpers ────────────────────────────

def _es_no_vigente(ind) -> bool:
    return _norm(getattr(ind, "es_vigente", None)) in ("no vigente", "no", "n")


def _vacio(v) -> bool:
    return v is None or _norm(v) in _NULOS


def _factor(pesos: list) -> float:
    """100.0 si todos los pesos están en [0,1] (escala decimal); 1.0 si no."""
    pos = [p for p in pesos if p is not None and p > 0]
    if not pos:
        return 1.0
    return 100.0 if all(p <= 1.0 for p in pos) else 1.0


def _leer_peso(valor) -> tuple[Optional[float], bool]:
    """(número, trae_pct) de una ponderación tal como la dejó el extractor.

    El texto con «%» ('2.86%', '0,5%') ya está en puntos porcentuales: su escala
    no depende del resto del plan. Un número suelto (0.0286 o 2.86) es ambiguo y
    su escala la decide `_factor` con los demás números sueltos del plan."""
    return a_float(valor), isinstance(valor, str) and valor.strip().endswith("%")


def _difiere(a: float, b: float, tol: float) -> bool:
    """¿``a`` y ``b`` difieren más allá de la tolerancia? La tolerancia absoluta
    (``tol``, 0,5 por defecto) se acota al 1 % de la mayor magnitud, para que una
    meta en fracción (0,8 frente a 1) no quede escondida por una tolerancia
    pensada para conteos."""
    return abs(a - b) > min(tol, 0.01 * max(abs(a), abs(b)))


def _parse_fecha(v) -> Optional[_dt.date]:
    """Parsea una fecha tolerando los formatos reales de los planes: datetime/
    date, AÑO suelto (entero o '2019'), serial de Excel, 'YYYY-MM-DD',
    'DD/MM/YYYY', 'DD/MM/YY' (2 dígitos) y 'MM/DD/YYYY' (formato US).
    Devuelve None ante fechas genuinamente inválidas (p. ej. 31/06, 31/02) o
    basura — son hallazgos reales que deben quedar como `fecha_invalida`.

    Es :func:`utilidades.fecha_de_valor`, la misma lectura que usa la capa de
    seguimiento."""
    return fecha_de_valor(v)


def _add(alertas, tipo, desc, ind=None, *, archivo="", politica="", campo=None, valor=None,
         cod_obj=None, cod_ir=None, cod_ip=None):
    alertas.append(crear_alerta(
        tipo, desc, archivo_fuente=archivo, nombre_politica=politica,
        codigo_objetivo=cod_obj, codigo_ir=cod_ir, codigo_ip=cod_ip,
        campo=campo, valor=valor))


# ─────────────────────────── reglas ─────────────────────────────

def _ponderacion(irs, ips, alertas, archivo, politica, tol=TOLERANCIA_PESO_PP):
    """V0/V1/V2 (sumas de pesos) + ponderación faltante.

    Las sumas se hacen en puntos porcentuales. Cada peso se lee como
    `(número, trae_pct)` y se lleva a puntos por separado: el texto con «%» va
    tal cual y los números sueltos se multiplican por un único factor del plan,
    que `_factor` decide mirando SOLO los números sueltos. Así un «2.86%»
    escrito como texto en un plan decimal (0.0377, 0.1418…) ya no lo pasa
    entero a la escala de porcentaje, ni un «0,5%» se lee como 50 %."""
    # Peso del objetivo (el de su primer IR vigente, si no el primero no nulo:
    # ver `elegir_peso_objetivo`) y peso del IR.
    candidatos_obj = defaultdict(list)
    peso_de_ir = {}
    pesos_por_obj = defaultdict(list)
    for ir in irs:
        obj = ir.codigo_objetivo or "SIN_OBJ"
        candidatos_obj[obj].append((ir.es_vigente, ir.peso_pct, ir.peso_objetivo_pct))
        p = _leer_peso(ir.peso_pct)
        if p[0] is None:
            if not _es_no_vigente(ir):
                _add(alertas, "ponderacion_faltante",
                     f"IR '{ir.codigo_ir}': vigente sin ponderación numérica.",
                     archivo=archivo, politica=politica, cod_obj=obj,
                     cod_ir=ir.codigo_ir, campo="peso_pct")
            p = (0.0, False)
        pesos_por_obj[obj].append(p)
        if ir.codigo_ir:
            peso_de_ir[ir.codigo_ir] = p
    peso_de_obj = {}
    for obj, candidatos in candidatos_obj.items():
        po = _leer_peso(elegir_peso_objetivo(candidatos))
        if po[0] is not None:
            peso_de_obj[obj] = po

    pesos_por_ir = defaultdict(list)
    for ip in ips:
        irk = ip.codigo_ir or "SIN_IR"
        p = _leer_peso(ip.peso_pct)
        if p[0] is None:
            if not _es_no_vigente(ip):
                _add(alertas, "ponderacion_faltante",
                     f"IP '{ip.codigo_ip}': vigente sin ponderación numérica.",
                     archivo=archivo, politica=politica, cod_ir=irk,
                     cod_ip=ip.codigo_ip, campo="peso_pct")
            p = (0.0, False)
        pesos_por_ir[irk].append(p)

    todos = (list(peso_de_obj.values())
             + [p for ps in pesos_por_obj.values() for p in ps]
             + [p for ps in pesos_por_ir.values() for p in ps])
    factor = _factor([v for v, pct in todos if not pct])

    def puntos(peso):
        v, pct = peso
        return v if pct else v * factor

    peso_de_obj = {k: puntos(p) for k, p in peso_de_obj.items()}
    peso_de_ir = {k: puntos(p) for k, p in peso_de_ir.items()}
    pesos_por_obj = {k: [puntos(p) for p in ps] for k, ps in pesos_por_obj.items()}
    pesos_por_ir = {k: [puntos(p) for p in ps] for k, ps in pesos_por_ir.items()}

    # V0
    if peso_de_obj:
        total = sum(peso_de_obj.values())
        if abs(total - 100.0) > tol:
            _add(alertas, "ponderacion_objetivos",
                 f"Los {len(peso_de_obj)} objetivo(s) suman {total:.2f}% (esperado 100%).",
                 archivo=archivo, politica=politica, campo="peso_objetivo",
                 valor=round(total, 2))
    # V1
    for obj, pesos in pesos_por_obj.items():
        total = sum(pesos)
        esperado = peso_de_obj.get(obj)
        if esperado is not None and abs(total - esperado) > tol:
            _add(alertas, "ponderacion_ir",
                 f"Pesos de IRs del OBJ '{obj}' suman {total:.2f}% pero el peso del objetivo es {esperado:.2f}%.",
                 archivo=archivo, politica=politica, cod_obj=obj, campo="peso_pct",
                 valor=round(total, 2))
    # V2
    for irk, pesos in pesos_por_ir.items():
        total = sum(pesos)
        esperado = peso_de_ir.get(irk)
        if esperado is not None and abs(total - esperado) > tol:
            _add(alertas, "ponderacion_ip",
                 f"Pesos de IPs del IR '{irk}' suman {total:.2f}% pero el peso del IR es {esperado:.2f}%.",
                 archivo=archivo, politica=politica, cod_ir=irk, campo="peso_pct",
                 valor=round(total, 2))


def _vigencia_ponderacion(inds, alertas, archivo, politica, tipo_label, cod_attr):
    """V18: No Vigente debe pesar 0; Vigente debe pesar > 0."""
    for ind in inds:
        cod = getattr(ind, cod_attr)
        peso = a_float(ind.peso_pct)
        if peso is None:
            continue
        no_vig = _es_no_vigente(ind)
        if no_vig and peso != 0:
            _add(alertas, "vigencia_ponderacion",
                 f"{tipo_label} '{cod}': No Vigente pero pondera {peso}% (debe ser 0%).",
                 archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                 cod_ip=getattr(ind, 'codigo_ip', None), campo="peso_pct", valor=peso)
        elif not no_vig and peso == 0:
            _add(alertas, "vigencia_ponderacion",
                 f"{tipo_label} '{cod}': Vigente pero pondera 0% (debe ser > 0%).",
                 archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                 cod_ip=getattr(ind, 'codigo_ip', None), campo="peso_pct", valor=peso)


def _tipologia(inds, alertas, archivo, politica, tipo_label, cod_attr):
    """V3 tipo de anualización + periodicidad."""
    for ind in inds:
        cod = getattr(ind, cod_attr)
        t = _norm(ind.tipo_anualizacion).upper()
        if t and t.lower() not in _NULOS and t not in TIPOS_ANUALIZACION_VALIDOS:
            _add(alertas, "tipo_anualizacion_invalido",
                 f"{tipo_label} '{cod}': tipo de anualización '{ind.tipo_anualizacion}' no reconocido.",
                 archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                 cod_ip=getattr(ind, 'codigo_ip', None), campo="tipo_anualizacion",
                 valor=ind.tipo_anualizacion)
        p = _norm(ind.periodicidad).upper()
        if p and p.lower() not in _NULOS and p not in PERIODICIDADES_VALIDAS:
            _add(alertas, "periodicidad_invalida",
                 f"{tipo_label} '{cod}': periodicidad '{ind.periodicidad}' fuera de catálogo.",
                 archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                 cod_ip=getattr(ind, 'codigo_ip', None), campo="periodicidad",
                 valor=ind.periodicidad)


def _fecha_como_texto(raw) -> bool:
    """La celda trae la fecha como texto («01/01/2024», «2024-01-01») en vez de
    una fecha de Excel. Un año suelto no cuenta: es una convención del plan."""
    return (isinstance(raw, str) and not _RE_ANIO.match(raw.strip())
            and fecha_de_valor(raw) is not None)


def _fechas(inds, alertas, archivo, politica, tipo_label, cod_attr):
    """V5: parseo y orden de fechas; fecha vacía y fecha escrita como texto (0.29.0)."""
    for ind in inds:
        cod = getattr(ind, cod_attr)
        fi_raw, ff_raw = ind.fecha_inicio, ind.fecha_fin
        fi = _parse_fecha(fi_raw) if not _vacio(fi_raw) else None
        ff = _parse_fecha(ff_raw) if not _vacio(ff_raw) else None
        for campo, raw, nombre in (("fecha_inicio", fi_raw, "inicio"), ("fecha_fin", ff_raw, "fin")):
            if _vacio(raw):
                _add(alertas, "PLAN_FECHA_VACIA",
                     f"{tipo_label} '{cod}': sin fecha de {nombre}; la exigencia de reporte "
                     f"y el fin efectivo no se pueden calcular.",
                     archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                     cod_ip=getattr(ind, 'codigo_ip', None), campo=campo)
            elif _fecha_como_texto(raw):
                _add(alertas, "PLAN_FECHA_COMO_TEXTO",
                     f"{tipo_label} '{cod}': la fecha de {nombre} está escrita como texto "
                     f"('{raw}'), no como fecha de Excel.",
                     archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                     cod_ip=getattr(ind, 'codigo_ip', None), campo=campo, valor=raw)
        if not _vacio(fi_raw) and fi is None:
            _add(alertas, "fecha_invalida",
                 f"{tipo_label} '{cod}': fecha de inicio no parseable ('{fi_raw}').",
                 archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                 cod_ip=getattr(ind, 'codigo_ip', None), campo="fecha_inicio", valor=fi_raw)
        if not _vacio(ff_raw) and ff is None:
            _add(alertas, "fecha_invalida",
                 f"{tipo_label} '{cod}': fecha de finalización no parseable ('{ff_raw}').",
                 archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                 cod_ip=getattr(ind, 'codigo_ip', None), campo="fecha_fin", valor=ff_raw)
        if fi and ff and fi > ff:
            _add(alertas, "fecha_inicio_mayor_fin",
                 f"{tipo_label} '{cod}': la fecha de inicio ({fi}) es posterior a la de fin ({ff}).",
                 archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                 cod_ip=getattr(ind, 'codigo_ip', None), campo="fecha_inicio", valor=str(fi))


def _metas_y_lb(inds, alertas, archivo, politica, tipo_label, cod_attr,
                tol_mf=TOLERANCIA_META_FINAL):
    """V6/V7 (meta no numérica), V8 (meta final), V9/V16 (línea base),
    V14 (meta vs LB), V15 (fuera de rango), V17 (metas vs meta final)."""
    for ind in inds:
        cod = getattr(ind, cod_attr)
        cir = getattr(ind, 'codigo_ir', None)
        cip = getattr(ind, 'codigo_ip', None)
        tipo = _norm(ind.tipo_anualizacion).upper()
        lb = a_float(ind.valor_linea_base)
        mf = a_float(ind.meta_final)
        metas = {int(a): a_float(v) for a, v in ind.metas_por_anio.items()
                 if a_float(v) is not None}

        # C5: escala mezclada — confusión de unidades ×100 (proporción 0-1 vs
        # porcentaje 0-100): metas con una fracción <1 y otra >1.5 cuyo cociente
        # es ≥50 (p. ej. 0.07 y 7.0). Conservador para no marcar conteos pequeños
        # legítimos como 1, 2, 3.
        frac = sorted(v for v in metas.values() if 0 < v < 1)
        altos = sorted(v for v in metas.values() if v > 1.5)
        if frac and altos and altos[-1] / frac[0] >= 50:
            _add(alertas, "escala_mezclada",
                 f"{tipo_label} '{cod}': metas mezclan escalas (fracción {frac[:3]} "
                 f"y valores {altos[:3]}; posible confusión 0-1 vs 0-100).",
                 archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip,
                 campo="metas_por_anio", valor=f"{frac[:3]} | {altos[:3]}")

        # V6/V7: meta anual no numérica (defensivo; el extractor ya filtra).
        for a, v in ind.metas_por_anio.items():
            if not _vacio(v) and a_float(v) is None:
                _add(alertas, "meta_no_numerica",
                     f"{tipo_label} '{cod}': meta_{a} no es numérica ('{v}').",
                     archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip,
                     campo=f"meta_{a}", valor=v)

        # V8: meta final faltante.
        if _vacio(ind.meta_final):
            _add(alertas, "meta_final_faltante",
                 f"{tipo_label} '{cod}': meta final no registrada.",
                 archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="meta_final")

        # V9: línea base.
        if _vacio(ind.valor_linea_base) and _vacio(ind.anio_linea_base):
            _add(alertas, "linea_base_faltante",
                 f"{tipo_label} '{cod}': línea base (valor y año) no registrada.",
                 archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip,
                 campo="valor_linea_base")
        elif not _vacio(ind.valor_linea_base) and lb is None:
            _add(alertas, "linea_base_no_numerica",
                 f"{tipo_label} '{cod}': valor de línea base no numérico ('{ind.valor_linea_base}').",
                 archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip,
                 campo="valor_linea_base", valor=ind.valor_linea_base)

        # V16: DECRECIENTE requiere línea base.
        if tipo == "DECRECIENTE" and lb is None:
            _add(alertas, "lb_obligatoria_decreciente",
                 f"{tipo_label} '{cod}': indicador DECRECIENTE sin línea base numérica.",
                 archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip,
                 campo="valor_linea_base")

        # V14: meta final vs línea base.
        if lb is not None and mf is not None and tipo in ("CRECIENTE", "DECRECIENTE"):
            if tipo == "CRECIENTE" and mf < lb:
                _add(alertas, "meta_vs_linea_base",
                     f"{tipo_label} '{cod}': CRECIENTE pero meta_final ({mf}) < línea base ({lb}).",
                     archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip,
                     campo="meta_final", valor=mf)
            elif tipo == "DECRECIENTE" and mf > lb:
                _add(alertas, "meta_vs_linea_base",
                     f"{tipo_label} '{cod}': DECRECIENTE pero meta_final ({mf}) > línea base ({lb}).",
                     archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip,
                     campo="meta_final", valor=mf)

        # V15, partida en dos (0.29.0): metas antes de la fecha de inicio (una
        # sola implementación: `metricas.metas_antes_de_inicio`, meta > 0) y
        # metas después de la fecha de fin (con meta programada).
        fi = _parse_fecha(ind.fecha_inicio)
        ff = _parse_fecha(ind.fecha_fin)
        if fi and metas:
            antes = metas_antes_de_inicio(ind.metas_por_anio, fi)
            if antes:
                _add(alertas, "meta_fuera_de_rango",
                     f"{tipo_label} '{cod}': metas anteriores a la fecha de inicio ({fi.year}): "
                     f"{', '.join(str(a) for a in antes)}. Esa meta cuenta en la meta acumulada.",
                     archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="metas",
                     valor=", ".join(str(a) for a in antes))
        if ff and metas:
            despues = sorted(a for a, v in metas.items()
                             if a > ff.year and hay_meta(v, tipo, mf))
            if despues:
                _add(alertas, "meta_fuera_de_rango",
                     f"{tipo_label} '{cod}': metas posteriores a la fecha de fin ({ff.year}): "
                     f"{', '.join(str(a) for a in despues)}.",
                     archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="metas",
                     valor=", ".join(str(a) for a in despues))

        # V12: brechas en metas.
        if fi and ff and metas:
            intervalo = INTERVALO_PERIODICIDAD.get(_norm(ind.periodicidad), 1)
            esperados = list(range(fi.year, ff.year + 1, intervalo))
            brechas = [str(y) for y in esperados if y not in metas]
            if brechas:
                _add(alertas, "brecha_en_metas",
                     f"{tipo_label} '{cod}': faltan metas en años esperados (cada {intervalo} año(s)): {', '.join(brechas)}.",
                     archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="metas")

        # V17: metas anuales vs meta final, en tres casos (0.29.0).
        if mf is not None and metas:
            if tipo == "SUMA":
                suma = sum(metas.values())
                if _difiere(suma, mf, tol_mf):
                    _add(alertas, "metas_vs_meta_final",
                         f"{tipo_label} '{cod}': SUMA — Σ metas ({suma:.2f}) ≠ meta_final ({mf:.2f}).",
                         archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="meta_final")
            elif tipo == "CONSTANTE":
                distintas = sorted(a for a, v in metas.items()
                                   if hay_meta(v, tipo, mf) and _difiere(v, mf, tol_mf))
                if distintas:
                    _add(alertas, "metas_vs_meta_final",
                         f"{tipo_label} '{cod}': CONSTANTE — metas distintas de la meta_final "
                         f"({mf:.2f}) en {', '.join(str(a) for a in distintas)}.",
                         archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="meta_final",
                         valor=", ".join(f"{a}: {metas[a]:g}" for a in distintas))
            elif tipo in ("CRECIENTE", "DECRECIENTE"):
                anios_ord = sorted(metas)
                ultima = next((metas[y] for y in reversed(anios_ord) if metas[y] != 0),
                              metas[anios_ord[-1]])
                if _difiere(ultima, mf, tol_mf):
                    _add(alertas, "metas_vs_meta_final",
                         f"{tipo_label} '{cod}': {tipo} — última meta ({ultima:.2f}) ≠ meta_final ({mf:.2f}).",
                         archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="meta_final")

        # Metas no monótonas (0.29.0): CRECIENTE que baja, DECRECIENTE que sube.
        if tipo in ("CRECIENTE", "DECRECIENTE") and metas:
            serie = [(a, v) for a, v in sorted(metas.items()) if hay_meta(v, tipo, mf)]
            quiebres = [f"{a0}→{a1} ({v0:g}→{v1:g})" for (a0, v0), (a1, v1) in zip(serie, serie[1:])
                        if (v1 < v0 if tipo == "CRECIENTE" else v1 > v0)]
            if quiebres:
                _add(alertas, "PLAN_METAS_NO_MONOTONAS",
                     f"{tipo_label} '{cod}': {tipo} con metas que "
                     f"{'bajan' if tipo == 'CRECIENTE' else 'suben'}: {'; '.join(quiebres)}.",
                     archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="metas",
                     valor="; ".join(quiebres))


def _vigencia_y_responsable(irs, ips, alertas, archivo, politica):
    """Vigencia vacía (IR e IP) y producto vigente sin entidad responsable (0.29.0)."""
    for inds, tipo_label, cod_attr in ((irs, "IR", "codigo_ir"), (ips, "IP", "codigo_ip")):
        for ind in inds:
            cod = getattr(ind, cod_attr)
            if _vacio(ind.es_vigente):
                _add(alertas, "PLAN_VIGENCIA_VACIA",
                     f"{tipo_label} '{cod}': la casilla Vigente/No Vigente está vacía; se "
                     f"asume vigente.",
                     archivo=archivo, politica=politica, cod_ir=getattr(ind, 'codigo_ir', None),
                     cod_ip=getattr(ind, 'codigo_ip', None), campo="es_vigente")
    for ip in ips:
        if not _es_no_vigente(ip) and _vacio(ip.entidad_responsable):
            _add(alertas, "PLAN_SIN_RESPONSABLE",
                 f"IP '{ip.codigo_ip}': producto vigente sin entidad responsable.",
                 archivo=archivo, politica=politica, cod_ir=ip.codigo_ir, cod_ip=ip.codigo_ip,
                 campo="entidad_responsable")


def _codigos_y_estructura(irs, ips, alertas, archivo, politica):
    """V13 (códigos malformados y mal escritos) y V11 (IR sin productos)."""
    for ir in irs:
        for texto, niveles, campo in ((ir.objetivo_especifico, 1, "objetivo"),
                                      (ir.resultado_esperado, 2, "resultado")):
            mal = codigo_mal_escrito(texto, niveles)
            if mal:
                _add(alertas, "PLAN_CODIGO_MAL_ESCRITO",
                     f"Código de {campo} mal escrito en la celda: '{mal}'.",
                     archivo=archivo, politica=politica, cod_obj=ir.codigo_objetivo,
                     cod_ir=ir.codigo_ir, campo=campo, valor=mal)
    for ip in ips:
        mal = codigo_mal_escrito(ip.producto_esperado, 3)
        if mal:
            _add(alertas, "PLAN_CODIGO_MAL_ESCRITO",
                 f"Código de producto mal escrito en la celda: '{mal}'.",
                 archivo=archivo, politica=politica, cod_ir=ip.codigo_ir, cod_ip=ip.codigo_ip,
                 campo="producto", valor=mal)
    for ir in irs:
        for code, rex, label in ((ir.codigo_objetivo, _RE_OBJ, "OBJ"),
                                  (ir.codigo_ir, _RE_IR, "IR")):
            if code and not rex.match(str(code)):
                _add(alertas, "codigo_malformado",
                     f"Código de {label} con formato inesperado: '{code}'.",
                     archivo=archivo, politica=politica, cod_ir=ir.codigo_ir,
                     campo="codigo", valor=code)
    for ip in ips:
        if ip.codigo_ip and not _RE_IP.match(str(ip.codigo_ip)):
            _add(alertas, "codigo_malformado",
                 f"Código de IP con formato inesperado: '{ip.codigo_ip}'.",
                 archivo=archivo, politica=politica, cod_ip=ip.codigo_ip,
                 campo="codigo", valor=ip.codigo_ip)

    # V11: IR vigente sin IPs.
    ir_con_ip = {ip.codigo_ir for ip in ips if ip.codigo_ir}
    for ir in irs:
        if ir.codigo_ir and ir.codigo_ir not in ir_con_ip and not _es_no_vigente(ir):
            _add(alertas, "ir_sin_productos",
                 f"IR '{ir.codigo_ir}': no tiene Indicadores de Producto asociados.",
                 archivo=archivo, politica=politica, cod_obj=ir.codigo_objetivo,
                 cod_ir=ir.codigo_ir)

    # B2: jerarquía IP→IR (el producto N.N.N debe colgar de un resultado N.N).
    ir_codes = {ir.codigo_ir for ir in irs if ir.codigo_ir}
    for ip in ips:
        c = ip.codigo_ip
        if c and str(c).count(".") >= 2:
            padre = str(c).rsplit(".", 1)[0]
            if padre not in ir_codes:
                _add(alertas, "jerarquia_ip",
                     f"IP '{c}': su resultado padre '{padre}' no existe entre los IR "
                     f"(jerarquía rota).",
                     archivo=archivo, politica=politica, cod_ir=padre, cod_ip=c,
                     campo="codigo_ir", valor=padre)


def _sector_entidad(irs, ips, alertas, archivo, politica, catalogo):
    """V4 (OPCIONAL): sector/entidad fuera del catálogo oficial. Solo se ejecuta
    si se inyecta `catalogo`. Si hay normalización difusa, sugiere la corrección."""
    if catalogo is None:
        return
    for inds, tipo_label, cir_attr, cip_attr in (
        (irs, "Resultado", "codigo_ir", None), (ips, "Producto", "codigo_ir", "codigo_ip")):
        for x in inds:
            cir = getattr(x, "codigo_ir", None)
            cip = getattr(x, cip_attr) if cip_attr else None
            cod = cip or cir
            for campo, valor, ok, sugerir, tipo in (
                ("sector_responsable", x.sector_responsable,
                 catalogo.es_sector_oficial, catalogo.sugerir_sector, "sector_no_oficial"),
                ("entidad_responsable", x.entidad_responsable,
                 catalogo.es_entidad_oficial, catalogo.sugerir_entidad, "entidad_no_oficial")):
                if valor and not ok(valor):
                    sug = sugerir(valor)
                    extra = f"; ¿quiso decir «{sug}»?" if sug else ""
                    _add(alertas, tipo,
                         f"{tipo_label} '{cod}': {campo} «{valor}» no está en el "
                         f"catálogo oficial{extra}.",
                         archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip,
                         campo=campo, valor=valor)


def validar_reglas(resultado, catalogo_oficial=None, *, tolerancia_peso_pp=None,
                   tolerancia_meta_final=None) -> list:
    """Ejecuta las reglas de negocio V0–V18 sobre el modelo canónico.

    `catalogo_oficial` (opcional): si se provee un `CatalogoOficial`, se evalúa
    además la regla **V4** (sector/entidad oficial). Por defecto V4 NO se ejecuta.
    `tolerancia_peso_pp` y `tolerancia_meta_final` (opcionales) sustituyen las
    tolerancias de la librería (ver ``extractor_pa.calidad.ParametrosCalidad``).
    Devuelve la lista de alertas (no modifica `resultado`)."""
    tol = TOLERANCIA_PESO_PP if tolerancia_peso_pp is None else tolerancia_peso_pp
    tol_mf = TOLERANCIA_META_FINAL if tolerancia_meta_final is None else tolerancia_meta_final
    irs = resultado.indicadores_resultado
    ips = resultado.indicadores_producto
    archivo = resultado.metadatos.archivo_fuente
    politica = resultado.metadatos.nombre_politica
    alertas = []

    _ponderacion(irs, ips, alertas, archivo, politica, tol)
    _vigencia_ponderacion(irs, alertas, archivo, politica, "IR", "codigo_ir")
    _vigencia_ponderacion(ips, alertas, archivo, politica, "IP", "codigo_ip")
    _tipologia(irs, alertas, archivo, politica, "IR", "codigo_ir")
    _tipologia(ips, alertas, archivo, politica, "IP", "codigo_ip")
    _fechas(irs, alertas, archivo, politica, "IR", "codigo_ir")
    _fechas(ips, alertas, archivo, politica, "IP", "codigo_ip")
    _metas_y_lb(irs, alertas, archivo, politica, "IR", "codigo_ir", tol_mf)
    _metas_y_lb(ips, alertas, archivo, politica, "IP", "codigo_ip", tol_mf)
    _vigencia_y_responsable(irs, ips, alertas, archivo, politica)
    _codigos_y_estructura(irs, ips, alertas, archivo, politica)
    _sector_entidad(irs, ips, alertas, archivo, politica, catalogo_oficial)

    # B2: objetivos (entidad) sin resultados/IR asociados.
    obj_con_ir = {ir.codigo_objetivo for ir in irs if ir.codigo_objetivo}
    for obj in getattr(resultado, "objetivos", []):
        if obj.codigo and obj.codigo not in obj_con_ir:
            _add(alertas, "objetivo_sin_resultados",
                 f"Objetivo '{obj.codigo}': no tiene Resultados/IR asociados.",
                 archivo=archivo, politica=politica, cod_obj=obj.codigo)
    return alertas
