# -*- coding: utf-8 -*-
"""
Cálculo del año de vigencia (Fase 3).

Determina, para un indicador con metas anuales, cuál es el "año de corte" actual
(`meta_vigencia_actual`) y el inmediatamente comparable anterior
(`meta_vigencia_anterior`). Estos valores son la base de los cálculos de avance
(% de cumplimiento) que harán los módulos de seguimiento aguas abajo.

Lógica heredada de generador-seguimiento (`PlanActionParser._año_vigencia_para`),
la única implementación que resolvía bien este punto. Prioridad para el año:
  1. Año EXPLÍCITO pedido por el usuario (si tiene meta; si no, el más cercano <=).
  2. Año ACTUAL del sistema (si tiene meta).
  3. Año anterior más cercano con meta.
  4. Primer año disponible (el plan es a futuro).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


def calcular_vigencia(
    metas: dict[int, Any],
    anio_explicito: Optional[int] = None,
) -> tuple[Optional[int], Optional[int], Any, Any]:
    """Devuelve (anio_vigencia, anio_vigencia_anterior, meta_actual, meta_anterior)."""
    anios = sorted(metas.keys())
    if not anios:
        return None, None, None, None

    anio_vig: Optional[int] = None

    # 1) Año explícito (con su año <= más cercano si el pedido no tiene meta).
    if anio_explicito is not None:
        if anio_explicito in metas:
            anio_vig = anio_explicito
        else:
            anteriores = [y for y in anios if y <= anio_explicito]
            if anteriores:
                anio_vig = anteriores[-1]

    # 2-4) Si no se resolvió por año explícito, usar el año actual / anterior / primero.
    if anio_vig is None:
        ahora = datetime.now().year
        if ahora in metas:
            anio_vig = ahora
        else:
            anteriores = [y for y in anios if y < ahora]
            anio_vig = anteriores[-1] if anteriores else anios[0]

    # Año anterior comparable: el inmediatamente previo si existe, si no el más
    # cercano por debajo del año de vigencia.
    previos = [y for y in anios if y < anio_vig]
    anio_vig_ant = (anio_vig - 1) if (anio_vig - 1) in metas else (previos[-1] if previos else None)

    meta_actual = metas.get(anio_vig)
    meta_anterior = metas.get(anio_vig_ant) if anio_vig_ant is not None else None
    return anio_vig, anio_vig_ant, meta_actual, meta_anterior
