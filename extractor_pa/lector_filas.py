# -*- coding: utf-8 -*-
"""
Lectura y normalización de las filas de datos.

Incluye:
- Lectura desde la fila de datos conservando el ÍNDICE de fila real (para poder
  releer las celdas de meta con su `number_format` y respetar la escala %).
- PRE-FILTRO de filas espurias (sin código de IR ni de IP en su valor original):
  evita que las filas de "totales" al final del bloque sean absorbidas por el
  forward-fill y contaminen los pesos del último IR (técnica de sispp-gobierno).
- Forward-fill básico de las columnas identificadoras del IR para resolver las
  celdas combinadas (versión Fase 1; la estrategia avanzada de 4 capas +
  ascensión de fila vigente se incorpora en la Fase 2).

Convención: una "fila" es la tupla `(indice_absoluto, valores)`, donde `valores`
es una lista mutable. El forward-fill muta esas listas in situ.
"""

from __future__ import annotations

from .utilidades import extraer_codigo, limpiar


def leer_filas(ws, fila_datos: int) -> list[tuple[int, list]]:
    """Devuelve [(indice_absoluto, valores)] de las filas no vacías, padded."""
    max_col = ws.max_column or 130
    filas: list[tuple[int, list]] = []
    for i, row in enumerate(ws.iter_rows(min_row=fila_datos, max_col=max_col,
                                         values_only=True)):
        if any(c is not None for c in row):
            filas.append((fila_datos + i, list(row)))
    if not filas:
        return []
    ancho = max(len(f) for _, f in filas)
    return [(r, f + [None] * (ancho - len(f))) for r, f in filas]


def prefiltrar_filas(filas: list[tuple[int, list]], col_res_1idx: int | None,
                     col_prod_1idx: int | None) -> list[tuple[int, list]]:
    """Descarta filas sin código de IR ni de IP en su valor ORIGINAL."""
    idx_res = (col_res_1idx or 0) - 1
    idx_prod = (col_prod_1idx or 0) - 1

    def pertenece(valores: list) -> bool:
        for idx in (idx_res, idx_prod):
            if 0 <= idx < len(valores) and extraer_codigo(limpiar(valores[idx])):
                return True
        return False

    return [(r, f) for (r, f) in filas if pertenece(f)]


def forward_fill(valores_filas: list[list], indices_0idx: list[int]) -> None:
    """Rellena hacia abajo (in situ) las columnas indicadas.

    Una celda vacía toma el último valor no vacío visto por encima en su columna."""
    previos: dict[int, object] = {}
    for valores in valores_filas:
        for i in indices_0idx:
            if i >= len(valores):
                continue
            v = valores[i]
            if v is None or (isinstance(v, str) and not v.strip()):
                valores[i] = previos.get(i)
            else:
                previos[i] = v
