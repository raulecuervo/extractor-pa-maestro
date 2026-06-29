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
from .utilidades import _norm, a_float

EPSILON = 0.5  # tolerancia de sumas de ponderación (en puntos porcentuales)

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


_EPOCH_EXCEL = _dt.date(1899, 12, 30)   # base de serie de fechas de Excel


def _parse_fecha(v) -> Optional[_dt.date]:
    """Parsea una fecha tolerando varios formatos reales de los planes:
    datetime/date, AÑO suelto (entero o '2019'), serial de Excel, 'YYYY-MM-DD',
    'DD/MM/YYYY', 'DD/MM/YY' (2 dígitos) y 'MM/DD/YYYY' (formato US).
    Devuelve None ante fechas genuinamente inválidas (p. ej. 31/06, 31/02) o
    basura — son hallazgos reales que deben quedar como `fecha_invalida`."""
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    if isinstance(v, (int, float)):
        y = int(v)
        # 1900..2100 → año suelto (p. ej. CTI usa 2019..2038 en columnas de fecha).
        if 1900 <= y <= 2100:
            return _dt.date(y, 1, 1)
        # Serial de Excel (rango ~2018..2060 ≈ 43000..58000).
        if 1 < y <= 80000:
            try:
                return _EPOCH_EXCEL + _dt.timedelta(days=y)
            except (OverflowError, ValueError):
                return None
        return None
    s = str(v or "").strip()
    if not s:
        return None
    # 'YYYY' (año suelto en texto).
    if re.fullmatch(r"(19|20)\d{2}", s):
        return _dt.date(int(s), 1, 1)
    # 'YYYY-MM-DD' (con o sin hora).
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            return _dt.date(int(s[:4]), int(s[5:7]), int(s[8:10]))
        except ValueError:
            return None
    # 'D/M/Y' con día/mes de 1-2 dígitos y año de 2 o 4 dígitos.
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2}|\d{4})$", s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:                      # año de 2 dígitos → 2000+
            y += 2000
        for d, mo in ((a, b), (b, a)):   # DD/MM primero; si falla, MM/DD (US)
            try:
                return _dt.date(y, mo, d)
            except ValueError:
                continue
    return None


def _add(alertas, tipo, desc, ind=None, *, archivo="", politica="", campo=None, valor=None,
         cod_obj=None, cod_ir=None, cod_ip=None):
    alertas.append(crear_alerta(
        tipo, desc, archivo_fuente=archivo, nombre_politica=politica,
        codigo_objetivo=cod_obj, codigo_ir=cod_ir, codigo_ip=cod_ip,
        campo=campo, valor=valor))


# ─────────────────────────── reglas ─────────────────────────────

def _ponderacion(irs, ips, alertas, archivo, politica):
    """V0/V1/V2 (sumas de pesos) + ponderación faltante."""
    # Peso del objetivo (primer valor no nulo por objetivo) y peso del IR.
    peso_de_obj, peso_de_ir = {}, {}
    pesos_por_obj = defaultdict(list)
    for ir in irs:
        obj = ir.codigo_objetivo or "SIN_OBJ"
        po = a_float(ir.peso_objetivo_pct)
        if obj not in peso_de_obj and po is not None:
            peso_de_obj[obj] = po
        p = a_float(ir.peso_pct)
        if p is None:
            if not _es_no_vigente(ir):
                _add(alertas, "ponderacion_faltante",
                     f"IR '{ir.codigo_ir}': vigente sin ponderación numérica.",
                     archivo=archivo, politica=politica, cod_obj=obj,
                     cod_ir=ir.codigo_ir, campo="peso_pct")
            p = 0.0
        pesos_por_obj[obj].append(p)
        if ir.codigo_ir:
            peso_de_ir[ir.codigo_ir] = p

    pesos_por_ir = defaultdict(list)
    for ip in ips:
        irk = ip.codigo_ir or "SIN_IR"
        p = a_float(ip.peso_pct)
        if p is None:
            if not _es_no_vigente(ip):
                _add(alertas, "ponderacion_faltante",
                     f"IP '{ip.codigo_ip}': vigente sin ponderación numérica.",
                     archivo=archivo, politica=politica, cod_ir=irk,
                     cod_ip=ip.codigo_ip, campo="peso_pct")
            p = 0.0
        pesos_por_ir[irk].append(p)

    factor = _factor(list(peso_de_obj.values())
                     + [p for ps in pesos_por_obj.values() for p in ps]
                     + [p for ps in pesos_por_ir.values() for p in ps])

    # V0
    if peso_de_obj:
        total = sum(peso_de_obj.values()) * factor
        if abs(total - 100.0) > EPSILON:
            _add(alertas, "ponderacion_objetivos",
                 f"Los {len(peso_de_obj)} objetivo(s) suman {total:.2f}% (esperado 100%).",
                 archivo=archivo, politica=politica, campo="peso_objetivo",
                 valor=round(total, 2))
    # V1
    for obj, pesos in pesos_por_obj.items():
        total = sum(pesos) * factor
        esperado = (peso_de_obj.get(obj) or 0) * factor
        if peso_de_obj.get(obj) is not None and abs(total - esperado) > EPSILON:
            _add(alertas, "ponderacion_ir",
                 f"Pesos de IRs del OBJ '{obj}' suman {total:.2f}% pero el peso del objetivo es {esperado:.2f}%.",
                 archivo=archivo, politica=politica, cod_obj=obj, campo="peso_pct",
                 valor=round(total, 2))
    # V2
    for irk, pesos in pesos_por_ir.items():
        total = sum(pesos) * factor
        p_ir = peso_de_ir.get(irk)
        if p_ir is not None:
            esperado = p_ir * factor
            if abs(total - esperado) > EPSILON:
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


def _fechas(inds, alertas, archivo, politica, tipo_label, cod_attr):
    """V5: parseo y orden de fechas."""
    for ind in inds:
        cod = getattr(ind, cod_attr)
        fi_raw, ff_raw = ind.fecha_inicio, ind.fecha_fin
        fi = _parse_fecha(fi_raw) if not _vacio(fi_raw) else None
        ff = _parse_fecha(ff_raw) if not _vacio(ff_raw) else None
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


def _metas_y_lb(inds, alertas, archivo, politica, tipo_label, cod_attr):
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

        # V15: metas fuera del rango de vigencia.
        fi = _parse_fecha(ind.fecha_inicio)
        ff = _parse_fecha(ind.fecha_fin)
        if fi and ff and metas:
            fuera = sorted(str(a) for a in metas if a < fi.year or a > ff.year)
            if fuera:
                _add(alertas, "meta_fuera_de_rango",
                     f"{tipo_label} '{cod}': metas fuera del rango de vigencia ({fi.year}-{ff.year}): {', '.join(fuera)}.",
                     archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="metas")

        # V12: brechas en metas.
        if fi and ff and metas:
            intervalo = INTERVALO_PERIODICIDAD.get(_norm(ind.periodicidad), 1)
            esperados = list(range(fi.year, ff.year + 1, intervalo))
            brechas = [str(y) for y in esperados if y not in metas]
            if brechas:
                _add(alertas, "brecha_en_metas",
                     f"{tipo_label} '{cod}': faltan metas en años esperados (cada {intervalo} año(s)): {', '.join(brechas)}.",
                     archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="metas")

        # V17: metas anuales vs meta final.
        if mf is not None and metas:
            if tipo == "SUMA":
                suma = sum(metas.values())
                if abs(suma - mf) > EPSILON:
                    _add(alertas, "metas_vs_meta_final",
                         f"{tipo_label} '{cod}': SUMA — Σ metas ({suma:.2f}) ≠ meta_final ({mf:.2f}).",
                         archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="meta_final")
            elif tipo in ("CONSTANTE", "CRECIENTE", "DECRECIENTE"):
                anios_ord = sorted(metas)
                ultima = next((metas[y] for y in reversed(anios_ord) if metas[y] != 0),
                              metas[anios_ord[-1]])
                if abs(ultima - mf) > EPSILON:
                    _add(alertas, "metas_vs_meta_final",
                         f"{tipo_label} '{cod}': {tipo} — última meta ({ultima:.2f}) ≠ meta_final ({mf:.2f}).",
                         archivo=archivo, politica=politica, cod_ir=cir, cod_ip=cip, campo="meta_final")


def _codigos_y_estructura(irs, ips, alertas, archivo, politica):
    """V13 (códigos malformados) y V11 (IR sin productos)."""
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


def validar_reglas(resultado, catalogo_oficial=None) -> list:
    """Ejecuta las reglas de negocio V0–V18 sobre el modelo canónico.

    `catalogo_oficial` (opcional): si se provee un `CatalogoOficial`, se evalúa
    además la regla **V4** (sector/entidad oficial). Por defecto V4 NO se ejecuta.
    Devuelve la lista de alertas (no modifica `resultado`)."""
    irs = resultado.indicadores_resultado
    ips = resultado.indicadores_producto
    archivo = resultado.metadatos.archivo_fuente
    politica = resultado.metadatos.nombre_politica
    alertas = []

    _ponderacion(irs, ips, alertas, archivo, politica)
    _vigencia_ponderacion(irs, alertas, archivo, politica, "IR", "codigo_ir")
    _vigencia_ponderacion(ips, alertas, archivo, politica, "IP", "codigo_ip")
    _tipologia(irs, alertas, archivo, politica, "IR", "codigo_ir")
    _tipologia(ips, alertas, archivo, politica, "IP", "codigo_ip")
    _fechas(irs, alertas, archivo, politica, "IR", "codigo_ir")
    _fechas(ips, alertas, archivo, politica, "IP", "codigo_ip")
    _metas_y_lb(irs, alertas, archivo, politica, "IR", "codigo_ir")
    _metas_y_lb(ips, alertas, archivo, politica, "IP", "codigo_ip")
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
