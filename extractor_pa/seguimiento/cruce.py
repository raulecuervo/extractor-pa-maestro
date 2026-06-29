# -*- coding: utf-8 -*-
"""
Cruce del seguimiento con el plan + consolidación por período (Fase S2).

- `cruzar_con_plan(res_seguimiento, res_plan)`: empareja cada indicador de
  seguimiento con su IR/IP del plan por **código numérico** (N.N → IR, N.N.N → IP)
  y enriquece `en_plan / tipo_plan / nombre_plan`. Devuelve un reporte.
- `consolidar_periodo(ind, anio, periodo)`: consolida los avances de un período
  (Q1–Q4 / S1 / S2 / Anual), respetando el tipo de anualización (SUMA suma los
  trimestres; el resto toma el último valor reportado).
- `consolidar(res, anio, periodo)`: aplica lo anterior a todos los indicadores.

Lógica de consolidación heredada de `generador-seguimiento`.
"""

from __future__ import annotations

from ..alertas import crear_alerta
from ..utilidades import a_float


# Trimestres que componen cada período.
PERIODO_TRIMESTRES = {
    "Q1": [1], "Q2": [2], "Q3": [3], "Q4": [4],
    "S1": [1, 2], "S2": [3, 4],
    "Anual": [1, 2, 3, 4],
}


# ─────────────────────────── cruce con el plan ───────────────────────────

def _indice_plan(res_plan):
    """{codigo_ir: IR}, {codigo_ip: IP} del plan."""
    ir = {i.codigo_ir: i for i in res_plan.indicadores_resultado if i.codigo_ir}
    ip = {i.codigo_ip: i for i in res_plan.indicadores_producto if i.codigo_ip}
    return ir, ip


def cruzar_con_plan(res_seguimiento, res_plan) -> dict:
    """Empareja los indicadores de seguimiento con los del plan (in situ).

    Devuelve {'total','asociados','sin_asociar','codigos_sin_plan'} y agrega
    alertas `codigo_seguimiento_sin_plan` a `res_seguimiento.alertas`."""
    ir_idx, ip_idx = _indice_plan(res_plan)
    total = asociados = 0
    sin_plan = []
    for ind in res_seguimiento.indicadores:
        cod = ind.codigo
        if not cod:
            continue
        total += 1
        n_niveles = cod.count(".")
        encontrado = None
        tipo = None
        if n_niveles >= 2 and cod in ip_idx:
            encontrado, tipo = ip_idx[cod], "IP"
        elif n_niveles == 1 and cod in ir_idx:
            encontrado, tipo = ir_idx[cod], "IR"
        else:
            # Fallback: probar ambos índices.
            if cod in ip_idx:
                encontrado, tipo = ip_idx[cod], "IP"
            elif cod in ir_idx:
                encontrado, tipo = ir_idx[cod], "IR"
        if encontrado is not None:
            ind.en_plan = True
            ind.tipo_plan = tipo
            ind.nombre_plan = encontrado.nombre_indicador
            asociados += 1
        else:
            ind.en_plan = False
            sin_plan.append(cod)

    for cod in sin_plan:
        res_seguimiento.alertas.append(crear_alerta(
            "codigo_seguimiento_sin_plan",
            f"El código de seguimiento '{cod}' no se encontró en el plan de acción.",
            archivo_fuente=res_seguimiento.metadatos.archivo_fuente,
            nombre_politica=res_seguimiento.metadatos.nombre_politica,
            codigo_ip=cod))

    return {
        "total": total,
        "asociados": asociados,
        "sin_asociar": len(sin_plan),
        "codigos_sin_plan": sin_plan,
    }


# ─────────────────────────── consolidación por período ───────────────────

def _es_suma(ind) -> bool:
    return (ind.tipo_anualizacion or "").strip().lower() == "suma"


def consolidar_periodo(ind, anio, periodo: str):
    """Consolida los avances de un indicador para (año, período). None si no hay datos."""
    trimestres = PERIODO_TRIMESTRES.get(periodo, [1, 2, 3, 4])
    presentes = [(q, ind.avances.get(f"{anio}_Q{q}"))
                 for q in trimestres if f"{anio}_Q{q}" in ind.avances]
    if not presentes:
        return None

    valores = [a_float(v) for _, v in presentes if a_float(v) is not None]
    suma = sum(valores) if valores else None
    ultimo_valor = presentes[-1][1]   # valor del trimestre mayor del período
    acumulado = ind.acumulados.get(str(anio))

    avance = suma if _es_suma(ind) else ultimo_valor

    return {
        "codigo": ind.codigo,
        "anio": anio,
        "periodo": periodo,
        "trimestres_encontrados": [q for q, _ in presentes],
        "avance_consolidado": avance,
        "suma_trimestres": suma,
        "ultimo_valor": ultimo_valor,
        "avance_acumulado": acumulado,
        "meta_anual": ind.metas.get(str(anio)),
        "meta_final": ind.meta_final,
        "pct_vigencia": ind.pct_vigencia.get(str(anio)),
        "pct_acumulado": ind.pct_acumulado.get(str(anio)),
        "tipo_anualizacion": ind.tipo_anualizacion,
        "en_plan": ind.en_plan,
        "tipo_plan": ind.tipo_plan,
    }


def consolidar(res_seguimiento, anio, periodo: str) -> list:
    """Consolida todos los indicadores con datos en (año, período)."""
    out = []
    for ind in res_seguimiento.indicadores:
        c = consolidar_periodo(ind, anio, periodo)
        if c is not None:
            out.append(c)
    return out
