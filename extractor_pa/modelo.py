# -*- coding: utf-8 -*-
"""
Modelo de datos CANÓNICO del extractor maestro.

Toda estrategia de extracción (formato nuevo, antiguo, …) produce SIEMPRE estas
mismas estructuras. Así el resto del sistema (validador de reglas V0–V18,
alertas de seguimiento, dashboards, persistencia) consume un único contrato,
sin importar de qué plantilla de Excel provino el dato.

Diseño heredado del análisis comparativo (ver PLAN_EXTRACTOR_MAESTRO.md):
incorpora `escala_pct` (de generador-seguimiento), `metas_por_anio`,
`meta_vigencia_actual/_anterior` (de generador-seguimiento) y los campos de
ficha técnica (de sispp-sdis / seguimiento-pp-sdis).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# Niveles de alerta UNIFICADOS (resuelve las 5 nomenclaturas distintas que
# tenían los proyectos originales). Se usa español en mayúscula.
NIVEL_ERROR = "ERROR"            # bloquea / dato inutilizable
NIVEL_ADVERTENCIA = "ADVERTENCIA"  # conviene revisar, no bloquea
NIVEL_INFO = "INFO"              # informativo

# Tipos de error FATAL de extracción (invalidan el resultado). El resto de
# ERRORes (reglas de negocio) son hallazgos de calidad, no fallos de extracción.
_TIPOS_FATALES = frozenset({
    "apertura", "hoja_no_encontrada", "formato_no_reconocido",
    "formato_no_compatible", "estructura",
})


@dataclass
class Alerta:
    """Alerta de EXTRACCIÓN (no de validación de reglas de negocio).

    Reporta problemas detectados al leer el Excel: hoja faltante, estructura no
    reconocida, fila sin nombre, escala dudosa, etc. Las reglas V0–V18 viven en
    un módulo aparte y consumen el modelo ya extraído.
    """
    nivel: str
    tipo: str
    descripcion: str
    archivo_fuente: str = ""
    nombre_politica: str = ""
    codigo_objetivo: str = ""
    codigo_ir: str = ""
    codigo_ip: str = ""
    campo: str = ""
    valor: str = ""


@dataclass
class IndicadorResultado:
    """Indicador de Resultado (IR), código tipo N.N."""
    codigo_objetivo: Optional[str] = None
    objetivo_especifico: Optional[str] = None
    peso_objetivo_pct: Any = None
    codigo_ir: Optional[str] = None
    resultado_esperado: Optional[str] = None
    nombre_indicador: Optional[str] = None
    es_vigente: Optional[str] = None
    peso_pct: Any = None
    formula: Optional[str] = None
    sector_responsable: Optional[str] = None
    entidad_responsable: Optional[str] = None
    ods: Optional[str] = None
    meta_ods: Optional[str] = None
    tipo_anualizacion: Optional[str] = None
    periodicidad: Optional[str] = None
    valor_linea_base: Any = None
    anio_linea_base: Any = None
    fuente_linea_base: Optional[str] = None
    fecha_inicio: Any = None
    fecha_fin: Any = None
    meta_final: Any = None
    # True si las metas/meta_final venían como celdas de porcentaje en Excel.
    escala_pct: bool = False
    # {año(int): valor}. Se llena con las columnas "Meta YYYY".
    metas_por_anio: dict = field(default_factory=dict)
    # Año de vigencia (corte) y comparables (Fase 3).
    anio_vigencia: Optional[int] = None
    anio_vigencia_anterior: Optional[int] = None
    meta_vigencia_actual: Any = None
    meta_vigencia_anterior: Any = None
    # Campos de ficha técnica (hoja "Ficha técnica IR#…"). Fase 4.
    metodologia: Optional[str] = None
    unidad_medida: Optional[str] = None
    fuente_datos: Optional[str] = None
    dias_rezago: Optional[int] = None
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None


@dataclass
class IndicadorProducto:
    """Indicador de Producto (IP), código tipo N.N.N."""
    codigo_objetivo: Optional[str] = None
    codigo_ir: Optional[str] = None
    codigo_ip: Optional[str] = None
    producto_esperado: Optional[str] = None
    nombre_indicador: Optional[str] = None
    es_vigente: Optional[str] = None
    peso_pct: Any = None
    formula: Optional[str] = None
    tipo_anualizacion: Optional[str] = None
    periodicidad: Optional[str] = None
    valor_linea_base: Any = None
    anio_linea_base: Any = None
    fuente_linea_base: Optional[str] = None
    fecha_inicio: Any = None
    fecha_fin: Any = None
    meta_final: Any = None
    escala_pct: bool = False
    metas_por_anio: dict = field(default_factory=dict)
    anio_vigencia: Optional[int] = None
    anio_vigencia_anterior: Optional[int] = None
    meta_vigencia_actual: Any = None
    meta_vigencia_anterior: Any = None
    sector_responsable: Optional[str] = None
    entidad_responsable: Optional[str] = None
    direccion_responsable: Optional[str] = None
    sector_corresponsable: Optional[str] = None
    entidad_corresponsable: Optional[str] = None
    direccion_corresponsable: Optional[str] = None
    objetivo_pdd: Optional[str] = None
    meta_pdd: Optional[str] = None
    proyecto_inversion: Optional[str] = None
    enfoque_principal: Optional[str] = None
    enfoque_secundario: Optional[str] = None
    # Ficha técnica (hoja "Ficha técnica IP#…"). Fase 4.
    metodologia: Optional[str] = None
    unidad_medida: Optional[str] = None
    fuente_datos: Optional[str] = None
    dias_rezago: Optional[int] = None
    descripcion: Optional[str] = None
    observaciones: Optional[str] = None


@dataclass
class RegistroFinanciero:
    """Una celda del bloque financiero (formato antiguo): por IP y por año."""
    codigo_ip: Optional[str] = None
    anio: Optional[int] = None
    costo_estimado: Any = None
    recurso_disponible: Any = None
    fuente_financiacion: Optional[str] = None
    codigo_proyecto: Optional[str] = None


@dataclass
class Metadatos:
    """Cabecera de la política y trazabilidad de la extracción."""
    nombre_politica: Optional[str] = None
    documento_conpes: Optional[str] = None
    sector_lider: Optional[str] = None
    entidad_lider: Optional[str] = None
    objetivo_general: Optional[str] = None
    archivo_fuente: str = ""
    formato_detectado: Optional[str] = None   # "nuevo" | "antiguo"
    hoja_usada: Optional[str] = None
    anios_detectados: list = field(default_factory=list)
    # Métricas de extracción (se llenan al final del pipeline).
    n_ir: int = 0
    n_ip: int = 0
    n_alertas: int = 0
    pct_ir_con_linea_base: Optional[float] = None   # completitud de línea base en IR


@dataclass
class ResultadoExtraccion:
    """Resultado completo de extraer un archivo de plan de acción."""
    metadatos: Metadatos
    indicadores_resultado: list = field(default_factory=list)
    indicadores_producto: list = field(default_factory=list)
    alertas: list = field(default_factory=list)
    financiero: list = field(default_factory=list)   # RegistroFinanciero (formato antiguo)

    @property
    def exitoso(self) -> bool:
        """True si se extrajo algún IR/IP y no hubo un error FATAL de extracción.

        Solo los errores de la capa de extracción (no abrir, hoja/formato/estructura)
        invalidan la extracción. Los errores de reglas de negocio (ponderación,
        metas…) son hallazgos de calidad, no fallos de extracción."""
        hay_fatal = any(a.tipo in _TIPOS_FATALES for a in self.alertas)
        hay_datos = bool(self.indicadores_resultado or self.indicadores_producto)
        return hay_datos and not hay_fatal

    def to_dict(self) -> dict:
        """Serializa a diccionario plano (apto para JSON)."""
        return {
            "metadatos": asdict(self.metadatos),
            "indicadores_resultado": [asdict(i) for i in self.indicadores_resultado],
            "indicadores_producto": [asdict(i) for i in self.indicadores_producto],
            "alertas": [asdict(a) for a in self.alertas],
            "financiero": [asdict(f) for f in self.financiero],
        }
