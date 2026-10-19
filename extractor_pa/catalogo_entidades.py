# -*- coding: utf-8 -*-
"""
Listado oficial de sectores y entidades del Distrito: la fuente única.

Por qué existe
--------------
Hasta la 0.22.0 cada aplicativo (alertas-seguimientos, sispp-sdis, sispp-gobierno,
validador, generador…) tenía su propia lista de sectores y entidades, y esta
librería otra más, escrita en código en `catalogo_oficial.py`. Las listas
divergían: la misma entidad en dos sectores, grafías distintas, duplicados. Los
ocho catálogos se consolidaron en un solo JSON (`data/entidades_distrito.json`),
que desde la 0.23.0 viaja dentro del paquete y es la única fuente de la que
salen `SECTORES_OFICIALES`, `ENTIDADES_OFICIALES` y el mapa entidad → sector.

Reglas de administración
------------------------
- El núcleo oficial es estable y **cambia solo con versión**: un sector o una
  entidad nueva, un cambio de nombre o de sector, es una versión nueva del JSON
  (`version`) y de extractor-pa. Ningún aplicativo edita este archivo.
- Las grafías nuevas que aparecen en los formatos las administra cada aplicativo
  como equivalencias propias y se consolidan aquí en bloque, en la versión
  siguiente, como `alias` o como `erratas`.
- **Un alias no es una errata.** Un alias es otra forma legítima de escribir el
  mismo nombre (nombre corto, nombre anterior, sigla con variantes, texto del
  desplegable sin espacios): el aplicativo lo reconoce sin avisar. Una errata es
  una grafía mal escrita que apareció en formatos reales («Secretaría Disrital
  de Gobierno»): el aplicativo la reconoce para agrupar bien, pero el Validador
  debe avisar para que la entidad corrija su formato. Hasta el listado 1.0.0
  iban mezcladas en `alias`; desde el 1.0.1 van en campos separados y
  `clasificar_entidad` / `clasificar_sector` dicen con cuál coincidió una grafía.
- La coincidencia es **determinista**: exacta tras normalizar (etiqueta, nombre,
  sigla, alias o errata) o por clave compacta, sin espacios, para los
  desplegables tipo «IntegraciónSocial». No hay coincidencia difusa: una grafía
  desconocida devuelve `None` y el aplicativo decide qué hacer con ella.
- `EXTRACTOR_PA_LISTADO` (variable de entorno) hace leer otro archivo. Es un
  camino de urgencia —un error del listado que no puede esperar a la versión
  siguiente—, no la forma normal de agregar entidades.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

#: JSON del paquete (se declara en `package-data` para que llegue al instalar).
RUTA_LISTADO = Path(__file__).with_name("data") / "entidades_distrito.json"

#: Variable de entorno con la ruta de un listado alternativo (camino de urgencia).
VARIABLE_RUTA = "EXTRACTOR_PA_LISTADO"

#: Clases de coincidencia que devuelven `clasificar_entidad` y `clasificar_sector`.
OFICIAL = "oficial"   # nombre, etiqueta o sigla
ALIAS = "alias"       # un alias, o la clave compacta de un nombre oficial o de un alias
ERRATA = "errata"     # una errata (o su clave compacta)
CLASES = (OFICIAL, ALIAS, ERRATA)   # en orden de precedencia

_NO_ALFANUMERICO = re.compile(r"[^a-zA-Z0-9]+")
_ESPACIOS = re.compile(r"\s+")


# ───────────────────────────── normalización ─────────────────────────────

def normalizar(texto) -> str:
    """Regla única de comparación de nombres de entidad y sector.

    NFKD sin tildes, minúsculas, solo letras, dígitos y espacios (la puntuación
    pasa a ser espacio) y espacios colapsados. Así «Instituto de Desarrollo
    Urbano - IDU», «Instituto de Desarrollo Urbano, IDU» e «INSTITUTO DE
    DESARROLLO URBANO IDU» resuelven a la misma clave. Es la misma regla que
    `normalizar_texto` de Alertas-Seguimientos y la que produjo el campo
    `nombre_normalizado` del JSON, de modo que las claves que un aplicativo
    administra desde su interfaz son intercambiables con las de este listado.
    """
    if texto is None:
        return ""
    s = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return _ESPACIOS.sub(" ", _NO_ALFANUMERICO.sub(" ", s).lower()).strip()


def clave_compacta(texto) -> str:
    """`normalizar` sin espacios: «IntegraciónSocial» e «Integración Social» dan
    «integracionsocial». Para los desplegables que pegan las palabras."""
    return normalizar(texto).replace(" ", "")


# ───────────────────────────── modelo ─────────────────────────────

def _clasificadas(oficiales, alias, erratas) -> Tuple[Tuple[str, str], ...]:
    """(grafía, clase) en orden de precedencia —oficiales, alias, erratas—, sin vacíos."""
    pares = ([(g, OFICIAL) for g in oficiales] + [(g, ALIAS) for g in alias]
             + [(g, ERRATA) for g in erratas])
    return tuple((g, clase) for g, clase in pares if g)


@dataclass(frozen=True)
class Sector:
    nombre: str
    nombre_normalizado: str
    alias: Tuple[str, ...] = ()
    erratas: Tuple[str, ...] = ()

    def grafias_clasificadas(self) -> Tuple[Tuple[str, str], ...]:
        """Cada grafía con su clase, en orden de precedencia: el nombre («oficial»),
        los alias («alias») y las erratas («errata»); sin vacíos."""
        return _clasificadas((self.nombre,), self.alias, self.erratas)

    def grafias(self) -> Tuple[str, ...]:
        """Todas las formas escritas que resuelven a este sector: nombre, alias y erratas."""
        return tuple(g for g, _ in self.grafias_clasificadas())


@dataclass(frozen=True)
class Entidad:
    id: str
    nombre: str
    sigla: str
    etiqueta: str
    sector: str
    tipo: str
    activa: bool
    alias: Tuple[str, ...] = ()
    nota_revision: str = ""
    nombre_normalizado: str = ""
    erratas: Tuple[str, ...] = ()

    def grafias_clasificadas(self) -> Tuple[Tuple[str, str], ...]:
        """Cada grafía con su clase, en orden de precedencia: etiqueta, nombre y
        sigla («oficial»), los alias («alias») y las erratas («errata»); sin vacíos."""
        return _clasificadas((self.etiqueta, self.nombre, self.sigla), self.alias, self.erratas)

    def grafias(self) -> Tuple[str, ...]:
        """Todas las formas escritas que resuelven a esta entidad: etiqueta,
        nombre, sigla, alias y erratas (sin vacíos)."""
        return tuple(g for g, _ in self.grafias_clasificadas())

    def nombres_oficiales(self) -> Tuple[str, ...]:
        """Las grafías oficiales (ni alias ni erratas): nombre, etiqueta y sigla."""
        return tuple(g for g in (self.nombre, self.etiqueta, self.sigla) if g)


def _indexar(objetos) -> Tuple[Dict[str, tuple], Dict[str, tuple]]:
    """Índices {clave normalizada: (objeto, clase)} y {clave compacta: (objeto, clase)}.

    Se llenan por clases, en el orden de `CLASES`, y dentro de cada clase en el
    orden del archivo: la primera aparición gana, así que una grafía legítima
    manda sobre una errata igual aunque esa errata esté antes en el listado
    (`integridad` denuncia esa contradicción). En el índice compacto, un nombre
    oficial o un alias valen como «alias»: coincidir con las palabras pegadas no
    es haber escrito el nombre oficial."""
    por_clave: Dict[str, tuple] = {}
    por_compacta: Dict[str, tuple] = {}
    pares = [(g, clase, o) for o in objetos for g, clase in o.grafias_clasificadas()]
    for rango in CLASES:
        for g, clase, o in pares:
            if clase != rango:
                continue
            k = normalizar(g)
            if not k:
                continue
            por_clave.setdefault(k, (o, clase))
            por_compacta.setdefault(k.replace(" ", ""), (o, ERRATA if clase == ERRATA else ALIAS))
    return por_clave, por_compacta


@dataclass(frozen=True)
class Listado:
    """El listado cargado, con sus índices de búsqueda.

    `huella` es el sha256 del JSON canónico: cambia si cambia cualquier dato
    (un alias, una errata, un sector), no si cambia el formato del archivo."""
    version: str
    fecha: str
    fuente: str
    sectores: Tuple[Sector, ...]
    entidades: Tuple[Entidad, ...]
    huella: str
    _entidades_por_clave: Dict[str, tuple] = field(default_factory=dict, repr=False, compare=False)
    _entidades_por_compacta: Dict[str, tuple] = field(default_factory=dict, repr=False, compare=False)
    _sectores_por_clave: Dict[str, tuple] = field(default_factory=dict, repr=False, compare=False)
    _sectores_por_compacta: Dict[str, tuple] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self):
        ent_clave, ent_comp = _indexar(self.entidades)
        sec_clave, sec_comp = _indexar(self.sectores)
        object.__setattr__(self, "_entidades_por_clave", ent_clave)
        object.__setattr__(self, "_entidades_por_compacta", ent_comp)
        object.__setattr__(self, "_sectores_por_clave", sec_clave)
        object.__setattr__(self, "_sectores_por_compacta", sec_comp)

    def entidad(self, nombre) -> Optional[Entidad]:
        """La entidad que corresponde a una grafía, o None. Ver `canonizar_entidad`."""
        return canonizar_entidad(nombre, self)

    def sector(self, nombre) -> Optional[Sector]:
        """El sector que corresponde a una grafía, o None. Ver `canonizar_sector`."""
        return canonizar_sector(nombre, self)

    def sector_de(self, entidad) -> Optional[str]:
        """Nombre del sector al que pertenece una entidad (por cualquiera de sus
        grafías), o None si la entidad no está en el listado."""
        e = self.entidad(entidad)
        return e.sector if e is not None else None


# ───────────────────────────── carga ─────────────────────────────

_CACHE: Dict[str, Tuple[Tuple[int, int], Listado]] = {}


def ruta_listado() -> Path:
    """Ruta que `cargar()` usa sin argumento: la de `EXTRACTOR_PA_LISTADO` si la
    variable está definida y no vacía; si no, el JSON del paquete."""
    valor = os.environ.get(VARIABLE_RUTA, "").strip()
    return Path(valor).expanduser() if valor else RUTA_LISTADO


def cargar(ruta=None) -> Listado:
    """Carga el listado: el del paquete, el de `EXTRACTOR_PA_LISTADO` o el de `ruta`.

    Un `ruta` explícito manda sobre la variable de entorno. Se guarda en caché
    por (ruta, mtime, tamaño): llamarlo en cada validación es gratis y, si el
    archivo cambia en disco, la carga siguiente lo recoge. Lanza
    `FileNotFoundError` si el archivo no está —al instalar, el JSON llega por
    `package-data`; en un ejecutable congelado (PyInstaller) hay que incluir
    `extractor_pa/data/*.json`— y `ValueError` si no tiene la estructura esperada.
    """
    por_variable = ruta is None and bool(os.environ.get(VARIABLE_RUTA, "").strip())
    ruta = Path(ruta).expanduser() if ruta is not None else ruta_listado()
    try:
        st = ruta.stat()
    except OSError as exc:
        origen = f" (tomada de la variable {VARIABLE_RUTA})" if por_variable else ""
        raise FileNotFoundError(
            f"No se encuentra el listado oficial de entidades y sectores: {ruta}{origen}. "
            "Al instalar el paquete debe llegar en extractor_pa/data/ (package-data); en un "
            "ejecutable congelado hay que empaquetar extractor_pa/data/*.json.") from exc
    clave = os.fspath(ruta.resolve())
    firma = (st.st_mtime_ns, st.st_size)
    en_cache = _CACHE.get(clave)
    if en_cache is not None and en_cache[0] == firma:
        return en_cache[1]
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"El listado de entidades {ruta} no es un JSON válido: {exc}") from exc
    listado = construir(crudo)
    _CACHE[clave] = (firma, listado)
    return listado


cargar_listado = cargar   # nombre con el que lo exporta `extractor_pa`


def _tupla(valores) -> Tuple[str, ...]:
    return tuple(str(v) for v in (valores or ()))


def construir(crudo: dict) -> Listado:
    """Arma un `Listado` desde el dict del JSON (sin tocar el disco).

    Campos opcionales de cada entidad: `sigla`, `tipo`, `nota_revision` (vacíos),
    `etiqueta` (el nombre), `activa` (True), `alias` y `erratas` (ninguno); de
    cada sector, `alias`, `erratas` y `nombre_normalizado` (se calcula). Un
    listado 1.0.0, que no trae `erratas`, carga igual. La huella se toma del JSON
    canónico (claves ordenadas, sin espacios), para que no dependa del formato."""
    if (not isinstance(crudo, dict) or not isinstance(crudo.get("sectores"), list)
            or not isinstance(crudo.get("entidades"), list)):
        raise ValueError("El listado de entidades debe ser un objeto JSON con las listas "
                         "'sectores' y 'entidades'.")
    canonico = json.dumps(crudo, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    huella = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
    sectores = tuple(
        Sector(nombre=str(s.get("nombre") or ""),
               nombre_normalizado=str(s.get("nombre_normalizado") or normalizar(s.get("nombre"))),
               alias=_tupla(s.get("alias")),
               erratas=_tupla(s.get("erratas")))
        for s in crudo["sectores"])
    entidades = tuple(
        Entidad(id=str(e.get("id") or ""),
                nombre=str(e.get("nombre") or ""),
                sigla=str(e.get("sigla") or ""),
                etiqueta=str(e.get("etiqueta") or e.get("nombre") or ""),
                sector=str(e.get("sector") or ""),
                tipo=str(e.get("tipo") or ""),
                activa=bool(e.get("activa", True)),
                alias=_tupla(e.get("alias")),
                nota_revision=str(e.get("nota_revision") or ""),
                nombre_normalizado=str(e.get("nombre_normalizado") or normalizar(e.get("nombre"))),
                erratas=_tupla(e.get("erratas")))
        for e in crudo["entidades"])
    return Listado(version=str(crudo.get("version") or ""),
                   fecha=str(crudo.get("fecha") or ""),
                   fuente=str(crudo.get("fuente") or ""),
                   sectores=sectores, entidades=entidades, huella=huella)


def _listado(listado: Optional[Listado]) -> Listado:
    return listado if listado is not None else cargar()


# ───────────────────────────── consultas ─────────────────────────────

def _buscar(clave: str, por_clave: Dict[str, tuple], por_compacta: Dict[str, tuple]) -> tuple:
    """(clase, objeto) para una clave ya normalizada: exacta y, si no, compacta."""
    par = por_clave.get(clave)
    if par is None:
        par = por_compacta.get(clave.replace(" ", ""))
    if par is None:
        return None, None
    objeto, clase = par
    return clase, objeto


def clasificar_entidad(nombre, listado: Optional[Listado] = None) -> Tuple[Optional[str], Optional[Entidad]]:
    """Con qué clase de grafía coincide `nombre` y a qué entidad corresponde.

    `("oficial", e)` si es su nombre, etiqueta o sigla; `("alias", e)` si es un
    alias o la clave compacta de un nombre oficial o de un alias; `("errata", e)`
    si es una errata (o su clave compacta); `(None, None)` si no coincide con
    nada. Es la función para quien tiene que avisar y no solo agrupar: el
    Validador acepta «oficial» y «alias» en silencio y, ante una «errata», pide
    a la entidad corregir su formato. Misma búsqueda que `canonizar_entidad`:
    exacta tras `normalizar` —etiqueta, nombre, sigla y alias antes que las
    erratas— y, si no, por clave compacta."""
    clave = normalizar(nombre)
    if not clave:
        return None, None
    lst = _listado(listado)
    return _buscar(clave, lst._entidades_por_clave, lst._entidades_por_compacta)


def clasificar_sector(nombre, listado: Optional[Listado] = None) -> Tuple[Optional[str], Optional[Sector]]:
    """Con qué clase de grafía coincide `nombre` y a qué sector corresponde:
    `("oficial", s)` por el nombre, `("alias", s)` por un alias o una clave
    compacta, `("errata", s)` por una errata, `(None, None)` si no coincide.
    Ver `clasificar_entidad`."""
    clave = normalizar(nombre)
    if not clave:
        return None, None
    lst = _listado(listado)
    return _buscar(clave, lst._sectores_por_clave, lst._sectores_por_compacta)


def canonizar_entidad(nombre, listado: Optional[Listado] = None) -> Optional[Entidad]:
    """La entidad oficial a la que corresponde una grafía, o None.

    Coincidencia exacta tras `normalizar` contra etiqueta, nombre, sigla y alias,
    después contra las erratas y, si no, por `clave_compacta`. Sin coincidencia
    difusa: «Secretaría Distrital de Ambientes» no es «Secretaría Distrital de
    Ambiente». Las entidades inactivas también resuelven, para que los datos
    históricos sigan cruzando. Para saber si la grafía era oficial, alias o
    errata, `clasificar_entidad`."""
    return clasificar_entidad(nombre, listado)[1]


def canonizar_sector(nombre, listado: Optional[Listado] = None) -> Optional[Sector]:
    """El sector oficial al que corresponde una grafía (nombre, alias o errata),
    o None. Misma regla que `canonizar_entidad`: exacta normalizada y luego
    compacta. Para saber con qué clase coincidió, `clasificar_sector`."""
    return clasificar_sector(nombre, listado)[1]


def sector_de(entidad_nombre, listado: Optional[Listado] = None) -> Optional[str]:
    """Nombre del sector oficial de una entidad (por cualquiera de sus grafías),
    o None si no está en el listado."""
    e = canonizar_entidad(entidad_nombre, listado)
    return e.sector if e is not None else None


def entidad_sector_norm(listado: Optional[Listado] = None) -> Dict[str, str]:
    """Mapa {grafía normalizada con `normalizar`: nombre del sector} para todas
    las grafías de todas las entidades (etiqueta, nombre, sigla, alias y erratas:
    una errata también debe cruzar con su sector).

    Es lo que los aplicativos inyectan como `entidad_sector` a
    `seguimiento.validacion_seg.validar_consistencia` para la regla
    ADVERTENCIA_SECTOR_ENTIDAD. Devuelve un dict nuevo cada vez."""
    lst = _listado(listado)
    return {normalizar(g): e.sector for e in lst.entidades for g in e.grafias() if normalizar(g)}


def sectores_oficiales(listado: Optional[Listado] = None) -> FrozenSet[str]:
    """Los nombres oficiales de los sectores (ni alias ni erratas)."""
    return frozenset(s.nombre for s in _listado(listado).sectores if s.nombre)


def entidades_oficiales(listado: Optional[Listado] = None) -> FrozenSet[str]:
    """Las grafías oficiales de las entidades: nombre, etiqueta y sigla (sin los
    alias, que son equivalencias de grafías no oficiales, ni las erratas).
    Incluye las inactivas: un dato histórico escrito con el nombre oficial de
    entonces no es un error de grafía."""
    return frozenset(g for e in _listado(listado).entidades for g in e.nombres_oficiales())


# ───────────────────────────── integridad ─────────────────────────────

def integridad(listado: Listado) -> List[str]:
    """Problemas del listado, uno por mensaje. Lista vacía = íntegro.

    Revisa lo que haría ambigua la canonización o incoherente el mapa
    entidad → sector: sector sin nombre o repetido; entidad sin nombre, con `id`
    repetido o con un sector que no existe; nombre normalizado repetido entre
    entidades; una misma grafía (o clave compacta) que apunta a dos entidades o
    a dos sectores; sigla repetida; una grafía compartida por una entidad y un
    sector **distinto del suyo** (si es su propio sector no es ambigua: la
    columna de sector y la de entidad traen a veces el mismo texto); y
    `nombre_normalizado` desactualizado.

    Y lo que confundiría los alias con las erratas, porque de esa distinción
    depende que el Validador avise o calle: un alias que repite el nombre, la
    etiqueta o la sigla de su propia entidad (o el nombre de su propio sector)
    sobra; una errata que repite un nombre oficial o un alias —de la misma
    entidad o de otra, del mismo sector o de otro— es una contradicción, porque
    la misma grafía no puede ser legítima y errónea a la vez; y una errata que
    está en dos entidades o en dos sectores es ambigua."""
    problemas: List[str] = []
    nombres_sector = {s.nombre for s in listado.sectores if s.nombre}

    sector_de_grafia: Dict[str, str] = {}      # nombre o alias normalizado → sector
    sector_de_errata: Dict[str, str] = {}      # errata normalizada → sector
    sector_de_compacta: Dict[str, str] = {}    # clave compacta de cualquier grafía → sector
    for i, s in enumerate(listado.sectores):
        if not s.nombre:
            problemas.append(f"Sector #{i + 1} sin nombre.")
            continue
        kn = normalizar(s.nombre)
        if s.nombre_normalizado != kn:
            problemas.append(f"Sector «{s.nombre}»: nombre_normalizado desactualizado "
                             f"(«{s.nombre_normalizado}» ≠ «{kn}»).")
        for g, clase in s.grafias_clasificadas():
            k = normalizar(g)
            if not k:
                problemas.append(f"Sector «{s.nombre}»: {'errata vacía' if clase == ERRATA else 'alias vacío'}.")
                continue
            if clase == ALIAS and k == kn:
                problemas.append(f"Sector «{s.nombre}»: el alias «{g}» repite su propio nombre.")
            mapa = sector_de_errata if clase == ERRATA else sector_de_grafia
            if mapa.get(k, s.nombre) != s.nombre:
                problemas.append(f"La {'errata' if clase == ERRATA else 'grafía'} «{g}» apunta a dos "
                                 f"sectores: «{mapa[k]}» y «{s.nombre}».")
            mapa.setdefault(k, s.nombre)
            c = k.replace(" ", "")
            if sector_de_compacta.get(c, s.nombre) != s.nombre:
                problemas.append(f"La clave compacta «{c}» apunta a dos sectores: "
                                 f"«{sector_de_compacta[c]}» y «{s.nombre}».")
            sector_de_compacta.setdefault(c, s.nombre)
    # Segunda pasada: el nombre o alias que una errata repite puede venir después.
    for s in listado.sectores:
        for g in s.erratas:
            k = normalizar(g)
            if k in sector_de_grafia:
                otro = sector_de_grafia[k]
                donde = "del mismo sector" if otro == s.nombre else f"del sector «{otro}»"
                problemas.append(f"Sector «{s.nombre}»: la errata «{g}» repite el nombre o un alias {donde}.")
    sector_de_cualquiera = {**sector_de_errata, **sector_de_grafia}

    ids: Dict[str, str] = {}
    nombres: Dict[str, str] = {}
    siglas: Dict[str, str] = {}
    entidad_de_grafia: Dict[str, str] = {}     # nombre, etiqueta, sigla o alias normalizado → ref
    clase_de_grafia: Dict[str, str] = {}       # … y con qué clase entró
    entidad_de_errata: Dict[str, str] = {}     # errata normalizada → ref
    entidad_de_compacta: Dict[str, str] = {}   # clave compacta de cualquier grafía → ref
    refs: List[str] = []
    for i, e in enumerate(listado.entidades):
        ref = e.id or e.nombre or f"#{i + 1}"
        refs.append(ref)
        if not e.nombre:
            problemas.append(f"Entidad {ref}: sin nombre.")
        if not e.id:
            problemas.append(f"Entidad «{e.nombre}»: sin id.")
        elif e.id in ids:
            problemas.append(f"Id repetido «{e.id}»: «{ids[e.id]}» y «{e.nombre}».")
        ids.setdefault(e.id, e.nombre)
        if e.sector not in nombres_sector:
            problemas.append(f"Entidad {ref}: el sector «{e.sector}» no existe en el listado.")
        if e.nombre and e.nombre_normalizado != normalizar(e.nombre):
            problemas.append(f"Entidad {ref}: nombre_normalizado desactualizado "
                             f"(«{e.nombre_normalizado}» ≠ «{normalizar(e.nombre)}»).")
        kn = normalizar(e.nombre)
        if kn and kn in nombres:
            problemas.append(f"Nombre repetido entre entidades: «{nombres[kn]}» y «{e.nombre}».")
        nombres.setdefault(kn, e.nombre)
        ks = normalizar(e.sigla)
        if ks:
            if ks in siglas:
                problemas.append(f"Sigla repetida «{e.sigla}»: «{siglas[ks]}» y «{e.nombre}».")
            siglas.setdefault(ks, e.nombre)
        propias = {normalizar(g) for g in e.nombres_oficiales()}
        for g, clase in e.grafias_clasificadas():
            k = normalizar(g)
            if not k:
                problemas.append(f"Entidad {ref}: {'errata vacía' if clase == ERRATA else 'alias vacío'}.")
                continue
            if clase == ALIAS and k in propias:
                problemas.append(f"Entidad {ref}: el alias «{g}» repite su propio nombre, etiqueta o sigla.")
            mapa = entidad_de_errata if clase == ERRATA else entidad_de_grafia
            if mapa.get(k, ref) != ref:
                problemas.append(f"La {'errata' if clase == ERRATA else 'grafía'} «{g}» apunta a dos "
                                 f"entidades: {mapa[k]} y {ref}.")
            mapa.setdefault(k, ref)
            if clase != ERRATA:
                clase_de_grafia.setdefault(k, clase)
            c = k.replace(" ", "")
            if entidad_de_compacta.get(c, ref) != ref:
                problemas.append(f"La clave compacta «{c}» apunta a dos entidades: "
                                 f"{entidad_de_compacta[c]} y {ref}.")
            entidad_de_compacta.setdefault(c, ref)
            if k in sector_de_cualquiera and sector_de_cualquiera[k] != e.sector:
                problemas.append(f"La grafía «{g}» es a la vez la entidad {ref} (sector "
                                 f"«{e.sector}») y el sector «{sector_de_cualquiera[k]}».")
    # Segunda pasada: el nombre oficial o alias que una errata repite puede venir después.
    for ref, e in zip(refs, listado.entidades):
        for g in e.erratas:
            k = normalizar(g)
            if k in entidad_de_grafia:
                otro = entidad_de_grafia[k]
                que = "el nombre oficial" if clase_de_grafia.get(k) == OFICIAL else "un alias"
                donde = "de la misma entidad" if otro == ref else f"de {otro}"
                problemas.append(f"Entidad {ref}: la errata «{g}» repite {que} {donde}.")
    return problemas


__all__ = [
    "RUTA_LISTADO", "VARIABLE_RUTA",
    "OFICIAL", "ALIAS", "ERRATA", "CLASES",
    "Sector", "Entidad", "Listado",
    "normalizar", "clave_compacta",
    "ruta_listado", "cargar", "cargar_listado", "construir",
    "clasificar_entidad", "clasificar_sector",
    "canonizar_entidad", "canonizar_sector", "sector_de", "entidad_sector_norm",
    "sectores_oficiales", "entidades_oficiales", "integridad",
]
