# -*- coding: utf-8 -*-
"""Pruebas del listado oficial de sectores y entidades (`catalogo_entidades`).

El listado es la fuente única de `SECTORES_OFICIALES`, `ENTIDADES_OFICIALES` y
del mapa entidad → sector. Estas pruebas fijan lo que los aplicativos pueden dar
por sentado: el JSON publicado es íntegro y versionado, la canonización es
determinista (sin coincidencia difusa) y la huella cambia si cambian los datos.
"""

import json

import pytest

from extractor_pa.catalogo_entidades import (
    RUTA_LISTADO, VARIABLE_RUTA, Entidad, Listado, Sector,
    canonizar_entidad, canonizar_sector, cargar, clave_compacta, construir,
    entidad_sector_norm, entidades_oficiales, integridad, normalizar, sector_de,
    sectores_oficiales,
)


def _json_publicado() -> dict:
    return json.loads(RUTA_LISTADO.read_text(encoding="utf-8"))


def _escribir(ruta, datos, indent=2):
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=indent), encoding="utf-8")
    return ruta


# ─────────────────────────── el JSON publicado ───────────────────────────

def test_el_listado_publicado_es_integro():
    assert integridad(cargar()) == []


def test_version_publicada_y_tamano():
    """Cambian solo con una versión nueva del listado (y de la librería)."""
    lst = cargar()
    assert lst.version == "1.0.1"
    assert len(lst.sectores) == 18 and len(lst.entidades) == 67
    assert lst.fecha and lst.fuente


def test_huella_estable_entre_cargas():
    a, b = cargar(), cargar()
    assert a.huella == b.huella and len(a.huella) == 64
    assert a is b, "la segunda carga debe salir de la caché"


def test_la_huella_cambia_con_los_datos_y_no_con_el_formato(tmp_path):
    datos = _json_publicado()
    compacto = _escribir(tmp_path / "compacto.json", datos, indent=None)
    assert cargar(compacto).huella == cargar().huella        # otro formato, mismos datos
    datos["entidades"][0]["alias"].append("Grafía nueva")
    distinto = _escribir(tmp_path / "distinto.json", datos)
    assert cargar(distinto).huella != cargar().huella


def test_la_cache_recoge_el_archivo_cambiado(tmp_path):
    datos = _json_publicado()
    ruta = _escribir(tmp_path / "listado.json", datos)
    antes = cargar(ruta)
    assert cargar(ruta) is antes
    datos["sectores"][0]["alias"] = ["Medio Ambiente"]
    _escribir(ruta, datos)                                   # cambia tamaño y mtime
    despues = cargar(ruta)
    assert despues is not antes and despues.huella != antes.huella
    assert canonizar_sector("Medio Ambiente", despues).nombre == "Ambiente"
    assert canonizar_sector("Medio Ambiente") is None       # el del paquete no cambió


# ─────────────────────────── normalización ───────────────────────────

@pytest.mark.parametrize("texto,esperado", [
    ("Instituto de Desarrollo Urbano, IDU", "instituto de desarrollo urbano idu"),
    ("INSTITUTO DE DESARROLLO URBANO - IDU", "instituto de desarrollo urbano idu"),
    ("Instituto  de   Desarrollo Urbano   IDU", "instituto de desarrollo urbano idu"),
    ("Agencia ATENEA, S.A.S.", "agencia atenea s a s"),
    ("Hábitat", "habitat"),
    (None, ""), ("", ""), ("   ", ""),
])
def test_normalizar(texto, esperado):
    assert normalizar(texto) == esperado


def test_clave_compacta_pega_las_palabras():
    assert clave_compacta("Integración Social") == "integracionsocial"
    assert clave_compacta("IntegraciónSocial") == "integracionsocial"
    assert clave_compacta(None) == ""


def test_nombre_normalizado_del_json_sigue_la_misma_regla():
    """La regla con que se escribió `nombre_normalizado` en el JSON es `normalizar`:
    las claves que un aplicativo administra con esa misma regla cruzan con este
    listado. Si alguien edita un nombre sin actualizar el campo, `integridad` avisa."""
    lst = cargar()
    for x in lst.sectores + lst.entidades:
        assert x.nombre_normalizado == normalizar(x.nombre)


# ─────────────────────────── canonización ───────────────────────────

@pytest.mark.parametrize("grafia", [
    "ICBF", "Nacional-ICBF", "Instituto Colombiano de Bienestar Familiar ICBF",
    "instituto colombiano de bienestar familiar, icbf",
])
def test_icbf_resuelve_por_sigla_alias_y_etiqueta(grafia):
    e = canonizar_entidad(grafia)
    assert e is not None and e.id == "ICBF"
    assert e.sector == "Entidades no distritales"
    assert sector_de(grafia) == "Entidades no distritales"


@pytest.mark.parametrize("grafia", ["Invest In Bogota", "Invest in Bogotá", "INVEST IN BOGOTÁ"])
def test_invest_in_bogota_es_la_corporacion(grafia):
    e = canonizar_entidad(grafia)
    assert e.nombre == "Corporación para el Desarrollo y la Productividad Bogotá Región"
    assert e.sector == "Desarrollo Económico, Industria y Turismo"


def test_sectores_pegados_de_los_desplegables():
    assert canonizar_sector("IntegraciónSocial").nombre == "Integración Social"
    assert canonizar_sector("Gestiónpública").nombre == "Gestión Pública"
    assert canonizar_sector("GESTIÓN PÚBLICA").nombre == "Gestión Pública"
    assert canonizar_sector("Mujer").nombre == "Mujeres"                 # alias


def test_coincidencia_exacta():
    e = canonizar_entidad("Secretaría Distrital de Ambiente")
    assert (e.id, e.sigla, e.sector) == ("SDA", "SDA", "Ambiente")
    assert canonizar_entidad("Secretaría Distrital de Ambiente, SDA") is e   # etiqueta
    assert canonizar_entidad("sda") is e                                      # sigla
    assert canonizar_sector("Ambiente").nombre == "Ambiente"


@pytest.mark.parametrize("grafia", [
    "Instituto Distrital de Cosas Raras", "Secretaría Distrital de Ambientes", "Ambeinte",
    None, "", "   ",
])
def test_sin_coincidencia_difusa(grafia):
    """Un parecido no basta: la grafía desconocida devuelve None y decide el aplicativo."""
    assert canonizar_entidad(grafia) is None
    assert canonizar_sector(grafia) is None
    assert sector_de(grafia) is None


def test_entidad_inactiva_sigue_resolviendo():
    e = canonizar_entidad("Metrovivienda")
    assert e is not None and e.activa is False and e.sector == "Hábitat"


def test_metodos_del_listado():
    lst = cargar()
    assert lst.entidad("IDU").sector == "Movilidad"
    assert lst.sector("Sector Social").nombre == "Integración Social"
    assert lst.sector_de("Secretaría Distrital de Integración Social, SDIS") == "Integración Social"
    assert lst.entidad("nadie") is None and lst.sector("nadie") is None
    assert lst.sector_de("nadie") is None


# ─────────────────────────── vistas para los consumidores ───────────────────────────

def test_entidad_sector_norm_tiene_las_variantes():
    mapa = entidad_sector_norm()
    assert mapa[normalizar("Nacional-ICBF")] == "Entidades no distritales"
    assert mapa[normalizar("Invest in Bogota")] == "Desarrollo Económico, Industria y Turismo"
    assert mapa[normalizar("Secretaría Distrital de Integración Social, SDIS")] == "Integración Social"
    assert mapa["sdis"] == "Integración Social"
    assert mapa["eru"] == "Hábitat"                               # alias histórico de Renobo
    assert all(k and k == normalizar(k) for k in mapa)            # claves ya normalizadas
    assert set(mapa.values()) <= sectores_oficiales()


def test_sectores_oficiales_son_los_del_json():
    esperados = {s["nombre"] for s in _json_publicado()["sectores"]}
    assert sectores_oficiales() == esperados and len(esperados) == 18
    assert {"Entes de Control", "Concejo de Bogotá", "Entidades no distritales"} <= esperados
    assert "Órganos de Control" not in esperados                   # alias, no nombre oficial


def test_entidades_oficiales_incluyen_nombre_etiqueta_y_sigla_pero_no_alias():
    oficiales = entidades_oficiales()
    assert {"Secretaría Distrital de Integración Social",
            "Secretaría Distrital de Integración Social, SDIS", "SDIS"} <= oficiales
    assert "Secretaría de Integración Social" not in oficiales      # alias
    assert "Metrovivienda" in oficiales                             # inactiva, pero oficial


# ─────────────────────────── variable de entorno ───────────────────────────

def _listado_minimo() -> dict:
    return {"version": "prueba", "fecha": "2026-01-01", "fuente": "pytest",
            "sectores": [{"nombre": "Sector de Prueba", "alias": []}],
            "entidades": [{"id": "EP", "sector": "Sector de Prueba", "nombre": "Entidad de Prueba",
                           "sigla": "EP", "alias": ["La Entidad"]}]}


def test_variable_de_entorno_cambia_el_listado(tmp_path, monkeypatch):
    ruta = _escribir(tmp_path / "urgencia.json", _listado_minimo())
    monkeypatch.setenv(VARIABLE_RUTA, str(ruta))
    lst = cargar()
    assert lst.version == "prueba" and len(lst.entidades) == 1
    assert canonizar_entidad("La Entidad").id == "EP"
    assert canonizar_entidad("ICBF") is None               # ya no es el listado del paquete
    assert sectores_oficiales() == {"Sector de Prueba"}
    assert integridad(lst) == []
    assert cargar(RUTA_LISTADO).version == "1.0.1"         # una ruta explícita manda
    monkeypatch.delenv(VARIABLE_RUTA)
    assert cargar().version == "1.0.1"


def test_variable_vacia_se_ignora(monkeypatch):
    monkeypatch.setenv(VARIABLE_RUTA, "   ")
    assert cargar().version == "1.0.1"


def test_archivo_inexistente_falla_con_un_mensaje_claro(tmp_path, monkeypatch):
    with pytest.raises(FileNotFoundError, match="no_existe.json"):
        cargar(tmp_path / "no_existe.json")
    monkeypatch.setenv(VARIABLE_RUTA, str(tmp_path / "tampoco.json"))
    with pytest.raises(FileNotFoundError, match=VARIABLE_RUTA):
        cargar()


def test_json_invalido_o_sin_estructura(tmp_path):
    ruta = tmp_path / "roto.json"
    ruta.write_text("{no es json", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON"):
        cargar(ruta)
    with pytest.raises(ValueError, match="sectores"):
        construir({"version": "x", "sectores": {}, "entidades": []})


# ─────────────────────────── integridad ───────────────────────────

def _lst(sectores, entidades) -> Listado:
    return Listado(version="t", fecha="", fuente="", sectores=tuple(sectores),
                   entidades=tuple(entidades), huella="")


def _sec(nombre, *alias) -> Sector:
    return Sector(nombre=nombre, nombre_normalizado=normalizar(nombre), alias=tuple(alias))


def _ent(id, nombre, sector, sigla="", *alias) -> Entidad:
    return Entidad(id=id, nombre=nombre, sigla=sigla,
                   etiqueta=f"{nombre}, {sigla}" if sigla else nombre, sector=sector,
                   tipo="distrital", activa=True, alias=tuple(alias),
                   nombre_normalizado=normalizar(nombre))


def test_integridad_denuncia_cada_problema():
    lst = _lst(
        [_sec("Salud"), _sec(""), _sec("Ambiente", "Salud")],
        [_ent("A", "Entidad A", "Salud", "EA", "Alias común"),
         _ent("B", "entidad a", "Salud", "EB"),                  # nombre repetido (normalizado)
         _ent("C", "Entidad C", "Salud", "EA", "Alias común"),   # sigla repetida; alias a dos entidades
         _ent("D", "Entidad D", "Sector Fantasma"),              # sector inexistente
         _ent("E", "Entidad E", "Salud", "", "Ambiente")],       # alias igual a un sector ajeno
    )
    problemas = "\n".join(integridad(lst))
    assert "Sector #2 sin nombre" in problemas
    assert "«Salud» apunta a dos sectores" in problemas
    assert "Nombre repetido entre entidades" in problemas
    assert "Sigla repetida «EA»" in problemas
    assert "«Alias común» apunta a dos entidades" in problemas
    assert "«Sector Fantasma» no existe" in problemas
    assert "es a la vez la entidad E" in problemas


def test_integridad_tolera_la_grafia_compartida_con_el_propio_sector():
    """«Nacional-ICBF» es alias del sector «Entidades no distritales» y de la entidad
    ICBF, que pertenece a ese sector: la columna de sector y la de entidad traen el
    mismo texto y no hay ambigüedad. Solo se denuncia si el sector es otro."""
    lst = _lst([_sec("Entidades no distritales", "Nacional-ICBF")],
               [_ent("ICBF", "Instituto Colombiano de Bienestar Familiar",
                     "Entidades no distritales", "ICBF", "Nacional-ICBF")])
    assert integridad(lst) == []


def test_integridad_detecta_nombre_normalizado_desactualizado():
    s = Sector(nombre="Salud", nombre_normalizado="saludd")
    e = Entidad(id="X", nombre="Entidad X", sigla="", etiqueta="Entidad X", sector="Salud",
                tipo="", activa=True, nombre_normalizado="otra cosa")
    problemas = integridad(_lst([s], [e]))
    assert any("Sector «Salud»: nombre_normalizado desactualizado" in p for p in problemas)
    assert any("Entidad X: nombre_normalizado desactualizado" in p for p in problemas)


def test_construir_rellena_los_campos_opcionales():
    lst = construir({"sectores": [{"nombre": "Salud"}],
                     "entidades": [{"id": "X", "nombre": "Entidad X", "sector": "Salud"}]})
    e = lst.entidades[0]
    assert (e.etiqueta, e.sigla, e.tipo, e.activa, e.alias, e.nota_revision) == (
        "Entidad X", "", "", True, (), "")
    assert lst.sectores[0].nombre_normalizado == "salud" and e.nombre_normalizado == "entidad x"
    assert lst.version == "" and integridad(lst) == []
