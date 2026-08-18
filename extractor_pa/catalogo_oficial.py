# -*- coding: utf-8 -*-
"""
Catálogo OFICIAL de sectores y entidades del Distrito (opcional).

Habilita la regla **V4** (`sector_no_oficial` / `entidad_no_oficial`) y la
**normalización difusa** de responsables. Es **opt-in**: si no se inyecta un
catálogo, V4 no se ejecuta y el comportamiento no cambia.

Listas heredadas de los aplicativos (extractor-planes-accion / validador). La
normalización difusa usa `rapidfuzz` si está instalado; si no, solo hace
coincidencia exacta (normalizada).
"""

from __future__ import annotations

from typing import Iterable, Optional

from .utilidades import _norm

SECTORES_OFICIALES = frozenset({
    "Ambiente", "Cultura, Recreación y Deporte",
    "Desarrollo Económico, Industria y Turismo", "Educación", "Gestión Jurídica",
    "Gestión Pública", "Gobierno", "Hábitat", "Hacienda", "Integración Social",
    "Movilidad", "Mujeres", "Planeación", "Salud",
    "Seguridad, Convivencia y Justicia", "Entes de Control",
})

ENTIDADES_OFICIALES = frozenset({
    "Secretaría Distrital de Ambiente", "Jardín Botánico José Celestino Mutis",
    "Instituto Distrital de Gestión de Riesgos y Cambio Climático",
    "Instituto Distrital de Protección y Bienestar Animal",
    "Secretaría de Cultura, Recreación y Deporte",
    "Instituto Distrital de Recreación y Deporte", "Orquesta Filarmónica de Bogotá",
    "Instituto Distrital de Patrimonio Cultural", "Fundación Gilberto Alzate Avendaño",
    "Instituto Distrital de las Artes", "Canal Capital",
    "Secretaría Distrital de Desarrollo Económico",
    "Instituto Popular para la Economía Social", "Instituto Distrital de Turismo",
    "Corporación para el Desarrollo y la Productividad Bogotá Región",
    "Secretaría de Educación del Distrito",
    "Instituto para la Investigación Educativa y el Desarrollo Pedagógico",
    "Universidad Distrital Francisco José de Caldas",
    "Agencia Distrital para la Educación Superior la Ciencia y la Tecnología",
    "Secretaría Jurídica Distrital", "Secretaría General de la Alcaldía Mayor de Bogotá",
    "Departamento Administrativo del Servicio Civil Distrital",
    "Dirección Distrital de Relaciones Internacionales", "Dirección Distrital de Archivo",
    "Secretaría Distrital de Gobierno",
    "Departamento Administrativo de la Defensoría del Espacio Público",
    "Instituto Distrital de la Participación y Acción Comunal",
    "Unidad Administrativa Especial Cuerpo Oficial de Bomberos",
    "Secretaría Distrital del Hábitat", "Caja de Vivienda Popular",
    "Unidad Administrativa Especial de Servicios Públicos",
    "Empresa de Renovación y Desarrollo Urbano de Bogotá", "Metrovivienda",
    "Instituto de Desarrollo Urbano",
    "Unidad Administrativa Especial de Rehabilitación y Mantenimiento Vial",
    "Secretaría Distrital de Hacienda",
    "Unidad Administrativa Especial de Catastro Distrital", "Lotería de Bogotá",
    "Fondo de Prestaciones Económicas Cesantías y Pensiones",
    "Secretaría Distrital de Integración Social",
    "Instituto Distrital para la Protección de la Niñez y la Juventud",
    "Secretaría Distrital de Movilidad",
    "Empresa de Transporte del Tercer Milenio Transmilenio", "Terminal de Transporte",
    "Empresa Metro de Bogotá", "Secretaría Distrital de la Mujer",
    "Secretaría Distrital de Planeación", "Secretaría Distrital de Salud",
    "Fondo Financiero Distrital de Salud", "Capital Salud EPS-S",
    "Subred Integrada de Servicios de Salud Norte",
    "Subred Integrada de Servicios de Salud Centro Oriente",
    "Subred Integrada de Servicios de Salud Sur",
    "Subred Integrada de Servicios de Salud Sur Occidente",
    "Instituto Distrital de Ciencia Biotecnología e Innovación en Salud",
    "Secretaría Distrital de Seguridad Convivencia y Justicia", "Contraloría de Bogotá",
    "Personería de Bogotá", "Veeduría Distrital", "Defensoría del Pueblo",
    "Concejo de Bogotá",
    # Siglas reconocidas
    "SDIS", "IDRD", "SDS", "SED", "SDP", "SDG", "SDH", "SDM", "SCRD", "UAESP",
    "IDU", "IDPC", "IDARTES", "IPES", "IDT", "IDIGER", "DASCD", "DADEP", "IDPAC",
    "CVP", "ERU", "UAECD", "UAERMV", "IDPYBA", "IDEP", "SDDE", "SJD", "SDHT",
    "SDSCJ", "FONCEP", "FFDS", "IDCBIS",
})


class CatalogoOficial:
    """Catálogo de sectores/entidades oficiales con normalización opcional.

    `umbral_fuzzy`: puntaje mínimo (0-100) de RapidFuzz para sugerir una corrección.
    """

    def __init__(self, sectores: Optional[Iterable[str]] = None,
                 entidades: Optional[Iterable[str]] = None, umbral_fuzzy: int = 88):
        self.sectores = frozenset(sectores) if sectores is not None else SECTORES_OFICIALES
        self.entidades = frozenset(entidades) if entidades is not None else ENTIDADES_OFICIALES
        self.umbral_fuzzy = umbral_fuzzy
        self._sec = {_norm(s): s for s in self.sectores}
        self._ent = {_norm(e): e for e in self.entidades}

    def es_sector_oficial(self, valor) -> bool:
        return (not valor) or _norm(valor) in self._sec

    def es_entidad_oficial(self, valor) -> bool:
        return (not valor) or _norm(valor) in self._ent

    def sugerir_sector(self, valor) -> Optional[str]:
        return self._sugerir(valor, self._sec)

    def sugerir_entidad(self, valor) -> Optional[str]:
        return self._sugerir(valor, self._ent)

    def _sugerir(self, valor, mapa) -> Optional[str]:
        if not valor:
            return None
        n = _norm(valor)
        if n in mapa:                       # ya coincide (salvo acentos/caso)
            return mapa[n] if mapa[n] != str(valor).strip() else None
        try:
            from rapidfuzz import process, fuzz
        except ImportError:
            return None
        m = process.extractOne(n, list(mapa.keys()), scorer=fuzz.WRatio)
        return mapa[m[0]] if (m and m[1] >= self.umbral_fuzzy) else None


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
# Una entidad pertenece a UN solo sector. El mapa lo curan las personas (no se deduce
# de los archivos) y se versiona junto a la librería para que el Validador de Plan de
# Acción, Alertas-Seguimientos y SISPP validen contra la misma fuente.
# Alimenta la regla ADVERTENCIA_SECTOR_ENTIDAD de `seguimiento.validacion_seg`.

def _cargar_entidad_sector() -> dict:
    """{entidad normalizada con `_norm`: sector oficial}. Vacío si falta el archivo."""
    import json
    from pathlib import Path

    ruta = Path(__file__).with_name("data") / "entidad_sector.json"
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {_norm(entidad): sector for entidad, sector in crudo.items()}


ENTIDAD_SECTOR = _cargar_entidad_sector()


def sector_oficial_de(entidad) -> Optional[str]:
    """Sector al que pertenece una entidad, o None si no está en la curaduría."""
    return ENTIDAD_SECTOR.get(_norm(entidad))
