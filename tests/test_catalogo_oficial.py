# -*- coding: utf-8 -*-
"""Pruebas del catálogo oficial / V4 (opcional) y la normalización difusa (B1)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa.catalogo_oficial import (
    CatalogoOficial, sugerencias_normalizacion, aplicar_normalizacion,
)
from extractor_pa.validacion import validar_reglas
from extractor_pa.modelo import (
    ResultadoExtraccion, Metadatos, IndicadorResultado, IndicadorProducto,
)


def _resultado(sector_ir, entidad_ip):
    meta = Metadatos(nombre_politica="P", archivo_fuente="x.xlsx")
    ir = IndicadorResultado(codigo_ir="1.1", sector_responsable=sector_ir)
    ip = IndicadorProducto(codigo_ir="1.1", codigo_ip="1.1.1", entidad_responsable=entidad_ip)
    return ResultadoExtraccion(meta, [ir], [ip])


def test_membresia_y_normalizacion():
    c = CatalogoOficial()
    assert c.es_sector_oficial("Ambiente") is True
    assert c.es_sector_oficial("Ambeinte") is False
    assert c.es_sector_oficial("") is True        # vacío no alerta
    # Tolerante a acentos/caso en la membresía.
    assert c.es_entidad_oficial("SECRETARÍA DISTRITAL DE SALUD") is True


def test_sugerencia_fuzzy():
    c = CatalogoOficial()
    assert c.sugerir_entidad("Secretaria de Movilidad") == "Secretaría Distrital de Movilidad"
    assert c.sugerir_sector("GestiónPública") == "Gestión Pública"


def test_v4_es_opcional():
    res = _resultado("Sector Inventado", "Entidad Inventada")
    # Sin catálogo: V4 NO se ejecuta.
    sin = [a for a in validar_reglas(res) if a.tipo in ("sector_no_oficial", "entidad_no_oficial")]
    assert sin == []
    # Con catálogo: V4 dispara.
    con = [a for a in validar_reglas(res, catalogo_oficial=CatalogoOficial())
           if a.tipo in ("sector_no_oficial", "entidad_no_oficial")]
    assert {a.tipo for a in con} == {"sector_no_oficial", "entidad_no_oficial"}


def test_normalizacion_aplica():
    res = _resultado("GestiónPública", "Secretaria de Movilidad")
    sug = sugerencias_normalizacion(res)
    assert any(s["sugerido"] == "Gestión Pública" for s in sug)
    n = aplicar_normalizacion(res)
    assert n >= 1
    assert res.indicadores_resultado[0].sector_responsable == "Gestión Pública"


def test_el_catalogo_entidad_sector_viaja_con_el_paquete():
    """Regresión: el JSON curado se carga desde `extractor_pa/data/`. Si no se declara
    en `package-data`, la librería funciona en el árbol de fuentes pero al INSTALARLA
    el archivo no llega y la regla ADVERTENCIA_SECTOR_ENTIDAD se apaga en silencio."""
    from extractor_pa.catalogo_oficial import ENTIDAD_SECTOR, sector_oficial_de

    assert ENTIDAD_SECTOR, "el catálogo entidad→sector llegó vacío"
    # Resuelve con y sin tildes (la clave se normaliza al cargar).
    assert sector_oficial_de("Secretaría Distrital de Integración Social, SDIS")
    assert (sector_oficial_de("SECRETARIA DISTRITAL DE INTEGRACION SOCIAL, SDIS")
            == sector_oficial_de("Secretaría Distrital de Integración Social, SDIS"))
