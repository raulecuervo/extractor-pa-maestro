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

import unicodedata
from datetime import date, datetime, timedelta
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


def periodo_de_fecha(raw: Any) -> Optional[tuple]:
    """``(año, trimestre)`` de una fecha: serial de Excel, ``'YYYY-MM-DD'`` o
    ``datetime``/``date``. ``None`` si no se reconoce.

    El extractor maestro entrega las fechas como texto ISO; los archivos
    legados, como serial. Leer solo el serial dejaba sin fecha de inicio a
    todo lo cargado con el maestro."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, (datetime, date)):
        return raw.year, (raw.month - 1) // 3 + 1
    try:
        s = float(raw)
    except (TypeError, ValueError):
        s = None
    if s is not None:
        if s <= 0:
            return None
        if s.is_integer() and 1900 <= s <= 2100:
            return int(s), 1      # un año suelto, no un serial de 1905
        d = datetime(1899, 12, 30) + timedelta(days=s)
        return d.year, (d.month - 1) // 3 + 1
    txt = str(raw).strip()
    try:
        d = datetime.strptime(txt[:10], "%Y-%m-%d")
        return d.year, (d.month - 1) // 3 + 1
    except ValueError:
        pass
    if len(txt) >= 4 and txt[:4].isdigit():
        return int(txt[:4]), 1
    return None


def _tipo(tipo: Any) -> str:
    return (str(tipo) if tipo is not None else "").upper().strip()


def hay_meta(meta_anual: Any, tipo: Any = None, meta_final: Any = None) -> bool:
    """¿La meta anual de un año cuenta como programada?

    Vacía no cuenta, y 0 tampoco: los planes escriben 0 en los años que el
    indicador no programa (CTI 3.1.1 es CRECIENTE con 4 y 5 y luego 0, 0, 0;
    leer esos ceros como meta derrumbaría su trayectoria). La excepción es un
    DECRECIENTE cuya meta final es 0: busca llegar a cero, así que un 0 en
    sus metas anuales es una meta real."""
    v = safe_float(meta_anual)
    if v is None:
        return False
    if v != 0:
        return True
    return _tipo(tipo) == "DECRECIENTE" and safe_float(meta_final) == 0


# ─────────────────────────── periodicidad y corte ───────────────────────────

# Meses que abarca cada periodicidad de medición (hoja "Listas" del formato
# oficial de seguimiento).
MESES_POR_PERIODICIDAD = {
    "mensual": 1, "bimestral": 2, "trimestral": 3, "semestral": 6, "anual": 12,
    "bienal": 24, "trienal": 36, "cuatrienal": 48, "quinquenal": 60,
}


def _meses_periodicidad(periodicidad: Any) -> Optional[int]:
    p = unicodedata.normalize("NFKD", str(periodicidad or ""))
    p = p.encode("ascii", "ignore").decode().strip().lower()
    return MESES_POR_PERIODICIDAD.get(p)


def _trimestre_valido(trimestre: Any) -> int:
    try:
        t = int(trimestre)
    except (TypeError, ValueError):
        return 4          # sin trimestre: corte de cierre
    return min(max(t, 1), 4)


def trimestre_exigible(trimestre: Any, periodicidad: Any = None) -> int:
    """Último trimestre del año, hasta el corte, en que la periodicidad obliga
    a haber reportado. 0 = todavía no le toca reportar ese año.

    Mensual, bimestral y trimestral reportan en cada corte; semestral en Q2 y
    Q4; anual —y las plurianuales, cuyo reporte cae al cierre del año— solo en
    Q4. Sin periodicidad reconocible se toma el corte."""
    t = _trimestre_valido(trimestre)
    meses = _meses_periodicidad(periodicidad)
    if meses is None or meses <= 3:
        return t
    if meses < 12:
        return (3 * t // meses) * meses // 3
    return 4 if t == 4 else 0


def trimestre_efectivo(trimestre: Any, periodicidad: Any = None,
                       reportados=()) -> int:
    """Trimestre hasta el que se prorratea la meta del año del corte.

    Es el más reciente entre el último trimestre REPORTADO en el año (hasta el
    corte) y el último en que la periodicidad EXIGÍA reportar. Así:

    - un indicador anual sin reporte a junio se evalúa contra la meta
      acumulada al año anterior (todavía no le toca reportar);
    - si reportó antes de lo que exige su periodicidad, cuenta ese reporte;
    - si le tocaba reportar y no lo hizo, igual se le exige el prorrateo.

    Es la regla del formato oficial de seguimiento (columnas "Acumulada" de la
    tabla Metas_Productos), con la exigencia por periodicidad añadida."""
    t = _trimestre_valido(trimestre)
    ultimo = 0
    for q in reportados or ():
        try:
            q = int(q)
        except (TypeError, ValueError):
            continue
        if 1 <= q <= t and q > ultimo:
            ultimo = q
    return max(ultimo, trimestre_exigible(t, periodicidad))


def trimestres_reportados(segs, anio: int, hasta_trimestre: int = 4) -> set:
    """Trimestres de ``anio`` (hasta ``hasta_trimestre``) con un reporte real.

    Las filas sintéticas no son reportes: son puntos de corte que inventa la
    aplicación para el tablero."""
    out = set()
    for s in segs or ():
        if s.get("sintetico") or s.get("valor_avance") is None:
            continue
        try:
            y, q = int(s["anio"]), int(s["trimestre"])
        except (KeyError, TypeError, ValueError):
            continue
        if y == int(anio) and 1 <= q <= hasta_trimestre:
            out.add(q)
    return out


def sin_iniciar_al_corte(fecha_inicio: Any, periodicidad: Any, anio: int,
                         trimestre: int, reportado: bool = False) -> bool:
    """¿El indicador todavía no debe entrar en los cálculos del corte?

    No entra mientras no haya llegado su primer reporte exigible: arranca
    después del corte, o arrancó este año y su periodicidad aún no le pide
    reportar (un anual que inicia en enero no reporta hasta Q4). Un indicador
    que ya reportó siempre entra, aunque se haya adelantado."""
    if reportado:
        return False
    ini = periodo_de_fecha(fecha_inicio)
    if ini is None:
        return False
    anio_ini, q_ini = ini
    t = _trimestre_valido(trimestre)
    if (anio_ini, q_ini) > (int(anio), t):
        return True
    if anio_ini < int(anio):
        return False
    return trimestre_exigible(t, periodicidad) < q_ini


# ─────────────────────────── fórmulas §10.1–§10.4 ───────────────────────────

def calc_mes(trimestre: Any, periodicidad: Any = None, reportados=None) -> int:
    """Mes hasta el que se prorratea la meta del año: 3 × :func:`trimestre_efectivo`.

    Puede ser 0: un indicador al que todavía no le toca reportar ese año se
    evalúa contra lo acumulado al año anterior. Sin periodicidad devuelve el
    mes del corte (Q1→3 … Q4→12), el comportamiento de v0.12.

    ``reportados``: trimestres del año con reporte real (ver
    :func:`trimestres_reportados`)."""
    return 3 * trimestre_efectivo(trimestre, periodicidad, reportados or ())


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


def reportes_vigencia(segs, anio: int, hasta_trimestre: int = 4) -> list:
    """Valores reportados en ``anio`` hasta ``hasta_trimestre``, en orden.

    ``segs``: filas de seguimiento, una por período, con las claves ``anio,
    trimestre, valor_avance`` (y opcionalmente ``sintetico``). Las filas
    sintéticas no son reportes."""
    filas = sorted(
        (s for s in segs or ()
         if not s.get("sintetico") and s.get("anio") == anio
         and (s.get("trimestre") or 0) <= hasta_trimestre),
        key=lambda s: s.get("trimestre") or 0)
    return [v for s in filas if (v := safe_float(s.get("valor_avance"))) is not None]


def calc_pct_vigencia(tipo, mp, lb, reportes) -> Optional[float]:
    """PAV — % de avance en la vigencia, FRACCIÓN 0–1.

    Lo logrado en el año contra la meta del período (MP): la meta del año
    prorrateada hasta el corte según el tipo de anualización y la periodicidad
    (:func:`calc_meta_periodo`, :func:`trimestre_efectivo`). Es el cálculo de la
    columna «Porcentaje de Avance en la Vigencia» del Excel del SDP.

    SUMA: Σ reportes / MP · CONSTANTE: último reporte / MP ·
    CRECIENTE/DECRECIENTE: (último reporte − LB)/(MP − LB).

    ``reportes``: valores reportados en el año hasta el corte (ver
    :func:`reportes_vigencia`). Sin reportes en el año no hay PAV: no se
    arrastra el valor de otra vigencia. En SUMA solo cuenta lo del año; en los
    demás tipos el reporte es un nivel y sumarlo lo duplicaría."""
    vals = [v for v in (safe_float(r) for r in reportes or ()) if v is not None]
    mp = safe_float(mp)
    if not vals or mp is None:
        return None
    t = _tipo(tipo)
    if t in ("CRECIENTE", "DECRECIENTE"):
        base = safe_float(lb) or 0.0
        den = mp - base
        return None if den == 0 else (vals[-1] - base) / den
    if mp == 0:
        return None
    return (sum(vals) if t == "SUMA" else vals[-1]) / mp


# ─────────────────────────── fórmulas §10.5 ───────────────────────────

def _contra_meta_final(tipo, valor, meta_final, lb) -> Optional[float]:
    """``valor`` expresado contra la meta final (fracción 0–1).

    CRECIENTE/DECRECIENTE: (valor − LB)/(meta_final − LB) · CONSTANTE/SUMA:
    valor/meta_final. En los tipos con línea base el único denominador
    imposible es meta_final = LB: una meta final 0 es legítima en un
    DECRECIENTE que busca llegar a cero (LB 20 → meta 0)."""
    if meta_final is None or valor is None:
        return None
    if _tipo(tipo) in ("CRECIENTE", "DECRECIENTE"):
        den = meta_final - lb
        return None if den == 0 else (valor - lb) / den
    return None if meta_final == 0 else valor / meta_final


def calc_trayectoria_ideal(tipo, mp, ma, meta_final, lb) -> Optional[float]:
    """Trayectoria ideal vs meta final (fracción 0–1). Es la misma cantidad que
    :func:`calc_tid`: en los tipos de nivel MA = MP, y en SUMA la trayectoria es
    la meta acumulada. Se conserva la firma por compatibilidad; si no llega MA
    se usa MP."""
    return calc_tid(tipo, ma if ma is not None else mp, meta_final, lb)


def calc_paf(tipo, av_acum, meta_final, lb) -> Optional[float]:
    """PAF — % de avance acumulado vs meta final (§10.5, fracción 0–1).
    CRECIENTE/DECRECIENTE: (AV − LB)/(meta_final − LB) · CONSTANTE/SUMA: AV/meta_final."""
    return _contra_meta_final(tipo, av_acum, meta_final, lb)


def calc_tid(tipo, ma, meta_final, lb) -> Optional[float]:
    """TID — trayectoria ideal vs meta final (§10.5, fracción 0–1).
    CRECIENTE/DECRECIENTE: (MA − LB)/(meta_final − LB) · CONSTANTE/SUMA: MA/meta_final."""
    return _contra_meta_final(tipo, ma, meta_final, lb)


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

def suma_metas_anteriores_suma(segs_al_corte, segs_todos, anio: int,
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


# Nombre anterior, privado. Alertas y Seguimiento lo importa así
# (motor_calculo.py); se conserva para no romperlo. Usar el público.
_suma_metas_prev_suma = suma_metas_anteriores_suma


def avance_acumulado_suma(segs_al_corte, segs_todos, anio: int, trimestre: int) -> float:
    """AV de un indicador SUMA al corte (año, trimestre).

    El «Acumulado {año}» del archivo es el total de lo que el archivo trae de
    ese año. Sirve tal cual cuando el corte cubre todos los reportes del año;
    si el año tiene reportes posteriores al corte (un corte intermedio leído de
    un archivo que ya trae el año completo), el avance al corte es el acumulado
    al cierre del año anterior más lo reportado en el año hasta el trimestre
    del corte. DDHH 1.2.1 (Suma anual, reporta en Q4): a 2022 Q1 lleva 3.704,
    lo del cierre de 2021, no los 6.804 del cierre de 2022.

    Las filas sintéticas no cuentan: son puntos de corte que inventa la
    aplicación, y su «acumulado» no sale del archivo (en años sin reporte de
    Q4 guardaba solo lo del año: AFRO 1.3.10 quedaba en 0,111 con 0,191
    acumulado). Sin ningún acumulado explícito se suman los reportes."""
    reales = [s for s in segs_al_corte if not s.get("sintetico")]

    def _valor(s):
        return safe_float(s.get("valor_avance"))

    def _ultimo_acumulado(filas):
        return next(((s["anio"], safe_float(s["acumulado"])) for s in reversed(filas)
                     if safe_float(s.get("acumulado")) is not None), None)

    reporta_despues = any(
        not s.get("sintetico") and _valor(s) is not None
        and s["anio"] == anio and s["trimestre"] > trimestre
        for s in segs_todos or ())
    if not reporta_despues:
        del_anio = _ultimo_acumulado([s for s in reales if s["anio"] == anio])
        if del_anio is not None:
            return del_anio[1]

    base = _ultimo_acumulado([s for s in reales if s["anio"] < anio])
    desde, total = (base[0], base[1]) if base else (None, 0.0)
    for s in reales:
        v = _valor(s)
        if v is None or (desde is not None and s["anio"] <= desde):
            continue
        if s["anio"] < anio or s["trimestre"] <= trimestre:
            total += v
    return total


def avance_sin_reportes(tipo, lb) -> float:
    """AV de un indicador de nivel que no ha reportado nada hasta el corte.

    CRECIENTE/DECRECIENTE: la LB, el nivel del que parte. CONSTANTE: 0. Un
    CONSTANTE nunca se mide contra la LB: su meta es el nivel que debe
    sostener cada año, y la LB puede estar en otra escala. Tomarla como avance
    inflaba PHV = AV/MA y PAF = AV/MF (LB 382 y MA 0,2 sin reportes daban
    PHV = 1910, un 191.000 %). SUMA no pasa por aquí (ver
    :func:`avance_acumulado_suma`)."""
    return 0.0 if _tipo(tipo) == "CONSTANTE" else lb


def metricas_corte(tipo, periodicidad, lb, segs_al_corte, segs_todos,
                   anio: int, trimestre: int,
                   metas_plan: Optional[dict] = None,
                   fecha_inicio: Any = None) -> dict:
    """Núcleo de métricas de un indicador al corte (año, trimestre). Port de
    ``db._calc_metricas_indicador`` de Alertas-Seguimientos.

    ``segs_al_corte`` / ``segs_todos``: listas de dicts con las claves
    ``anio, trimestre, meta_anual, meta_final, acumulado, valor_avance``
    (y opcionalmente ``sintetico``), ordenadas por (anio, trimestre); la
    primera filtrada al período ≤ corte, la segunda con toda la historia.
    ``metas_plan``: metas por año del plan base (solo se usa en SUMA).

    La meta del año se prorratea hasta :func:`trimestre_efectivo`, que mira la
    periodicidad y los trimestres efectivamente reportados.

    Retorna dict con ``av_acum, meta_anual, meta_prev, meta_final, mp, ma,
    sum_metas_prev, pav, phv, tray, paf, tid, brecha, periodo_str,
    trimestre_efectivo, sin_iniciar`` — porcentajes en FRACCIÓN 0–1.
    ``sin_iniciar`` solo se evalúa si se pasa ``fecha_inicio``: el indicador
    aún no debe entrar en los cálculos del corte (ver
    :func:`sin_iniciar_al_corte`)."""
    t = _tipo(tipo)

    # meta_final: del seguimiento más reciente que la tenga (toda la historia)
    meta_final = next(
        (s["meta_final"] for s in reversed(segs_todos)
         if s.get("meta_final") is not None), None)

    def _programada(s):
        return hay_meta(s.get("meta_anual"), t, meta_final)

    # meta_anual: la del año seleccionado. Si el plan no programó ese año, el
    # indicador sostiene el nivel del último año anterior que sí tiene meta;
    # nunca se le exige la de un año posterior al corte (Mujer 10.1.9, sin
    # meta en 2022, quedaba contra la meta final de 2024 y con trayectoria del
    # 100 % en 2022). Para SUMA no hay respaldo: la meta anual es un
    # incremento, no un nivel.
    meta_anual = next(
        (s["meta_anual"] for s in segs_todos
         if s["anio"] == anio and _programada(s)), None)
    if meta_anual is None and t != "SUMA":
        meta_anual = next(
            (s["meta_anual"] for s in reversed(segs_todos)
             if s["anio"] < anio and _programada(s)), None)

    # meta_prev: meta anual del año anterior al seleccionado
    meta_prev = next(
        (s["meta_anual"] for s in reversed(segs_todos)
         if s["anio"] == anio - 1 and _programada(s)), None)

    # Sin meta en el año contiguo, MP se interpolaría desde 0 y marcaría como
    # sobre-ejecución a un indicador que solo sostiene su nivel. Se toma la
    # última meta conocida; si el indicador no tiene historia (primer reporte
    # de su vida), el piso depende del tipo:
    #   CONSTANTE             -> la meta ES el nivel: MP = MV, sin prorrateo.
    #   CRECIENTE/DECRECIENTE -> se parte de la línea base.
    # SUMA no usa meta_prev (su MP es MV × mes/12).
    if t != "SUMA" and meta_prev is None:
        meta_prev = next(
            (s["meta_anual"] for s in reversed(segs_todos)
             if s["anio"] < anio and _programada(s)), None)
        if meta_prev is None:
            meta_prev = meta_anual if t == "CONSTANTE" else lb

    # Antes de su primera meta programada el plan todavía no le exige avance:
    # el nivel exigido es el punto de partida (LB en CRECIENTE/DECRECIENTE, 0 en
    # CONSTANTE) y la trayectoria ideal queda en 0 %. Un indicador sin ninguna
    # meta anual en el plan sigue sin trayectoria: el plan está incompleto.
    nivel_inicial = None
    if t != "SUMA" and meta_anual is None:
        despues = any(s["anio"] > anio and _programada(s) for s in segs_todos) or any(
            str(k).isdigit() and int(k) > anio and hay_meta(v, t, meta_final)
            for k, v in (metas_plan or {}).items())
        if despues:
            nivel_inicial = lb if t in ("CRECIENTE", "DECRECIENTE") else 0.0
            meta_prev = nivel_inicial

    if t == "SUMA":
        sum_metas_prev = suma_metas_anteriores_suma(
            segs_al_corte, segs_todos, anio, metas_plan)
        av_acum = avance_acumulado_suma(segs_al_corte, segs_todos, anio, trimestre)
    else:
        sum_metas_prev = 0.0
        av_acum = next(
            (s["valor_avance"] for s in reversed(segs_al_corte)
             if s.get("valor_avance") is not None), avance_sin_reportes(t, lb))

    reportados = trimestres_reportados(segs_al_corte, anio, trimestre)
    q_ef = trimestre_efectivo(trimestre, periodicidad, reportados)
    mes = 3 * q_ef
    sin_iniciar = fecha_inicio is not None and sin_iniciar_al_corte(
        fecha_inicio, periodicidad, anio, trimestre,
        reportado=any(not s.get("sintetico") and s.get("valor_avance") is not None
                      for s in segs_al_corte))
    # SUMA sin meta anual en el año seleccionado: MP=0, MA=sum_metas_prev
    # (el indicador sigue participando con su acumulado y sus metas previas).
    meta_anual_mp = meta_anual if meta_anual is not None else (
        0.0 if t == "SUMA" else nivel_inicial)
    mp = calc_meta_periodo(t, meta_anual_mp, meta_prev, mes)
    ma = calc_meta_acum(t, mp, sum_metas_prev)
    phv = calc_pct_hasta_vig(t, av_acum, ma, lb)
    tray = calc_trayectoria_ideal(t, mp, ma, meta_final, lb)
    paf = calc_paf(t, av_acum, meta_final, lb)
    tid = calc_tid(t, ma, meta_final, lb)
    pav = calc_pct_vigencia(t, mp, lb, reportes_vigencia(segs_al_corte, anio, trimestre))

    return dict(
        av_acum=av_acum, meta_anual=meta_anual, meta_prev=meta_prev, meta_final=meta_final,
        mp=mp, ma=ma, sum_metas_prev=sum_metas_prev,
        pav=pav, phv=phv, tray=tray, paf=paf, tid=tid, brecha=calc_brecha(paf, tid),
        periodo_str=f"{anio} Q{trimestre}",
        trimestre_efectivo=q_ef, sin_iniciar=sin_iniciar,
    )
