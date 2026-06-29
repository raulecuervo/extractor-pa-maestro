# -*- coding: utf-8 -*-
"""
Interfaz común de las estrategias de extracción.

Cada formato (nuevo, antiguo) implementa `extraer(...)` y devuelve SIEMPRE la
misma tripleta canónica, de modo que el pipeline es agnóstico al formato.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import MapeoColumnas
from ..modelo import IndicadorProducto, IndicadorResultado, Alerta


class EstrategiaExtraccion(ABC):
    """Contrato de una estrategia de extracción de un formato concreto."""

    nombre_formato: str = "desconocido"

    @abstractmethod
    def extraer(
        self,
        ws,
        mapeo: MapeoColumnas,
        nombre_archivo: str,
        nombre_politica: str | None,
        anio_vigencia: int | None = None,
    ) -> tuple[list[IndicadorResultado], list[IndicadorProducto], list, list[Alerta], list]:
        """Devuelve (indicadores_resultado, indicadores_producto, financiero,
        alertas, objetivos).

        `financiero` es la lista de `RegistroFinanciero` (vacía en formato nuevo).
        `anio_vigencia` es el año de corte para `meta_vigencia_actual/_anterior`."""
        raise NotImplementedError
