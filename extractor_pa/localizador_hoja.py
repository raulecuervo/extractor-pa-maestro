# -*- coding: utf-8 -*-
"""
Localización flexible de la hoja del plan de acción.

Cascada heredada de extractor-planes-accion (`seleccionar_hoja_plan`), la más
robusta del conjunto:
  1. Nombre exacto configurado ("Plan de acción") o "Plan de acción Actual".
  2. Hoja cuyo nombre contiene "plan" + "acci" (excluyendo "instructivo").
  3. Hoja cuyo nombre contiene "matriz" (caso PPMYEG / Mujer).
  4. Primera hoja con > 40 columnas (la tabla de datos, no "Desplegables").
"""

from __future__ import annotations

from typing import Optional

from .utilidades import _norm


# Hojas que NUNCA son la tabla de datos.
_HOJAS_EXCLUIDAS = {"desplegables", "desplegables 2", "instructivo"}


def localizar_hoja(wb, nombre_config: str = "Plan de acción") -> Optional[str]:
    """Devuelve el nombre de la hoja del plan, o None si no se encuentra."""
    nombres = wb.sheetnames

    # 1) Coincidencia exacta (normalizada) con el nombre configurado o variantes.
    objetivos = {_norm(nombre_config), _norm(nombre_config + " Actual")}
    for n in nombres:
        if _norm(n) in objetivos:
            return n

    # 2) Fuzzy: contiene "plan" y "acci", excluyendo instructivos.
    candidatas = [
        n for n in nombres
        if "plan" in _norm(n) and "acci" in _norm(n) and "instructivo" not in _norm(n)
    ]
    if candidatas:
        # La más corta suele ser la genérica ("Plan de acción").
        return min(candidatas, key=len)

    # 3) Contiene "matriz".
    for n in nombres:
        if "matriz" in _norm(n):
            return n

    # 4) Primera hoja "ancha" (> 40 columnas) que no esté excluida.
    for n in nombres:
        if _norm(n) in _HOJAS_EXCLUIDAS:
            continue
        ws = wb[n]
        if (ws.max_column or 0) > 40:
            return n

    return None
