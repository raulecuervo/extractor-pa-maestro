# -*- coding: utf-8 -*-
"""
Carga de archivos de seguimiento `.xlsb` (pyxlsb).

`pyxlsb` es dependencia opcional de la librería (extra `xlsb`); se importa en
tiempo de ejecución para no obligar a instalarlo si solo se usa el plan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..utilidades import _norm


def _open_workbook(ruta):
    try:
        from pyxlsb import open_workbook
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "La extracción de seguimiento requiere pyxlsb. "
            "Instala con: pip install extractor-pa[xlsb]  (o pip install pyxlsb)."
        ) from e
    return open_workbook(str(ruta))


def localizar_hoja(wb, *contiene: str) -> Optional[str]:
    """Devuelve el nombre de hoja cuyo nombre contiene TODOS los términos dados
    (normalizados). Ej.: localizar_hoja(wb, 'avance', 'cuantitativo')."""
    objetivos = [_norm(t) for t in contiene]
    for nombre in wb.sheets:
        n = _norm(nombre)
        if all(o in n for o in objetivos):
            return nombre
    return None


def leer_hoja(wb, nombre_hoja: str) -> dict:
    """Lee una hoja `.xlsb` a un dict {indice_fila: {indice_col: valor}}.

    Índices 0-based (los de pyxlsb). Solo guarda celdas no vacías."""
    mapa: dict = {}
    with wb.get_sheet(nombre_hoja) as ws:
        for row in ws.rows():
            if not row:
                continue
            fila = row[0].r
            vals = {c.c: c.v for c in row if c.v is not None and c.v != ""}
            if vals:
                mapa[fila] = vals
    return mapa


def abrir(ruta: str | Path):
    """Context manager del workbook .xlsb."""
    return _open_workbook(ruta)
