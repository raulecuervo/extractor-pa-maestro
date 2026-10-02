# -*- coding: utf-8 -*-
"""
Resolución de columnas por ENCABEZADO (no por posición fija).

Combina dos fortalezas del análisis comparativo:
- Buscar las anclas en TODAS las filas de encabezado 9/10/11 (de sispp-sdis),
  porque el encabezado de grupo cae en distinta fila según la versión.
- Resolver las CELDAS COMBINADAS del encabezado leyendo el valor del ancla
  superior-izquierda de cada rango (de creador-planes-accion).

Devuelve un mapa `cols` {clave_logica: columna_1idx} y los diccionarios de
columnas de metas anuales para IR e IP.
"""

from __future__ import annotations

import re
from typing import Optional

from .config import MapeoColumnas
from .utilidades import _norm, a_int


class EstructuraNoReconocida(ValueError):
    """Las anclas obligatorias no se encontraron en los encabezados."""


_RE_META_ANIO = re.compile(r"^meta (\d{4})$")

# Otras redacciones del mismo encabezado en versiones anteriores de la plantilla
# (texto normalizado). Solo se prueban si el ancla configurada no aparece, así
# que no cambian nada en un plan que trae la redacción vigente.
_ALIAS_ANCLAS = {
    "responsables de la ejecucion": ("responsable de la ejecucion",),
    "importancia relativa del resultado (%)": (
        "importancia relativa del indicador de resultado (%)",),
    "importancia relativa del producto (%)": (
        "ponderacion relativa del producto (%)", "importancia relativa de productos (%)"),
}

# Encabezados del bloque financiero dentro del grupo de cada año (normalizados).
_COSTO = ("costo estimado", "costo")
_CAMPOS_FINANCIEROS = (
    ("recurso_disponible", "recurso disponible"),
    ("fuente_financiacion", "fuente de financiacion"),
    ("codigo_proyecto", "codigo proyecto"),
)


def _mapa_anclas_combinadas(ws, filas: tuple) -> dict:
    """Mapa (fila, col) -> valor del ancla superior-izquierda de cada rango
    combinado que intersecte las filas de encabezado."""
    mapa = {}
    fmin, fmax = min(filas), max(filas)
    # En workbooks abiertos sin read_only, ws.merged_cells.ranges está disponible.
    for rng in getattr(ws.merged_cells, "ranges", []):
        if rng.min_row > fmax or rng.max_row < fmin:
            continue
        top = ws.cell(row=rng.min_row, column=rng.min_col).value
        for r in range(rng.min_row, rng.max_row + 1):
            for c in range(rng.min_col, rng.max_col + 1):
                mapa[(r, c)] = top
    return mapa


def resolver_columnas(ws, mapeo: MapeoColumnas):
    """Devuelve (cols, metas_ir_cols, metas_ip_cols, financiero_cols).

    `financiero_cols` es una lista de (anio, {campo: columna}) para el bloque
    financiero del formato antiguo (vacía en el formato nuevo)."""
    max_col = ws.max_column or 130
    filas = mapeo.filas_encabezado
    anclas = _mapa_anclas_combinadas(ws, filas)

    def valor(r: int, c: int):
        # Respeta el ancla de la celda combinada si aplica.
        return anclas[(r, c)] if (r, c) in anclas else ws.cell(row=r, column=c).value

    # Diccionario {texto_normalizado: primera_columna} por cada fila de encabezado.
    dict_por_fila: dict[int, dict[str, int]] = {}
    for n in filas:
        d: dict[str, int] = {}
        for c in range(1, max_col + 1):
            v = valor(n, c)
            if v is not None:
                clave = _norm(v)
                if clave and clave not in d:
                    d[clave] = c
        dict_por_fila[n] = d

    # Lista (texto_norm, col) de la ÚLTIMA fila de encabezado (típicamente 11),
    # donde viven las columnas repetidas y las metas anuales.
    fila_detalle = filas[-1]
    detalle = [
        (_norm(valor(fila_detalle, c)), c)
        for c in range(1, max_col + 1)
        if valor(fila_detalle, c) is not None
    ]

    def ancla_cab(texto: str) -> Optional[int]:
        """Busca el ancla en las filas de encabezado, en orden; si no aparece,
        prueba sus redacciones anteriores (`_ALIAS_ANCLAS`)."""
        k = _norm(texto)
        for clave in (k, *_ALIAS_ANCLAS.get(k, ())):
            for n in filas:
                if clave in dict_por_fila[n]:
                    return dict_por_fila[n][clave]
        return None

    # --- Anclas OBLIGATORIAS ---
    col_meta_final_ir = ancla_cab(mapeo.ancla_meta_final_ir)
    col_producto = ancla_cab(mapeo.ancla_producto)
    if not col_meta_final_ir or not col_producto:
        raise EstructuraNoReconocida(
            f"No se encontró '{mapeo.ancla_meta_final_ir}' o "
            f"'{mapeo.ancla_producto}' en los encabezados (filas {filas})."
        )

    col_meta_final_ip = ancla_cab(mapeo.ancla_meta_final_ip)
    col_resp = ancla_cab(mapeo.ancla_responsables)
    col_corresp = ancla_cab(mapeo.ancla_corresponsables)

    # --- Metas anuales: 'Meta YYYY' en la fila de detalle, separadas por IR/IP ---
    metas_ir_cols: dict[int, int] = {}
    metas_ip_cols: dict[int, int] = {}
    for texto, col in detalle:
        m = _RE_META_ANIO.match(texto)
        if m:
            anio = int(m.group(1))
            destino = metas_ir_cols if col < col_producto else metas_ip_cols
            destino[anio] = col

    # --- Helpers de ocurrencias por texto ---
    # Las ocurrencias de un encabezado repetido se buscan en la fila de detalle y
    # en la del medio: en las plantillas anteriores el del IR y el del IP no
    # siempre están en la misma fila (Negra-Afro v2: la «Fecha de inicio» del IR
    # en la fila 12 y la del IP en la 11; Vejez: «Tipo de anualización» en la 11).
    fila_media = filas[-2] if len(filas) > 1 else fila_detalle
    medio = [
        (_norm(valor(fila_media, c)), c)
        for c in range(1, max_col + 1)
        if valor(fila_media, c) is not None
    ]

    def todas(texto: str) -> list[int]:
        k = _norm(texto)
        return sorted({c for t, c in detalle + medio if t == k})

    def pos(lista: list[int], idx: int) -> Optional[int]:
        return lista[idx] if idx < len(lista) else None

    cols: dict[str, Optional[int]] = {
        "objetivo": mapeo.col_objetivo,
        "peso_objetivo": mapeo.col_peso_objetivo,
        "meta_final_ir": col_meta_final_ir,
        "producto": col_producto,
        "meta_final_ip": col_meta_final_ip,
    }

    # IR por ancla (con fallback posicional solo si el formato lo permite).
    for texto, (clave, fb) in mapeo.anclas_ir.items():
        col = ancla_cab(texto)
        if col is None and mapeo.fallback_posicional:
            col = fb
        cols[clave] = col

    # Columnas repetidas (por orden 0=IR, 1=IP): Valor/Año/Fecha/Tipo/Enfoque…
    for texto, (clave_ir, clave_ip) in mapeo.anclas_repetidas.items():
        occ = todas(texto)
        cols[clave_ir] = pos(occ, 0)
        cols[clave_ip] = pos(occ, 1)

    if mapeo.anclas_ip:
        # IP por ANCLA (formato antiguo/variante con columnas reordenadas). Si
        # dos textos apuntan a la misma clave, gana el primero que aparezca.
        for texto, clave in mapeo.anclas_ip.items():
            col = ancla_cab(texto)
            if col is not None or clave not in cols:
                cols[clave] = col
    else:
        # IP por OFFSETS desde 'Producto esperado' (formato nuevo).
        cols.update({
            "nombre_ip": col_producto + 1,
            "vigente_ip": col_producto + 2,
            "peso_ip": col_producto + 3,
            "formula_ip": col_producto + 4,
            "tipo_anual_ip": col_producto + 5,
            "periodicidad_ip": col_producto + 6,
            "objetivo_pdd": col_producto + 7,
            "meta_pdd": col_producto + 8,
            "proyecto_inv": col_producto + 9,
            "enfoque_princ": col_producto + 10,
            "enfoque_sec": col_producto + 11,
        })

    # Responsables / corresponsables (None si no existen en este formato).
    def bloque_responsables(col):
        """(sector, entidad, dirección) del bloque que empieza en `col`. Se leen
        por sus subencabezados cuando los hay: en Adultez v2 el título combinado
        «Responsable de la ejecución» empieza una columna antes, sobre «Costo
        total». Sin subencabezados, las tres columnas siguientes al título."""
        if not col:
            return None, None, None
        sub: dict[str, int] = {}
        for c in range(col, col + 4):
            for n in filas:
                t = _norm(valor(n, c))
                if t == "sector":
                    sub.setdefault("sector", c)
                elif t.startswith("entidad"):
                    sub.setdefault("entidad", c)
                elif t.startswith("direccion"):
                    sub.setdefault("direccion", c)
        sector = sub.get("sector", col)
        return sector, sub.get("entidad", sector + 1), sub.get("direccion", sector + 2)

    cols["sector_resp"], cols["entidad_resp"], cols["dir_resp"] = bloque_responsables(col_resp)
    (cols["sector_corresp"], cols["entidad_corresp"],
     cols["dir_corresp"]) = bloque_responsables(col_corresp)

    # --- Bloque financiero (formato antiguo): un grupo de columnas por año ---
    # Cada grupo empieza en «Costo Estimado» (o «Costo») y sigue con Recurso
    # disponible, Fuente de financiación y, si la plantilla lo trae, Código del
    # proyecto. El año está en la fila del medio, sobre el «Costo» del grupo.
    financiero_cols: list = []
    if mapeo.detectar_financiero:
        inicios = [col for texto, col in detalle if texto in _COSTO]
        por_col = dict((c, t) for t, c in detalle)
        for i, col in enumerate(inicios):
            fin = inicios[i + 1] if i + 1 < len(inicios) else col + 4
            grupo = {"costo_estimado": col}
            for campo, prefijo in _CAMPOS_FINANCIEROS:
                grupo[campo] = next((c for c in range(col + 1, min(fin, col + 4))
                                     if por_col.get(c, "").startswith(prefijo)), None)
            financiero_cols.append((a_int(valor(fila_media, col)), grupo))

    return cols, metas_ir_cols, metas_ip_cols, financiero_cols
