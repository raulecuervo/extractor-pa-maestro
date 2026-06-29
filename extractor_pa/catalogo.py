# -*- coding: utf-8 -*-
"""
Catálogo CONSOLIDADO de alertas, errores y chequeos.

Único punto de verdad de todos los tipos de alerta del sistema, consolidando lo
revisado en los 9 aplicativos de política pública:

- `validador-plan-accion`  → reglas V0–V18 (modular, la referencia).
- `generador-seguimiento`  → mismas V0–V18 (códigos `V0`..`V18` explícitos).
- `sispp-gobierno`         → V0–V18 inline + extras (periodicidad, objetivo sin
                             resultados, formato no compatible, IP duplicado).
- `extractor-planes-accion`→ tipo_anualización, sector/entidad, meta no numérica,
                             código malformado.
- `creador-planes-accion`  → validación de captura (error/aviso).
- `alertas-seguimientos`   → 15 tipos de consistencia del SEGUIMIENTO.
- `sispp-sdis`             → alertas OPERATIVAS (vencimiento, rezago…) y CUALITATIVAS.
- `sistema-seguimiento-v3` → reglas de calidad declarativas Q001–Q003.
- `seguimiento-pp-sdis`    → (sin motor de alertas).

Cada tipo se normaliza a la nomenclatura ÚNICA de nivel: ERROR / ADVERTENCIA / INFO.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

# Niveles unificados (definidos en modelo; aquí solo se reexportan).
from .modelo import NIVEL_ERROR, NIVEL_ADVERTENCIA, NIVEL_INFO

NIVELES_VALIDOS = (NIVEL_ERROR, NIVEL_ADVERTENCIA, NIVEL_INFO)

# Capas del sistema (a qué módulo pertenece el chequeo).
CAPA_EXTRACCION = "extraccion"          # leído/estructura del Excel del plan
CAPA_VALIDACION_PLAN = "validacion_plan"  # reglas de negocio V0–V18 sobre el plan
CAPA_SEGUIMIENTO = "seguimiento"        # consistencia del reporte de seguimiento
CAPA_OPERATIVA = "operativa"            # alertas temporales/push a usuarios
CAPA_CUALITATIVA = "cualitativa"        # justificaciones obligatorias
CAPA_CALIDAD = "calidad"                # reglas de calidad declarativas


@dataclass(frozen=True)
class TipoAlerta:
    codigo: str            # identificador único (tipo)
    nivel: str             # ERROR | ADVERTENCIA | INFO
    familia: str           # agrupación temática
    capa: str              # CAPA_*
    descripcion: str       # qué significa
    regla: Optional[str] = None     # código de regla de origen (V0..V18, RN-…)
    implementado: bool = False      # ¿lo produce el extractor maestro hoy?


# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO
# ─────────────────────────────────────────────────────────────────────────────
_TIPOS = [
    # ── Familia: Estructura / Extracción (capa extracción, implementadas) ──
    TipoAlerta("apertura", NIVEL_ERROR, "Estructura", CAPA_EXTRACCION,
               "El archivo no se pudo abrir.", implementado=True),
    TipoAlerta("hoja_no_encontrada", NIVEL_ERROR, "Estructura", CAPA_EXTRACCION,
               "No se encontró la hoja del plan de acción.", implementado=True),
    TipoAlerta("formato_no_reconocido", NIVEL_ERROR, "Estructura", CAPA_EXTRACCION,
               "El detector no pudo determinar el formato (ni nuevo ni antiguo).",
               implementado=True),
    TipoAlerta("formato_no_compatible", NIVEL_ERROR, "Estructura", CAPA_EXTRACCION,
               "La plantilla es incompatible con el formato vigente.",
               regla="sispp-gobierno"),
    TipoAlerta("estructura", NIVEL_ERROR, "Estructura", CAPA_EXTRACCION,
               "Faltan las anclas obligatorias ('Meta de resultado Final'/'Producto esperado').",
               implementado=True),
    TipoAlerta("metadatos", NIVEL_ADVERTENCIA, "Estructura", CAPA_EXTRACCION,
               "No se pudo identificar el nombre de la política en la cabecera.",
               regla="sispp-gobierno"),
    TipoAlerta("sin_ir", NIVEL_ADVERTENCIA, "Estructura", CAPA_EXTRACCION,
               "No se extrajo ningún Indicador de Resultado.", implementado=True),
    TipoAlerta("sin_ip", NIVEL_ADVERTENCIA, "Estructura", CAPA_EXTRACCION,
               "No se extrajo ningún Indicador de Producto.", implementado=True),
    TipoAlerta("ir_sin_nombre", NIVEL_ADVERTENCIA, "Estructura", CAPA_EXTRACCION,
               "Una fila trae código de IR pero sin nombre (se omitió).",
               implementado=True),
    TipoAlerta("ip_sin_nombre", NIVEL_ADVERTENCIA, "Estructura", CAPA_EXTRACCION,
               "Una fila trae código de IP pero sin nombre (se omitió).",
               implementado=True),

    # ── Familia: Estructura del SEGUIMIENTO (.xlsb) ──
    TipoAlerta("apertura_seguimiento", NIVEL_ERROR, "Estructura seguimiento", CAPA_EXTRACCION,
               "No se pudo abrir el archivo .xlsb de seguimiento.", implementado=True),
    TipoAlerta("hoja_seguimiento_no_encontrada", NIVEL_ERROR, "Estructura seguimiento", CAPA_EXTRACCION,
               "No se encontró la hoja 'Avance Cuantitativo'.", implementado=True),
    TipoAlerta("anclas_no_encontradas", NIVEL_ERROR, "Estructura seguimiento", CAPA_EXTRACCION,
               "No se encontraron las anclas de bloques en la fila de encabezados.",
               implementado=True),
    TipoAlerta("sin_indicadores_seguimiento", NIVEL_ADVERTENCIA, "Estructura seguimiento", CAPA_EXTRACCION,
               "No se extrajo ningún indicador de seguimiento.", implementado=True),
    TipoAlerta("indicador_seguimiento_sin_codigo", NIVEL_INFO, "Estructura seguimiento", CAPA_EXTRACCION,
               "Fila de seguimiento sin código de indicador reconocible.", implementado=True),
    TipoAlerta("codigo_seguimiento_sin_plan", NIVEL_INFO, "Estructura seguimiento", CAPA_SEGUIMIENTO,
               "Un código de seguimiento no se encontró en el plan de acción.",
               implementado=True),

    # ── Familia: Códigos / Jerarquía (capa validación, estructurales) ──
    TipoAlerta("codigo_malformado", NIVEL_INFO, "Códigos", CAPA_VALIDACION_PLAN,
               "Código con formato inesperado (OBJ=N, IR=N.N, IP=N.N.N).",
               regla="V13", implementado=True),
    TipoAlerta("codigo_ip_duplicado", NIVEL_ERROR, "Códigos", CAPA_VALIDACION_PLAN,
               "Un mismo código de IP aparece más de una vez.",
               regla="V10", implementado=True),
    TipoAlerta("ir_sin_productos", NIVEL_ADVERTENCIA, "Códigos", CAPA_VALIDACION_PLAN,
               "Un IR vigente no tiene Indicadores de Producto asociados.",
               regla="V11", implementado=True),
    TipoAlerta("objetivo_sin_resultados", NIVEL_ADVERTENCIA, "Códigos", CAPA_VALIDACION_PLAN,
               "Un objetivo específico no tiene Resultados/IR asociados.",
               regla="sispp-gobierno", implementado=False),
    TipoAlerta("jerarquia_ip", NIVEL_ERROR, "Códigos", CAPA_VALIDACION_PLAN,
               "El producto N.N.N no cuelga de su resultado N.N (jerarquía rota).",
               regla="creador", implementado=False),

    # ── Familia: Consistencia entre filas (capa extracción) ──
    TipoAlerta("inconsistencia_en_ir", NIVEL_ADVERTENCIA, "Consistencia", CAPA_EXTRACCION,
               "El mismo IR aparece en varias filas con un valor no vacío distinto.",
               implementado=True),

    # ── Familia: Ponderación V0/V1/V2/V18 ──
    TipoAlerta("ponderacion_objetivos", NIVEL_ERROR, "Ponderación", CAPA_VALIDACION_PLAN,
               "Los pesos de los objetivos no suman 100%.",
               regla="V0", implementado=True),
    TipoAlerta("ponderacion_ir", NIVEL_ERROR, "Ponderación", CAPA_VALIDACION_PLAN,
               "Los pesos de los IR de un objetivo no igualan el peso del objetivo.",
               regla="V1", implementado=True),
    TipoAlerta("ponderacion_ip", NIVEL_ERROR, "Ponderación", CAPA_VALIDACION_PLAN,
               "Los pesos de los IP de un IR no igualan el peso del IR.",
               regla="V2", implementado=True),
    TipoAlerta("ponderacion_faltante", NIVEL_ERROR, "Ponderación", CAPA_VALIDACION_PLAN,
               "Indicador vigente sin ponderación numérica.",
               regla="V1/V2", implementado=True),
    TipoAlerta("vigencia_ponderacion", NIVEL_ERROR, "Ponderación", CAPA_VALIDACION_PLAN,
               "Incoherencia vigencia↔ponderación (No Vigente debe pesar 0; Vigente >0).",
               regla="V18", implementado=True),

    # ── Familia: Tipología / catálogos V3/V4 ──
    TipoAlerta("tipo_anualizacion_invalido", NIVEL_ERROR, "Tipología", CAPA_VALIDACION_PLAN,
               "Tipo de anualización fuera del catálogo (CRECIENTE/DECRECIENTE/CONSTANTE/SUMA).",
               regla="V3", implementado=True),
    TipoAlerta("periodicidad_invalida", NIVEL_ADVERTENCIA, "Tipología", CAPA_VALIDACION_PLAN,
               "Periodicidad fuera del catálogo.",
               regla="sispp-gobierno", implementado=True),
    TipoAlerta("sector_no_oficial", NIVEL_INFO, "Tipología", CAPA_VALIDACION_PLAN,
               "Sector responsable no reconocido en el catálogo oficial (opcional).",
               regla="V4", implementado=True),
    TipoAlerta("entidad_no_oficial", NIVEL_INFO, "Tipología", CAPA_VALIDACION_PLAN,
               "Entidad responsable no reconocida en el catálogo oficial (opcional).",
               regla="V4", implementado=True),

    # ── Familia: Fechas V5 ──
    TipoAlerta("fecha_invalida", NIVEL_ADVERTENCIA, "Fechas", CAPA_VALIDACION_PLAN,
               "Fecha no parseable.", regla="V5", implementado=True),
    TipoAlerta("fecha_inicio_mayor_fin", NIVEL_ERROR, "Fechas", CAPA_VALIDACION_PLAN,
               "La fecha de inicio es posterior a la de finalización.",
               regla="V5", implementado=True),

    # ── Familia: Metas V6/V7/V8/V12/V14/V15/V17 ──
    TipoAlerta("meta_no_numerica", NIVEL_ERROR, "Metas", CAPA_VALIDACION_PLAN,
               "Una meta anual no es numérica.", regla="V6/V7", implementado=True),
    TipoAlerta("meta_final_faltante", NIVEL_ERROR, "Metas", CAPA_VALIDACION_PLAN,
               "Falta la meta final del indicador.", regla="V8", implementado=True),
    TipoAlerta("brecha_en_metas", NIVEL_ADVERTENCIA, "Metas", CAPA_VALIDACION_PLAN,
               "Faltan metas en años esperados según la periodicidad/vigencia.",
               regla="V12", implementado=True),
    TipoAlerta("meta_fuera_de_rango", NIVEL_ADVERTENCIA, "Metas", CAPA_VALIDACION_PLAN,
               "Hay metas en años fuera del rango de vigencia (inicio–fin).",
               regla="V15", implementado=True),
    TipoAlerta("meta_vs_linea_base", NIVEL_ERROR, "Metas", CAPA_VALIDACION_PLAN,
               "CRECIENTE con meta_final < línea base (o DECRECIENTE al revés).",
               regla="V14", implementado=True),
    TipoAlerta("metas_vs_meta_final", NIVEL_ERROR, "Metas", CAPA_VALIDACION_PLAN,
               "SUMA: Σ metas anuales ≠ meta_final; resto: última meta ≠ meta_final.",
               regla="V17", implementado=True),
    TipoAlerta("escala_mezclada", NIVEL_ADVERTENCIA, "Metas", CAPA_VALIDACION_PLAN,
               "Las metas anuales del indicador mezclan escalas (fracción 0-1 y "
               "valores >1.5), posible error de unidades.", regla="escala", implementado=True),

    # ── Familia: Línea base V9/V16 ──
    TipoAlerta("linea_base_faltante", NIVEL_INFO, "Línea base", CAPA_VALIDACION_PLAN,
               "Línea base (valor y/o año) no registrada.", regla="V9", implementado=True),
    TipoAlerta("linea_base_no_numerica", NIVEL_ADVERTENCIA, "Línea base", CAPA_VALIDACION_PLAN,
               "El valor de línea base no es numérico.", regla="V9", implementado=True),
    TipoAlerta("lb_obligatoria_decreciente", NIVEL_ERROR, "Línea base", CAPA_VALIDACION_PLAN,
               "Indicador DECRECIENTE sin línea base (es obligatoria).",
               regla="V16", implementado=True),

    # ── Familia: Seguimiento — consistencia del reporte (alertas-seguimientos) ──
    TipoAlerta("ERROR_ESTABILIDAD", NIVEL_ERROR, "Seguimiento", CAPA_SEGUIMIENTO,
               "Campo inmutable del indicador modificado entre cargas."),
    TipoAlerta("ERROR_RETROACTIVO", NIVEL_ERROR, "Seguimiento", CAPA_SEGUIMIENTO,
               "Valor histórico (periodo cerrado) modificado."),
    TipoAlerta("ERROR_NO_NUMERICO", NIVEL_ERROR, "Seguimiento", CAPA_SEGUIMIENTO,
               "Reporte cuantitativo con valor no numérico."),
    TipoAlerta("ADVERTENCIA_ESCALA", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "Incoherencia de escala entre la meta y el reporte."),
    TipoAlerta("ADVERTENCIA_AVANCE", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "El avance supera la meta + 25% (umbral 125%)."),
    TipoAlerta("ADVERTENCIA_LIMITE_VIG", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "El reporte/suma de la vigencia supera el 125% de la meta programada."),
    TipoAlerta("ADVERTENCIA_ACUM_META_VIG", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "El acumulado supera la meta acumulada de la vigencia."),
    TipoAlerta("ADVERTENCIA_ACUM_META_FIN", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "El acumulado supera la meta final."),
    TipoAlerta("ADVERTENCIA_META_SIN_REP", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "Existe meta para la vigencia pero no hay reporte."),
    TipoAlerta("ADVERTENCIA_REP_SIN_META", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "Hay reporte pero la meta es 0 o no existe."),
    TipoAlerta("ADVERTENCIA_PCT_HASTA_VIG", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "% de avance hasta la vigencia fuera de rango (<50% o >125%)."),
    TipoAlerta("ADVERTENCIA_DISCREPANCIA_PCT", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "El % reportado difiere del calculado (acumulado/meta anual)."),
    TipoAlerta("ADVERTENCIA_CUAL", NIVEL_ADVERTENCIA, "Seguimiento", CAPA_SEGUIMIENTO,
               "Indicador Vigente sin reporte cualitativo."),
    TipoAlerta("INFO_IND_NUEVO", NIVEL_INFO, "Seguimiento", CAPA_SEGUIMIENTO,
               "Indicador nuevo (no existía en el archivo base)."),
    TipoAlerta("INFO_IND_FALTANTE", NIVEL_INFO, "Seguimiento", CAPA_SEGUIMIENTO,
               "Indicador presente en la base pero ausente en el nuevo archivo."),

    # ── Familia: Operativas / temporales (sispp-sdis) ──
    TipoAlerta("INDICADOR_SIN_RESPONSABLE", NIVEL_ADVERTENCIA, "Operativa", CAPA_OPERATIVA,
               "Indicador vigente sin ejecutor asignado.", regla="RN-ALE-001"),
    TipoAlerta("INDICADOR_SIN_SEGUIMIENTO", NIVEL_ADVERTENCIA, "Operativa", CAPA_OPERATIVA,
               "Indicador sin reporte en el período.", regla="RN-ALE-001"),
    TipoAlerta("PROXIMO_VENCIMIENTO", NIVEL_ADVERTENCIA, "Operativa", CAPA_OPERATIVA,
               "Faltan N días (5/3/1) para la fecha límite y el reporte está pendiente.",
               regla="RN-ALE-004"),
    TipoAlerta("REZAGO", NIVEL_ADVERTENCIA, "Operativa", CAPA_OPERATIVA,
               "Semáforo ROJO/AMARILLO (ejecución baja/media).", regla="semáforo"),
    TipoAlerta("SOBRECUMPLIMIENTO", NIVEL_ADVERTENCIA, "Operativa", CAPA_OPERATIVA,
               "PHV supera el umbral de sobre ejecución (>125%).", regla="semáforo"),
    TipoAlerta("DISMINUCION_CRECIENTE", NIVEL_ADVERTENCIA, "Operativa", CAPA_OPERATIVA,
               "Indicador CRECIENTE cuyo valor disminuyó vs período anterior.",
               regla="RN-CUA-002"),
    TipoAlerta("AUMENTO_DECRECIENTE", NIVEL_ADVERTENCIA, "Operativa", CAPA_OPERATIVA,
               "Indicador DECRECIENTE cuyo valor aumentó vs período anterior.",
               regla="RN-CUA-003"),
    TipoAlerta("CRP_SOBREASIGNADO", NIVEL_ADVERTENCIA, "Operativa", CAPA_OPERATIVA,
               "Un CRP tiene >100% comprometido en una política.", regla="RN-FIN-004"),

    # ── Familia: Cualitativas (sispp-sdis RN-CUL) ──
    TipoAlerta("justificacion_rezago_obligatoria", NIVEL_ERROR, "Cualitativa", CAPA_CUALITATIVA,
               "Falta la justificación obligatoria de rezago (semáforo ROJO/AMARILLO).",
               regla="RN-CUL-003"),
    TipoAlerta("justificacion_sobrecumplimiento_obligatoria", NIVEL_ERROR, "Cualitativa", CAPA_CUALITATIVA,
               "Falta la justificación obligatoria de sobrecumplimiento.",
               regla="RN-CUL-003"),

    # ── Familia: Calidad declarativa (sistema-seguimiento-v3) ──
    TipoAlerta("Q001", NIVEL_ERROR, "Calidad", CAPA_CALIDAD,
               "No permitir metas finales negativas.", regla="Q001"),
    TipoAlerta("Q002", NIVEL_ERROR, "Calidad", CAPA_CALIDAD,
               "No cerrar la política sin corte final publicado.", regla="Q002"),
    TipoAlerta("Q003", NIVEL_ADVERTENCIA, "Calidad", CAPA_CALIDAD,
               "Cada ajuste debe tener justificación.", regla="Q003"),
]

# Las 15 alertas de consistencia del seguimiento (familia "Seguimiento") ya están
# implementadas en `extractor_pa.seguimiento.validar_consistencia` (Fase S3).
_TIPOS = [replace(t, implementado=True) if (t.familia == "Seguimiento" and not t.implementado) else t
          for t in _TIPOS]

# Índice por código.
CATALOGO = {t.codigo: t for t in _TIPOS}


def nivel_de(codigo: str, defecto: str = NIVEL_ADVERTENCIA) -> str:
    """Nivel canónico de un tipo de alerta (según el catálogo)."""
    t = CATALOGO.get(codigo)
    return t.nivel if t else defecto


def esta_registrado(codigo: str) -> bool:
    return codigo in CATALOGO


def por_capa(capa: str) -> list:
    return [t for t in _TIPOS if t.capa == capa]


def por_familia(familia: str) -> list:
    return [t for t in _TIPOS if t.familia == familia]
