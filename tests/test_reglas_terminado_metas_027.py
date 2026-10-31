# -*- coding: utf-8 -*-
"""Reglas de la 0.27.0 (OAP Secretaría de Gobierno, 31-oct-2026).

1. Producto terminado según su periodicidad: el fin efectivo es el fin del
   periodo de reporte que contiene la fecha de fin, y en el año final la meta
   del año se reparte solo hasta ese fin efectivo.
2. Todas las metas del plan cuentan, también las anteriores a la fecha de
   inicio; ``metas_antes_de_inicio`` las señala para la alerta de calidad.
3. Un producto que nunca reportó y ya debía queda en 0 %, con peso completo y
   trayectoria normal.

Los datos son sintéticos.
"""

import pytest

from extractor_pa.seguimiento import fin_efectivo, metas_antes_de_inicio
from extractor_pa.seguimiento.metricas import (
    avance_constante, exige_reporte_en, metricas_corte, sin_iniciar_al_corte,
)


def _fila(anio, q, meta, mf, valor=None, acumulado=None):
    return dict(anio=anio, trimestre=q, meta_anual=meta, meta_final=mf,
                acumulado=acumulado, valor_avance=valor)


def _m(tipo, per, lb, segs, anio, q, **kw):
    al_corte = [s for s in segs if (s["anio"], s["trimestre"]) <= (anio, q)]
    return metricas_corte(tipo, per, lb, al_corte, segs, anio, q, **kw)


# ═══════════════════════ 1. Fin efectivo según periodicidad ═══════════════════════

@pytest.mark.parametrize("fecha,per,esperado", [
    ("2026-06-30", "Trimestral", (2026, 2)),
    ("2026-02-15", "Trimestral", (2026, 1)),
    ("2026-08-31", "Trimestral", (2026, 3)),
    ("2026-06-30", "Mensual", (2026, 2)),
    ("2026-03-31", "Semestral", (2026, 2)),
    ("2026-06-30", "Semestral", (2026, 2)),
    ("2026-07-31", "Semestral", (2026, 4)),
    ("2026-03-31", "Anual", (2026, 4)),
    ("2026-06-30", "Anual", (2026, 4)),
    ("2026-06-30", "Cuatrienal", (2026, 4)),
    ("2026-06-30", None, (2026, 2)),            # sin periodicidad: el trimestre
    ("2026-06-30", "rara", (2026, 2)),
])
def test_fin_efectivo(fecha, per, esperado):
    assert fin_efectivo(fecha, per) == esperado


def test_fin_efectivo_sin_fecha():
    assert fin_efectivo(None, "Anual") is None
    assert fin_efectivo("", "Anual") is None


def _suma_dos_anios(per):
    """Suma, meta 100 en 2025 y 100 en 2026, MF 200; termina el 30-jun-2026.
    Reportó 100 en 2025; en 2026 no ha reportado."""
    segs = [_fila(2025, 4, 100, 200, 100, 100)]
    segs += [_fila(2026, q, 100, 200) for q in (1, 2, 3, 4)]
    return segs


@pytest.mark.parametrize("q,ma,tid,terminado", [
    (1, 150, 0.75, False),     # la meta de 2026 se reparte en 2 trimestres: Q1 = 50
    (2, 200, 1.00, True),      # Q2 = la meta completa: termina
    (3, 200, 1.00, True),
    (4, 200, 1.00, True),
])
def test_trimestral_que_termina_en_junio(q, ma, tid, terminado):
    m = _m("Suma", "Trimestral", 0.0, _suma_dos_anios("Trimestral"), 2026, q,
           fecha_fin="2026-06-30")
    assert m["fin_efectivo"] == (2026, 2)
    assert m["ma"] == pytest.approx(ma)
    assert m["tid"] == pytest.approx(tid)
    assert m["terminado"] is terminado
    assert m["trimestre_efectivo"] == min(q, 2)


def test_trimestral_que_termina_en_junio_meta_unica_100():
    """El ejemplo de la OAP: trimestral, meta anual 100 = MF, termina en junio."""
    segs = [_fila(2026, q, 100, 100) for q in (1, 2)]
    q1 = _m("Suma", "Trimestral", 0.0, segs, 2026, 1, fecha_fin="2026-06-30")
    q2 = _m("Suma", "Trimestral", 0.0, segs, 2026, 2, fecha_fin="2026-06-30")
    assert q1["ma"] == pytest.approx(50) and q1["tid"] == pytest.approx(0.5)
    assert q2["ma"] == pytest.approx(100) and q2["tid"] == pytest.approx(1.0)
    # 0.26.0 repartía la meta en 4 trimestres: Q1 = 25 %
    sin_fin = _m("Suma", "Trimestral", 0.0, segs, 2026, 1)
    assert sin_fin["tid"] == pytest.approx(0.25)


@pytest.mark.parametrize("q,ma,tid,terminado,q_ef", [
    (1, 100, 0.50, False, 0),    # semestral aún no reporta en Q1
    (2, 200, 1.00, True, 2),     # fin efectivo Q2
    (3, 200, 1.00, True, 2),
    (4, 200, 1.00, True, 2),
])
def test_semestral_que_termina_en_junio(q, ma, tid, terminado, q_ef):
    m = _m("Suma", "Semestral", 0.0, _suma_dos_anios("Semestral"), 2026, q,
           fecha_fin="2026-06-30")
    assert m["ma"] == pytest.approx(ma)
    assert m["tid"] == pytest.approx(tid)
    assert m["terminado"] is terminado
    assert m["trimestre_efectivo"] == q_ef


@pytest.mark.parametrize("q,ma,tid,terminado,q_ef", [
    (1, 100, 0.50, False, 0),    # anual: no reporta hasta Q4
    (2, 100, 0.50, False, 0),    # termina en junio pero espera al reporte de Q4
    (3, 100, 0.50, False, 0),
    (4, 200, 1.00, True, 4),
])
def test_anual_que_termina_en_junio_espera_a_q4(q, ma, tid, terminado, q_ef):
    m = _m("Suma", "Anual", 0.0, _suma_dos_anios("Anual"), 2026, q,
           fecha_fin="2026-06-30")
    assert m["fin_efectivo"] == (2026, 4)
    assert m["ma"] == pytest.approx(ma)
    assert m["tid"] == pytest.approx(tid)
    assert m["terminado"] is terminado
    assert m["trimestre_efectivo"] == q_ef


def test_anual_que_termina_en_junio_no_se_exige_en_q2():
    segs = _suma_dos_anios("Anual")
    q2 = _m("Suma", "Anual", 0.0, segs, 2026, 2, fecha_fin="2026-06-30")
    assert q2["pav"] is None                     # en Q2 no se le exige
    q4 = _m("Suma", "Anual", 0.0, segs, 2026, 4, fecha_fin="2026-06-30")
    assert q4["pav"] == pytest.approx(0.0)       # en Q4 sí: no reportó → 0


def test_trimestral_que_termina_en_septiembre_reparte_en_tres():
    segs = [_fila(2026, q, 90, 90) for q in (1, 2, 3, 4)]
    tids = [_m("Suma", "Trimestral", 0.0, segs, 2026, q, fecha_fin="2026-09-30")["tid"]
            for q in (1, 2, 3, 4)]
    assert tids == pytest.approx([1 / 3, 2 / 3, 1.0, 1.0])


def test_creciente_trimestral_que_termina_en_junio():
    """Creciente, LB 0, metas 0,4 (2025) y 0,8 (2026), MF 1."""
    segs = [_fila(2025, 4, 0.4, 1, 0.4)] + [_fila(2026, q, 0.8, 1) for q in (1, 2)]
    q1 = _m("Creciente", "Trimestral", 0.0, segs, 2026, 1, fecha_fin="2026-06-30")
    assert q1["ma"] == pytest.approx(0.6)        # (0,8 − 0,4) × 1/2 + 0,4
    q2 = _m("Creciente", "Trimestral", 0.0, segs, 2026, 2, fecha_fin="2026-06-30")
    assert q2["ma"] == pytest.approx(1.0) and q2["tid"] == pytest.approx(1.0)


def test_q3_y_q4_del_anio_final_no_exigen_reporte():
    """Trimestral que termina en junio: después de Q2 no se le pide reporte."""
    segs = [_fila(2026, q, 100, 100, v) for q, v in ((1, 40), (2, 60), (3, None), (4, None))]
    for q in (3, 4):
        m = _m("Suma", "Trimestral", 0.0, segs, 2026, q, fecha_fin="2026-06-30")
        assert m["pav"] == pytest.approx(1.0)    # 100 de 100: no se suma un 0 de Q3/Q4
        assert m["tid"] == pytest.approx(1.0)


def test_constante_que_termina_en_junio_conserva_su_reporte_de_q2():
    segs = [_fila(2026, q, 1, 1, v) for q, v in ((1, 1), (2, 1), (3, None), (4, None))]
    for q in (3, 4):
        m = _m("Constante", "Trimestral", 0.0, segs, 2026, q, fecha_fin="2026-06-30")
        assert m["av_acum"] == pytest.approx(1.0)
        assert m["paf"] == pytest.approx(1.0)
    # En el año siguiente, también
    m = _m("Constante", "Trimestral", 0.0, segs, 2027, 2, fecha_fin="2026-06-30")
    assert m["av_acum"] == pytest.approx(1.0)
    # Sin el fin, Q3 sin reporte vale 0 (regla de 0.26.0)
    assert _m("Constante", "Trimestral", 0.0, segs, 2026, 3)["av_acum"] == pytest.approx(0.0)


def test_avance_constante_respeta_el_fin_efectivo():
    segs = [_fila(2026, 1, 1, 1, 1), _fila(2026, 2, 1, 1, 1)]
    assert avance_constante(segs, 2026, 4, "Trimestral", lambda y: True, (2026, 2)) == 1.0
    assert avance_constante(segs, 2026, 4, "Trimestral", lambda y: True) == 0.0


def test_terminado_el_31_de_diciembre_sigue_igual():
    """Lo de 0.26.0 se mantiene: termina en Q4 del año, en Q4 ya es la meta final."""
    segs = [_fila(2025, 4, 0.5, 1, 0.25, 0.25)]
    m = metricas_corte("Suma", "Anual", 0.0, segs, segs, 2025, 4, fecha_fin="2025-12-31")
    assert m["terminado"] and m["tid"] == pytest.approx(1.0)
    assert m["paf"] == pytest.approx(0.25)


# ═══════════════════════ 2. Metas anteriores a la fecha de inicio ═══════════════════════

def test_metas_antes_de_inicio():
    plan = {"2022": 5, "2023": 5, "2024": 0, "2025": None, "final": 20}
    assert metas_antes_de_inicio(plan, "2024-03-01") == [2022, 2023]
    assert metas_antes_de_inicio(plan, "2022-01-01") == []
    assert metas_antes_de_inicio({2021: 1, 2026: 1}, "2026-01-01") == [2021]   # claves int
    assert metas_antes_de_inicio(plan, None) == []
    assert metas_antes_de_inicio(None, "2024-01-01") == []
    assert metas_antes_de_inicio({"2020": "x", "2021": -1}, "2024-01-01") == []


def test_suma_toma_las_metas_anteriores_al_inicio():
    """Inicia en 2023, el plan trae meta 10 en 2022 (probable error del plan).
    La 0.26.0 la descartaba; desde la 0.27.0 cuenta para la meta acumulada."""
    plan = {"2022": 10, "2023": 10, "2024": 10, "final": 30}
    segs = [_fila(2023, 4, 10, 30, 10, 10), _fila(2024, 2, 10, 30, 5, 15)]
    m = _m("Suma", "Semestral", 0.0, segs, 2024, 2, metas_plan=plan, fecha_inicio="2023-01-01")
    assert m["sum_metas_prev"] == pytest.approx(20)        # 2022 + 2023
    assert m["ma"] == pytest.approx(25)
    assert m["tid"] == pytest.approx(25 / 30)
    assert metas_antes_de_inicio(plan, "2023-01-01") == [2022]


def test_creciente_toma_la_meta_anterior_al_inicio_como_meta_previa():
    """Creciente que inicia en 2023 con meta 0,2 en 2022: el prorrateo de 2023
    parte de 0,2 (la 0.26.0 partía de la LB)."""
    plan = {"2022": 0.2, "2023": 0.6, "final": 1}
    segs = [_fila(2023, 2, 0.6, 1, 0.3)]
    m = _m("Creciente", "Semestral", 0.0, segs, 2023, 2, metas_plan=plan,
           fecha_inicio="2023-01-01")
    assert m["meta_prev"] == pytest.approx(0.2)
    assert m["ma"] == pytest.approx(0.4)                   # (0,6 − 0,2) × 6/12 + 0,2


def test_antes_del_inicio_no_se_exige_ni_pesa():
    """Vendedores 3.1.10 (sintético): inicia en 2026 con meta en 2025."""
    plan = {"2025": 5, "2026": 5, "final": 10}
    segs = [_fila(2025, 4, 5, 10), _fila(2026, 2, 5, 10)]
    m25 = _m("Suma", "Trimestral", 0.0, segs, 2025, 4, metas_plan=plan, fecha_inicio="2026-01-01")
    assert m25["sin_iniciar"] is True
    assert m25["trimestre_efectivo"] == 0                  # 2025 no le exige
    assert m25["pav"] is None
    # Ya iniciado, la meta de 2025 sí cuenta en la acumulada
    m26 = _m("Suma", "Trimestral", 0.0, segs, 2026, 2, metas_plan=plan, fecha_inicio="2026-01-01")
    assert m26["sin_iniciar"] is False
    assert m26["ma"] == pytest.approx(7.5)                 # 5 + 5 × 2/4
    assert sin_iniciar_al_corte("2026-01-01", "Trimestral", 2025, 4)


def test_constante_no_cae_a_cero_por_un_anio_anterior_al_inicio():
    """Constante anual que inicia en 2026 con meta (errada) en 2025 y reporta
    en 2026 Q4: a 2027 Q2 vale lo de 2026; 2025 no se le exige."""
    plan = {"2025": 1, "2026": 1, "2027": 1, "final": 1}
    segs = [_fila(2026, 4, 1, 1, 1), _fila(2027, 2, 1, 1)]
    m = _m("Constante", "Anual", 0.0, segs, 2027, 2, metas_plan=plan, fecha_inicio="2026-01-01")
    assert m["av_acum"] == pytest.approx(1.0)


# ═══════════════════════ 3. Nunca reportado y exigible ═══════════════════════

@pytest.mark.parametrize("tipo,lb,metas,mf,ma", [
    ("Suma", 0.0, {"2025": 10, "2026": 10}, 20, 15),           # 10 + 10 × 2/4
    ("Constante", 0.0, {"2025": 1, "2026": 1}, 1, 1),
    ("Creciente", 0.1, {"2025": 0.3, "2026": 0.5}, 0.5, 0.4),  # (0,5 − 0,3) × 2/4 + 0,3
    ("Decreciente", 20.0, {"2025": 15, "2026": 10}, 10, 12.5),
])
@pytest.mark.parametrize("con_filas", [True, False])
def test_nunca_reportado_y_exigible_queda_en_cero(tipo, lb, metas, mf, ma, con_filas):
    """Trimestral, inicia en 2025, sin ningún reporte; corte 2026 Q2. Con filas
    vacías del seguimiento o sin ninguna fila (solo el plan)."""
    plan = {**metas, "final": mf}
    segs = ([_fila(y, q, metas[str(y)], mf) for y in (2025, 2026) for q in (1, 2, 3, 4)
             if (y, q) <= (2026, 2)] if con_filas else [])
    m = _m(tipo, "Trimestral", lb, segs, 2026, 2, metas_plan=plan, fecha_inicio="2025-01-01")
    assert m["sin_iniciar"] is False                       # peso completo
    assert m["trimestre_efectivo"] == 2
    assert m["ma"] == pytest.approx(ma)                    # trayectoria normal
    assert m["tid"] is not None and m["tid"] > 0
    for k in ("pav", "phv", "paf"):
        assert m[k] is not None, k                         # 0 %, no vacío
        assert m[k] == pytest.approx(0.0), k


def test_nunca_reportado_anual_aun_no_exigible_sigue_sin_pav():
    """Contraste: si en el año aún no le toca reportar, el PAV sigue vacío."""
    segs = [_fila(2025, 4, 10, 20), _fila(2026, 2, 10, 20)]
    m = _m("Suma", "Anual", 0.0, segs, 2026, 2, fecha_inicio="2025-01-01")
    assert m["pav"] is None
    assert m["paf"] == pytest.approx(0.0)


def test_exige_reporte_en_sin_cambios():
    assert exige_reporte_en(2026, {2026: True}, 2026) is True
    assert exige_reporte_en(2027, {2027: True}, 2026) is False
