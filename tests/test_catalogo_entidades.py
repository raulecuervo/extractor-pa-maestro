# -*- coding: utf-8 -*-
"""Pruebas del listado oficial de sectores y entidades (`catalogo_entidades`).

El listado es la fuente única de `SECTORES_OFICIALES`, `ENTIDADES_OFICIALES` y
del mapa entidad → sector. Estas pruebas fijan lo que los aplicativos pueden dar
por sentado: el JSON publicado es íntegro y versionado, la canonización es
determinista (sin coincidencia difusa), los alias y las erratas van separados
—y `clasificar_*` dice con cuál coincidió una grafía— y la huella cambia si
cambian los datos.
"""

import json

import pytest

from extractor_pa.catalogo_entidades import (
    ALIAS, ERRATA, OFICIAL, RUTA_LISTADO, VARIABLE_RUTA, Entidad, Listado, Sector,
    canonizar_entidad, canonizar_sector, cargar, clasificar_entidad, clasificar_sector,
    clave_compacta, construir, entidad_sector_norm, entidades_oficiales, integridad,
    normalizar, sector_de, sectores_oficiales,
)

#: Versión del listado que viaja en el paquete. Cambia solo con una versión nueva
#: del listado (y de la librería).
VERSION = "1.0.2"


def _json_publicado() -> dict:
    return json.loads(RUTA_LISTADO.read_text(encoding="utf-8"))


def _escribir(ruta, datos, indent=2):
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=indent), encoding="utf-8")
    return ruta


# ─────────────────────────── el JSON publicado ───────────────────────────

def test_el_listado_publicado_es_integro():
    assert integridad(cargar()) == []


def test_version_publicada():
    """La versión cambia solo con una versión nueva del listado (y de la librería).
    El número de sectores y entidades no se fija aquí: lo que importa es que el
    listado sea íntegro, no su tamaño."""
    lst = cargar()
    assert lst.version == VERSION
    assert lst.fecha and lst.fuente
    assert lst.sectores and lst.entidades
    assert integridad(lst) == []


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
    """Resuelve por la sigla («Invest in Bogotá»): ya no hace falta un alias que
    la repita sin tilde, porque la comparación normaliza."""
    clase, e = clasificar_entidad(grafia)
    assert clase == OFICIAL
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
    assert canonizar_entidad("Secretaría de Ambiente") is e                   # alias (1.0.1)
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
    assert clasificar_entidad(grafia) == (None, None)
    assert clasificar_sector(grafia) == (None, None)


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


# ─────────────────────────── alias y erratas ───────────────────────────
# Un alias es otra forma legítima de escribir el mismo nombre: se reconoce sin
# avisar. Una errata es una grafía mal escrita que apareció en formatos reales:
# se reconoce para agrupar bien, pero el Validador debe avisar. Desde el listado
# 1.0.1 van en campos separados.

ERRATAS_DE_SECTOR = [
    ("Cultura, Recrecación y Deporte", "Cultura, Recreación y Deporte"),
    ("Desarrollo Econimico", "Desarrollo Económico, Industria y Turismo"),
    ("Secretaría, Convivencia y Justicia", "Seguridad, Convivencia y Justicia"),
    ("Entidades No Distrtitales", "Entidades no distritales"),
]

ERRATAS_DE_ENTIDAD = [
    ("Instituto Disitrital de Gestión de Riesgos y Cambio Climático IDIGER", "IDIGER"),
    ("Instituto Disitrital de Protección y Bienestar Animal", "IDPYBA"),
    ("Corporación para el Desarollo y la productividad Bogotá Región Invest In Bogotá", "INVEST"),
    ("Agencia Distrital para la Eduacción Superior, la Ciencia y la Tecnología", "ATENEA"),
    ("Secretaría de Educación del Distrital", "SED"),
    ("Secretaría de Educación del Distrito (SDE)", "SED"),
    ("Insituto Distrital de la Participación y Acción Comunal - IDPAC", "IDPAC"),
    ("Secretaría Disrital de Gobierno", "SDG"),
    ("Unidad Administrativa Especial de Serecios Publicos - UAESP", "UAESP"),
    ("Secretaria Distrial de Integración Social", "SDIS"),
    ("Entidades No Distrtitales", "NO_DISTRITALES"),
    # Listado 1.0.2: planes de acción de sispp-gobierno (oct-2026).
    ("Secretaría Distrittal de Gobierno", "SDG"),
    ("Instituto Distrital de la Participacón y Acción Comunal", "IDPAC"),
    ("TRANSMILENO S.A", "TRANSMILENIO"),
    ("Secretaría de Cultura Recreación y Deportes", "SCRD"),
    ("Secretaría Distrital de Integración - SDIS", "SDIS"),
    ("Region Administrativa de Planeación Especial", "RAPE"),
]


@pytest.mark.parametrize("grafia,sector", ERRATAS_DE_SECTOR)
def test_la_errata_de_sector_resuelve_pero_se_clasifica_como_errata(grafia, sector):
    assert canonizar_sector(grafia).nombre == sector
    clase, s = clasificar_sector(grafia)
    assert clase == ERRATA and s.nombre == sector
    assert grafia in s.erratas and grafia not in s.alias


@pytest.mark.parametrize("grafia,id_entidad", ERRATAS_DE_ENTIDAD)
def test_la_errata_de_entidad_resuelve_pero_se_clasifica_como_errata(grafia, id_entidad):
    assert canonizar_entidad(grafia).id == id_entidad
    clase, e = clasificar_entidad(grafia)
    assert clase == ERRATA and e.id == id_entidad
    assert grafia in e.erratas and grafia not in e.alias
    assert sector_de(grafia) == e.sector                      # agrupa, aunque avise


# Listado 1.0.2: grafías legítimas que aparecieron en los planes de acción de
# sispp-gobierno (oct-2026) y que hasta la 1.0.1 solo resolvía el fuzzy del
# aplicativo. Se reconocen sin avisar.
ALIAS_1_0_2_DE_ENTIDAD = [
    ("Secretaría del Hábitat", "SDHT"),
    ("Secretaría del Habitat", "SDHT"),                       # como viene en el plan
    ("Secretaría Distrital de Hábitat y Territorio", "SDHT"),
    ("Empresa Metro", "EMB"),
    ("Secretaría Distrital de Seguridad y Convivencia", "SDSCJ"),
]

ALIAS_1_0_2_DE_SECTOR = [
    ("Desarrollo Económico y Turismo", "Desarrollo Económico, Industria y Turismo"),
    ("Integración", "Integración Social"),
    ("Sector Planeación", "Planeación"),
]


@pytest.mark.parametrize("grafia,id_entidad", ALIAS_1_0_2_DE_ENTIDAD)
def test_alias_de_entidad_1_0_2(grafia, id_entidad):
    clase, e = clasificar_entidad(grafia)
    assert (clase, e.id) == (ALIAS, id_entidad)


@pytest.mark.parametrize("grafia,sector", ALIAS_1_0_2_DE_SECTOR)
def test_alias_de_sector_1_0_2(grafia, sector):
    clase, s = clasificar_sector(grafia)
    assert (clase, s.nombre) == (ALIAS, sector)
    assert canonizar_entidad(grafia) is None          # no es una entidad


def test_la_errata_con_otros_acentos_tambien_resuelve():
    """«Recreaciòn» (acento grave) y «deportes» en minúscula: la misma clave."""
    assert clasificar_entidad("Secretaria de Cultura Recreaciòn y Deportes") == (
        ERRATA, canonizar_entidad("SCRD"))


def test_toda_grafia_del_listado_se_clasifica_con_su_dueno():
    """Lo que vale para las grafías de arriba vale para todas las del JSON: cada
    nombre oficial, alias y errata resuelve a su dueño con su clase, de modo que
    ninguna errata queda tapada por un alias igual ni al revés."""
    lst = cargar()
    for s in lst.sectores:
        assert clasificar_sector(s.nombre) == (OFICIAL, s)
        for g in s.alias:
            assert clasificar_sector(g) == (ALIAS, s), g
        for g in s.erratas:
            assert clasificar_sector(g) == (ERRATA, s), g
    for e in lst.entidades:
        for g in e.nombres_oficiales():
            assert clasificar_entidad(g) == (OFICIAL, e), g
        for g in e.alias:
            assert clasificar_entidad(g) == (ALIAS, e), g
        for g in e.erratas:
            assert clasificar_entidad(g) == (ERRATA, e), g


def test_clasificar_entidad_distingue_oficial_alias_y_errata():
    sdm = canonizar_entidad("SDM")
    assert clasificar_entidad("SDM") == (OFICIAL, sdm)
    assert clasificar_entidad("Secretaría Distrital de Movilidad, SDM") == (OFICIAL, sdm)
    assert clasificar_entidad("Secretaría de Movilidad") == (ALIAS, sdm)            # alias nuevo en 1.0.1
    assert clasificar_entidad("SecretaríaDistritalDeMovilidad") == (ALIAS, sdm)     # clave compacta del nombre
    assert clasificar_entidad("Secretaría de Ambiente") == (ALIAS, canonizar_entidad("SDA"))
    assert clasificar_entidad("Secretaria Distrial de Integración Social") == (ERRATA, canonizar_entidad("SDIS"))
    assert clasificar_entidad("SecretariaDistrialDeIntegraciónSocial")[0] == ERRATA  # compacta de una errata
    assert clasificar_entidad("Metrovivienda")[0] == OFICIAL                         # inactiva, pero oficial


def test_clasificar_sector_distingue_oficial_alias_y_errata():
    social = canonizar_sector("Integración Social")
    assert clasificar_sector("Integración Social") == (OFICIAL, social)
    assert clasificar_sector("Sector Social") == (ALIAS, social)
    assert clasificar_sector("IntegraciónSocial") == (ALIAS, social)                 # clave compacta
    assert clasificar_sector("Cultura, Recrecación y Deporte")[0] == ERRATA


def test_sdh_es_hacienda_y_no_habitat():
    """«SDH» es la sigla de Hacienda. La SDHT tenía el alias «Secretaría Distrital
    del Hábitat (SDH)», que una búsqueda por sigla confundiría; se retiró."""
    assert clasificar_entidad("SDH")[1].sector == "Hacienda"
    habitat = canonizar_entidad("SDHT")
    assert habitat.sector == "Hábitat"
    assert all("sdh" not in normalizar(g).split() for g in habitat.grafias())


def test_nacional_icbf_es_la_entidad_icbf_y_no_un_sector():
    """«Nacional-ICBF» es una grafía de la entidad ICBF; no es un sector, así que
    ya no está entre los alias del sector «Entidades no distritales»."""
    assert clasificar_entidad("Nacional-ICBF") == (ALIAS, canonizar_entidad("ICBF"))
    assert clasificar_sector("Nacional-ICBF") == (None, None)
    assert canonizar_sector("Nacional").nombre == "Entidades no distritales"   # ese alias sí queda


def test_ningun_alias_repite_una_grafia_oficial_de_su_dueno():
    """Un alias que repite el nombre, la etiqueta o la sigla de su propia entidad
    (o el nombre de su propio sector) sobra: `integridad` lo denuncia y el JSON
    publicado no lo tiene."""
    lst = cargar()
    for e in lst.entidades:
        propias = {normalizar(g) for g in e.nombres_oficiales()}
        assert not propias & {normalizar(a) for a in e.alias}, e.id
    for s in lst.sectores:
        assert normalizar(s.nombre) not in {normalizar(a) for a in s.alias}, s.nombre


def test_un_listado_1_0_0_sin_erratas_carga_igual(tmp_path):
    """El campo `erratas` llegó en el listado 1.0.1; un JSON 1.0.0 (sin él) carga
    con erratas vacías, íntegro, y simplemente no reconoce las grafías mal escritas."""
    datos = _json_publicado()
    for x in datos["sectores"] + datos["entidades"]:
        del x["erratas"]
    datos["version"] = "1.0.0"
    lst = cargar(_escribir(tmp_path / "listado_100.json", datos))
    assert lst.version == "1.0.0" and len(lst.entidades) == len(cargar().entidades)
    assert all(x.erratas == () for x in lst.sectores + lst.entidades)
    assert integridad(lst) == []
    assert clasificar_entidad("SDIS", lst) == (OFICIAL, lst.entidad("SDIS"))
    assert canonizar_entidad("Secretaria Distrial de Integración Social", lst) is None
    assert canonizar_sector("Desarrollo Econimico", lst) is None


# ─────────────────────────── vistas para los consumidores ───────────────────────────

def test_entidad_sector_norm_tiene_las_variantes():
    mapa = entidad_sector_norm()
    assert mapa[normalizar("Nacional-ICBF")] == "Entidades no distritales"
    assert mapa[normalizar("Invest in Bogota")] == "Desarrollo Económico, Industria y Turismo"
    assert mapa[normalizar("Secretaría Distrital de Integración Social, SDIS")] == "Integración Social"
    assert mapa["sdis"] == "Integración Social"
    assert mapa["eru"] == "Hábitat"                               # alias histórico de Renobo
    assert mapa[normalizar("Secretaria Distrial de Integración Social")] == "Integración Social"   # errata
    assert mapa[normalizar("Secretaría Disrital de Gobierno")] == "Gobierno"                     # errata
    assert all(k and k == normalizar(k) for k in mapa)            # claves ya normalizadas
    assert set(mapa.values()) <= sectores_oficiales()


def test_sectores_oficiales_son_los_del_json():
    esperados = {s["nombre"] for s in _json_publicado()["sectores"]}
    assert sectores_oficiales() == esperados
    assert {"Entes de Control", "Concejo de Bogotá", "Entidades no distritales"} <= esperados
    assert "Órganos de Control" not in esperados                   # alias, no nombre oficial
    assert "Desarrollo Econimico" not in esperados                 # errata, menos aún


def test_entidades_oficiales_incluyen_nombre_etiqueta_y_sigla_pero_no_alias_ni_erratas():
    oficiales = entidades_oficiales()
    assert {"Secretaría Distrital de Integración Social",
            "Secretaría Distrital de Integración Social, SDIS", "SDIS"} <= oficiales
    assert "Secretaría de Integración Social" not in oficiales      # alias
    assert "Secretaria Distrial de Integración Social" not in oficiales   # errata
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
    assert cargar(RUTA_LISTADO).version == VERSION         # una ruta explícita manda
    monkeypatch.delenv(VARIABLE_RUTA)
    assert cargar().version == VERSION


def test_variable_vacia_se_ignora(monkeypatch):
    monkeypatch.setenv(VARIABLE_RUTA, "   ")
    assert cargar().version == VERSION


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


def _sec(nombre, *alias, erratas=()) -> Sector:
    return Sector(nombre=nombre, nombre_normalizado=normalizar(nombre), alias=tuple(alias),
                  erratas=tuple(erratas))


def _ent(id, nombre, sector, sigla="", *alias, erratas=()) -> Entidad:
    return Entidad(id=id, nombre=nombre, sigla=sigla,
                   etiqueta=f"{nombre}, {sigla}" if sigla else nombre, sector=sector,
                   tipo="distrital", activa=True, alias=tuple(alias),
                   nombre_normalizado=normalizar(nombre), erratas=tuple(erratas))


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


def test_integridad_denuncia_alias_redundantes_y_erratas_contradictorias():
    """De la distinción alias/errata depende que el Validador avise o calle: un
    alias que repite una grafía oficial de su dueño sobra; una errata que repite
    un nombre oficial o un alias (propio o ajeno) se contradice; una errata en
    dos entidades o dos sectores es ambigua."""
    lst = _lst(
        [_sec("Salud", "salud"),                                      # alias que repite su nombre
         _sec("Ambiente", erratas=("Ambeinte",)),
         _sec("Hábitat", erratas=("Ambeinte",)),                      # la misma errata en dos sectores
         _sec("Gobierno", erratas=("Mujer",)),                        # errata = alias de otro sector (que viene después)
         _sec("Mujeres", "Mujer")],
        [_ent("A", "Entidad A", "Salud", "EA", "EA", "Entidad A, EA"),        # alias = sigla, alias = etiqueta
         _ent("B", "Entidad B", "Salud", "EB", erratas=("Entidad B", "Alias de C")),   # errata = su nombre; = alias ajeno
         _ent("C", "Entidad C", "Salud", "EC", "Alias de C", erratas=("Entidad Z",)),
         _ent("D", "Entidad D", "Salud", "ED", erratas=("Entidad Z",))],    # la misma errata en dos entidades
    )
    problemas = "\n".join(integridad(lst))
    assert "Sector «Salud»: el alias «salud» repite su propio nombre" in problemas
    assert "La errata «Ambeinte» apunta a dos sectores: «Ambiente» y «Hábitat»" in problemas
    assert "Sector «Gobierno»: la errata «Mujer» repite el nombre o un alias del sector «Mujeres»" in problemas
    assert "Entidad A: el alias «EA» repite su propio nombre, etiqueta o sigla" in problemas
    assert "Entidad A: el alias «Entidad A, EA» repite su propio nombre, etiqueta o sigla" in problemas
    assert "Entidad B: la errata «Entidad B» repite el nombre oficial de la misma entidad" in problemas
    assert "Entidad B: la errata «Alias de C» repite un alias de C" in problemas
    assert "La errata «Entidad Z» apunta a dos entidades: C y D" in problemas


def test_integridad_acepta_alias_y_erratas_distintos():
    lst = _lst([_sec("Salud", "Sector Salud", erratas=("Salut",))],
               [_ent("A", "Entidad A", "Salud", "EA", "La A", erratas=("Entidá A",))])
    assert integridad(lst) == []
    assert clasificar_entidad("Entidá A", lst) == (ERRATA, lst.entidades[0])
    assert clasificar_sector("Salut", lst) == (ERRATA, lst.sectores[0])


def test_integridad_tolera_la_grafia_compartida_con_el_propio_sector():
    """Si un sector y una entidad que pertenece a él comparten una grafía (en el
    listado 1.0.0 «Nacional-ICBF» era alias de los dos), no hay ambigüedad: la
    columna de sector y la de entidad traen el mismo texto. Solo se denuncia si
    el sector es otro."""
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
    assert (e.etiqueta, e.sigla, e.tipo, e.activa, e.alias, e.erratas, e.nota_revision) == (
        "Entidad X", "", "", True, (), (), "")
    assert lst.sectores[0].nombre_normalizado == "salud" and lst.sectores[0].erratas == ()
    assert e.nombre_normalizado == "entidad x"
    assert lst.version == "" and integridad(lst) == []
