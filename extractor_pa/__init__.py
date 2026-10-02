# -*- coding: utf-8 -*-
"""
extractor_pa — Extractor maestro de planes de acción de política pública.

API pública:
    from extractor_pa import extraer_plan_accion, MapeoColumnas

    resultado = extraer_plan_accion("ruta/al/plan.xlsx")
    print(resultado.metadatos.nombre_politica)
    for ir in resultado.indicadores_resultado:
        print(ir.codigo_ir, ir.nombre_indicador, ir.metas_por_anio)

Cubre los formatos nuevo y antiguo del plan (.xlsx), las fichas técnicas, las
reglas de negocio V0–V18, la gobernanza de alertas y los adaptadores de salida.
El seguimiento (.xlsb/.xlsx) vive en el subpaquete `extractor_pa.seguimiento`.
Estado y estabilidad de cada capa: README.md.
"""

from .config import MapeoColumnas, MAPEO_NUEVO, MAPEO_ANTIGUO
from .modelo import (
    Alerta,
    IndicadorProducto,
    IndicadorResultado,
    Objetivo,
    Metadatos,
    RegistroFinanciero,
    ResultadoExtraccion,
    NIVEL_ERROR,
    NIVEL_ADVERTENCIA,
    NIVEL_INFO,
)
from .pipeline import extraer_plan_accion
from .validacion import validar_reglas
from .catalogo import CATALOGO, TipoAlerta, nivel_de
from .gobernanza import (
    clave_alerta, RegistroGobernanza, Reconciliacion, ItemTriage,
    ESTADOS_VALIDOS, ESTADOS_PENDIENTES,
)
from .decisiones import (
    RegistroDecisiones, aplicar_decisiones, ACCIONES_VALIDAS, CAMPOS_ENTIDAD,
)
from .catalogo_oficial import (
    CatalogoOficial, CATALOGO_OFICIAL_DEFECTO, SECTORES_OFICIALES, ENTIDADES_OFICIALES,
    sugerencias_normalizacion, aplicar_normalizacion,
)
from .exportadores import (
    tablas,
    tablas_consolidadas,
    exportar_json,
    exportar_json_consolidado,
    exportar_csv,
    exportar_csv_consolidado,
    exportar_excel,
    exportar_excel_consolidado,
    a_dataframes,
    a_dataframes_consolidado,
)

__version__ = "0.18.0"

__all__ = [
    "extraer_plan_accion",
    "MapeoColumnas",
    "MAPEO_NUEVO",
    "MAPEO_ANTIGUO",
    "ResultadoExtraccion",
    "Metadatos",
    "IndicadorResultado",
    "IndicadorProducto",
    "Objetivo",
    "RegistroFinanciero",
    "Alerta",
    "validar_reglas",
    "CATALOGO",
    "TipoAlerta",
    "nivel_de",
    "clave_alerta",
    "RegistroGobernanza",
    "Reconciliacion",
    "ItemTriage",
    "ESTADOS_VALIDOS",
    "ESTADOS_PENDIENTES",
    "RegistroDecisiones",
    "aplicar_decisiones",
    "ACCIONES_VALIDAS",
    "CAMPOS_ENTIDAD",
    "CatalogoOficial",
    "CATALOGO_OFICIAL_DEFECTO",
    "SECTORES_OFICIALES",
    "ENTIDADES_OFICIALES",
    "sugerencias_normalizacion",
    "aplicar_normalizacion",
    "tablas",
    "tablas_consolidadas",
    "exportar_json",
    "exportar_json_consolidado",
    "exportar_csv",
    "exportar_csv_consolidado",
    "exportar_excel",
    "exportar_excel_consolidado",
    "a_dataframes",
    "a_dataframes_consolidado",
    "NIVEL_ERROR",
    "NIVEL_ADVERTENCIA",
    "NIVEL_INFO",
]
