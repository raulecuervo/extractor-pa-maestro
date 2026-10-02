# -*- coding: utf-8 -*-
"""
Contrato con los aplicativos que consumen extractor-pa.

Cada nombre de esta lista lo importa algún aplicativo hermano (alertas-seguimientos,
sispp-gobierno, sispp-sdis, generador-seguimiento, validador_plan_accion,
extractor-planes-accion, creador-planes-accion, seguimiento-pp-sdis). Si una
refactorización lo mueve o lo renombra, esta prueba falla aquí y no en producción.
Para retirar un nombre, primero hay que migrar a los consumidores.
"""

from __future__ import annotations

import importlib

import pytest

# (módulo, nombre) tal como lo importan los consumidores.
CONTRATO = [
    # Plan: todos los adaptadores de extracción.
    ("extractor_pa", "extraer_plan_accion"),
    ("extractor_pa", "__version__"),
    # sispp-gobierno (dashboard_pp/parche_extractor.py) parchea esta función.
    ("extractor_pa.utilidades", "extraer_codigo"),
    # Seguimiento: alertas-seguimientos, sispp-sdis, sispp-gobierno, generador-seguimiento.
    ("extractor_pa.seguimiento", "extraer_seguimiento"),
    ("extractor_pa.seguimiento", "consolidar_periodo"),
    ("extractor_pa.seguimiento", "validar_archivo"),
    ("extractor_pa.seguimiento", "validar_consistencia"),
    ("extractor_pa.seguimiento", "indicador_desde_dict"),
    ("extractor_pa.seguimiento", "IndicadorSeguimiento"),
    ("extractor_pa.seguimiento", "MetadatosSeguimiento"),
    ("extractor_pa.seguimiento", "ResultadoSeguimiento"),
    ("extractor_pa.seguimiento.validacion_seg", "validar_consistencia"),
    ("extractor_pa.seguimiento.validacion_seg", "a_porcentaje"),
    ("extractor_pa.seguimiento.validacion_seg", "parse_period"),
    ("extractor_pa.seguimiento.validacion_seg", "limites_de_semaforo"),
    # alertas-seguimientos/motor_calculo.py reexporta estas fórmulas de metricas.
    *[("extractor_pa.seguimiento.metricas", n) for n in (
        "safe_float", "parse_lb", "anio_de_serial_excel", "periodo_de_fecha", "hay_meta",
        "trimestre_exigible", "trimestre_efectivo", "trimestres_reportados", "calc_mes",
        "sin_iniciar_al_corte", "lb_de_indicador", "calc_lb_ficticia_decreciente",
        "calc_meta_periodo", "calc_meta_acum", "calc_sum_metas_prev",
        "_suma_metas_prev_suma", "calc_pct_vigencia", "reportes_vigencia",
        "calc_pct_hasta_vig", "calc_paf", "calc_tid", "calc_trayectoria_ideal",
        "calc_brecha", "avance_acumulado_suma", "avance_sin_reportes", "metricas_corte",
    )],
]

# Lo que se usa desde un submódulo también debe estar en la API pública del
# subpaquete, para que los consumidores puedan dejar de importar de submódulos.
PUBLICOS_SEGUIMIENTO = [
    "safe_float", "parse_lb", "parse_period", "limites_de_semaforo",
    "suma_metas_anteriores_suma",
]


@pytest.mark.parametrize("modulo,nombre", CONTRATO, ids=lambda x: str(x))
def test_nombre_del_contrato_existe(modulo, nombre):
    mod = importlib.import_module(modulo)
    assert hasattr(mod, nombre), f"{modulo}.{nombre} desapareció y lo usa un consumidor"


@pytest.mark.parametrize("nombre", PUBLICOS_SEGUIMIENTO)
def test_helpers_publicos_en_seguimiento(nombre):
    import extractor_pa.seguimiento as seg
    assert nombre in seg.__all__
    assert getattr(seg, nombre) is getattr(
        importlib.import_module(getattr(seg, nombre).__module__), nombre)


def test_alias_privado_es_la_funcion_publica():
    from extractor_pa.seguimiento import metricas
    assert metricas._suma_metas_prev_suma is metricas.suma_metas_anteriores_suma
