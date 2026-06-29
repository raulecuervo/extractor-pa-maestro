# -*- coding: utf-8 -*-
"""Unit tests por etapa (Hito 2): helpers puros de utilidades, vigencia y fichas."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa.utilidades import (a_float, extraer_codigo, es_vigente,
                                     peso_positivo, clave_grupo)
from extractor_pa.vigencia import calcular_vigencia
from extractor_pa.lector_fichas import codigo_de_hoja_ficha
from extractor_pa.pipeline import _es_nombre_politica


# ── utilidades.a_float (tolerante, formato europeo) ──
@pytest.mark.parametrize("entrada,esperado", [
    (10, 10.0), (10.5, 10.5),
    ("9%", 9.0), ("$1.234,56", 1234.56),   # europeo: punto miles, coma decimal
    ("74,5", 74.5), ("  12  ", 12.0),
    (None, None), ("n/a", None), ("", None), ("texto", None),
])
def test_a_float(entrada, esperado):
    assert a_float(entrada) == esperado


# ── utilidades.extraer_codigo ──
@pytest.mark.parametrize("texto,niveles,esperado", [
    ("1.1 Aumento de la cobertura", 2, "1.1"),
    ("4.1.5Nombre pegado", 3, "4.1.5"),
    ("5. 1 Productividad", 2, "5.1"),     # separador con espacio → normaliza
    ("2 Objetivo general", 1, "2"),
    ("Sin código", None, None),
    ("3.2.1", None, "3.2.1"),
])
def test_extraer_codigo(texto, niveles, esperado):
    assert extraer_codigo(texto, niveles) == esperado


# ── utilidades.es_vigente / peso_positivo / clave_grupo ──
@pytest.mark.parametrize("valor,esperado", [
    ("Vigente", True), ("", True), (None, True),
    ("No Vigente", False), ("No", False),
])
def test_es_vigente(valor, esperado):
    assert es_vigente(valor) is esperado


@pytest.mark.parametrize("valor,esperado", [
    (0.5, True), ("10%", True), (0, False), ("", False), ("abc", False),
])
def test_peso_positivo(valor, esperado):
    assert peso_positivo(valor) is esperado


def test_clave_grupo_usa_codigo():
    assert clave_grupo("1.1 Resultado X") == "1.1"


# ── vigencia.calcular_vigencia ──
def test_vigencia_anio_explicito_presente():
    metas = {2024: 10, 2025: 20, 2026: 30}
    assert calcular_vigencia(metas, 2025) == (2025, 2024, 20, 10)


def test_vigencia_anio_explicito_ausente_toma_anterior():
    metas = {2024: 10, 2025: 20, 2026: 30}
    # 2027 no existe → toma el <= más cercano (2026).
    assert calcular_vigencia(metas, 2027) == (2026, 2025, 30, 20)


def test_vigencia_sin_metas():
    assert calcular_vigencia({}, 2025) == (None, None, None, None)


# ── lector_fichas.codigo_de_hoja_ficha (5 convenciones de nombre) ──
@pytest.mark.parametrize("nombre,esperado", [
    ("Ficha técnica IR#1.1", "1.1"),
    ("Ficha técnica IP#1.1.1", "1.1.1"),
    ("R. 1.1", "1.1"),
    ("IR_1.1", "1.1"),
    ("1.1.1. Descripción del producto", "1.1.1"),
    ("Plan de acción", None),
    ("Instructivo", None),
])
def test_codigo_de_hoja_ficha(nombre, esperado):
    assert codigo_de_hoja_ficha(nombre) == esperado


# ── pipeline._es_nombre_politica (C1: nombre vs decreto/CONPES/'No aplica') ──
@pytest.mark.parametrize("valor,esperado", [
    ("Política Pública de Servicios Públicos", True),
    ("POLÍTICA PÚBLICA DISTRITAL DE TRANSPARENCIA E INTEGRIDAD", True),
    ("233 de 2023", False),       # decreto
    ("01/2018", False),           # conpes/decreto con barra
    ("No aplica", False),
    ("", False), (None, False),
    ("Objetivo General de la Política Pública: lograr...", False),
    ("FORMATO DE PLAN DE ACCION POLÍTICAS PÚBLICAS", False),
])
def test_es_nombre_politica(valor, esperado):
    assert _es_nombre_politica(valor) is esperado
