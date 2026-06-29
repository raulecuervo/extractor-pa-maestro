# -*- coding: utf-8 -*-
"""
Regresión EXHAUSTIVA (golden completo): todas las políticas (plan + seguimiento).

Pesada (re-extrae ~90 archivos), por eso está marcada `slow` y NO corre en el
`pytest` por defecto. Ejecutar antes de migrar:

    pytest -m slow            # solo la regresión completa
    pytest -m ""              # toda la suite, incluida la completa

Generar/actualizar los golden:  python scripts/gen_golden.py
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa import extraer_plan_accion
from extractor_pa.regresion import huella_plan, huella_seguimiento, diferencias
from tests.corpus import descubrir_planes, descubrir_seguimientos, GOLDEN_DIR

pytestmark = pytest.mark.slow


def _golden(clave):
    ruta = os.path.join(GOLDEN_DIR, clave + ".json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.mark.parametrize("clave,ruta", descubrir_planes())
def test_golden_plan_completo(clave, ruta):
    esperado = _golden(clave)
    if esperado is None:
        pytest.skip(f"golden no generado: {clave}")
    difs = diferencias(esperado, huella_plan(extraer_plan_accion(ruta)))
    assert not difs, f"Regresión en {clave}:\n  " + "\n  ".join(difs)


@pytest.mark.parametrize("clave,ruta", descubrir_seguimientos())
def test_golden_seguimiento_completo(clave, ruta):
    try:
        import pyxlsb  # noqa: F401
    except ImportError:
        pytest.skip("pyxlsb no instalado")
    esperado = _golden(clave)
    if esperado is None:
        pytest.skip(f"golden no generado: {clave}")
    from extractor_pa.seguimiento import extraer_seguimiento
    difs = diferencias(esperado, huella_seguimiento(extraer_seguimiento(ruta)))
    assert not difs, f"Regresión en {clave}:\n  " + "\n  ".join(difs)
