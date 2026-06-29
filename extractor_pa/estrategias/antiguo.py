# -*- coding: utf-8 -*-
"""
Estrategia del FORMATO ANTIGUO (variante con bloque financiero).

Tras la Fase 4b, el motor de extracción es **el mismo** que el del formato nuevo
(`ExtractorNuevo`): toda la diferencia vive en el `MapeoColumnas` (`MAPEO_ANTIGUO`),
que resuelve el IP por ancla y activa la lectura del bloque financiero. Por eso
`ExtractorAntiguo` es simplemente una subclase con otro nombre de formato; el
pipeline elige el mapeo adecuado según el detector.
"""

from __future__ import annotations

from .nuevo import ExtractorNuevo


class ExtractorAntiguo(ExtractorNuevo):
    nombre_formato = "antiguo"
