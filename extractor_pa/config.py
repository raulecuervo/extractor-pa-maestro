# -*- coding: utf-8 -*-
"""
Configuración del mapeo de columnas.

En vez de tener posiciones fijas dispersas por el código (frágil ante cambios
de plantilla), TODAS las anclas y filas clave viven aquí, en objetos
configurables. Heredado de sispp-sdis, que permitía sobreescribir el mapeo.

Hay dos mapeos predefinidos:
- `MAPEO_NUEVO`:   formato vigente (IP por offsets desde «Producto esperado»).
- `MAPEO_ANTIGUO`: variante con bloque financiero y columnas reordenadas
                   (p. ej. plan_accion_pp_cti); IP resuelto POR ANCLA.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MapeoColumnas:
    """Anclas y posiciones del plan de acción."""

    hoja: str = "Plan de acción"
    filas_encabezado: tuple = (9, 10, 11)
    fila_datos: int = 12

    # Anclas OBLIGATORIAS (si faltan, la estructura no se reconoce).
    ancla_meta_final_ir: str = "Meta de resultado Final"
    ancla_producto: str = "Producto esperado"

    # Anclas opcionales (encabezados de grupo, pueden caer en fila 9 o 10).
    ancla_meta_final_ip: str = "Meta de producto Final"
    ancla_responsables: str = "Responsables de la ejecución"
    ancla_corresponsables: str = "Corresponsables de la ejecución"

    # Posiciones fijas iniciales (mismo lugar en ambos formatos).
    col_objetivo: int = 1
    col_peso_objetivo: int = 2

    # Anclas de columnas IR: {ancla_texto: (clave_destino, fallback_1idx)}.
    anclas_ir: dict = field(default_factory=lambda: {
        "Nombre del indicador de resultado": ("nombre_ir", 4),
        "Vigente/No Vigente": ("vigente_ir", 5),
        "Importancia relativa  del resultado (%)": ("peso_ir", 6),
        "Fórmula del indicador de resultado": ("formula_ir", 7),
        "Sector Responsable": ("sector_ir", 8),
        "Entidad Responsable": ("entidad_ir", 9),
        "ODS": ("ods", 10),
        "Meta  ODS": ("meta_ods", 11),
        "Tipo de anualización": ("tipo_anual_ir", 12),
        "Periodicidad": ("periodicidad_ir", 13),
        "Resultado esperado": ("resultado", 3),
    })

    # Si el ancla IR no se encuentra, ¿usar la posición de respaldo? El formato
    # nuevo sí (robustez); el antiguo NO (las posiciones difieren y serían erróneas).
    fallback_posicional: bool = True

    # Anclas de columnas IP (formato antiguo/variante). Si es None, el IP se
    # resuelve por OFFSETS desde «Producto esperado» (formato nuevo).
    anclas_ip: Optional[dict] = None

    # Encabezados que se REPITEN (una vez para IR, otra para IP); se asignan por
    # orden de aparición (0=IR, 1=IP). {texto: (clave_ir, clave_ip)}.
    anclas_repetidas: dict = field(default_factory=lambda: {
        "Valor": ("lb_valor_ir", "lb_valor_ip"),
        "Año": ("lb_anio_ir", "lb_anio_ip"),
        "Fuente": ("lb_fuente_ir", "lb_fuente_ip"),
        "Fecha de inicio": ("fecha_inicio_ir", "fecha_inicio_ip"),
        "Fecha de finalización": ("fecha_fin_ir", "fecha_fin_ip"),
    })

    # ¿Detectar y leer el bloque financiero (Costo/Recurso/Fuente/Proyecto)?
    detectar_financiero: bool = False

    # Metadatos de cabecera: (clave, fila, columna).
    celdas_metadatos: tuple = (
        ("nombre_politica", 4, 2),
        ("sector_lider", 7, 2),
        ("entidad_lider", 7, 8),
        ("objetivo_general", 8, 1),
    )


# Mapeo del formato VIGENTE (nuevo).
MAPEO_NUEVO = MapeoColumnas()


# Mapeo de la variante ANTIGUA con bloque financiero (p. ej. plan_accion_pp_cti).
# El bloque IR no trae Vigente/Sector/Entidad/ODS; el IP está reordenado y va
# seguido de un bloque financiero de 4 columnas por año.
MAPEO_ANTIGUO = MapeoColumnas(
    fallback_posicional=False,
    detectar_financiero=True,
    anclas_ir={
        "Resultado esperado": ("resultado", None),
        "Importancia relativa  del resultado (%)": ("peso_ir", None),
        "Nombre del indicador de resultado": ("nombre_ir", None),
        "Fórmula del indicador de resultado": ("formula_ir", None),
    },
    anclas_ip={
        "Estado Vigente / No vigente": "vigente_ip",
        "Importancia relativa del producto (%)": "peso_ip",
        "Nombre indicador de producto": "nombre_ip",
        "Fórmula del indicador de producto": "formula_ip",
        "Indicador del PDD": "objetivo_pdd",
        "Código Meta PDD": "meta_pdd",
    },
    anclas_repetidas={
        "Valor": ("lb_valor_ir", "lb_valor_ip"),
        "Año": ("lb_anio_ir", "lb_anio_ip"),
        "Fecha de inicio": ("fecha_inicio_ir", "fecha_inicio_ip"),
        "Fecha de finalización": ("fecha_fin_ir", "fecha_fin_ip"),
        "Tipo de anualización": ("tipo_anual_ir", "tipo_anual_ip"),
        "Enfoque": ("enfoque_ir", "enfoque_princ"),
    },
)
