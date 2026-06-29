# -*- coding: utf-8 -*-
"""Estrategias de extracción por formato (patrón Strategy)."""

from .base import EstrategiaExtraccion
from .nuevo import ExtractorNuevo
from .antiguo import ExtractorAntiguo

__all__ = ["EstrategiaExtraccion", "ExtractorNuevo", "ExtractorAntiguo"]
