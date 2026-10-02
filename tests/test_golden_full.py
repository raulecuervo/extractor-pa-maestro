# -*- coding: utf-8 -*-
"""
Regresión EXHAUSTIVA (golden completo): todas las políticas (plan + seguimiento).

Pesada (re-extrae ~90 archivos), por eso está marcada `slow` y NO corre en el
`pytest` por defecto. Ejecutar antes de migrar:

    pytest -m slow            # solo la regresión completa
    pytest -m ""              # toda la suite, incluida la completa

Generar/actualizar los golden:  python scripts/gen_golden.py

Un archivo sin golden se salta aquí; que el corpus entero se quede sin golden
lo detecta `test_golden.py::test_corpus_cubierto_por_golden` (suite rápida).
Raíz del corpus y convención de claves: ver `tests/corpus.py`.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa import extraer_plan_accion
from extractor_pa.regresion import huella_plan, huella_seguimiento
from tests.corpus import (cargar_golden, comparar_golden, descubrir_planes,
                          descubrir_seguimientos, mensaje_regresion)

pytestmark = pytest.mark.slow


@pytest.mark.parametrize("clave,ruta", descubrir_planes())
def test_golden_plan_completo(clave, ruta):
    esperado = cargar_golden(clave)
    if esperado is None:
        pytest.skip(f"golden no generado: {clave}")
    obtenido = huella_plan(extraer_plan_accion(ruta))
    difs = comparar_golden(esperado, obtenido)
    assert not difs, mensaje_regresion(clave, esperado, obtenido, difs)


@pytest.mark.parametrize("clave,ruta", descubrir_seguimientos())
def test_golden_seguimiento_completo(clave, ruta):
    try:
        import pyxlsb  # noqa: F401
    except ImportError:
        pytest.skip("pyxlsb no instalado")
    esperado = cargar_golden(clave)
    if esperado is None:
        pytest.skip(f"golden no generado: {clave}")
    from extractor_pa.seguimiento import extraer_seguimiento
    obtenido = huella_seguimiento(extraer_seguimiento(ruta))
    difs = comparar_golden(esperado, obtenido)
    assert not difs, mensaje_regresion(clave, esperado, obtenido, difs)
