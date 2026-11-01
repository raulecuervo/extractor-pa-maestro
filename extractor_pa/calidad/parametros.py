# -*- coding: utf-8 -*-
"""
Parámetros configurables del motor de calidad.

Todo lo que un consumidor puede ajustar (umbrales del semáforo, tolerancias,
corte del análisis, catálogos inyectados, reglas activas) vive aquí, en un solo
objeto inmutable, para que las reglas no lean constantes sueltas de cada
módulo. Los valores por defecto son los de la librería (ADR-001).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Optional

from ..seguimiento.validacion_seg import UMBRALES_SEMAFORO, limites_de_semaforo
from ..validacion import EPSILON as TOLERANCIA_META_FINAL
from ..validacion import TOLERANCIA_PESO_PP

# Sobre ejecución por encima de este múltiplo de la meta es «posible error de
# escala» (ADR-001: el doble de la sobre ejecución del semáforo naranja).
UMBRAL_ESCALA = 2.5


@dataclass(frozen=True)
class ParametrosCalidad:
    """Parámetros del motor. Se construye con valores por defecto y se ajusta
    con :meth:`con` (devuelve una copia)."""

    # Semáforo en % (rojo = piso del % hasta la vigencia; naranja = techo de
    # sobre ejecución). La app inyecta los de Parametrizaciones; el pipeline
    # los de SDP 3.1.
    umbrales_semaforo: Mapping[str, float] = field(
        default_factory=lambda: dict(UMBRALES_SEMAFORO))
    # Tolerancia de las sumas de ponderación, en puntos porcentuales (ADR-001).
    tolerancia_peso_pp: float = TOLERANCIA_PESO_PP
    # Tolerancia absoluta al comparar metas anuales con la meta final (V17).
    tolerancia_meta_final: float = TOLERANCIA_META_FINAL
    # Múltiplo de la meta a partir del cual una sobre ejecución se trata como
    # posible error de escala (ADR-001: 250 %).
    umbral_escala: float = UMBRAL_ESCALA
    # Cociente entre metas de un mismo indicador que delata escalas mezcladas.
    ratio_escala_mezclada: float = 50.0
    # Primer año de la serie histórica de seguimiento.
    anio_min: int = 2018
    # Qué periodicidad manda en la exigencia de reporte: la del plan (cuando se
    # evalúa con plan) o la del formato de seguimiento.
    periodicidad_de: str = "plan"
    # Corte del análisis ``(año, trimestre)``. ``None``: el del archivo.
    corte: Optional[tuple] = None
    # ``False``: se descartan los hallazgos de indicadores No Vigentes, salvo
    # «No Vigente con ponderación» (RN-06 de alertas-seguimientos).
    incluir_no_vigentes: bool = True
    # ``False``: no se incluyen las alertas estructurales de la extracción
    # (``res.alertas``) entre los hallazgos.
    incluir_estructurales: bool = True
    # Mapa {entidad normalizada: sector oficial} de la app (ADVERTENCIA_SECTOR_ENTIDAD).
    entidad_sector: Optional[Mapping[str, str]] = None
    # ``CatalogoOficial`` para la regla V4 (sector/entidad fuera del listado).
    catalogo_oficial: Any = None
    # Reglas activas (códigos canónicos). ``None``: las ``por_defecto``.
    reglas_activas: Optional[frozenset] = None
    # Reglas que se apagan aunque sean por defecto.
    reglas_inactivas: frozenset = frozenset()

    # ── derivados ──
    @property
    def limites(self) -> tuple:
        """``(piso, techo)`` en fracción (ver ``limites_de_semaforo``)."""
        return limites_de_semaforo(self.umbrales_semaforo)

    @property
    def umbral_sobreejecucion(self) -> float:
        """Techo de sobre ejecución en fracción (naranja del semáforo)."""
        return self.limites[1]

    def con(self, **cambios) -> "ParametrosCalidad":
        """Copia con los cambios indicados."""
        return replace(self, **cambios)

    def activa(self, regla) -> bool:
        """¿La regla corre con estos parámetros?"""
        if regla.codigo in self.reglas_inactivas:
            return False
        if self.reglas_activas is not None:
            return regla.codigo in self.reglas_activas
        return regla.por_defecto


PARAMETROS_POR_DEFECTO = ParametrosCalidad()
