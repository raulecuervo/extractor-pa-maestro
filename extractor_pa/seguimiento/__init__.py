# -*- coding: utf-8 -*-
"""
Sub-paquete de SEGUIMIENTO (avances periódicos) del extractor maestro.

Fase S1: extracción del `.xlsb` (Avance Cuantitativo/Cualitativo) al modelo
canónico de seguimiento, con detección por anclas e histórico completo.

API:
    from extractor_pa.seguimiento import extraer_seguimiento
    res = extraer_seguimiento("Seguimiento a Productos PP BTI S1-25.xlsb")
    print(res.metadatos.nombre_politica, res.metadatos.anios_detectados)
    for ind in res.indicadores:
        print(ind.codigo, ind.avances)
"""

from .extractor import extraer_seguimiento
from .cruce import cruzar_con_plan, consolidar, consolidar_periodo, PERIODO_TRIMESTRES
from .validacion_seg import (
    validar_consistencia,
    validar_archivo,
    semaforo_de,
    semaforo_indicador,
    UMBRALES_SEMAFORO,
    UMBRAL_AVANCE,
)
from .exportadores_seg import (
    tablas_seguimiento,
    tablas_seguimiento_consolidadas,
    tabla_consolidado,
    exportar_json_seguimiento,
    exportar_csv_seguimiento,
    exportar_excel_seguimiento,
    exportar_csv_seguimiento_consolidado,
    exportar_excel_seguimiento_consolidado,
)
from .modelo import (
    IndicadorSeguimiento,
    MetadatosSeguimiento,
    ResultadoSeguimiento,
)

__all__ = [
    "extraer_seguimiento",
    "cruzar_con_plan",
    "consolidar",
    "consolidar_periodo",
    "PERIODO_TRIMESTRES",
    "validar_consistencia",
    "validar_archivo",
    "semaforo_de",
    "semaforo_indicador",
    "UMBRALES_SEMAFORO",
    "UMBRAL_AVANCE",
    "tablas_seguimiento",
    "tablas_seguimiento_consolidadas",
    "tabla_consolidado",
    "exportar_json_seguimiento",
    "exportar_csv_seguimiento",
    "exportar_excel_seguimiento",
    "exportar_csv_seguimiento_consolidado",
    "exportar_excel_seguimiento_consolidado",
    "IndicadorSeguimiento",
    "MetadatosSeguimiento",
    "ResultadoSeguimiento",
]
