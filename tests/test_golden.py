# -*- coding: utf-8 -*-
"""
Pruebas de regresión (golden files).

Re-ejecuta el extractor maestro sobre el corpus y compara su huella con la
huella esperada (`tests/golden/<clave>.json`). Detecta cualquier deriva del
maestro entre versiones. Cada caso se salta si el archivo fuente o su golden no
están disponibles (suite portable).

Para actualizar los golden tras un cambio intencional:
    python scripts/gen_golden.py
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa import extraer_plan_accion
from extractor_pa.regresion import huella_plan, huella_seguimiento, diferencias
from tests.corpus import CORPUS_PLAN, CORPUS_SEGUIMIENTO, GOLDEN_DIR


def _golden(clave):
    ruta = os.path.join(GOLDEN_DIR, clave + ".json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("clave,ruta", CORPUS_PLAN)
def test_golden_plan(clave, ruta):
    if not os.path.exists(ruta):
        pytest.skip(f"archivo no disponible: {clave}")
    esperado = _golden(clave)
    if esperado is None:
        pytest.skip(f"golden no generado: {clave} (correr scripts/gen_golden.py)")
    obtenido = huella_plan(extraer_plan_accion(ruta))
    difs = diferencias(esperado, obtenido)
    assert not difs, f"Regresión en {clave}:\n  " + "\n  ".join(difs)


@pytest.mark.parametrize("clave,ruta", CORPUS_SEGUIMIENTO)
def test_golden_seguimiento(clave, ruta):
    if not os.path.exists(ruta):
        pytest.skip(f"archivo no disponible: {clave}")
    try:
        import pyxlsb  # noqa: F401
    except ImportError:
        pytest.skip("pyxlsb no instalado")
    esperado = _golden(clave)
    if esperado is None:
        pytest.skip(f"golden no generado: {clave}")
    from extractor_pa.seguimiento import extraer_seguimiento
    obtenido = huella_seguimiento(extraer_seguimiento(ruta))
    difs = diferencias(esperado, obtenido)
    assert not difs, f"Regresión en {clave}:\n  " + "\n  ".join(difs)
