# -*- coding: utf-8 -*-
"""Convención de claves del corpus golden (`tests/corpus.py`), sin archivos reales.

Corre también en el CI, donde las pruebas con el corpus se saltan: si la
convención se rompe, se nota aquí aunque no haya datos.
"""

import os
import subprocess
import sys

import pytest

RAIZ_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ_REPO)

from tests.corpus import claves_duplicadas, comparar_golden, slug_politica


@pytest.mark.parametrize("nombre,slug", [
    ("29__pa_bti_v4-26_dp_v1.xlsx", "bti"),
    ("01__pa_transparencia_v8-26_dp_0_v1.xlsx", "transparencia"),
    ("17__pa_pp_pyba_v5-26_dp_v1.xlsx", "pyba"),
    ("30__pa_pp_movilidad_cero_y_bajas_v5-26_v1.xlsx", "movilidad_cero_y_bajas"),
    ("37__plan_accion_pp_indigena_v3_2026.xlsx", "indigena"),
    ("39__pa_pp_negra-afro_v3_26.xlsx", "negra_afro"),
    ("42__pa_42_servicio_ciudadania_v1_26_v1.xlsx", "servicio_ciudadania"),
    ("Decreto_193_de_2022__pa_trata_v4-26_dp_c_v1.xlsx", "trata"),
    ("Decreto_034_de_2023__pa_leo_v6_26_0.xlsx", "leo"),
    ("Acuerdo_761_de_2020__pa_x_v1.xlsx", "x"),
    ("plan_accion_pp_adultez_v2_2023_v1.xlsx", "adultez"),
    ("Plan de Acción - BTI v4-26.xlsx", "bti"),
    ("Acción Climática.xlsb", "accion_climatica"),
    ("Servicio a la Ciudadania.xlsb", "servicio_a_la_ciudadania"),
    ("PA_V4-26.xlsx", "pa_v4_26"),            # sin política: el nombre entero
])
def test_slug_politica(nombre, slug):
    assert slug_politica(nombre) == slug


@pytest.mark.parametrize("viejo,nuevo", [
    # Renombrados reales de 01_planes_accion (2026-09-21).
    ("PA_BTI_V4-26_DP.xlsx", "29__pa_bti_v4-26_dp_v1.xlsx"),
    ("PA_Trata_V4-26_DP_.xlsx", "Decreto_193_de_2022__pa_trata_v4-26_dp_c_v1.xlsx"),
    ("PA_LEO_V1-26.xlsx", "Decreto_034_de_2023__pa_leo_v6_26_0.xlsx"),
    ("PA_42_Servicio_Ciudadania_V1_26.xlsx", "42__pa_42_servicio_ciudadania_v1_26_v1.xlsx"),
    ("PA_Infancia_V5-26-DP.xlsx", "27__pa_infancia_v5-26-dp_0_v1.xlsx"),
    ("PA_PYBA_V5-26_DP.xlsx", "17__pa_pp_pyba_v5-26_dp_v1.xlsx"),
    ("Plan Accion PP_Negra-Afro_V3_2025 15.12.2025.xlsx", "39__pa_pp_negra-afro_v3_26.xlsx"),
    ("Plan Accion PP_Indigena_V3_2025 15.12.2025.xlsx", "37__plan_accion_pp_indigena_v3_2026.xlsx"),
    ("plan_accion_pp_cti_v4-25.xlsx", "04__pa_cti_v5-26_0_v1.xlsx"),
])
def test_renombrado_conserva_clave(viejo, nuevo):
    assert slug_politica(viejo) == slug_politica(nuevo)


def test_slug_con_ruta_de_windows_o_de_linux():
    assert slug_politica(r"C:\d\29__pa_bti_v4-26_dp_v1.xlsx") == "bti"
    assert slug_politica("/d/29__pa_bti_v4-26_dp_v1.xlsx") == "bti"


def test_claves_duplicadas():
    corpus = [("plan_bti", "a_v1.xlsx"), ("plan_bti", "a_v2.xlsx"), ("plan_leo", "b.xlsx")]
    assert claves_duplicadas(corpus) == {"plan_bti": ["a_v1.xlsx", "a_v2.xlsx"]}
    assert claves_duplicadas(corpus[1:]) == {}


def test_comparar_golden_ignora_el_nombre_del_archivo():
    esperado = {"archivo": "PA_BTI_V4-26_DP.xlsx", "n_ip": 46}
    assert comparar_golden(esperado, {"archivo": "29__pa_bti_v4-26_dp_v1.xlsx", "n_ip": 46}) == []
    assert comparar_golden(esperado, {"archivo": "PA_BTI_V4-26_DP.xlsx", "n_ip": 45})


def test_raiz_del_corpus_por_variable_de_entorno(tmp_path):
    entorno = dict(os.environ, EXTRACTOR_PA_CORPUS=str(tmp_path))
    out = subprocess.run(
        [sys.executable, "-c", "from tests.corpus import DIR_PLANES; print(DIR_PLANES)"],
        cwd=RAIZ_REPO, env=entorno, capture_output=True, text=True, check=True).stdout.strip()
    assert out == os.path.join(str(tmp_path), "sispp-gobierno", "01_planes_accion")
