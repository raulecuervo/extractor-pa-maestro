# -*- coding: utf-8 -*-
"""
Detección del formato del plan de acción: "nuevo" | "antiguo" | None.

Heurísticas heredadas de extractor-planes-accion (`detectar_formato`), el único
proyecto que soportaba ambos formatos. Se evalúan en orden y se devuelve el
primer veredicto con su confianza y motivo (útil para alertas y trazabilidad).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Veredicto:
    formato: Optional[str]   # "nuevo" | "antiguo" | None
    confianza: str           # "alta" | "media" | "baja"
    motivo: str


# Patrón de hoja de ficha técnica: "IR 1.1", "IP#1.1.1", "Ficha técnica IP 1.1.1"...
_RE_HOJA_FICHA = re.compile(r"\bi[rp][\s#:.\-]*\d+(?:\.\d+)+", re.I)


def _textos_fila(ws, n: int, max_col: int) -> set[str]:
    """Conjunto de textos (sin saltos de línea) presentes en la fila n."""
    out = set()
    for c in range(1, max_col + 1):
        v = ws.cell(row=n, column=c).value
        if v is not None:
            out.add(str(v).strip().replace("\n", " "))
    return out


_MARCADORES_FINANCIEROS = (
    "costo estimado", "costos estimados", "recurso disponible",
    "fuente de financiacion",
)


def detectar_formato(ws, wb=None) -> Veredicto:
    """Determina el formato de la hoja del plan de acción ya localizada."""
    from .utilidades import _norm
    max_col = min(ws.max_column or 130, 130)

    # H0 — Bloque financiero en los encabezados (filas 9-11) -> ANTIGUO.
    # Tiene prioridad sobre las anclas nuevas: hay plantillas (p. ej. CTI) que
    # conservan las anclas «Meta de resultado Final»/«Producto esperado» PERO
    # con columnas reordenadas y un bloque financiero, y deben tratarse aparte.
    for n in (9, 10, 11):
        for c in range(1, max_col + 1):
            v = ws.cell(row=n, column=c).value
            if v and any(m in _norm(v) for m in _MARCADORES_FINANCIEROS):
                return Veredicto("antiguo", "alta",
                                 f"Bloque financiero en encabezados (fila {n}: '{str(v).strip()[:30]}')")

    # H1 — Anclas del formato NUEVO en la fila 10.
    f10 = _textos_fila(ws, 10, max_col)
    if "Meta de resultado Final" in f10 and "Producto esperado" in f10:
        return Veredicto("nuevo", "alta",
                         "Anclas 'Meta de resultado Final' + 'Producto esperado' en fila 10")

    # H2 — Anclas del formato ANTIGUO (resultado en F25, financiero en F26).
    f25 = _textos_fila(ws, 25, max_col)
    f26 = _textos_fila(ws, 26, max_col)
    if "Resultado esperado" in f25 and ("Costo" in f26 or "Recurso disponible" in f26):
        return Veredicto("antiguo", "alta",
                         "Anclas 'Resultado esperado' (F25) + columnas financieras (F26)")

    # H2b — Variante DRAFE (anclas en filas 7-8).
    f7 = _textos_fila(ws, 7, max_col)
    f8 = _textos_fila(ws, 8, max_col)
    if "Resultado esperado" in f7 and any(t.startswith("Costo") or t.startswith("Recurso disponible") for t in f8):
        return Veredicto("antiguo", "alta",
                         "Anclas 'Resultado esperado' (F7) + columnas financieras (F8)")

    # H3 — Columnas financieras en cualquier fila 4-35 -> antiguo.
    for fila in range(4, 36):
        for c in range(1, max_col + 1):
            v = ws.cell(row=fila, column=c).value
            if v is not None:
                t = str(v).strip()
                if t.startswith("Recurso disponible") or t == "Fuente de financiación":
                    return Veredicto("antiguo", "alta",
                                     f"Columna financiera '{t}' en fila {fila}")

    # H4 — Muchas hojas de fichas técnicas -> antiguo (requiere el workbook).
    if wb is not None:
        fichas = [s for s in wb.sheetnames if _RE_HOJA_FICHA.search(s)]
        if len(fichas) >= 3:
            return Veredicto("antiguo", "alta",
                             f"{len(fichas)} hojas de fichas técnicas (IR/IP x.x)")

    # H5 — Posición de los datos.
    if ws.cell(row=12, column=1).value and ws.cell(row=12, column=3).value:
        return Veredicto("nuevo", "media", "Datos desde la fila 12 (patrón nuevo)")
    if ws.cell(row=27, column=1).value:
        return Veredicto("antiguo", "media", "Datos desde la fila 27 (patrón antiguo)")

    return Veredicto(None, "baja", "No se pudo determinar el formato con confianza")
