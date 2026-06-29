# -*- coding: utf-8 -*-
"""
Normalización avanzada de celdas combinadas (Fase 2).

Reemplaza el forward-fill simple de la Fase 1 por la estrategia de 4 CAPAS
heredada de sispp-gobierno, la más robusta del análisis comparativo. Su objetivo
es resolver las celdas combinadas SIN que los valores de un IR contaminen al IR
siguiente cuando este trae celdas vacías.

Capas (las metas anuales se EXCLUYEN siempre: se leen de la primera fila del IR):
  1. Forward-fill LIBRE de las columnas identificadoras (objetivo, resultado):
     son textos que cambian con cada grupo nuevo, así que no hay riesgo de
     contaminación (el siguiente valor reinicia el grupo).
  2. Forward-fill de `peso_objetivo` AGRUPADO por objetivo: solo se propaga
     dentro del mismo objetivo.
  3. Forward-fill del resto de campos del IR AGRUPADO por resultado (código IR):
     solo se propaga dentro del mismo IR.
  4. Ascensión de la "fila vigente autoritativa": si la primera fila del IR es
     una versión histórica No Vigente (peso 0) y la versión vigente (peso > 0)
     está en una fila inferior, se promueven los valores de la fila vigente a
     todo el grupo, para que el extractor (que lee la primera fila) tome la
     versión correcta.
"""

from __future__ import annotations

from .lector_filas import forward_fill
from .utilidades import clave_grupo, es_vigente, peso_positivo


# Campos del IR que se propagan dentro del mismo IR (capas 3 y 4).
# NO incluye objetivo/resultado (capa 1) ni las metas anuales (excluidas).
_COLS_IR_GRUPO = [
    "nombre_ir", "vigente_ir", "peso_ir", "formula_ir", "sector_ir",
    "entidad_ir", "ods", "meta_ods", "tipo_anual_ir", "periodicidad_ir",
    "lb_valor_ir", "lb_anio_ir", "lb_fuente_ir", "fecha_inicio_ir",
    "fecha_fin_ir", "meta_final_ir",
]


def forward_fill_por_grupo(valores_filas: list[list], col_grupo_0idx: int,
                           cols_0idx: list[int]) -> None:
    """Forward-fill que se REINICIA cuando cambia el valor de la columna de grupo.

    Requiere que la columna de grupo ya esté rellenada (capa 1)."""
    previos: dict[int, object] = {}
    grupo_actual = object()  # centinela que nunca coincide con la primera fila
    for valores in valores_filas:
        g = valores[col_grupo_0idx] if col_grupo_0idx < len(valores) else None
        gk = clave_grupo(g)
        if gk != grupo_actual:
            grupo_actual = gk
            previos = {}
        for i in cols_0idx:
            if i >= len(valores):
                continue
            v = valores[i]
            if v is None or (isinstance(v, str) and not v.strip()):
                valores[i] = previos.get(i)
            else:
                previos[i] = v


def ascender_fila_vigente_por_grupo(valores_filas: list[list], col_grupo_0idx: int,
                                    col_vigente_0idx: int, col_peso_0idx: int,
                                    cols_propagar_0idx: list[int]) -> None:
    """Promueve los valores de la fila vigente (Vigente + peso>0) a todo su grupo.

    Solo actúa si la primera fila del grupo NO es ya esa fila vigente."""
    # Agrupar índices de fila por grupo, preservando el orden de aparición.
    grupos: dict[str, list[int]] = {}
    orden: list[str] = []
    for idx, valores in enumerate(valores_filas):
        g = valores[col_grupo_0idx] if col_grupo_0idx < len(valores) else None
        gk = clave_grupo(g)
        if gk not in grupos:
            grupos[gk] = []
            orden.append(gk)
        grupos[gk].append(idx)

    for gk in orden:
        indices = grupos[gk]
        if len(indices) < 2:
            continue  # un solo registro: nada que ascender
        # Buscar la primera fila Vigente con peso > 0 (autoritativa).
        fila_vig = None
        for i in indices:
            v = valores_filas[i]
            vig = v[col_vigente_0idx] if col_vigente_0idx < len(v) else None
            peso = v[col_peso_0idx] if col_peso_0idx < len(v) else None
            if es_vigente(vig) and peso_positivo(peso):
                fila_vig = v
                break
        if fila_vig is None:
            continue
        # Si la primera fila del grupo ya es la vigente, no hay que hacer nada.
        if valores_filas[indices[0]] is fila_vig:
            continue
        # Propagar los valores de la fila vigente a TODAS las filas del grupo.
        for i in indices:
            destino = valores_filas[i]
            for c in cols_propagar_0idx:
                if c < len(destino) and c < len(fila_vig):
                    destino[c] = fila_vig[c]


def normalizar_celdas_combinadas(valores_filas: list[list], cols: dict) -> None:
    """Aplica las 4 capas in situ usando el mapa de columnas resuelto."""
    col_obj = cols.get("objetivo")
    col_res = cols.get("resultado")

    # Capa 1 — ffill libre de las columnas de agrupamiento.
    grupo_cols = [c - 1 for c in (col_obj, col_res) if c]
    if grupo_cols:
        forward_fill(valores_filas, grupo_cols)

    # Capa 2 — peso_objetivo agrupado por objetivo.
    if col_obj and cols.get("peso_objetivo"):
        forward_fill_por_grupo(valores_filas, col_obj - 1, [cols["peso_objetivo"] - 1])

    # Capa 3 — resto de campos del IR agrupados por resultado (código IR).
    cols_ir = [cols[k] - 1 for k in _COLS_IR_GRUPO if cols.get(k)]
    if col_res and cols_ir:
        forward_fill_por_grupo(valores_filas, col_res - 1, cols_ir)

    # Capa 4 — ascensión de la fila vigente dentro del grupo del IR.
    if col_res and cols.get("vigente_ir") and cols.get("peso_ir"):
        cols_propagar = list(cols_ir)
        if cols.get("peso_objetivo"):
            cols_propagar.append(cols["peso_objetivo"] - 1)
        ascender_fila_vigente_por_grupo(
            valores_filas, col_res - 1,
            cols["vigente_ir"] - 1, cols["peso_ir"] - 1, cols_propagar,
        )
