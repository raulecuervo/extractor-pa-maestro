# -*- coding: utf-8 -*-
"""
Capa 2 de la convergencia (MS-32a): fórmulas de `metricas.py` contra los casos
documentados (FORMULAS.md de Alertas / CONTEXTO §10 de SISPP) y semántica de
PRODUCCIÓN de `validacion_seg` v2 (las divergencias corregidas del port v1).
"""
import pytest

from extractor_pa.seguimiento import (
    IndicadorSeguimiento,
    MetadatosSeguimiento,
    ResultadoSeguimiento,
    HallazgoSeguimiento,
    anio_de_serial_excel,
    calc_brecha,
    calc_lb_ficticia_decreciente,
    calc_meta_acum,
    calc_meta_periodo,
    calc_mes,
    calc_paf,
    calc_pct_hasta_vig,
    calc_sum_metas_prev,
    calc_tid,
    calc_trayectoria_ideal,
    crear_hallazgo,
    indicador_desde_dict,
    lb_de_indicador,
    metricas_corte,
    validar_archivo,
    validar_consistencia,
)
from extractor_pa.seguimiento.metricas import parse_lb, safe_float


# ─────────────────────────── helpers de fixtures ───────────────────────────

def _res(*inds, archivo="nuevo.xlsb", politica="PP Demo"):
    return ResultadoSeguimiento(
        MetadatosSeguimiento(archivo_fuente=archivo, nombre_politica=politica),
        indicadores=list(inds))


def _ind(**kw):
    base = dict(codigo="1.1.1", nombre="Indicador demo", sector="Sector X",
                entidad="Entidad Y", estado="Vigente", corte="Q2",
                anio_reporte=2026, tipo_anualizacion="Suma",
                periodicidad="Trimestral")
    base.update(kw)
    return IndicadorSeguimiento(**base)


def _tipos(alertas):
    return [a.tipo for a in alertas]


# ─────────────────────────── conversión numérica ───────────────────────────

def test_safe_float_estricto_como_produccion():
    assert safe_float(1.5) == 1.5
    assert safe_float("2.5") == 2.5
    assert safe_float("1,5") is None      # producción NO tolera coma decimal
    assert safe_float("50%") is None      # ni sufijo %
    assert safe_float(None) is None


def test_parse_lb_y_serial_excel():
    assert parse_lb("12,5") == 12.5
    assert parse_lb("") == 0.0
    assert parse_lb("N/A") == 0.0
    assert anio_de_serial_excel(45658) == 2025      # 2025-01-01
    assert anio_de_serial_excel("no-fecha") is None
    assert anio_de_serial_excel(0) is None


# ─────────────────────────── fórmulas §10.1–§10.4 ───────────────────────────

def test_ejemplo_verificado_contexto_10_6():
    """SUMA, meta 2026=50.000, metas previas Σ=150.000, corte junio (Q2)."""
    mes = calc_mes(2, "Trimestral")
    assert mes == 6
    mp = calc_meta_periodo("SUMA", 50000, None, mes)
    assert mp == 25000
    ma = calc_meta_acum("SUMA", mp, 150000)
    assert ma == 175000
    phv = calc_pct_hasta_vig("SUMA", 25000, ma, 0)
    assert phv == pytest.approx(25000 / 175000)      # ≈ 0.1428 (FRACCIÓN 0–1)
    assert round(phv * 100, 1) == 14.3               # §10.6: 14,3 % en el borde


def test_meta_periodo_interpolada_no_suma():
    # (MV − MV_año_anterior) × mes/12 + MV_año_anterior
    assert calc_meta_periodo("CRECIENTE", 100, 40, 6) == pytest.approx(70)
    # sin meta del año anterior: MV × mes/12
    assert calc_meta_periodo("CONSTANTE", 100, None, 6) == pytest.approx(50)
    assert calc_meta_periodo("SUMA", 100, 40, 6) == pytest.approx(50)


def test_calc_mes_por_periodicidad():
    assert calc_mes(2, "Anual") == 12
    assert calc_mes(2, "Semestral") == 12
    assert calc_mes(1, "Semestral") == 6
    assert calc_mes(3, "Trimestral") == 9


def test_phv_con_linea_base():
    # CRECIENTE: LB=50, MA=100, AV=87.5 → (87.5−50)/(100−50) = 0.75
    assert calc_pct_hasta_vig("CRECIENTE", 87.5, 100, 50) == pytest.approx(0.75)
    # DECRECIENTE que baja hacia la meta produce PHV creciente
    assert calc_pct_hasta_vig("DECRECIENTE", 70, 40, 100) == pytest.approx(0.5)
    # denominador 0 → None
    assert calc_pct_hasta_vig("CRECIENTE", 10, 50, 50) is None
    assert calc_pct_hasta_vig("SUMA", 10, 0, 0) is None


def test_sum_metas_prev_con_anio_min():
    metas = {"2019": 10, "2020": 20, "2025": 99}
    assert calc_sum_metas_prev(metas, 2021) == 30
    assert calc_sum_metas_prev(metas, 2021, anio_min=2020) == 20
    assert calc_sum_metas_prev({}, 2021) == 0.0


# ─────────────────────────── fórmulas §10.5 ───────────────────────────

def test_paf_tid_brecha():
    # CRECIENTE: LB=0, meta_final=200
    paf = calc_paf("CRECIENTE", 80, 200, 0)
    tid = calc_tid("CRECIENTE", 100, 200, 0)
    assert paf == pytest.approx(0.4)
    assert tid == pytest.approx(0.5)
    assert calc_brecha(paf, tid) == pytest.approx(-0.1)   # rezago
    # DECRECIENTE: LB=100, meta_final=40, AV=70 → (70−100)/(40−100)=0.5
    assert calc_paf("DECRECIENTE", 70, 40, 100) == pytest.approx(0.5)
    # meta_final None/0 → None
    assert calc_paf("SUMA", 10, None, 0) is None
    assert calc_tid("SUMA", 10, 0, 0) is None
    assert calc_brecha(None, 0.5) is None


def test_trayectoria_ideal():
    assert calc_trayectoria_ideal("CRECIENTE", 70, None, 200, 0) == pytest.approx(0.35)
    # CONSTANTE/SUMA usa MA (o MP si MA es None)
    assert calc_trayectoria_ideal("SUMA", 25, 175, 500, 0) == pytest.approx(0.35)
    assert calc_trayectoria_ideal("SUMA", 25, None, 500, 0) == pytest.approx(0.05)


# ─────────────────────────── LB ficticia (RN-CUA-009) ───────────────────────────

def test_lb_ficticia_decreciente():
    metas = {"2020": 100, "2021": 80, "2022": 60}
    # (MetaInicial − MetaFinal)/(AñoFinal − AñoInicial + 1) + MetaInicial
    assert calc_lb_ficticia_decreciente(metas, 40) == pytest.approx((100 - 40) / 3 + 100)
    # sin meta_final explícita usa la última meta anual (60)
    assert calc_lb_ficticia_decreciente(metas) == pytest.approx((100 - 60) / 3 + 100)
    # anio_fin explícito manda sobre el último año con meta
    assert calc_lb_ficticia_decreciente(metas, 40, anio_fin=2025) == pytest.approx((100 - 40) / 6 + 100)
    assert calc_lb_ficticia_decreciente({}, 40) is None
    assert calc_lb_ficticia_decreciente({"final": 40}, None) is None


def test_lb_de_indicador():
    # LB explícita gana siempre (con coma decimal)
    assert lb_de_indicador("12,5", "DECRECIENTE") == 12.5
    # DECRECIENTE sin LB → ficticia
    metas = {"2020": 100, "2021": 80, "2022": 60}
    assert lb_de_indicador(None, "Decreciente", metas, 40) == pytest.approx(120.0)
    # otros tipos sin LB → 0.0
    assert lb_de_indicador("", "CRECIENTE", metas, 40) == 0.0
    # DECRECIENTE sin LB y sin metas → 0.0
    assert lb_de_indicador(None, "DECRECIENTE", {}, None) == 0.0


# ─────────────────────────── núcleo al corte ───────────────────────────

def test_metricas_corte_suma():
    """Réplica del flujo de _calc_metricas_indicador para SUMA con acumulado."""
    segs = [
        dict(anio=2025, trimestre=4, meta_anual=150000, meta_final=500000,
             acumulado=150000, valor_avance=40000),
        dict(anio=2026, trimestre=1, meta_anual=50000, meta_final=500000,
             acumulado=160000, valor_avance=10000),
        dict(anio=2026, trimestre=2, meta_anual=50000, meta_final=500000,
             acumulado=175000, valor_avance=15000),
    ]
    m = metricas_corte("SUMA", "Trimestral", 0.0, segs, segs, 2026, 2)
    assert m["meta_anual"] == 50000
    assert m["mp"] == pytest.approx(25000)
    assert m["ma"] == pytest.approx(175000)          # 150000 + 25000
    assert m["av_acum"] == 175000                    # acumulado explícito al corte
    assert m["phv"] == pytest.approx(1.0)
    assert m["paf"] == pytest.approx(175000 / 500000)
    assert m["tid"] == pytest.approx(175000 / 500000)
    assert m["brecha"] == pytest.approx(0.0)
    assert m["periodo_str"] == "2026 Q2"


def test_metricas_corte_suma_sin_acumulado_reconstruye():
    segs = [
        dict(anio=2025, trimestre=4, meta_anual=100, meta_final=400,
             acumulado=100, valor_avance=30),
        dict(anio=2026, trimestre=1, meta_anual=100, meta_final=400,
             acumulado=None, valor_avance=10),
        dict(anio=2026, trimestre=2, meta_anual=100, meta_final=400,
             acumulado=None, valor_avance=20),
    ]
    m = metricas_corte("SUMA", "Trimestral", 0.0, segs, segs, 2026, 2)
    # producción prioriza el acumulado explícito más reciente ≤ corte (2025 → 100)
    assert m["av_acum"] == pytest.approx(100)
    segs_sin_acum = [dict(s, acumulado=None) for s in segs]
    m2 = metricas_corte("SUMA", "Trimestral", 0.0, segs_sin_acum, segs_sin_acum, 2026, 2)
    # sin ningún acumulado: acum año previo (0) + reportes de la vigencia
    assert m2["av_acum"] == pytest.approx(30)


def test_metricas_corte_creciente_con_lb():
    segs = [
        dict(anio=2026, trimestre=2, meta_anual=100, meta_final=200,
             acumulado=None, valor_avance=87.5),
    ]
    m = metricas_corte("Creciente", "Trimestral", 50.0, segs, segs, 2026, 2)
    # MP interpola sin meta previa: 100×6/12=50 → MA=MP=50 → PHV=(87.5−50)/(50−50)=None
    assert m["ma"] == pytest.approx(50)
    assert m["phv"] is None
    assert m["paf"] == pytest.approx((87.5 - 50) / (200 - 50))
    assert m["tid"] == pytest.approx((50 - 50) / (200 - 50))


# ─────────────────────────── hallazgos: shape make_finding ───────────────────────────

def test_crear_hallazgo_shape_exacto_make_finding():
    h = crear_hallazgo(
        "ERROR_RETROACTIVO", codigo="1.1.1", politica="PP Demo",
        sector="Sector X", entidad="Entidad Y", nombre="N" * 200,
        campo="Avance 2024 Q4", val_base=0.2, val_nuevo="X" * 300,
        periodo="2024 Q4", detalle="cambió", archivo="nuevo.xlsb")
    f = h.as_finding()
    assert f == {
        "tipo": "ERROR_RETROACTIVO",
        "severidad": "Error",
        "descripcion": "Error – Valor histórico modificado",
        "codigo": "1.1.1",
        "politica": "PP Demo",
        "sector": "Sector X",
        "entidad": "Entidad Y",
        "nombre": "N" * 120,          # truncado [:120] de make_finding
        "campo": "Avance 2024 Q4",
        "val_base": "0.2",            # str() como make_finding
        "val_nuevo": "X" * 200,       # truncado [:200]
        "periodo": "2024 Q4",
        "detalle": "cambió",
        "file_nuevo": "nuevo.xlsb",
    }
    # compatibilidad con la Alerta v1
    assert h.nivel == "ERROR"
    assert h.codigo_ip == "1.1.1"
    assert h.valor == "0.2 | " + "X" * 200


# ─────────────────────────── validaciones: semántica de producción ───────────────────────────

def test_avance_meta_sin_meta_omite_todo_el_chequeo():
    """Divergencia (a) corregida: meta None/0 → early-return, NI pct_vigencia."""
    ind = _ind(metas={}, pct_vigencia={"2026": 1.5},
               avances={"2026_Q1": 10, "2026_Q2": 20})
    alertas = validar_archivo(_res(ind))
    assert "ADVERTENCIA_AVANCE" not in _tipos(alertas)
    assert "ADVERTENCIA_LIMITE_VIG" not in _tipos(alertas)
    # con meta sí se evalúa
    ind2 = _ind(metas={"2026": 10}, pct_vigencia={"2026": 1.5},
                avances={"2026_Q1": 3, "2026_Q2": 4})
    assert "ADVERTENCIA_AVANCE" in _tipos(validar_archivo(_res(ind2)))


def test_retroactividad_salta_base_vacia():
    """Divergencia (b) corregida: base vacía no alerta; base 0 SÍ alerta."""
    base = _res(_ind(anio_reporte=2025, corte="Q4",
                     avances={"2025_Q1": "", "2025_Q2": None, "2025_Q3": 0, "2025_Q4": 5},
                     acumulados={"2025": ""}),
                archivo="base.xlsb")
    nuevo = _res(_ind(anio_reporte=2026, corte="Q1",
                      avances={"2025_Q1": 9, "2025_Q2": 9, "2025_Q3": 7, "2025_Q4": 5},
                      acumulados={"2025": 30}))
    retro = [a for a in validar_consistencia(base, nuevo) if a.tipo == "ERROR_RETROACTIVO"]
    # solo Q3 (0→7): los vacíos ""/None no alertan; Q4 no cambió; acumulado "" tampoco
    assert len(retro) == 1
    assert retro[0].campo == "Avance 2025 Q3"
    assert retro[0].val_base == "0"
    assert retro[0].val_nuevo == "7"


def test_estabilidad_conserva_tildes_y_compara_upper():
    """Divergencia (d): producción conserva tildes → 'Educación' ≠ 'Educacion'."""
    base = _res(_ind(sector="Educación"), archivo="base.xlsb")
    nuevo = _res(_ind(sector="EDUCACION"))
    tipos = _tipos(validar_consistencia(base, nuevo))
    assert "ERROR_ESTABILIDAD" in tipos
    # solo cambia mayúsculas/espacios → NO alerta
    base2 = _res(_ind(sector="Educación  Distrital"), archivo="base.xlsb")
    nuevo2 = _res(_ind(sector="EDUCACIÓN DISTRITAL"))
    assert "ERROR_ESTABILIDAD" not in _tipos(validar_consistencia(base2, nuevo2))


def test_estabilidad_etiquetas_de_produccion():
    base = _res(_ind(ponderacion="10", linea_base="5"), archivo="base.xlsb")
    nuevo = _res(_ind(ponderacion="20", linea_base="7"))
    campos = {a.campo for a in validar_consistencia(base, nuevo)
              if a.tipo == "ERROR_ESTABILIDAD"}
    assert campos == {"Ponderación (%)", "Valor Línea Base"}


def test_no_numerico_estricto():
    """Divergencia (e): '1,5' NO es numérico para producción."""
    ind = _ind(avances={"2026_Q1": "1,5", "2026_Q2": "2.5"})
    alertas = [a for a in validar_archivo(_res(ind)) if a.tipo == "ERROR_NO_NUMERICO"]
    assert len(alertas) == 1
    assert alertas[0].campo == "Avance 2026 Q1"
    assert alertas[0].detalle.startswith("El valor '1,5' no es numérico")


def test_acumulado_usa_fecha_inicio_para_anio_de_arranque():
    """Divergencia (c): el año de inicio sale de fecha_inicio, no de min(metas)."""
    # metas desde 2019, pero fecha_inicio 2025 → solo suma metas 2025-2026 (=20)
    ind = _ind(fecha_inicio="2025-01-01", corte="Q2", anio_reporte=2026,
               acumulados={"2026": 25},
               metas={"2019": 100, "2025": 10, "2026": 10},
               avances={"2026_Q1": 5})
    tipos = _tipos(validar_archivo(_res(ind)))
    assert "ADVERTENCIA_ACUM_META_VIG" in tipos       # 25 > 20
    # sin fecha_inicio: fallback a anio_min=2018 → suma 120 → no alerta
    ind2 = _ind(fecha_inicio=None, corte="Q2", anio_reporte=2026,
                acumulados={"2026": 25},
                metas={"2019": 100, "2025": 10, "2026": 10},
                avances={"2026_Q1": 5})
    assert "ADVERTENCIA_ACUM_META_VIG" not in _tipos(validar_archivo(_res(ind2)))


def test_acumulado_supera_meta_final():
    ind = _ind(corte="Q2", anio_reporte=2026, meta_final=20,
               acumulados={"2026": 25}, metas={"2026": 30},
               avances={"2026_Q1": 25})
    assert "ADVERTENCIA_ACUM_META_FIN" in _tipos(validar_archivo(_res(ind)))


def test_pct_hasta_vig_fuera_de_rango_y_etiqueta():
    ind = _ind(metas={"2026": 100}, pct_vigencia={"2026": 0.30},
               avances={"2026_Q1": 30}, acumulados={"2026": 30})
    bajos = [a for a in validar_archivo(_res(ind))
             if a.tipo == "ADVERTENCIA_PCT_HASTA_VIG"]
    assert len(bajos) == 1
    assert bajos[0].campo == "% Avance Hasta Vigencia 2026"   # etiqueta de producción
    assert "inferior al 50%" in bajos[0].detalle


def test_cualitativo_solo_vigentes_y_periodicidad():
    ind = _ind(estado="Vigente", periodicidad="Trimestral", corte="Q2",
               cualitativos={"2026_Q1": "texto"})       # falta Q2
    cual = [a for a in validar_archivo(_res(ind)) if a.tipo == "ADVERTENCIA_CUAL"]
    assert [c.campo for c in cual] == ["Cualitativo 2026 Q2"]
    # no vigente → nada
    ind2 = _ind(estado="No vigente", cualitativos={})
    assert "ADVERTENCIA_CUAL" not in _tipos(validar_archivo(_res(ind2)))
    # semestral: solo el trimestre de corte
    ind3 = _ind(periodicidad="Semestral", corte="Q2", cualitativos={})
    cual3 = [a for a in validar_archivo(_res(ind3)) if a.tipo == "ADVERTENCIA_CUAL"]
    assert [c.campo for c in cual3] == ["Cualitativo 2026 Q2"]


def test_discrepancia_pct():
    ind = _ind(metas={"2026": 100}, acumulados={"2026": 50},
               pct_vigencia={"2026": 0.60}, avances={"2026_Q1": 50})
    disc = [a for a in validar_archivo(_res(ind))
            if a.tipo == "ADVERTENCIA_DISCREPANCIA_PCT"]
    assert len(disc) == 1
    assert disc[0].val_base.startswith("Calculado=0.500")
    assert disc[0].val_nuevo == "Reportado=0.600"


def test_info_nuevo_faltante_textos_de_produccion():
    base = _res(_ind(codigo="9.9.9"), archivo="base.xlsb")
    nuevo = _res(_ind(codigo="8.8.8"))
    alertas = validar_consistencia(base, nuevo)
    nuevos = [a for a in alertas if a.tipo == "INFO_IND_NUEVO"]
    faltan = [a for a in alertas if a.tipo == "INFO_IND_FALTANTE"]
    assert len(nuevos) == 1 and len(faltan) == 1
    assert nuevos[0].detalle.startswith("Indicador 8.8.8 presente en este archivo")
    assert "recargue el archivo base" in nuevos[0].detalle
    assert faltan[0].detalle == "Presente en la base, ausente en el nuevo archivo"
    # la política del finding sale de los metadatos del archivo nuevo
    assert nuevos[0].politica == "PP Demo"
    assert nuevos[0].archivo == "nuevo.xlsb"


def test_indicador_desde_dict_mapea_claves_de_alertas():
    d = {
        "codigo": "1.1", "file": "x.xlsb", "corte": "Q2", "anio_reporte": 2026,
        "estado": "Vigente", "tipo_anual": "Decreciente",
        "periodicidad": "Trimestral", "fecha_inicio": 45658, "fecha_fin": None,
        "linea_base": "", "ind_esperado": "IE", "nombre": "Nom", "sector": "S",
        "entidad": "E", "ponderacion": 10, "politica": "PP",
        "avances": {"2026_Q1": 5}, "acumulados": {"2026": 5},
        "metas": {"2026": 10, "final": 40}, "pct_vigencia": {"2026": 0.5},
        "cualitativos": {"2026_Q1": "ok"}, "avance_enfoques": {},
    }
    ind = indicador_desde_dict(d)
    assert ind.indicador_esperado == "IE"
    assert ind.tipo_anualizacion == "Decreciente"
    assert ind.meta_final == 40
    assert "final" not in ind.metas and ind.metas["2026"] == 10
    assert ind.avances == {"2026_Q1": 5}
    # el dict original no se muta
    assert d["metas"] == {"2026": 10, "final": 40}
