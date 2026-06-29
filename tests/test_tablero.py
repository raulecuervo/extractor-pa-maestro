# -*- coding: utf-8 -*-
"""Pruebas del tablero de cumplimiento (Hito 5): emparejamiento y render (sin I/O)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa.tablero import clave_politica, emparejar, render_html, _ORDEN_SEM


@pytest.mark.parametrize("nombre,clave", [
    ("PA_BTI_V4-26_DP.xlsx", "bti"),
    ("BTI.xlsb", "bti"),
    ("PA_Educacion_V2_26_DP.xlsx", "educacion"),
    ("Educación.xlsb", "educacion"),
    ("Plan Accion PP_Negra-Afro_V3_2025 15.12.2025.xlsx", "negraafro"),
])
def test_clave_politica(nombre, clave):
    assert clave_politica(nombre) == clave


def test_emparejar_une_plan_y_seguimiento():
    planes = [r"d\PA_BTI_V4-26_DP.xlsx", r"d\PA_Educacion_V2_26_DP.xlsx"]
    segs = [r"s\BTI.xlsb", r"s\Educación.xlsb", r"s\Mujer.xlsb"]
    pares = emparejar(planes, segs)
    by = {c: (p, s) for c, p, s in pares}
    assert by["bti"][0] and by["bti"][1]           # ambos
    assert by["educacion"][0] and by["educacion"][1]
    assert by["mujer"][0] is None and by["mujer"][1]  # seguimiento sin plan


def test_render_html_basico():
    fila = {"clave": "bti", "politica": "PP BTI", "archivo_plan": "PA_BTI.xlsx",
            "archivo_seg": "BTI.xlsb", "n_ir": 7, "n_ip": 46, "n_seg": 38,
            "n_asociados": 38, "n_error": 5, "n_advertencia": 4, "pct_promedio": 74.7,
            "semaforo": {k: 0 for k in _ORDEN_SEM}}
    fila["semaforo"]["VERDE"] = 22
    html = render_html([fila], 2025, "Anual")
    assert "<table" in html and "PP BTI" in html and "Tablero de cumplimiento" in html
