# -*- coding: utf-8 -*-
"""
Catálogo de reglas de calidad (fuente única; ADR-001).

Cada :class:`Regla` tiene un **código canónico** estable (``PLAN_…``,
``SEG_…``, ``CRUCE_…``, ``SERIE_…``, ``EXT_…``) y la lista de los **tipos
legados** que sustituye: el ``tipo`` de ``Alerta`` del plan (``catalogo.py``),
el ``tipo`` de ``HallazgoSeguimiento`` (``seguimiento/hallazgos.py``), las
reglas V0–V18 del validador, los ``tipo_alerta`` del pipeline de sispp y los
temas de ``observaciones_politica``.

Mientras dure la transición, ``Hallazgo.tipo`` sigue siendo el tipo legado
(el gate de paridad de alertas-seguimientos y ``alertas_planes_accion.csv``
no cambian); el código canónico va en ``Hallazgo.regla``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..catalogo import CAPA_EXTRACCION, CAPA_VALIDACION_PLAN, _TIPOS
from ..modelo import NIVEL_ADVERTENCIA, NIVEL_ERROR, NIVEL_INFO

# Severidades (las de ``HallazgoSeguimiento``/``make_finding``).
SEV_ERROR, SEV_ADVERTENCIA, SEV_INFO = "Error", "Advertencia", "Info"
SEVERIDADES = (SEV_ERROR, SEV_ADVERTENCIA, SEV_INFO)

NIVEL_A_SEVERIDAD = {NIVEL_ERROR: SEV_ERROR, NIVEL_ADVERTENCIA: SEV_ADVERTENCIA,
                     NIVEL_INFO: SEV_INFO}
SEVERIDAD_A_NIVEL = {v: k for k, v in NIVEL_A_SEVERIDAD.items()}
# Presentación en ``observaciones_politica`` (sispp-gobierno).
SEVERIDAD_A_OBSERVACION = {SEV_ERROR: "Alta", SEV_ADVERTENCIA: "Media", SEV_INFO: "Baja"}

# Niveles del objeto observado.
NIV_POLITICA, NIV_OBJETIVO, NIV_RESULTADO, NIV_PRODUCTO = "politica", "objetivo", "resultado", "producto"
NIV_INDICADOR, NIV_ARCHIVO = "indicador", "archivo"

# A qué se aplica la regla (qué datos necesita).
APLICA_PLAN = "plan"                      # solo el plan de acción
APLICA_SEGUIMIENTO = "seguimiento"        # un archivo de seguimiento (año del corte)
APLICA_SERIE = "serie"                    # el histórico del seguimiento
APLICA_ENTRE_CARGAS = "entre_cargas"      # base contra nuevo
APLICA_CRUCE = "cruce"                    # plan y seguimiento
APLICA_ESTRUCTURA_PLAN = "estructura_plan"
APLICA_ESTRUCTURA_SEG = "estructura_seguimiento"


@dataclass(frozen=True)
class Regla:
    codigo: str                 # canónico y estable, p. ej. "PLAN_PESO_OBJETIVOS"
    nombre: str                 # etiqueta corta (tema en observaciones_politica)
    descripcion: str            # qué significa (texto para la entidad)
    severidad: str              # Error | Advertencia | Info
    nivel: str                  # politica | objetivo | resultado | producto | indicador | archivo
    aplica_a: str               # APLICA_*
    familia: str                # Ponderación, Metas, Escala, Exigencia, Códigos…
    tipos_legados: tuple = ()   # tipos/códigos que sustituye
    accion: str = ""            # «Solicitar alcance…», «Solicitar ajuste del plan…»
    afecta_avance: bool = False
    por_defecto: bool = True    # las experimentales entran apagadas
    origen: str = ""            # V0–V18, pipeline, app, OAP…
    implementado: bool = True   # ¿la produce el motor?

    @property
    def nivel_alerta(self) -> str:
        """ERROR | ADVERTENCIA | INFO (nomenclatura de ``Alerta``)."""
        return SEVERIDAD_A_NIVEL[self.severidad]


def _r(codigo, nombre, descripcion, severidad, nivel, aplica_a, familia, *legados,
       accion="", afecta_avance=False, por_defecto=True, origen="", implementado=True):
    return Regla(codigo, nombre, descripcion, severidad, nivel, aplica_a, familia,
                 tuple(legados), accion, afecta_avance, por_defecto, origen, implementado)


_AJUSTE_PLAN = "Solicitar el ajuste del plan de acción ante la SDP."
_ALCANCE = "Solicitar alcance a la entidad para corregir el formato de seguimiento."
_CONFIRMAR = ("Confirmar con la entidad si es real y dejar la explicación en el cualitativo; "
              "por encima de 250 % revisar la escala y, si es error, solicitar alcance.")

# ─────────────────────────────────────────────────────────────────────────────
# Reglas del PLAN DE ACCIÓN (V0–V18 de ``validacion.py``, envueltas)
# ─────────────────────────────────────────────────────────────────────────────
_PLAN = [
    _r("PLAN_PESO_OBJETIVOS", "Pesos de los objetivos no suman 100 %",
       "Los pesos de los objetivos específicos no suman 100 %.",
       SEV_ERROR, NIV_POLITICA, APLICA_PLAN, "Ponderación",
       "ponderacion_objetivos", "V0", "Pesos de la política no suman 100 %",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V0"),
    _r("PLAN_PESO_CADENA_OBJ_IR", "Pesos de los resultados no cuadran con el objetivo",
       "La suma de los pesos de los IR de un objetivo no es igual al peso del objetivo.",
       SEV_ERROR, NIV_OBJETIVO, APLICA_PLAN, "Ponderación",
       "ponderacion_ir", "V1", "cadena_objetivo_resultados", "Pesos del objetivo no cuadran",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V1"),
    _r("PLAN_PESO_CADENA_IR_IP", "Pesos de los productos no cuadran con el resultado",
       "La suma de los pesos de los IP de un IR no es igual al peso del IR.",
       SEV_ERROR, NIV_RESULTADO, APLICA_PLAN, "Ponderación",
       "ponderacion_ip", "V2", "cadena_resultado_productos",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V2"),
    _r("PLAN_VIGENTE_SIN_PESO", "Indicador vigente sin ponderación",
       "Un indicador vigente no tiene ponderación numérica o pondera 0 %.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Ponderación",
       "ponderacion_faltante", "vigencia_ponderacion", "V18", "indicador_sin_ponderacion",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V1/V2/V18"),
    _r("PLAN_NO_VIGENTE_CON_PESO", "Indicador No Vigente con ponderación",
       "El plan marca el indicador como «No Vigente» pero le deja ponderación; ese peso "
       "no lo puede cumplir nadie.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Ponderación",
       "vigencia_ponderacion", "V18", "Producto No Vigente con peso",
       accion="Solicitar ajuste del plan: peso 0 o redistribuirlo.", afecta_avance=True,
       origen="V18; observaciones.obs_no_vigentes"),
    _r("PLAN_VIGENCIA_VACIA", "Vigencia sin diligenciar",
       "La casilla Vigente/No Vigente está vacía; el sistema asume vigente.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Ponderación", "PLAN_VIGENCIA_VACIA",
       "indicador_sin_vigencia", accion=_AJUSTE_PLAN, origen="alertas_datos (pipeline)"),
    _r("PLAN_SIN_RESPONSABLE", "Producto sin entidad responsable",
       "Un producto vigente no tiene entidad responsable: nadie lo ve como propio.",
       SEV_ADVERTENCIA, NIV_PRODUCTO, APLICA_PLAN, "Tipología", "PLAN_SIN_RESPONSABLE",
       "indicador_sin_responsable", "INDICADOR_SIN_RESPONSABLE", "V4c",
       accion=_AJUSTE_PLAN, origen="alertas_datos (pipeline); V4c"),
    _r("PLAN_TIPO_ANUALIZACION_INVALIDO", "Tipo de anualización no reconocido",
       "El tipo de anualización no es CRECIENTE, DECRECIENTE, CONSTANTE ni SUMA.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Tipología",
       "tipo_anualizacion_invalido", "V3", accion=_AJUSTE_PLAN, afecta_avance=True, origen="V3"),
    _r("PLAN_PERIODICIDAD_INVALIDA", "Periodicidad fuera del catálogo",
       "La periodicidad de medición no está en el catálogo del formato.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Tipología",
       "periodicidad_invalida", accion=_AJUSTE_PLAN, origen="sispp-gobierno"),
    _r("PLAN_SECTOR_NO_OFICIAL", "Sector fuera del listado oficial",
       "El sector responsable no está en el listado oficial de sectores (requiere catálogo).",
       SEV_INFO, NIV_INDICADOR, APLICA_PLAN, "Tipología", "sector_no_oficial", "V4", origen="V4"),
    _r("PLAN_ENTIDAD_NO_OFICIAL", "Entidad fuera del listado oficial",
       "La entidad responsable no está en el listado oficial de entidades (requiere catálogo).",
       SEV_INFO, NIV_INDICADOR, APLICA_PLAN, "Tipología", "entidad_no_oficial", "V4", origen="V4"),
    _r("PLAN_FECHA_INVALIDA", "Fecha no legible",
       "La fecha de inicio o de fin no se puede leer como fecha.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Fechas", "fecha_invalida", "V5",
       accion=_AJUSTE_PLAN, origen="V5"),
    _r("PLAN_FECHA_VACIA", "Sin fecha de inicio o de fin",
       "Falta la fecha de inicio o la de fin: la exigencia de reporte y el fin efectivo no se "
       "pueden calcular.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Fechas", "PLAN_FECHA_VACIA",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="formato 3.4 (ADR-001)"),
    _r("PLAN_FECHA_COMO_TEXTO", "Fecha escrita como texto",
       "La fecha está escrita como texto en la celda, no como fecha de Excel.",
       SEV_INFO, NIV_INDICADOR, APLICA_PLAN, "Fechas", "PLAN_FECHA_COMO_TEXTO",
       origen="formato 3.4 (ADR-001)"),
    _r("PLAN_FECHA_INICIO_MAYOR_FIN", "Fecha de fin anterior a la de inicio",
       "La fecha de inicio es posterior a la de finalización.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Fechas", "fecha_inicio_mayor_fin", "V5",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V5"),
    _r("PLAN_META_NO_NUMERICA", "Meta anual no numérica",
       "Una meta anual no es un número.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Metas", "meta_no_numerica", "V6", "V7",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V6/V7"),
    _r("PLAN_META_FINAL_FALTANTE", "Sin meta final",
       "El indicador no tiene meta final registrada.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Metas", "meta_final_faltante", "V8",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V8"),
    _r("PLAN_BRECHA_EN_METAS", "Faltan metas en años de la vigencia",
       "Según la periodicidad y las fechas, faltan metas en años esperados.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Metas", "brecha_en_metas", "V12",
       accion=_AJUSTE_PLAN, origen="V12"),
    _r("META_ANTES_INICIO", "Meta antes de la fecha de inicio",
       "Hay meta programada (> 0) en años anteriores al de la fecha de inicio: probable error "
       "del plan de acción. Esa meta cuenta en la meta acumulada y la trayectoria ideal.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Metas", "META_ANTES_INICIO",
       "meta_fuera_de_rango", "V15", "Meta antes de la fecha de inicio", "ADVERTENCIA_META_ANTES_INICIO",
       "EXTRA_FECHAS_INICIO_SIN_META",
       accion="Solicitar el ajuste del plan: corregir la fecha de inicio o las metas.",
       afecta_avance=True, origen="V15; metricas.metas_antes_de_inicio (0.27.0); app db; pipeline"),
    _r("PLAN_META_DESPUES_FIN", "Meta después de la fecha de fin",
       "Hay meta programada en años posteriores al de la fecha de fin.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Metas", "meta_fuera_de_rango", "V15",
       "EXTRA_FECHAS_FIN_CON_META", accion=_AJUSTE_PLAN, origen="V15"),
    _r("PLAN_META_VS_LINEA_BASE", "Meta final en sentido contrario a la línea base",
       "CRECIENTE con meta final menor que la línea base, o DECRECIENTE con meta final mayor.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Metas", "meta_vs_linea_base", "V14",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V14"),
    _r("PLAN_SUMA_METAS_VS_MF", "SUMA: las metas anuales no suman la meta final",
       "En un indicador SUMA la suma de las metas anuales debe ser la meta final.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Metas", "metas_vs_meta_final", "V17",
       "EXTRA_META_FINAL_VS_SUMA", accion=_AJUSTE_PLAN, afecta_avance=True, origen="V17"),
    _r("PLAN_CONSTANTE_METAS_DISTINTAS", "CONSTANTE con metas distintas de la meta final",
       "En un indicador CONSTANTE todas las metas anuales deben ser la meta final.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Metas", "metas_vs_meta_final", "V17",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V17; formato 3.4"),
    _r("PLAN_ULTIMA_META_VS_MF", "Última meta distinta de la meta final",
       "En CRECIENTE y DECRECIENTE la última meta anual debe ser la meta final.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Metas", "metas_vs_meta_final", "V17",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V17"),
    _r("PLAN_METAS_NO_MONOTONAS", "Metas no monótonas",
       "CRECIENTE con una meta anual menor que la anterior, o DECRECIENTE con una mayor.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Metas", "PLAN_METAS_NO_MONOTONAS",
       accion=_AJUSTE_PLAN, origen="formato 3.4 (ADR-001)"),
    _r("PLAN_ESCALA_MEZCLADA", "Metas en escalas mezcladas",
       "Las metas anuales mezclan una fracción (0–1) con valores mucho mayores: posible "
       "confusión entre proporción y porcentaje.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Escala", "escala_mezclada",
       accion=_AJUSTE_PLAN, origen="extractor-pa"),
    _r("PLAN_LINEA_BASE_FALTANTE", "Sin línea base",
       "No hay valor ni año de línea base.",
       SEV_INFO, NIV_INDICADOR, APLICA_PLAN, "Línea base", "linea_base_faltante", "V9", origen="V9"),
    _r("PLAN_LINEA_BASE_NO_NUMERICA", "Línea base no numérica",
       "El valor de la línea base no es un número.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_PLAN, "Línea base", "linea_base_no_numerica", "V9",
       accion=_AJUSTE_PLAN, origen="V9"),
    _r("PLAN_LB_OBLIGATORIA_DECRECIENTE", "DECRECIENTE sin línea base",
       "Un indicador DECRECIENTE necesita línea base numérica para calcular su avance.",
       SEV_ERROR, NIV_INDICADOR, APLICA_PLAN, "Línea base", "lb_obligatoria_decreciente", "V16",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="V16"),
    _r("PLAN_CODIGO_MALFORMADO", "Código con formato inesperado",
       "El código no tiene la forma OBJ=N, IR=N.N o IP=N.N.N.",
       SEV_INFO, NIV_INDICADOR, APLICA_PLAN, "Códigos", "codigo_malformado", "V13", origen="V13"),
    _r("PLAN_CODIGO_MAL_ESCRITO", "Código mal escrito",
       "El código se lee pero está mal escrito en la celda (punto doble, espacio, carácter "
       "invisible o prefijo); hoy el pipeline lo corrige sin avisar.",
       SEV_INFO, NIV_INDICADOR, APLICA_PLAN, "Códigos", "PLAN_CODIGO_MAL_ESCRITO",
       accion=_AJUSTE_PLAN, origen="utilidades.codigo_mal_escrito (ADR-001)"),
    _r("PLAN_IR_SIN_PRODUCTOS", "Resultado vigente sin productos",
       "Un IR vigente no tiene indicadores de producto asociados.",
       SEV_ADVERTENCIA, NIV_RESULTADO, APLICA_PLAN, "Códigos", "ir_sin_productos", "V11",
       "resultado_sin_productos", origen="V11"),
    _r("PLAN_JERARQUIA_ROTA", "Producto sin su resultado",
       "El producto N.N.N no cuelga de un resultado N.N existente.",
       SEV_ERROR, NIV_PRODUCTO, APLICA_PLAN, "Códigos", "jerarquia_ip", "producto_sin_resultado",
       accion=_AJUSTE_PLAN, afecta_avance=True, origen="creador; pipeline"),
    _r("PLAN_OBJETIVO_SIN_RESULTADOS", "Objetivo sin resultados",
       "Un objetivo específico no tiene resultados/IR asociados.",
       SEV_ADVERTENCIA, NIV_OBJETIVO, APLICA_PLAN, "Códigos", "objetivo_sin_resultados",
       origen="sispp-gobierno"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Reglas del SEGUIMIENTO (``validacion_seg.py``, envueltas)
# ─────────────────────────────────────────────────────────────────────────────
_SEG = [
    _r("SEG_NO_NUMERICO", "Reporte no numérico",
       "Un reporte cuantitativo del año del corte no es un número.",
       SEV_ERROR, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Reporte", "ERROR_NO_NUMERICO",
       accion=_ALCANCE, afecta_avance=True, origen="alertas-seguimientos"),
    _r("SEG_ESCALA", "Escala del reporte distinta de la meta",
       "La meta está en escala 0–1 y el reporte supera 1 (o al revés) en el año del corte.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Escala", "ADVERTENCIA_ESCALA",
       "Escala: meta en fracción y reporte en 0-100",
       accion="Solicitar alcance a la entidad: reportar en la misma escala de la meta.",
       afecta_avance=True, origen="alertas-seguimientos; observaciones.obs_escala"),
    _r("SEG_SOBREEJECUCION_PCT", "% de avance de la vigencia sobre el umbral de sobre ejecución",
       "El % de avance de la vigencia que trae el archivo supera el techo del semáforo (naranja, "
       "125 %): sobre ejecución. Por encima de 250 % es posible error de escala (Advertencia).",
       SEV_INFO, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Sobre ejecución", "ADVERTENCIA_AVANCE",
       "Avance entre 200 % y 500 %", "Avance mayor a 500 %", "pct_total > 300%",
       accion=_CONFIRMAR, origen="alertas-seguimientos; observaciones.obs_escala; calidad.py"),
    _r("SEG_SOBREEJECUCION_VIG", "Avance de la vigencia sobre el umbral de sobre ejecución",
       "El avance calculado en la vigencia (reportes contra la meta del periodo) supera el "
       "techo del semáforo.",
       SEV_INFO, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Sobre ejecución", "ADVERTENCIA_LIMITE_VIG",
       "EXTRA_SOBRE_EJECUCION_VIG", accion=_CONFIRMAR, origen="alertas-seguimientos"),
    _r("SEG_ACUMULADO_SOBRE_META_VIG", "Acumulado supera la meta acumulada",
       "El acumulado reportado supera la suma de las metas hasta el año del corte.",
       SEV_INFO, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Sobre ejecución",
       "ADVERTENCIA_ACUM_META_VIG", accion=_CONFIRMAR, origen="alertas-seguimientos"),
    _r("SEG_ACUMULADO_SOBRE_META_FINAL", "Acumulado supera la meta final",
       "El acumulado reportado supera la meta final del indicador.",
       SEV_INFO, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Sobre ejecución",
       "ADVERTENCIA_ACUM_META_FIN", accion=_CONFIRMAR, origen="alertas-seguimientos"),
    _r("SEG_META_SIN_REPORTE", "Meta sin reporte exigible",
       "El año del corte tiene meta y la periodicidad exigía reportar, pero no hay reporte.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Exigencia", "ADVERTENCIA_META_SIN_REP",
       "Sin reporte", "Falta reporte exigible",
       accion=_ALCANCE, afecta_avance=True, origen="alertas-seguimientos; estado_reporte"),
    _r("SEG_REPORTE_SIN_META", "Reporte en año sin meta",
       "Hay reporte en el año del corte pero la meta es 0 o no existe.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Exigencia", "ADVERTENCIA_REP_SIN_META",
       "meta_anual = 0 con valor reportado", accion=_AJUSTE_PLAN, origen="alertas-seguimientos"),
    _r("SEG_PCT_HASTA_VIG_FUERA_RANGO", "% hasta la vigencia fuera del semáforo",
       "El % de avance hasta la vigencia está por debajo del rojo (Advertencia) o por encima "
       "del naranja (Info; Advertencia por encima de 250 %).",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Sobre ejecución",
       "ADVERTENCIA_PCT_HASTA_VIG", accion=_CONFIRMAR, origen="alertas-seguimientos"),
    _r("SEG_DISCREPANCIA_PCT", "% reportado distinto del calculado",
       "El % de avance de la vigencia que trae el archivo difiere del calculado con sus reportes "
       "y la meta del periodo.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Reporte", "ADVERTENCIA_DISCREPANCIA_PCT",
       accion=_ALCANCE, origen="alertas-seguimientos"),
    _r("SEG_CUALITATIVO_VACIO", "Cualitativo vacío",
       "Indicador vigente sin reporte cualitativo en el corte.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Reporte", "ADVERTENCIA_CUAL",
       accion=_ALCANCE, origen="alertas-seguimientos"),
    _r("SEG_VIGENTE_SIN_PESO", "Indicador vigente sin ponderación (seguimiento)",
       "El formato de seguimiento trae el indicador vigente sin ponderación mayor que 0.",
       SEV_ERROR, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Ponderación", "ERROR_PONDERACION_OBLIGATORIA",
       accion=_ALCANCE, afecta_avance=True, origen="alertas-seguimientos"),
    _r("SEG_SECTOR_ENTIDAD", "Sector distinto del oficial de la entidad",
       "El sector que trae el archivo no es el oficial de esa entidad (requiere el mapa de la app).",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Tipología", "ADVERTENCIA_SECTOR_ENTIDAD",
       accion=_ALCANCE, origen="alertas-seguimientos"),
    _r("SEG_REPORTE_NEGATIVO", "Reporte negativo",
       "Un reporte cuantitativo es negativo.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Reporte", "SEG_REPORTE_NEGATIVO",
       "valor_reportado negativo", accion=_ALCANCE, afecta_avance=True,
       origen="calidad.py (pipeline); formato 3.4"),
    _r("SEG_NO_VIGENTE_CON_PESO", "Indicador No Vigente con ponderación (seguimiento)",
       "El formato marca el indicador como No Vigente pero le deja ponderación mayor que 0.",
       SEV_ERROR, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Ponderación", "SEG_NO_VIGENTE_CON_PESO",
       "Producto No Vigente con peso",
       accion="Solicitar ajuste: peso 0 o redistribuirlo.", afecta_avance=True,
       origen="observaciones.obs_no_vigentes (ADR-001)"),
    _r("SERIE_RETROCESO", "Retroceso del indicador",
       "CRECIENTE con un reporte menor que el anterior, o DECRECIENTE con uno mayor.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SERIE, "Serie", "SERIE_RETROCESO",
       "DISMINUCION_CRECIENTE", "AUMENTO_DECRECIENTE", "EXTRA_SENTIDO_CONTRARIO",
       accion="Confirmar con la entidad; si es error, solicitar alcance.",
       origen="ml_comentarios (87 %); sispp-sdis RN-CUA; formato 3.4"),
    _r("SERIE_REPORTE_SIN_META", "Reporte en año sin meta (serie)",
       "Hay reportes en años cerrados que no tienen meta programada.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SERIE, "Exigencia", "SERIE_REPORTE_SIN_META",
       accion=_AJUSTE_PLAN, origen="calidad.py (pipeline); formato 3.4"),
    _r("SERIE_ESCALA", "Posible error de escala en la serie",
       "En un año cerrado el avance supera 250 % de la meta, o la meta está en 0–1 y el "
       "reporte supera 1.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_SERIE, "Escala", "SERIE_ESCALA",
       "EXTRA_ESCALA_SERIE", "Avance mayor a 500 %", "valor > 10× la meta (posible escala)",
       accion="Revisar la escala con la entidad; si es error, solicitar alcance.",
       afecta_avance=True, origen="observaciones.obs_escala; calidad.py (ADR-001)"),
    _r("SERIE_SOBREEJECUCION", "Sobre ejecución en un año cerrado",
       "En un año cerrado el avance supera el techo del semáforo (hasta 250 %).",
       SEV_INFO, NIV_INDICADOR, APLICA_SERIE, "Sobre ejecución", "SERIE_SOBREEJECUCION",
       "pct_total entre 150% y 300%", accion=_CONFIRMAR, origen="calidad.py (ADR-001)"),
    # entre cargas
    _r("CARGA_CAMPO_INMUTABLE", "Campo inmutable modificado entre cargas",
       "Un campo de identidad del indicador cambió respecto del archivo base.",
       SEV_ERROR, NIV_INDICADOR, APLICA_ENTRE_CARGAS, "Entre cargas", "ERROR_ESTABILIDAD",
       accion=_ALCANCE, origen="alertas-seguimientos"),
    _r("CARGA_VALOR_HISTORICO", "Valor histórico modificado",
       "Un avance o acumulado de un periodo cerrado cambió respecto del archivo base.",
       SEV_ERROR, NIV_INDICADOR, APLICA_ENTRE_CARGAS, "Entre cargas", "ERROR_RETROACTIVO",
       accion="Verificar el alcance que respalda el cambio.", afecta_avance=True,
       origen="alertas-seguimientos"),
    _r("CARGA_CAMBIO_META", "Meta modificada entre cargas",
       "Una meta anual o la meta final cambió respecto del archivo base (ajuste al plan).",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_ENTRE_CARGAS, "Entre cargas", "ADVERTENCIA_CAMBIO_META",
       accion="Verificar que el acto administrativo respalde el ajuste.", afecta_avance=True,
       origen="alertas-seguimientos"),
    _r("CARGA_CAMBIO_ESTADO", "Cambio de estado entre cargas",
       "El indicador cambió de estado (p. ej. Vigente → No Vigente).",
       SEV_INFO, NIV_INDICADOR, APLICA_ENTRE_CARGAS, "Entre cargas", "INFO_CAMBIO_ESTADO",
       origen="alertas-seguimientos"),
    _r("CARGA_INDICADOR_NUEVO", "Indicador nuevo",
       "El indicador no existía en el archivo base.",
       SEV_INFO, NIV_INDICADOR, APLICA_ENTRE_CARGAS, "Entre cargas", "INFO_IND_NUEVO",
       origen="alertas-seguimientos"),
    _r("CARGA_INDICADOR_FALTANTE", "Indicador faltante",
       "El indicador estaba en el archivo base y no aparece en el nuevo.",
       SEV_INFO, NIV_INDICADOR, APLICA_ENTRE_CARGAS, "Entre cargas", "INFO_IND_FALTANTE",
       origen="alertas-seguimientos"),
]


def _reglas_estructurales() -> list:
    """Alertas estructurales de la extracción (``res.alertas``), una regla por
    tipo del catálogo legado, con su mismo nivel."""
    out = []
    for t in _TIPOS:
        if not t.implementado:
            continue
        if t.capa == CAPA_EXTRACCION:
            es_seg = t.familia == "Estructura seguimiento"
            aplica = APLICA_ESTRUCTURA_SEG if es_seg else APLICA_ESTRUCTURA_PLAN
        elif t.capa == CAPA_VALIDACION_PLAN and t.codigo == "codigo_ip_duplicado":
            aplica = APLICA_ESTRUCTURA_PLAN
        else:
            continue
        out.append(_r("EXT_" + t.codigo.upper(), t.descripcion.rstrip(".").split(":")[0][:80],
                      t.descripcion, NIVEL_A_SEVERIDAD[t.nivel], NIV_ARCHIVO, aplica,
                      t.familia, t.codigo, origen="extracción",
                      afecta_avance=t.nivel == NIVEL_ERROR))
    # El código IP duplicado sí es un error «duro» del plan (ADR-001).
    return out


_ESTRUCTURA = _reglas_estructurales()

# ─────────────────────────────────────────────────────────────────────────────
# Reglas de CRUCE plan ↔ seguimiento
# ─────────────────────────────────────────────────────────────────────────────
_CRUCE = [
    _r("CRUCE_IND_NO_EN_PLAN", "Indicador del seguimiento que no está en el plan",
       "El formato de seguimiento reporta un indicador vigente cuyo código no existe en el "
       "plan de acción: su avance no llega al tablero.",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_CRUCE, "Cruce", "CRUCE_IND_NO_EN_PLAN",
       "codigo_seguimiento_sin_plan", "indicador_reportado_sin_plan",
       "Productos del seguimiento que no están en el plan 2026",
       accion="Verificar la correspondencia de códigos con la entidad y la SDP.",
       afecta_avance=True, origen="seguimiento.cruzar_con_plan; alertas_datos; observaciones"),
    _r("CRUCE_IND_NO_EN_SEGUIMIENTO", "Indicador del plan que no está en el seguimiento",
       "Un indicador vigente del plan, con peso y ya iniciado, no aparece en el formato de "
       "seguimiento con el mismo código (¿se renumeró o no se reporta?).",
       SEV_ADVERTENCIA, NIV_INDICADOR, APLICA_CRUCE, "Cruce", "CRUCE_IND_NO_EN_SEGUIMIENTO",
       "Productos del plan que no están en el seguimiento",
       accion="Verificar con la entidad y con la SDP la correspondencia de códigos.",
       afecta_avance=True, origen="observaciones.obs_cruce_plan_seguimiento"),
    _r("CRUCE_PERIODICIDAD_DISTINTA", "Periodicidad distinta entre plan y seguimiento",
       "La periodicidad del plan no coincide con la del formato; la exigencia de reporte "
       "usa la del plan.",
       SEV_INFO, NIV_INDICADOR, APLICA_CRUCE, "Cruce", "CRUCE_PERIODICIDAD_DISTINTA",
       accion=_ALCANCE, origen="ADR-001 (C5)"),
]

REGLAS: list = _ESTRUCTURA + _PLAN + _SEG + _CRUCE
CATALOGO_CALIDAD: dict = {r.codigo: r for r in REGLAS}
assert len(CATALOGO_CALIDAD) == len(REGLAS), "códigos de regla repetidos"


# ─────────────────────────── correspondencia con los tipos legados ───────────

def _indice_legados() -> dict:
    idx: dict = {}
    for r in REGLAS:
        for t in r.tipos_legados:
            idx.setdefault(t, []).append(r.codigo)
    return idx


_LEGADOS = _indice_legados()

# Tipos legados que corresponden a más de una regla: se decide por el texto.
_DESAMBIGUAR = {
    "vigencia_ponderacion": (("No Vigente pero pondera", "PLAN_NO_VIGENTE_CON_PESO"),
                             ("", "PLAN_VIGENTE_SIN_PESO")),
    "meta_fuera_de_rango": (("anteriores a la fecha de inicio", "META_ANTES_INICIO"),
                            ("", "PLAN_META_DESPUES_FIN")),
    "metas_vs_meta_final": (("SUMA", "PLAN_SUMA_METAS_VS_MF"),
                            ("CONSTANTE", "PLAN_CONSTANTE_METAS_DISTINTAS"),
                            ("", "PLAN_ULTIMA_META_VS_MF")),
}


def regla_de_tipo(tipo: str, descripcion: str = "") -> Regla:
    """Regla canónica de un tipo legado (de ``Alerta`` o ``HallazgoSeguimiento``).
    Si el tipo no está en el catálogo devuelve una regla genérica con su mismo
    código, para no perder nunca un hallazgo."""
    if tipo in _DESAMBIGUAR:
        for marca, codigo in _DESAMBIGUAR[tipo]:
            if marca in (descripcion or ""):
                return CATALOGO_CALIDAD[codigo]
    codigos = _LEGADOS.get(tipo)
    if codigos:
        return CATALOGO_CALIDAD[codigos[0]]
    if tipo in CATALOGO_CALIDAD:
        return CATALOGO_CALIDAD[tipo]
    return Regla(tipo, tipo, "", SEV_INFO, NIV_INDICADOR, APLICA_SEGUIMIENTO, "Otros",
                 (tipo,), origen="desconocido", implementado=False)


def por_aplica_a(*aplica_a: str) -> list:
    return [r for r in REGLAS if r.aplica_a in aplica_a]


def por_familia(familia: str) -> list:
    return [r for r in REGLAS if r.familia == familia]
