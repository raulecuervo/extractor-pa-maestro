# -*- coding: utf-8 -*-
"""
Resolución por ANCLAS de la hoja de seguimiento (la técnica robusta de
`generador-seguimiento` / `sispp-gobierno`).

La hoja 'Avance Cuantitativo' tiene:
- Fila de BLOQUES (índice 2): encabezados de grupo → anclas.
- Fila de AÑOS (índice 3): los años bajo cada bloque.
- Datos desde la fila índice 5: una fila por indicador.

A partir de las anclas y los años se construyen los mapas {año: columna} de cada
métrica (trimestres, acumulado, meta anual, % vigencia/acumulado/total).
"""

from __future__ import annotations

import re

# Índices de fila (0-based, como los entrega pyxlsb).
FILA_BLOQUES = 2
FILA_ANIOS = 3
FILA_DATOS = 5
COL_FIN_META = 14   # límite para el mapa cualitativo

# Columnas fijas de identificación (0-based), bloque "Información general".
COL_ESTADO = 2       # Vigente / No vigente
COL_CODIGO = 3       # "Indicador esperado"
COL_NOMBRE = 4
COL_SECTOR = 5
COL_ENTIDAD = 6
COL_PONDERACION = 7
COL_LINEA_BASE = 8
COL_TIPO_ANUAL = 9
COL_PERIODICIDAD = 10
COL_FECHA_INI = 11
COL_FECHA_FIN = 12
COL_CORTE = 13
COL_ANIO_REPORTE = 14

# Anclas de bloque en la fila de bloques (texto normalizado por regex).
ANCLAS_CUANT = {
    "avance":    re.compile(r"avance\s+y\s+seguimiento", re.I),
    "metas":     re.compile(r"metas\s+programadas", re.I),
    "pct_vig":   re.compile(r"meta\s+programada\s+de\s+la\s+vigencia", re.I),
    "pct_acum":  re.compile(r"meta\s+acumulada\s+hasta\s+la\s+vigencia", re.I),
    "pct_total": re.compile(r"meta\s+final", re.I),
}


class AnclasNoEncontradas(ValueError):
    """No se hallaron las anclas obligatorias en la fila de bloques."""


def detectar_anclas(fila_bloques: dict) -> dict:
    """{nombre_ancla: columna} a partir de la fila de bloques."""
    anclas = {}
    for col, val in fila_bloques.items():
        texto = str(val).strip()
        for nombre, patron in ANCLAS_CUANT.items():
            if nombre not in anclas and patron.search(texto):
                anclas[nombre] = col
    faltantes = [k for k in ANCLAS_CUANT if k not in anclas]
    if faltantes:
        raise AnclasNoEncontradas(f"Faltan anclas en la fila de bloques: {faltantes}")
    return anclas


def construir_mapas_cuant(fila_anios: dict, anclas: dict):
    """Devuelve (anios, mapa_trim, mapa_acum, mapa_meta, col_meta_final,
    mapa_meta_acum, mapa_pct_vig, mapa_pct_acum, mapa_pct_total).

    `mapa_meta_acum` = meta acumulada hasta la vigencia (bloque entre meta_final
    y pct_vig: col_pct_vig - n + i)."""
    col_avance = anclas["avance"]
    col_metas = anclas["metas"]
    col_pct_vig = anclas["pct_vig"]
    col_pct_acum = anclas["pct_acum"]
    col_pct_total = anclas["pct_total"]

    # Años en el bloque de trimestres (entre 'avance' y 'metas').
    anios = sorted(
        int(v) for c, v in fila_anios.items()
        if col_avance <= c < col_metas
        and isinstance(v, (int, float)) and 2000 <= int(v) <= 2040
    )
    if not anios:
        raise AnclasNoEncontradas("No se encontraron años entre las anclas 'avance' y 'metas'.")

    n = len(anios)
    mapa_trim, mapa_acum, mapa_meta, mapa_meta_acum = {}, {}, {}, {}
    mapa_pct_vig, mapa_pct_acum, mapa_pct_total = {}, {}, {}
    for i, anio in enumerate(anios):
        base_q = col_avance + i * 4
        mapa_trim[anio] = {1: base_q, 2: base_q + 1, 3: base_q + 2, 4: base_q + 3}
        mapa_acum[anio] = col_metas - n + i     # los acumulados van justo antes de 'metas'
        mapa_meta[anio] = col_metas + i
        mapa_meta_acum[anio] = col_pct_vig - n + i   # meta acumulada (antes de pct_vig)
        mapa_pct_vig[anio] = col_pct_vig + i
        mapa_pct_acum[anio] = col_pct_acum + i
        mapa_pct_total[anio] = col_pct_total + i
    col_meta_final = col_metas + n
    return (anios, mapa_trim, mapa_acum, mapa_meta, col_meta_final,
            mapa_meta_acum, mapa_pct_vig, mapa_pct_acum, mapa_pct_total)


def construir_mapa_cual(fila_anios_cual: dict) -> dict:
    """{año: {trimestre: {'cualitativo': col, 'enfoques': col}}} para la hoja cualitativa."""
    anios_cols = sorted(
        (int(v), c) for c, v in fila_anios_cual.items()
        if c > COL_FIN_META and isinstance(v, (int, float)) and 2000 <= int(v) <= 2040
    )
    mapa = {}
    for anio, base in anios_cols:
        mapa[anio] = {q + 1: {"cualitativo": base + q * 2, "enfoques": base + q * 2 + 1}
                      for q in range(4)}
    return mapa
