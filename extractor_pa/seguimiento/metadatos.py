# -*- coding: utf-8 -*-
"""
Metadatos del seguimiento derivados del NOMBRE del archivo.

Portado de `alertas-seguimientos/extractor.py`: el tipo (productos/resultados),
la sigla/nombre de la política y el período (S1/S2/Q1–Q4 + año) suelen venir en
el nombre del `.xlsb`, p. ej.:
  "Seguimiento a Productos PP BTI S1-25.xlsb" → productos · BTI · S1 · 2025
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


def tipo_desde_nombre(filename: str) -> Optional[str]:
    """'productos' | 'resultados' | None según el nombre del archivo."""
    stem = Path(str(filename)).stem.lower()
    if "producto" in stem:
        return "productos"
    if "resultado" in stem:
        return "resultados"
    return None


def politica_desde_nombre(filename: str) -> str:
    """Nombre/sigla de la política a partir del nombre del archivo."""
    stem = Path(str(filename)).stem
    # Quitar el sufijo de período (S1-25, S2_2025, Q3-2024…) al final.
    stem_limpio = re.sub(r"[\s_\-]+[SsQq][1-4][\s_\-]\d{2,4}.*$", "", stem).strip()
    # 1) Patrón 'PP <nombre>' (separador espacio o guion bajo).
    m = re.search(r"(?<![A-Za-z0-9])PP[\s_]+([A-Za-z][A-Za-z0-9_\s-]*)", stem_limpio)
    if m:
        name = re.sub(r"[\s_]+", " ", m.group(1)).strip().strip("-").strip()
        if name:
            return name
    # 2) Sigla en MAYÚSCULAS tras 'Productos'/'Resultados'.
    m = re.search(r"\b(?:Productos|Resultados)\b[\s_]+([A-Z]{2,}[A-Z0-9_-]*)", stem_limpio)
    if m:
        return m.group(1).upper()
    # 3) Fallback: el stem completo.
    return stem


def periodo_desde_nombre(filename: str) -> tuple[Optional[str], Optional[int]]:
    """(periodo, año) a partir del nombre. Ej.: 'S1-25' → ('S1', 2025)."""
    stem = Path(str(filename)).stem
    m = re.search(r"(?<![A-Za-z0-9])([Ss][12]|[Qq][1-4])[_\-\s](\d{2,4})(?!\d)", stem)
    if not m:
        return None, None
    periodo = m.group(1).upper()
    anio_raw = int(m.group(2))
    anio = 2000 + anio_raw if anio_raw < 100 else anio_raw
    return periodo, anio
