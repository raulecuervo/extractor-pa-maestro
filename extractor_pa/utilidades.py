# -*- coding: utf-8 -*-
"""
Utilidades de bajo nivel compartidas por todo el extractor.

Combina las mejores versiones encontradas en el análisis comparativo:
- `_norm`           normalización para comparar encabezados (sin tildes).
- `a_float`         parseo numérico tolerante, incluido formato EUROPEO
                    (de sispp-sdis: "1.234,56" -> 1234.56).
- `extraer_codigo`  extracción de códigos N / N.N / N.N.N con regex tolerante
                    al nombre pegado al código (de generador-seguimiento y
                    creador-planes-accion).
- `leer_celda_escala`  lectura de metas respetando el number_format de Excel
                    (de generador-seguimiento: 0.0736 con formato % -> 7.36).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional


# Valores que se consideran "vacíos" en las celdas del plan de acción.
NULOS = {"", "nan", "none", "nd", "n/a", "n.a.", "n.a", "na", "_", "-"}

# Marcas de celda de meta que no aportan dato.
META_NULOS = NULOS | {"n.d.", "no aplica", "na."}


def _norm(texto: Any) -> str:
    """Minúsculas, sin tildes, espacios colapsados. Para comparar encabezados."""
    if texto is None:
        return ""
    s = re.sub(r"\s+", " ", str(texto)).strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def limpiar(valor: Any) -> Any:
    """Normaliza un valor de celda: colapsa espacios y mapea nulos a None.

    No convierte tipos numéricos ni fechas (se preservan tal cual para que el
    parser de escala/fecha decida después)."""
    if valor is None:
        return None
    if isinstance(valor, str):
        s = re.sub(r"\s+", " ", valor).strip()
        return None if _norm(s) in NULOS else s
    return valor


def a_float(valor: Any) -> Optional[float]:
    """Convierte a float de forma tolerante.

    Acepta enteros/flotantes, porcentajes como texto ("9%"), símbolos de moneda
    y el formato EUROPEO con punto de miles y coma decimal ("1.234,56")."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip().replace("%", "").replace("$", "").strip()
    if _norm(s) in NULOS:
        return None
    try:
        return float(s)
    except ValueError:
        # Segundo intento: formato europeo "1.234,56" -> "1234.56"
        try:
            return float(s.replace(".", "").replace(",", "."))
        except ValueError:
            return None


def a_int(valor: Any) -> Optional[int]:
    f = a_float(valor)
    return int(f) if f is not None else None


def extraer_codigo(texto: Any, niveles: Optional[int] = None) -> Optional[str]:
    """Extrae el código numérico al inicio de un texto.

    - `niveles=None`: devuelve el primer `N(.N)*` que aparezca (cualquier nivel).
    - `niveles=1|2|3`: exige exactamente ese nº de niveles (OE=1, IR=2, IP=3) y
      usa un negative lookahead para NO confundir "1.1.1" con "1.1".

    Tolerante al nombre pegado al código ("4.1.5Nombre") y a separadores
    irregulares ("1 . 1", "1.1.")."""
    if not texto:
        return None
    # Colapsa espacios y normaliza separadores: "1 . 1" -> "1.1"
    t = re.sub(r"\s*\.\s*", ".", re.sub(r"\s+", " ", str(texto).strip()))
    if niveles:
        # (?!\d) impide que "1.1.1" sea capturado como "1.1" cuando niveles=2.
        patron = r"^\s*(\d+" + r"\.\d+" * (niveles - 1) + r")(?!\d)"
    else:
        patron = r"^(\d+(?:\.\d+)*)"
    m = re.match(patron, t)
    return m.group(1).rstrip(".") if m else None


def es_vigente(valor: Any) -> bool:
    """True si el valor de la columna 'Vigente/No Vigente' indica VIGENTE.

    Se asume vigente cuando está vacío; solo es "no vigente" si lo dice explícito."""
    s = _norm(valor)
    return "no vigente" not in s and s not in ("no", "n")


def peso_positivo(valor: Any) -> bool:
    """True si el peso/ponderación es un número > 0."""
    f = a_float(valor)
    return f is not None and f > 0


def clave_grupo(valor: Any) -> str:
    """Clave de agrupamiento de un IR/objetivo: su código (1, 1.1) o el texto norm."""
    return extraer_codigo(valor) or _norm(valor)


def leer_celda_escala(cell: Any) -> tuple[Optional[float], bool]:
    """Lee una celda de meta respetando su escala de porcentaje.

    Devuelve `(valor, es_pct)`:
    - Celda numérica con number_format '%': el valor es fracción (0.0736) y se
      multiplica ×100 -> 7.36. `es_pct=True`.
    - Texto '74.97%': se extrae 74.97 sin dividir. `es_pct=True`.
    - Cualquier otro número o texto numérico: se devuelve tal cual. `es_pct=False`.
    - Vacío/ND: `(None, False)`.

    (Lógica heredada de generador-seguimiento `_read_cell_meta`.)"""
    val = getattr(cell, "value", cell)
    if val is None:
        return None, False
    fmt = getattr(cell, "number_format", "") or ""
    if isinstance(val, (int, float)):
        v = float(val)
        if "%" in fmt:
            # round() elimina el ruido binario de multiplicar por 100 (0.07 -> 7.0).
            return round(v * 100.0, 6), True
        return v, False
    s = str(val).strip()
    if _norm(s) in META_NULOS:
        return None, False
    if s.endswith("%"):
        try:
            return float(s.rstrip("%").replace(",", ".").replace(" ", "")), True
        except ValueError:
            return None, False
    f = a_float(s)
    return f, False
