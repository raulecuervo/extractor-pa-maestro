# -*- coding: utf-8 -*-
"""
Catálogo OFICIAL de sectores y entidades del Distrito (regla V4, opcional).

Habilita la regla **V4** (`sector_no_oficial` / `entidad_no_oficial`) y las
sugerencias de normalización de responsables. Es **opt-in**: si no se inyecta un
catálogo, V4 no se ejecuta y el comportamiento no cambia.

Desde la 0.23.0 aquí no hay listas escritas en código: `SECTORES_OFICIALES` y
`ENTIDADES_OFICIALES` se calculan al importar desde el listado único
`data/entidades_distrito.json` (módulo `catalogo_entidades`), para que esta
librería y los aplicativos validen contra la misma fuente. La normalización
difusa con `rapidfuzz` se retiró: una sugerencia sale solo de una equivalencia
conocida (alias del listado o clave compacta), nunca de un parecido.
"""

from __future__ import annotations

from typing import Iterable, Optional

from .catalogo_entidades import (
    canonizar_entidad, canonizar_sector, clave_compacta, entidad_sector_norm,
    entidades_oficiales, normalizar, sector_de, sectores_oficiales,
)
from .utilidades import _norm

#: Nombres oficiales de los sectores: los del listado (sin alias).
SECTORES_OFICIALES = sectores_oficiales()

#: Grafías oficiales de las entidades: nombre, etiqueta («Nombre, SIGLA») y sigla.
#: Los alias del listado no están aquí: son grafías que se reconocen, no oficiales.
ENTIDADES_OFICIALES = entidades_oficiales()


class CatalogoOficial:
    """Catálogo de sectores/entidades oficiales con sugerencias deterministas.

    Sin argumentos usa el listado oficial completo: la membresía la dan las grafías
    oficiales y las sugerencias salen también de los alias del listado. Con
    `sectores` o `entidades` propios, la membresía y las sugerencias se limitan a
    esa lista (coincidencia normalizada y por clave compacta).

    `umbral_fuzzy` se acepta y se ignora: se conserva para no romper las llamadas
    anteriores a la 0.23.0, cuando existía la normalización difusa.
    """

    def __init__(self, sectores: Optional[Iterable[str]] = None,
                 entidades: Optional[Iterable[str]] = None, umbral_fuzzy: Optional[int] = None):
        self.sectores = frozenset(sectores) if sectores is not None else SECTORES_OFICIALES
        self.entidades = frozenset(entidades) if entidades is not None else ENTIDADES_OFICIALES
        self.umbral_fuzzy = umbral_fuzzy
        self._sectores_del_listado = sectores is None
        self._entidades_del_listado = entidades is None
        self._sec = {normalizar(s): s for s in self.sectores}
        self._ent = {normalizar(e): e for e in self.entidades}
        self._sec_compacta = {clave_compacta(s): s for s in self.sectores}
        self._ent_compacta = {clave_compacta(e): e for e in self.entidades}

    def es_sector_oficial(self, valor) -> bool:
        return (not valor) or normalizar(valor) in self._sec

    def es_entidad_oficial(self, valor) -> bool:
        return (not valor) or normalizar(valor) in self._ent

    def sugerir_sector(self, valor) -> Optional[str]:
        """Nombre oficial del sector que corresponde a `valor`, si difiere de lo
        escrito; None si ya está bien escrito o no se reconoce."""
        return self._sugerir(valor, self._sec, self._sec_compacta,
                             canonizar_sector if self._sectores_del_listado else None)

    def sugerir_entidad(self, valor) -> Optional[str]:
        """Nombre oficial de la entidad que corresponde a `valor`, si difiere de
        lo escrito; None si ya está bien escrito o no se reconoce."""
        return self._sugerir(valor, self._ent, self._ent_compacta,
                             canonizar_entidad if self._entidades_del_listado else None)

    @staticmethod
    def _sugerir(valor, mapa, compacta, canonizar) -> Optional[str]:
        if not valor:
            return None
        n = normalizar(valor)
        if not n:
            return None
        oficial = mapa.get(n)                            # coincide salvo acentos/caso/puntuación
        if oficial is None:
            oficial = compacta.get(n.replace(" ", ""))   # «GestiónPública»
        if oficial is None and canonizar is not None:
            obj = canonizar(valor)                       # alias del listado → nombre oficial
            oficial = obj.nombre if obj is not None else None
        return oficial if oficial is not None and oficial != str(valor).strip() else None


CATALOGO_OFICIAL_DEFECTO = CatalogoOficial()


def sugerencias_normalizacion(resultado, catalogo: Optional[CatalogoOficial] = None) -> list:
    """Devuelve sugerencias de normalización de sector/entidad (no modifica nada).

    Cada sugerencia: dict(codigo, tipo, campo, original, sugerido). Opt-in:
    requiere un catálogo (por defecto, el oficial)."""
    catalogo = catalogo or CATALOGO_OFICIAL_DEFECTO
    out = []
    grupos = ((resultado.indicadores_resultado, "IR", "codigo_ir"),
              (resultado.indicadores_producto, "IP", "codigo_ip"))
    for inds, tipo, cod_attr in grupos:
        for x in inds:
            for campo, sugerir in (("sector_responsable", catalogo.sugerir_sector),
                                    ("entidad_responsable", catalogo.sugerir_entidad)):
                val = getattr(x, campo, None)
                sug = sugerir(val)
                if sug and _norm(sug) != _norm(val):
                    out.append({"codigo": getattr(x, cod_attr, None), "tipo": tipo,
                                "campo": campo, "original": val, "sugerido": sug})
    return out


def aplicar_normalizacion(resultado, catalogo: Optional[CatalogoOficial] = None) -> int:
    """Aplica in-place las sugerencias de normalización a `resultado`. Devuelve el
    número de campos cambiados. Opt-in."""
    catalogo = catalogo or CATALOGO_OFICIAL_DEFECTO
    n = 0
    idx_ir = {i.codigo_ir: i for i in resultado.indicadores_resultado}
    idx_ip = {i.codigo_ip: i for i in resultado.indicadores_producto}
    for s in sugerencias_normalizacion(resultado, catalogo):
        obj = (idx_ir if s["tipo"] == "IR" else idx_ip).get(s["codigo"])
        if obj is not None:
            setattr(obj, s["campo"], s["sugerido"])
            n += 1
    return n


# ───────────────── entidad → sector oficial (curaduría compartida) ─────────────────
# Una entidad pertenece a UN solo sector. El mapa sale del listado único y se
# versiona junto a la librería para que el Validador de Plan de Acción,
# Alertas-Seguimientos y SISPP validen contra la misma fuente.
# Alimenta la regla ADVERTENCIA_SECTOR_ENTIDAD de `seguimiento.validacion_seg`.

def norm_entidad(valor) -> str:
    """Clave de comparación de nombres de entidad/sector: la regla única
    `catalogo_entidades.normalizar` (sin tildes, minúsculas, sin puntuación,
    espacios colapsados). Se conserva con este nombre porque `validacion_seg` y
    los aplicativos lo conocen así; es exactamente la misma función."""
    return normalizar(valor)


#: {grafía normalizada: sector oficial}, tomado del listado al importar. Es una
#: instantánea: si `EXTRACTOR_PA_LISTADO` se define después de importar, use
#: `catalogo_entidades.entidad_sector_norm()`.
ENTIDAD_SECTOR = entidad_sector_norm()


def sector_oficial_de(entidad) -> Optional[str]:
    """Sector al que pertenece una entidad (por cualquiera de sus grafías), o None
    si no está en el listado."""
    return sector_de(entidad)
