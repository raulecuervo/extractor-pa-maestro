# -*- coding: utf-8 -*-
"""Pruebas del catálogo oficial / V4 (opcional) y de las sugerencias de
normalización (B1), que desde la 0.23.0 salen del listado único y son
deterministas: alias y clave compacta, sin coincidencia difusa."""

import json
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa.catalogo_oficial import (
    CatalogoOficial, SECTORES_OFICIALES, ENTIDADES_OFICIALES,
    sugerencias_normalizacion, aplicar_normalizacion,
)
from extractor_pa.catalogo_entidades import RUTA_LISTADO, cargar, entidad_sector_norm
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
    # La puntuación tampoco cuenta: el nombre oficial lleva comas.
    assert c.es_entidad_oficial("Secretaría Distrital de Seguridad Convivencia y Justicia") is True
    # La sigla es grafía oficial; un alias se reconoce (se sugiere) pero no es oficial.
    assert c.es_entidad_oficial("SDIS") is True
    assert c.es_entidad_oficial("Secretaría de Integración Social") is False


def test_sugerencias_deterministas():
    """Antes de la 0.23.0 las sugerencias venían de rapidfuzz (parecidos); ahora
    salen de equivalencias conocidas: acentos/caso/puntuación, clave compacta y
    alias del listado. Lo que no es una equivalencia no se sugiere."""
    c = CatalogoOficial()
    assert c.sugerir_sector("GestiónPública") == "Gestión Pública"               # clave compacta
    assert c.sugerir_sector("Mujer") == "Mujeres"                                # alias del listado
    assert c.sugerir_sector("Gestión Pública") is None                           # ya está bien
    assert c.sugerir_entidad("SECRETARIA DISTRITAL DE MOVILIDAD") == "Secretaría Distrital de Movilidad"
    assert c.sugerir_entidad("Secretaría de Integración Social") == "Secretaría Distrital de Integración Social"
    assert c.sugerir_entidad("SDIS") is None                                     # sigla oficial: no se corrige
    assert c.sugerir_entidad("Secretaria de Movilidad") is None                  # parecido, no equivalencia


def test_umbral_fuzzy_se_acepta_y_se_ignora():
    """Firma anterior a la 0.23.0: `CatalogoOficial(umbral_fuzzy=88)` sigue construyendo."""
    c = CatalogoOficial(umbral_fuzzy=88)
    assert c.umbral_fuzzy == 88 and c.es_sector_oficial("Salud")


def test_catalogo_propio_no_usa_los_alias_del_listado():
    c = CatalogoOficial(sectores=["Salud"], entidades=["Mi Entidad"])
    assert c.es_sector_oficial("Ambiente") is False
    assert c.sugerir_sector("Mujer") is None
    assert c.sugerir_entidad("mi entidad") == "Mi Entidad"
    assert c.sugerir_entidad("MiEntidad") == "Mi Entidad"


def test_v4_es_opcional():
    res = _resultado("Sector Inventado", "Entidad Inventada")
    # Sin catálogo: V4 NO se ejecuta.
    sin = [a for a in validar_reglas(res) if a.tipo in ("sector_no_oficial", "entidad_no_oficial")]
    assert sin == []
    # Con catálogo: V4 dispara.
    con = [a for a in validar_reglas(res, catalogo_oficial=CatalogoOficial())
           if a.tipo in ("sector_no_oficial", "entidad_no_oficial")]
    assert {a.tipo for a in con} == {"sector_no_oficial", "entidad_no_oficial"}


def test_v4_sugiere_la_grafia_oficial_sin_fuzzy():
    res = _resultado("GestiónPública", "Secretaría de Integración Social")
    por_tipo = {a.tipo: a.descripcion
                for a in validar_reglas(res, catalogo_oficial=CatalogoOficial())
                if a.tipo in ("sector_no_oficial", "entidad_no_oficial")}
    assert "¿quiso decir «Gestión Pública»?" in por_tipo["sector_no_oficial"]
    assert ("¿quiso decir «Secretaría Distrital de Integración Social»?"
            in por_tipo["entidad_no_oficial"])


def test_normalizacion_aplica():
    res = _resultado("GestiónPública", "Secretaría de Integración Social")
    sug = sugerencias_normalizacion(res)
    assert any(s["sugerido"] == "Gestión Pública" for s in sug)
    n = aplicar_normalizacion(res)
    assert n == 2
    assert res.indicadores_resultado[0].sector_responsable == "Gestión Pública"
    assert res.indicadores_producto[0].entidad_responsable == "Secretaría Distrital de Integración Social"


def test_listas_oficiales_salen_del_listado():
    """Hasta la 0.22.0 eran listas escritas en código (16 sectores); ahora son las
    del JSON, que trae además «Concejo de Bogotá» y «Entidades no distritales»."""
    crudo = json.loads(RUTA_LISTADO.read_text(encoding="utf-8"))
    assert SECTORES_OFICIALES == {s["nombre"] for s in crudo["sectores"]}
    assert len(SECTORES_OFICIALES) == 18
    # Nombre, etiqueta y sigla de cada entidad; los alias no (salvo que repitan una).
    assert ENTIDADES_OFICIALES == {
        g for e in crudo["entidades"] for g in (e["nombre"], e["etiqueta"], e["sigla"]) if g}


def test_el_mapa_entidad_sector_viaja_con_el_paquete():
    """Regresión: el listado se carga desde `extractor_pa/data/`. Si no se declara en
    `package-data`, la librería funciona en el árbol de fuentes pero al INSTALARLA el
    archivo no llega. `ENTIDAD_SECTOR` es la instantánea de `entidad_sector_norm()`."""
    from extractor_pa.catalogo_oficial import ENTIDAD_SECTOR, sector_oficial_de

    assert ENTIDAD_SECTOR, "el mapa entidad→sector llegó vacío"
    assert ENTIDAD_SECTOR == entidad_sector_norm()
    # Resuelve con y sin tildes (la clave se normaliza).
    assert sector_oficial_de("Secretaría Distrital de Integración Social, SDIS") == "Integración Social"
    assert (sector_oficial_de("SECRETARIA DISTRITAL DE INTEGRACION SOCIAL, SDIS")
            == sector_oficial_de("Secretaría Distrital de Integración Social, SDIS"))
    # También por sigla, alias y clave compacta.
    assert sector_oficial_de("ERU") == "Hábitat"
    assert sector_oficial_de("Nacional-ICBF") == "Entidades no distritales"
    assert sector_oficial_de("SecretaríaDistritalDeAmbiente") == "Ambiente"
    assert sector_oficial_de("Entidad Inventada") is None


def test_entidad_sector_json_es_un_derivado_sincronizado():
    """`data/entidad_sector.json` ya no lo lee la librería, pero los `.spec` de
    PyInstaller de sispp-gobierno y sispp-SDP lo empaquetan por ruta: se conserva
    como derivado del listado ({etiqueta: sector}). Si se desincroniza, regenerar
    con `python scripts/gen_entidad_sector.py`."""
    ruta = RUTA_LISTADO.with_name("entidad_sector.json")
    derivado = json.loads(ruta.read_text(encoding="utf-8"))
    assert derivado == {e.etiqueta: e.sector for e in cargar().entidades}


def test_norm_entidad_ignora_puntuacion_y_tildes():
    """El mapa lo administra Alertas-Seguimientos desde su interfaz y se inyecta a la
    librería: si las dos normalizaciones no coinciden, el mapa no cruza y la regla
    ADVERTENCIA_SECTOR_ENTIDAD se apaga en silencio. `norm_entidad` es la regla única
    `catalogo_entidades.normalizar` (réplica de `normalizar_texto`)."""
    from extractor_pa.catalogo_oficial import norm_entidad
    from extractor_pa.catalogo_entidades import normalizar

    esperado = "instituto de desarrollo urbano idu"
    for grafia in ("Instituto de Desarrollo Urbano, IDU",
                   "INSTITUTO DE DESARROLLO URBANO - IDU",
                   "Instituto  de   Desarrollo Urbano   IDU"):
        assert norm_entidad(grafia) == esperado == normalizar(grafia)
    assert norm_entidad(None) == "" and norm_entidad("") == ""
    assert norm_entidad("Agencia ATENEA, S.A.S.") == "agencia atenea s a s"
