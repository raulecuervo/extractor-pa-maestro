# -*- coding: utf-8 -*-
"""Reglas de exigencia de reporte definidas por la OAP (30-oct-2026).

Cada prueba usa un producto real de los formatos S1-2026 y el corte que se
calcula. Las cifras son las que la regla exige, no las del formato oficial
cuando este se aparta (Constante sin reporte exigible).
"""

import pytest

from extractor_pa.seguimiento.metricas import (
    hay_meta, metricas_corte, sin_iniciar_al_corte, trimestre_efectivo,
)


def _fila(anio, q, meta, mf, valor=None, acumulado=None):
    return dict(anio=anio, trimestre=q, meta_anual=meta, meta_final=mf,
                acumulado=acumulado, valor_avance=valor)


def _al_corte(segs, anio, q):
    return [s for s in segs if (s["anio"], s["trimestre"]) <= (anio, q)]


def _m(tipo, per, lb, segs, anio, q, **kw):
    return metricas_corte(tipo, per, lb, _al_corte(segs, anio, q), segs, anio, q, **kw)


# ── Caso 1 y 2: ponderación 0 mientras no llega su primer reporte exigible ──

def test_caso_1_inicia_despues_del_corte():
    # Seguridad 3.1.6: Creciente anual, inicia 15-nov-2026; corte 2026 Q2
    assert sin_iniciar_al_corte("2026-11-15", "Anual", 2026, 2)


def test_caso_2_anual_que_inicia_en_enero_no_reporta_hasta_q4():
    # Ruralidad 3.1.8: Constante anual, inicia 1-ene-2026
    assert sin_iniciar_al_corte("2026-01-01", "Anual", 2026, 2)
    assert not sin_iniciar_al_corte("2026-01-01", "Anual", 2026, 4)


# ── Caso 3: nunca ha reportado y ya debía (trimestral) ──

def _afro_324():
    """Afro 3.2.4: Creciente trimestral, LB 0,011; metas 0,015/0,02/0,025;
    MF 0,10; nunca ha reportado."""
    segs = [_fila(2024, 4, 0.015, 0.1), _fila(2025, 4, 0.02, 0.1)]
    segs += [_fila(2026, q, 0.025, 0.1) for q in (1, 2)]
    return segs


def test_caso_3_trayectoria_prorrateada_al_trimestre_exigible():
    m = _m("Creciente", "Trimestral", 0.011, _afro_324(), 2026, 2)
    assert m["trimestre_efectivo"] == 2
    assert m["ma"] == pytest.approx(0.0225)
    assert m["tid"] == pytest.approx((0.0225 - 0.011) / (0.1 - 0.011))   # 12,9 %
    assert m["av_acum"] == pytest.approx(0.011)                          # la LB
    assert m["paf"] == pytest.approx(0.0)
    assert m["phv"] == pytest.approx(0.0)
    assert m["pav"] == pytest.approx(0.0)


def test_caso_3_sin_filas_del_anio_usa_metas_del_plan():
    """Sin filas de 2026 (nunca reportó), la meta del año sale del plan."""
    segs = [_fila(2024, 4, 0.015, 0.1), _fila(2025, 4, 0.02, 0.1)]
    m = metricas_corte("Creciente", "Trimestral", 0.011, segs, segs, 2026, 2,
                       metas_plan={"2024": 0.015, "2025": 0.02, "2026": 0.025})
    assert m["ma"] == pytest.approx(0.0225)
    assert m["tid"] == pytest.approx(0.129, abs=1e-3)


# ── Caso 4: anual que nunca ha reportado, en un corte que aún no le exige ──

def test_caso_4_anual_a_junio_queda_en_la_meta_de_la_vigencia_anterior():
    # Afro 3.1.48: Creciente anual, metas 0,1/0,3/0,5, MF 1, sin LB
    segs = [_fila(2024, 4, 0.1, 1), _fila(2025, 4, 0.3, 1),
            _fila(2026, 1, 0.5, 1), _fila(2026, 2, 0.5, 1)]
    m = _m("Creciente", "Anual", 0.0, segs, 2026, 2)
    assert m["trimestre_efectivo"] == 0
    assert m["tid"] == pytest.approx(0.3)            # no 0,4
    assert m["paf"] == pytest.approx(0.0)
    assert m["pav"] is None                          # aún no le toca en 2026
    # Con las metas solo en el plan da lo mismo
    p = metricas_corte("Creciente", "Anual", 0.0, segs[:2], segs[:2], 2026, 2,
                       metas_plan={"2024": 0.1, "2025": 0.3, "2026": 0.5})
    assert p["tid"] == pytest.approx(0.3)


# ── Caso 5 y 6: Suma sin reporte exigible = reporte 0 ──

def test_caso_5_suma_trimestral_reporte_parcial():
    """Mujer 8.1.15: Suma trimestral, 5 por año, MA a 2025 = 28, MF 53;
    reportó 2 en 2026 Q1 y nada en Q2 → Q2 cuenta como 0."""
    segs = [_fila(2025, 4, 5, 53, 0, 39)]
    segs += [_fila(2026, 1, 5, 53, 2, 41), _fila(2026, 2, 5, 53, None, 41)]
    m = _m("Suma", "Trimestral", 0.0, segs, 2026, 2,
           metas_plan={str(y): v for y, v in
                       {2020: 3, 2021: 5, 2022: 5, 2023: 5, 2024: 5, 2025: 5, 2026: 5}.items()})
    assert m["trimestre_efectivo"] == 2
    assert m["ma"] == pytest.approx(30.5)            # 28 + 5 × 2/4
    assert m["tid"] == pytest.approx(30.5 / 53)      # 57,5 %
    assert m["paf"] == pytest.approx(41 / 53)


def test_caso_6_suma_semestral_sin_reporte_en_el_anio():
    """Raizales 1.1.3: Suma semestral, metas 1/2/2, MF 24, acumulado 1."""
    segs = [_fila(2024, 4, 1, 24), _fila(2025, 2, 2, 24, 0, 0),
            _fila(2025, 4, 2, 24, 1, 1), _fila(2026, 2, 2, 24, None, 1)]
    m = _m("Suma", "Semestral", 0.0, segs, 2026, 2)
    assert m["ma"] == pytest.approx(4)               # 1 + 2 + 2 × 6/12
    assert m["tid"] == pytest.approx(4 / 24)
    assert m["paf"] == pytest.approx(1 / 24)
    assert m["pav"] == pytest.approx(0.0)            # reporte 0 en 2026


# ── Caso 7: Constante sin reporte exigible = 0 ──

def _afro_4112():
    """Afro 4.1.12: Constante trimestral, meta 1 en 2025 y 2026, MF 1;
    reportó 0 en 2025 Q2 y 1 en 2025 Q4; nada en 2026."""
    return [_fila(2024, 4, 0, 1), _fila(2025, 2, 1, 1, 0), _fila(2025, 4, 1, 1, 1),
            _fila(2026, 1, 1, 1), _fila(2026, 2, 1, 1)]


def test_caso_7_constante_trimestral_sin_reporte_exigible_es_cero():
    m = _m("Constante", "Trimestral", 0.0, _afro_4112(), 2026, 2)
    assert m["av_acum"] == pytest.approx(0.0)
    assert m["paf"] == pytest.approx(0.0)
    assert m["phv"] == pytest.approx(0.0)
    assert m["pav"] == pytest.approx(0.0)
    assert m["tid"] == pytest.approx(1.0)
    # En 2025 Q4 sí reportó: 100 %
    assert _m("Constante", "Trimestral", 0.0, _afro_4112(), 2025, 4)["paf"] == pytest.approx(1.0)


def test_caso_7_constante_que_deja_de_reportar_a_mitad_de_anio():
    segs = _afro_4112()
    segs[3]["valor_avance"] = 1                       # reporta 2026 Q1, no Q2
    assert _m("Constante", "Trimestral", 0.0, segs, 2026, 2)["av_acum"] == pytest.approx(0.0)
    assert _m("Constante", "Trimestral", 0.0, segs, 2026, 1)["av_acum"] == pytest.approx(1.0)


def _afro_213():
    """Afro 2.1.3: Constante anual, meta 0,0833 en 2024-2026, MF 1;
    reportó 0,0833 en 2024 Q4 y nada en 2025."""
    return [_fila(2024, 4, 0.0833, 1, 0.0833), _fila(2025, 4, 0.0833, 1),
            _fila(2026, 2, 0.0833, 1)]


def test_caso_7_constante_anual_sin_reporte_en_q4_es_cero():
    m = _m("Constante", "Anual", 0.0, _afro_213(), 2025, 4)
    assert m["av_acum"] == pytest.approx(0.0)
    assert m["pav"] == pytest.approx(0.0)
    assert m["tid"] == pytest.approx(0.0833)


def test_caso_7_constante_anual_a_junio_toma_la_vigencia_anterior():
    # 2026 aún no le exige: queda lo de 2025, que fue 0 por no reportar
    m = _m("Constante", "Anual", 0.0, _afro_213(), 2026, 2)
    assert m["av_acum"] == pytest.approx(0.0)
    assert m["tid"] == pytest.approx(0.0833)
    assert m["pav"] is None
    # Si en 2025 hubiera reportado, se conserva ese valor
    segs = _afro_213()
    segs[1]["valor_avance"] = 0.0833
    assert _m("Constante", "Anual", 0.0, segs, 2026, 2)["av_acum"] == pytest.approx(0.0833)


# ── Caso 8: Creciente sin reporte exigible repite el último valor ──

def test_caso_8_creciente_semestral_repite_el_ultimo_reporte():
    """Afro 6.3.13: Creciente semestral, metas 0,15/0,55/1, MF 1; reportó 0,15."""
    segs = [_fila(2024, 4, 0.15, 1, 0.15), _fila(2025, 2, 0.55, 1, 0.15),
            _fila(2025, 4, 0.55, 1, 0.15), _fila(2026, 2, 1, 1)]
    m = _m("Creciente", "Semestral", 0.0, segs, 2026, 2)
    assert m["av_acum"] == pytest.approx(0.15)
    assert m["ma"] == pytest.approx(0.775)
    assert m["paf"] == pytest.approx(0.15)
    assert m["pav"] == pytest.approx(0.15 / 0.775)   # el valor repetido vs MP


# ── Caso 9: Creciente que baja ──

def test_caso_9_creciente_que_baja_deja_el_valor_reportado_y_puede_ser_negativo():
    # Afro 2.2.3: reportó 0,2 en 2024 y 0 en 2025 (sin LB) → 0 %
    segs = [_fila(2024, 4, 0.2, 1, 0.2), _fila(2025, 4, 0.3, 1, 0.0)]
    assert _m("Creciente", "Anual", 0.0, segs, 2025, 4)["paf"] == pytest.approx(0.0)
    # Con LB 0,1, un reporte de 0,05 deja el avance negativo
    segs = [_fila(2024, 4, 0.2, 1, 0.2), _fila(2025, 4, 0.3, 1, 0.05)]
    assert _m("Creciente", "Anual", 0.1, segs, 2025, 4)["paf"] < 0


# ── Caso 10: reporta antes de lo exigido ──

def test_caso_10_anual_que_reporta_en_junio_prorratea_a_q2():
    """Vendedores 1.1.12: Suma anual, 3.200 por año, MA a 2025 = 7.400, MF 35.000."""
    segs = [_fila(2025, 4, 3200, 35000, 13764, 23439),
            _fila(2026, 2, 3200, 35000, 2739, 26178)]
    plan = {"2023": 3200, "2024": 1000, "2025": 3200, "2026": 3200}
    m = _m("Suma", "Anual", 3991, segs, 2026, 2, metas_plan=plan)
    assert m["trimestre_efectivo"] == 2
    assert m["ma"] == pytest.approx(9000)
    assert m["paf"] == pytest.approx(26178 / 35000)


# ── Caso 11: periodicidad mayor que anual, exigida solo en años con meta ──

def test_caso_11_quinquenal_solo_exige_en_anios_con_meta():
    """Movilidad Cero 1.1.5: Suma quinquenal desde 2025, meta 2025 = 1, MF 4;
    reportó 0 en 2025 Q4. 2026 no tiene meta: no se le exige reporte."""
    segs = [_fila(2025, 4, 1, 4, 0, 0), _fila(2026, 2, None, 4), _fila(2026, 4, None, 4)]
    m = _m("Suma", "Quinquenal", 0.0, segs, 2026, 2)
    assert m["tid"] == pytest.approx(0.25)
    assert m["trimestre_efectivo"] == 0
    q4 = _m("Suma", "Quinquenal", 0.0, segs, 2026, 4)
    assert q4["trimestre_efectivo"] == 0             # ni siquiera en Q4
    assert q4["tid"] == pytest.approx(0.25)
    assert q4["pav"] is None


def test_caso_11_bienal_en_anio_con_meta_se_trata_como_anual():
    segs = [_fila(2024, 4, 1, 4, 1, 1), _fila(2026, 4, 1, 4)]
    m = _m("Suma", "Bienal", 0.0, segs, 2026, 4, metas_plan={"2024": 1, "2025": 0, "2026": 1})
    assert m["trimestre_efectivo"] == 4
    assert m["ma"] == pytest.approx(2)
    assert m["pav"] == pytest.approx(0.0)            # le tocaba y no reportó


def test_trimestre_efectivo_sin_meta_no_exige():
    assert trimestre_efectivo(4, "Anual", (), exige=False) == 0
    assert trimestre_efectivo(4, "Anual", (2,), exige=False) == 2
    assert trimestre_efectivo(4, "Anual", ()) == 4


# ── Caso 12: producto terminado y vigente ──

def test_caso_12_terminado_conserva_avance_y_trayectoria_en_la_meta_final():
    # Afro 1.1.10: Suma anual, 2024 (meta 1 = MF), reportó 1
    segs = [_fila(2024, 4, 1, 1, 1, 1)]
    m = metricas_corte("Suma", "Anual", 0.0, segs, segs, 2026, 2, fecha_fin="2024-12-31")
    assert m["paf"] == pytest.approx(1.0) and m["tid"] == pytest.approx(1.0)
    # Afro 1.4.2: terminó en 2025 con 0,25 de 1
    segs = [_fila(2024, 4, 0.5, 1, 0, 0), _fila(2025, 4, 0.5, 1, 0.25, 0.25)]
    m = metricas_corte("Suma", "Anual", 0.0, segs, segs, 2026, 2, fecha_fin="2025-12-31")
    assert m["paf"] == pytest.approx(0.25) and m["tid"] == pytest.approx(1.0)
    # Creciente cuya última meta anual no llega a la final: tras el fin, 100 %
    segs = [_fila(2023, 4, 0.8, 1, 0.9)]
    m = metricas_corte("Creciente", "Anual", 0.0, segs, segs, 2026, 2, fecha_fin="2023-12-31")
    assert m["tid"] == pytest.approx(1.0) and m["paf"] == pytest.approx(0.9)


def test_caso_12_constante_terminado_conserva_su_ultimo_reporte():
    segs = [_fila(2024, 4, 1, 1, 1)]
    m = metricas_corte("Constante", "Anual", 0.0, segs, segs, 2026, 2, fecha_fin="2024-12-31")
    assert m["av_acum"] == pytest.approx(1.0) and m["tid"] == pytest.approx(1.0)


# ── Caso 13: año sin meta dentro de la vigencia ──

def test_caso_13_constante_sin_meta_en_el_anio_toma_el_ultimo_anio_con_meta():
    """Rrom 13.1.5: Constante trimestral, solo meta 2024 = 1 = MF; reportó 1 en
    2024 Q4, 2025 Q1 y Q2; nada después. 2025 y 2026 no tienen meta."""
    segs = [_fila(2024, 4, 1, 1, 1), _fila(2025, 1, None, 1, 1), _fila(2025, 2, None, 1, 1),
            _fila(2026, 1, None, 1), _fila(2026, 2, None, 1)]
    m = _m("Constante", "Trimestral", 0.0, segs, 2026, 2)
    assert m["av_acum"] == pytest.approx(1.0)
    assert m["paf"] == pytest.approx(1.0)
    assert m["tid"] == pytest.approx(1.0)
    assert m["pav"] is None


# ── Meta 0 = sin meta ──

def test_meta_cero_no_exige_reporte():
    assert not hay_meta(0, "Suma", 10)
    segs = [_fila(2025, 4, 2, 10, 2, 2), _fila(2026, 2, 0, 10)]
    m = _m("Suma", "Semestral", 0.0, segs, 2026, 2)
    assert m["trimestre_efectivo"] == 0
    assert m["pav"] is None
    # Constante con meta 0 en 2026: conserva lo de 2025
    segs = [_fila(2025, 4, 1, 1, 1), _fila(2026, 2, 0, 1)]
    k = _m("Constante", "Trimestral", 0.0, segs, 2026, 2)
    assert k["av_acum"] == pytest.approx(1.0)


def test_anio_ausente_entre_metas_conocidas_no_exige():
    """Comunicación Comunitaria 1.1.3: metas en 2024 y 2026, ninguna en 2025.
    2025 no exige reporte, así que en 2026 Q2 (anual, aún no exige) el
    Constante conserva lo reportado en 2024 y no queda en 0."""
    from extractor_pa.seguimiento.metricas import exige_reporte_en
    programada = {2024: True, 2026: True}
    assert exige_reporte_en(2025, programada) is False
    assert exige_reporte_en(2024, programada) is True
    assert exige_reporte_en(2026, programada) is True
    assert exige_reporte_en(2025, {}) is True
