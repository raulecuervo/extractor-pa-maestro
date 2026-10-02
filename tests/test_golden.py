# -*- coding: utf-8 -*-
"""
Pruebas de regresión (golden files).

Re-ejecuta el extractor maestro sobre el corpus curado y compara su huella con
la huella esperada (`tests/golden/<clave>.json`). Detecta cualquier deriva del
maestro entre versiones. Un caso se salta si su carpeta del corpus no está
(suite portable, p. ej. en el CI); pero si la carpeta está y la política curada
no aparece, o ningún archivo del corpus tiene golden, la prueba falla: la
regresión no se puede apagar sin que se note.

Raíz del corpus y convención de claves: ver `tests/corpus.py`.

Para actualizar los golden tras un cambio intencional:
    python scripts/gen_golden.py
"""

from __future__ import annotations

import os
import sys
import warnings

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa import extraer_plan_accion
from extractor_pa.regresion import huella_plan, huella_seguimiento
from tests.corpus import (CORPUS_PLAN, CORPUS_SEGUIMIENTO, DIR_PLANES, DIR_SEG_GOB,
                          cargar_golden, claves_duplicadas, claves_golden,
                          comparar_golden, descubrir_planes, descubrir_seguimientos,
                          mensaje_regresion)


def _exigir_archivo(clave, ruta, carpeta, lista):
    """Salta si el archivo no está; falla si es una política curada que falta
    en una carpeta del corpus que sí existe."""
    if ruta is None:
        if os.path.isdir(carpeta):
            pytest.fail(f"{clave}: la política curada no está en {carpeta} "
                        f"(¿se renombró o se retiró?): actualizar {lista} en tests/corpus.py")
        pytest.skip(f"corpus no disponible: {carpeta}")
    if not os.path.exists(ruta):
        pytest.skip(f"archivo no disponible: {ruta}")


def _exigir_golden(clave):
    esperado = cargar_golden(clave)
    if esperado is None:
        pytest.fail(f"golden no generado: {clave} (correr scripts/gen_golden.py)")
    return esperado


@pytest.mark.parametrize("clave,ruta", CORPUS_PLAN)
def test_golden_plan(clave, ruta):
    _exigir_archivo(clave, ruta, DIR_PLANES, "CURADO_PLAN")
    esperado = _exigir_golden(clave)
    obtenido = huella_plan(extraer_plan_accion(ruta))
    difs = comparar_golden(esperado, obtenido)
    assert not difs, mensaje_regresion(clave, esperado, obtenido, difs)


@pytest.mark.parametrize("clave,ruta", CORPUS_SEGUIMIENTO)
def test_golden_seguimiento(clave, ruta):
    _exigir_archivo(clave, ruta, DIR_SEG_GOB, "CURADO_SEGUIMIENTO")
    try:
        import pyxlsb  # noqa: F401
    except ImportError:
        pytest.skip("pyxlsb no instalado")
    esperado = _exigir_golden(clave)
    from extractor_pa.seguimiento import extraer_seguimiento
    obtenido = huella_seguimiento(extraer_seguimiento(ruta))
    difs = comparar_golden(esperado, obtenido)
    assert not difs, mensaje_regresion(clave, esperado, obtenido, difs)


# ── Salud del corpus (no extrae nada: solo nombres de archivo) ──

_CORPUS_COMPLETO = [
    pytest.param("plan", descubrir_planes, DIR_PLANES, CORPUS_PLAN, id="planes"),
    pytest.param("seg", descubrir_seguimientos, DIR_SEG_GOB, CORPUS_SEGUIMIENTO,
                 id="seguimientos"),
]


@pytest.mark.parametrize("prefijo,descubrir,carpeta,curado", _CORPUS_COMPLETO)
def test_corpus_cubierto_por_golden(prefijo, descubrir, carpeta, curado):
    """Si el corpus existe, sus archivos deben tener golden.

    Ninguno con golden → falla (la regresión completa se estaría saltando
    entera). Algunos sin golden, o golden sin archivo → advertencia."""
    corpus = descubrir()
    if not corpus:
        pytest.skip(f"corpus no disponible: {carpeta}")
    sin_golden = [os.path.basename(r) for c, r in corpus if cargar_golden(c) is None]
    if len(sin_golden) == len(corpus):
        pytest.fail(
            f"Ningún archivo de {carpeta} ({len(corpus)}) tiene golden: la regresión "
            f"está apagada. ¿Se renombraron los archivos o cambió la convención de "
            f"claves? Correr scripts/gen_golden.py y revisar las diferencias. "
            f"Ejemplos: {sin_golden[:3]}")
    if sin_golden:
        warnings.warn(f"{len(sin_golden)} de {len(corpus)} archivos de {carpeta} sin "
                      f"golden (su regresión se salta): {sin_golden}")
    usadas = {c for c, _ in corpus} | {c for c, _ in curado}
    huerfanos = sorted(claves_golden(prefijo) - usadas)
    if huerfanos:
        warnings.warn(f"golden sin archivo en el corpus (borrar con "
                      f"scripts/gen_golden.py --podar): {huerfanos}")


@pytest.mark.parametrize("prefijo,descubrir,carpeta,curado", _CORPUS_COMPLETO)
def test_corpus_claves_unicas(prefijo, descubrir, carpeta, curado):
    """Dos archivos con la misma clave compartirían golden: uno nunca se probaría."""
    corpus = descubrir()
    if not corpus:
        pytest.skip(f"corpus no disponible: {carpeta}")
    dup = claves_duplicadas(corpus)
    assert not dup, (f"claves de golden repetidas en {carpeta} (¿dos versiones del "
                     f"mismo plan?): {dup}")
