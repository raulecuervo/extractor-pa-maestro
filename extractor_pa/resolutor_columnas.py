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
        """Busca el ancla en las filas de encabezado, en orden."""
        k = _norm(texto)
        for n in filas:
            if k in dict_por_fila[n]:
                return dict_por_fila[n][k]
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
    def todas(texto: str) -> list[int]:
        k = _norm(texto)
        return sorted(c for t, c in detalle if t == k)

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
        # IP por ANCLA (formato antiguo/variante con columnas reordenadas).
        for texto, clave in mapeo.anclas_ip.items():
            cols[clave] = ancla_cab(texto)
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
    cols["sector_resp"] = col_resp
    cols["entidad_resp"] = col_resp + 1 if col_resp else None
    cols["dir_resp"] = col_resp + 2 if col_resp else None
    cols["sector_corresp"] = col_corresp
    cols["entidad_corresp"] = col_corresp + 1 if col_corresp else None
    cols["dir_corresp"] = col_corresp + 2 if col_corresp else None

    # --- Bloque financiero (formato antiguo): grupos de 4 columnas por año ---
    financiero_cols: list = []
    if mapeo.detectar_financiero:
        k_costo = _norm("Costo Estimado")
        for texto, col in detalle:
            if texto == k_costo:
                anio = a_int(valor(10, col))  # el año está en la fila 10 del grupo
                financiero_cols.append((anio, {
                    "costo_estimado": col,
                    "recurso_disponible": col + 1,
                    "fuente_financiacion": col + 2,
                    "codigo_proyecto": col + 3,
                }))

    return cols, metas_ir_cols, metas_ip_cols, financiero_cols
