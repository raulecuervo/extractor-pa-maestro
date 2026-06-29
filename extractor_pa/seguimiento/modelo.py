# -*- coding: utf-8 -*-
"""
Modelo canónico del SEGUIMIENTO (avances periódicos).

A diferencia del plan (un registro por indicador), el seguimiento es una serie
**indicador × año × trimestre**: avances trimestrales, acumulados, metas anuales
y porcentajes (vigencia / acumulado / total), más el reporte cualitativo.

Reutiliza la clase `Alerta` y el catálogo de la librería del plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from ..modelo import Alerta  # noqa: F401  (reexport implícito para conveniencia)


# Errores que invalidan la extracción del seguimiento.
_FATALES_SEG = frozenset({
    "apertura_seguimiento", "hoja_seguimiento_no_encontrada", "anclas_no_encontradas",
})


@dataclass
class IndicadorSeguimiento:
    """Histórico de avances de un indicador (clave de series: '<año>_Q<n>')."""
    codigo: Optional[str] = None              # código numérico N.N / N.N.N
    indicador_esperado: Optional[str] = None  # texto original de la celda
    nombre: Optional[str] = None
    sector: Optional[str] = None
    entidad: Optional[str] = None
    tipo_archivo: Optional[str] = None        # 'productos' | 'resultados'
    ind_no: Optional[int] = None
    meta_final: Any = None
    # Columnas fijas de identificación del .xlsb (0-14).
    estado: Optional[str] = None              # Vigente / No vigente
    ponderacion: Any = None
    linea_base: Any = None
    tipo_anualizacion: Optional[str] = None   # Suma / Creciente / Decreciente / Constante
    periodicidad: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    corte: Optional[str] = None               # Q1..Q4 del reporte
    anio_reporte: Any = None
    # Cruce con el plan (Fase S2).
    en_plan: bool = False
    tipo_plan: Optional[str] = None           # 'IR' | 'IP'
    nombre_plan: Optional[str] = None
    # Series por año×trimestre / por año.
    avances: dict = field(default_factory=dict)         # '2024_Q1' -> valor
    acumulados: dict = field(default_factory=dict)       # '2024' -> valor
    metas: dict = field(default_factory=dict)            # '2024' -> meta anual
    metas_acumuladas: dict = field(default_factory=dict)  # '2024' -> meta acumulada hasta vigencia
    pct_vigencia: dict = field(default_factory=dict)     # '2024' -> %
    pct_acumulado: dict = field(default_factory=dict)    # '2024' -> %
    pct_total: dict = field(default_factory=dict)        # '2024' -> %
    cualitativos: dict = field(default_factory=dict)     # '2024_Q1' -> texto
    avance_enfoques: dict = field(default_factory=dict)  # '2024_Q1' -> texto


@dataclass
class MetadatosSeguimiento:
    archivo_fuente: str = ""
    nombre_politica: Optional[str] = None
    tipo_archivo: Optional[str] = None     # 'productos' | 'resultados'
    periodo: Optional[str] = None          # 'S1' | 'S2' | 'Q1'..'Q4'
    anio_reporte: Optional[int] = None
    hoja_usada: Optional[str] = None
    anios_detectados: list = field(default_factory=list)


@dataclass
class ResultadoSeguimiento:
    metadatos: MetadatosSeguimiento
    indicadores: list = field(default_factory=list)
    alertas: list = field(default_factory=list)

    @property
    def exitoso(self) -> bool:
        hay_fatal = any(a.tipo in _FATALES_SEG for a in self.alertas)
        return bool(self.indicadores) and not hay_fatal

    def to_dict(self) -> dict:
        return {
            "metadatos": asdict(self.metadatos),
            "indicadores": [asdict(i) for i in self.indicadores],
            "alertas": [asdict(a) for a in self.alertas],
        }
