# -*- coding: utf-8 -*-
"""
Calidad: catálogo único de reglas y motor de alertas de plan y seguimiento.

API::

    from extractor_pa.calidad import evaluar, ParametrosCalidad, CATALOGO_CALIDAD

    hallazgos = evaluar(plan=res_plan)                       # reglas del plan
    hallazgos = evaluar(seguimiento=res_seg, base=res_base)  # seguimiento (+ entre cargas)
    hallazgos = evaluar(plan=res_plan, seguimiento=res_seg, corte=(2026, 2))

    for h in hallazgos:
        h.as_finding()        # dict de la tabla `alertas` de alertas-seguimientos
        h.a_alerta()          # `Alerta` del plan (alertas_planes_accion.csv)
        h.a_observacion(politica_key="MUJER")   # fila de observaciones_politica

    # Atajos para los consumidores (0.29.0):
    alertas_plan(res_plan)                                   # pipeline, paso 01
    observaciones_desde(res_plan, res_seg, corte=(2026, 2),
                        politica_key="MUJER")                # pipeline, paso 06
    hallazgos_app(res_seg, base=res_base, parametros=...)    # alertas-seguimientos

Las fachadas ``validacion.validar_reglas``, ``seguimiento.validar_archivo`` y
``seguimiento.validar_consistencia`` siguen vigentes; el motor las envuelve.
Decisiones: ``docs/adr/ADR-001-catalogo-alertas.md``.
"""

from .catalogo import (
    APLICA_CRUCE, APLICA_ENTRE_CARGAS, APLICA_ESTRUCTURA_PLAN, APLICA_ESTRUCTURA_SEG,
    APLICA_PLAN, APLICA_SEGUIMIENTO, APLICA_SERIE, CATALOGO_CALIDAD, REGLAS,
    SEV_ADVERTENCIA, SEV_ERROR, SEV_INFO, SEVERIDAD_A_OBSERVACION, Regla, por_aplica_a,
    por_familia, regla_de_tipo,
)
from .hallazgo import (
    COLS_OBSERVACION, FUENTE_CRUCE, FUENTE_PLAN, FUENTE_SEGUIMIENTO, Hallazgo, desde_alerta,
    desde_hallazgo_seguimiento,
)
from .motor import (
    alertas_plan, evaluar, filtrar, hallazgos_app, hallazgos_cruce, hallazgos_plan,
    hallazgos_seguimiento, observaciones_desde,
)
from .parametros import PARAMETROS_POR_DEFECTO, UMBRAL_ESCALA, ParametrosCalidad

__all__ = [
    "evaluar", "filtrar", "hallazgos_plan", "hallazgos_seguimiento", "hallazgos_cruce",
    "alertas_plan", "hallazgos_app", "observaciones_desde",
    "CATALOGO_CALIDAD", "REGLAS", "Regla", "regla_de_tipo", "por_aplica_a", "por_familia",
    "Hallazgo", "desde_alerta", "desde_hallazgo_seguimiento", "COLS_OBSERVACION",
    "FUENTE_PLAN", "FUENTE_SEGUIMIENTO", "FUENTE_CRUCE",
    "ParametrosCalidad", "PARAMETROS_POR_DEFECTO", "UMBRAL_ESCALA",
    "SEV_ERROR", "SEV_ADVERTENCIA", "SEV_INFO", "SEVERIDAD_A_OBSERVACION",
    "APLICA_PLAN", "APLICA_SEGUIMIENTO", "APLICA_SERIE", "APLICA_ENTRE_CARGAS", "APLICA_CRUCE",
    "APLICA_ESTRUCTURA_PLAN", "APLICA_ESTRUCTURA_SEG",
]
