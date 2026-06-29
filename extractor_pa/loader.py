# -*- coding: utf-8 -*-
"""
Carga del libro de Excel.

Se abre con `data_only=True` (lee los valores cacheados, no las fórmulas) y
SIN `read_only`, porque necesitamos acceder a `ws.merged_cells` para resolver
las celdas combinadas de los encabezados (técnica heredada de
creador-planes-accion). El costo de no usar read_only es asumible para el
tamaño de estos archivos.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import openpyxl


def abrir_workbook(ruta: str | Path):
    """Abre el .xlsx y devuelve el workbook de openpyxl.

    Lanza la excepción original si el archivo no se puede abrir; el pipeline la
    captura y la convierte en una alerta de estructura."""
    with warnings.catch_warnings():
        # openpyxl avisa de estilos/validaciones no soportadas: no son relevantes.
        warnings.simplefilter("ignore")
        return openpyxl.load_workbook(ruta, data_only=True, read_only=False)
