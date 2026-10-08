# -*- coding: utf-8 -*-
"""Pruebas unitarias del parser de fechas (Sprint 0 · C2) y de la regla de
escala mezclada (C5)."""

import datetime as dt
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa.validacion import _parse_fecha


@pytest.mark.parametrize("entrada,esperado", [
    (dt.date(2025, 3, 15), dt.date(2025, 3, 15)),
    (dt.datetime(2025, 3, 15, 9, 0), dt.date(2025, 3, 15)),
    (2019, dt.date(2019, 1, 1)),            # año suelto entero
    ("2038", dt.date(2038, 1, 1)),          # año suelto texto
    ("2024-12-31", dt.date(2024, 12, 31)),  # ISO
    ("15/03/2025", dt.date(2025, 3, 15)),   # DD/MM/YYYY
    ("31/12/38", dt.date(2038, 12, 31)),    # DD/MM/YY (2 dígitos)
    (48944, dt.date(2033, 12, 31)),         # serial de Excel
    ("12/31/2024", dt.date(2024, 12, 31)),  # MM/DD/YYYY (US, día>12)
])
def test_parse_fecha_validas(entrada, esperado):
    assert _parse_fecha(entrada) == esperado


@pytest.mark.parametrize("entrada", [
    "31/06/2021",    # junio no tiene 31 → inválida real
    "31/02/2025",    # febrero 31 → inválida real
    "31/012/2050",   # basura
    "01/10/20237",   # año imposible
    "", None, "texto",
])
def test_parse_fecha_invalidas(entrada):
    assert _parse_fecha(entrada) is None


@pytest.mark.parametrize("entrada,esperado", [
    ("01/01/2024", dt.date(2024, 1, 1)),
    ("1/7/2025", dt.date(2025, 7, 1)),
    ("01-07-2025", dt.date(2025, 7, 1)),
    ("01.07.2025", dt.date(2025, 7, 1)),
    ("01/02/2024", dt.date(2024, 2, 1)),     # día primero, como Excel en español
    ("2024/05/01", dt.date(2024, 5, 1)),
    ("2024-05-01 00:00:00", dt.date(2024, 5, 1)),
    ("2024-05-01T08:30", dt.date(2024, 5, 1)),
    ("45292", dt.date(2024, 1, 1)),          # serial de Excel escrito como texto
    (45292.75, dt.date(2024, 1, 1)),
    (2024.0, dt.date(2024, 1, 1)),
])
def test_fecha_de_valor(entrada, esperado):
    from extractor_pa.utilidades import fecha_de_valor
    assert fecha_de_valor(entrada) == esperado


@pytest.mark.parametrize("entrada", [None, "", True, "sin fecha", "2024/13/01", -5, 0])
def test_fecha_de_valor_invalidas(entrada):
    from extractor_pa.utilidades import fecha_de_valor
    assert fecha_de_valor(entrada) is None


def test_plan_y_seguimiento_leen_igual_las_fechas():
    """El plan (`validacion._parse_fecha`) y el seguimiento
    (`metricas.periodo_de_fecha`) usan la misma lectura."""
    from extractor_pa.seguimiento.metricas import fecha_de_valor as en_metricas, periodo_de_fecha
    from extractor_pa.utilidades import fecha_de_valor
    assert en_metricas is fecha_de_valor
    for v in ("15/05/2024", "2024-05-15", 45427, "2024"):
        d = _parse_fecha(v)
        assert d == fecha_de_valor(v)
        assert periodo_de_fecha(v) == (d.year, (d.month - 1) // 3 + 1)


def test_escala_mezclada_no_marca_conteos_pequenos():
    """Metas 1, 2, 3 (conteos) NO deben marcarse como escala mezclada."""
    from extractor_pa.modelo import IndicadorProducto
    from extractor_pa.validacion import _metas_y_lb
    ind = IndicadorProducto(codigo_ip="1.1.1", meta_final="6",
                            metas_por_anio={"2024": "1", "2025": "2", "2026": "3"})
    alertas = []
    _metas_y_lb([ind], alertas, "x.xlsx", "P", "Producto", "codigo_ip")
    assert not any(a.tipo == "escala_mezclada" for a in alertas)


def test_escala_mezclada_detecta_confusion_x100():
    """0.07 junto a 7.0 (ratio 100) sí es confusión de unidades 0-1 vs 0-100."""
    from extractor_pa.modelo import IndicadorProducto
    from extractor_pa.validacion import _metas_y_lb
    ind = IndicadorProducto(codigo_ip="2.1.1", meta_final="7",
                            metas_por_anio={"2024": "0.07", "2025": "7"})
    alertas = []
    _metas_y_lb([ind], alertas, "x.xlsx", "P", "Producto", "codigo_ip")
    assert any(a.tipo == "escala_mezclada" for a in alertas)
