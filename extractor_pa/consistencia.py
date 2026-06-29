# -*- coding: utf-8 -*-
"""
Chequeos de consistencia (Fase 5).

El IR se repite en cada fila de sus IP; sus campos deberían ser idénticos en
todas esas filas. Cuando una fila trae un valor NO vacío distinto al de las
demás, es una inconsistencia del dato (p. ej. el mismo IR con dos nombres o dos
ponderaciones). Se compara sobre los valores ORIGINALES (antes de la
normalización de celdas combinadas, que justamente uniformiza esos valores).

También detecta códigos de IP duplicados.

Heredado de validador-plan-accion / sispp-gobierno (`_CAMPOS_IR_CONSISTENCIA`,
`_num_igual`), adaptado al modelo canónico.
"""

from __future__ import annotations

from collections import defaultdict

from .alertas import crear_alerta
from .modelo import NIVEL_ADVERTENCIA
from .utilidades import _norm, a_float, extraer_codigo, limpiar


# Columnas del IR que deben coincidir en todas sus filas: (clave_columna, etiqueta).
_CAMPOS_CONSISTENCIA = [
    ("nombre_ir", "nombre_indicador"),
    ("vigente_ir", "es_vigente"),
    ("peso_ir", "peso_pct"),
    ("formula_ir", "formula"),
    ("sector_ir", "sector_responsable"),
    ("entidad_ir", "entidad_responsable"),
    ("tipo_anual_ir", "tipo_anualizacion"),
    ("periodicidad_ir", "periodicidad"),
    ("lb_valor_ir", "valor_linea_base"),
    ("lb_anio_ir", "anio_linea_base"),
    ("meta_final_ir", "meta_final"),
    ("fecha_inicio_ir", "fecha_inicio"),
    ("fecha_fin_ir", "fecha_fin"),
]


def _consistentes(valores: list) -> bool:
    """True si todos los valores (no vacíos) son equivalentes.

    Tolerante a número vs texto ('44' == '44.0' == 44) y a mayúsculas/espacios."""
    if len(valores) <= 1:
        return True
    nums = [a_float(v) for v in valores]
    if all(n is not None for n in nums):
        return (max(nums) - min(nums)) <= 1e-9
    return len({_norm(str(v)) for v in valores}) <= 1


def _distintos(valores: list) -> list:
    """Representaciones distintas (para el mensaje de la alerta), preservando orden."""
    vistos, out = set(), []
    for v in valores:
        k = _norm(str(v))
        if k not in vistos:
            vistos.add(k)
            out.append(str(v).strip())
    return out


def _no_vacios(lista_orig: list, col_1idx: int) -> list:
    """Valores no vacíos de una columna a lo largo de las filas originales del IR."""
    out = []
    for orig in lista_orig:
        i = col_1idx - 1
        v = limpiar(orig[i]) if 0 <= i < len(orig) else None
        if v is not None and str(v).strip() != "":
            out.append(v)
    return out


def chequear_consistencia_ir(pares, cols, metas_ir_cols, archivo, politica):
    """Compara los valores ORIGINALES de cada IR entre sus filas.

    `pares`: lista de (valores_normalizados, valores_originales)."""
    alertas = []

    # Agrupar las filas ORIGINALES por código de IR (tomado de la fila normalizada).
    col_res = cols.get("resultado")
    if not col_res:
        return alertas
    grupos = defaultdict(list)
    for val_norm, val_orig in pares:
        cir = extraer_codigo(limpiar(val_norm[col_res - 1]) if col_res - 1 < len(val_norm) else None,
                             niveles=2)
        if cir:
            grupos[cir].append(val_orig)

    for cir, lista_orig in grupos.items():
        if len(lista_orig) < 2:
            continue
        # Campos fijos del IR.
        for clave, etiqueta in _CAMPOS_CONSISTENCIA:
            col = cols.get(clave)
            if not col:
                continue
            vals = _no_vacios(lista_orig, col)
            if not _consistentes(vals):
                distintos = _distintos(vals)
                alertas.append(crear_alerta(
                    "inconsistencia_en_ir",
                    f"IR '{cir}': '{etiqueta}' difiere entre filas ({' | '.join(distintos)})",
                    archivo_fuente=archivo, nombre_politica=politica,
                    codigo_ir=cir, campo=etiqueta, valor=" | ".join(distintos)))
        # Metas anuales del IR.
        for anio, col in metas_ir_cols.items():
            vals = _no_vacios(lista_orig, col)
            if not _consistentes(vals):
                distintos = _distintos(vals)
                alertas.append(crear_alerta(
                    "inconsistencia_en_ir",
                    f"IR '{cir}': 'meta_{anio}' difiere entre filas ({' | '.join(distintos)})",
                    archivo_fuente=archivo, nombre_politica=politica,
                    codigo_ir=cir, campo=f"meta_{anio}", valor=" | ".join(distintos)))

    return alertas


def chequear_duplicados_ip(indicadores_producto, archivo, politica):
    """Detecta códigos de IP repetidos entre los indicadores extraídos."""
    alertas = []
    vistos = {}
    for ip in indicadores_producto:
        cod = ip.codigo_ip
        if not cod:
            continue
        if cod in vistos:
            alertas.append(crear_alerta(
                "codigo_ip_duplicado",
                f"Código de IP duplicado: '{cod}' (aparece más de una vez).",
                archivo_fuente=archivo, nombre_politica=politica,
                codigo_ip=cod, campo="codigo_ip", valor=cod))
        else:
            vistos[cod] = True
    return alertas
