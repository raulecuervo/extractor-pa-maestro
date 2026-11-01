# -*- coding: utf-8 -*-
"""
Reglas de la 0.29.0 (ADR-001, «Cambia alertas»): cada una con un caso que la
activa y otro que no. Cubre las decisiones de F0 (tolerancia 0,1 pp, umbrales
125 / 250 %, exigencia con `fin_efectivo` y periodicidad del plan, No Vigentes),
las reglas movidas desde el pipeline y las nuevas.
"""

from __future__ import annotations

import datetime as dt

from extractor_pa.calidad import (
    COLS_OBSERVACION, ParametrosCalidad, alertas_plan, evaluar, hallazgos_app,
    observaciones_desde,
)
from extractor_pa.modelo import IndicadorProducto, IndicadorResultado, Metadatos, ResultadoExtraccion
from extractor_pa.seguimiento import (
    IndicadorSeguimiento, MetadatosSeguimiento, ResultadoSeguimiento, validar_archivo,
)

TODO = ParametrosCalidad(incluir_no_vigentes=True)


def _plan(*ips, irs=None):
    irs = irs if irs is not None else [
        IndicadorResultado(codigo_objetivo="1", codigo_ir="1.1", nombre_indicador="IR",
                           es_vigente="Vigente", peso_pct=100, peso_objetivo_pct=100,
                           tipo_anualizacion="SUMA", periodicidad="Anual",
                           fecha_inicio=dt.datetime(2024, 1, 1), fecha_fin=dt.datetime(2026, 12, 31),
                           meta_final=sum(a_f(ip.peso_pct) for ip in ips) or 100,
                           metas_por_anio={2024: 30, 2025: 30, 2026: 40}, valor_linea_base=0,
                           anio_linea_base=2023, sector_responsable="Gobierno",
                           entidad_responsable="SDG")]
    irs[0].meta_final = 100
    return ResultadoExtraccion(Metadatos(nombre_politica="PP", archivo_fuente="pa.xlsx"),
                               indicadores_resultado=irs, indicadores_producto=list(ips))


def a_f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _ip(**kw):
    base = dict(codigo_objetivo="1", codigo_ir="1.1", codigo_ip="1.1.1", nombre_indicador="IP",
                es_vigente="Vigente", peso_pct=100, tipo_anualizacion="SUMA",
                periodicidad="Trimestral", fecha_inicio=dt.datetime(2024, 1, 1),
                fecha_fin=dt.datetime(2026, 12, 31), meta_final=100,
                metas_por_anio={2024: 30, 2025: 30, 2026: 40}, valor_linea_base=0,
                anio_linea_base=2023, entidad_responsable="SDG", producto_esperado="1.1.1 Producto")
    base.update(kw)
    return IndicadorProducto(**base)


def _reglas_plan(plan, **p):
    return [h.regla for h in evaluar(plan=plan, parametros=TODO.con(**p), aplica_a=["plan"])]


def _ind(**kw):
    base = dict(codigo="1.1.1", nombre="Ind", sector="Gobierno", entidad="SDG", estado="Vigente",
                corte="Q2", anio_reporte=2026, tipo_anualizacion="Suma", periodicidad="Trimestral",
                ponderacion=5, fecha_inicio="2024-01-01", fecha_fin="2026-12-31", meta_final=100,
                metas={"2024": 30, "2025": 30, "2026": 40})
    base.update(kw)
    return IndicadorSeguimiento(**base)


def _seg(*inds, politica="PP"):
    return ResultadoSeguimiento(MetadatosSeguimiento(archivo_fuente="s.xlsb", nombre_politica=politica),
                                list(inds))


def _hs(seg, plan=None, **p):
    return evaluar(plan=plan, seguimiento=seg, parametros=TODO.con(**p))


def _reglas_seg(seg, plan=None, **p):
    return [h.regla for h in _hs(seg, plan, **p)]


# ─────────────────────────── plan: decisiones F0 ───────────────────────────


def test_tolerancia_de_pesos_0_1_pp():
    base = _plan(_ip(peso_pct=100))
    assert "PLAN_PESO_OBJETIVOS" not in _reglas_plan(base)
    base.indicadores_resultado[0].peso_objetivo_pct = 100.15     # 0,15 pp de más
    assert "PLAN_PESO_OBJETIVOS" in _reglas_plan(base)
    base.indicadores_resultado[0].peso_objetivo_pct = 100.08
    assert "PLAN_PESO_OBJETIVOS" not in _reglas_plan(base)
    # Cadena IR → IP con la misma tolerancia.
    assert "PLAN_PESO_CADENA_IR_IP" in _reglas_plan(_plan(_ip(peso_pct=99.8)))
    assert "PLAN_PESO_CADENA_IR_IP" not in _reglas_plan(_plan(_ip(peso_pct=99.95)))


def test_no_vigente_con_peso_y_vigente_sin_peso():
    r = _reglas_plan(_plan(_ip(es_vigente="No Vigente", peso_pct=100)))
    assert "PLAN_NO_VIGENTE_CON_PESO" in r and "PLAN_VIGENTE_SIN_PESO" not in r
    r = _reglas_plan(_plan(_ip(peso_pct=0)))
    assert "PLAN_VIGENTE_SIN_PESO" in r and "PLAN_NO_VIGENTE_CON_PESO" not in r
    assert "PLAN_VIGENTE_SIN_PESO" in _reglas_plan(_plan(_ip(peso_pct=None)))
    # Un No Vigente con peso 0 no alerta nada de ponderación.
    r = _reglas_plan(_plan(_ip(es_vigente="No Vigente", peso_pct=0)))
    assert not {"PLAN_NO_VIGENTE_CON_PESO", "PLAN_VIGENTE_SIN_PESO"} & set(r)


def test_severidades_del_plan_segun_adr():
    hs = {h.regla: h for h in evaluar(plan=_plan(_ip(peso_pct=0, meta_final=None, periodicidad="Rara",
                                                     fecha_inicio=None)), parametros=TODO)}
    assert hs["PLAN_VIGENTE_SIN_PESO"].severidad == "Error"
    assert hs["PLAN_META_FINAL_FALTANTE"].severidad == "Error"
    assert hs["PLAN_PERIODICIDAD_INVALIDA"].severidad == "Advertencia"
    assert hs["PLAN_FECHA_VACIA"].severidad == "Advertencia"


# ─────────────────────────── plan: reglas nuevas ───────────────────────────


def test_metas_no_monotonas():
    sube_y_baja = _ip(tipo_anualizacion="CRECIENTE", metas_por_anio={2024: 10, 2025: 20, 2026: 15},
                      meta_final=15)
    assert "PLAN_METAS_NO_MONOTONAS" in _reglas_plan(_plan(sube_y_baja))
    ok = _ip(tipo_anualizacion="CRECIENTE", metas_por_anio={2024: 10, 2025: 20, 2026: 20}, meta_final=20)
    assert "PLAN_METAS_NO_MONOTONAS" not in _reglas_plan(_plan(ok))
    dec = _ip(tipo_anualizacion="DECRECIENTE", metas_por_anio={2024: 10, 2025: 12, 2026: 5},
              meta_final=5, valor_linea_base=20)
    assert "PLAN_METAS_NO_MONOTONAS" in _reglas_plan(_plan(dec))
    # Los ceros de relleno no cuentan como meta (CTI 3.1.1: 4, 5, 0, 0).
    relleno = _ip(tipo_anualizacion="CRECIENTE", metas_por_anio={2024: 4, 2025: 5, 2026: 0}, meta_final=5)
    assert "PLAN_METAS_NO_MONOTONAS" not in _reglas_plan(_plan(relleno))
    assert "PLAN_METAS_NO_MONOTONAS" not in _reglas_plan(_plan(_ip()))  # SUMA no aplica


def test_constante_con_metas_distintas_y_suma_que_no_suma():
    const = _ip(tipo_anualizacion="CONSTANTE", metas_por_anio={2024: 1, 2025: 0.8, 2026: 1}, meta_final=1)
    hs = {h.regla: h for h in evaluar(plan=_plan(const), parametros=TODO)}
    assert "PLAN_CONSTANTE_METAS_DISTINTAS" in hs and hs["PLAN_CONSTANTE_METAS_DISTINTAS"].severidad == "Error"
    assert "2025" in hs["PLAN_CONSTANTE_METAS_DISTINTAS"].detalle
    assert hs["PLAN_CONSTANTE_METAS_DISTINTAS"].tipo == "metas_vs_meta_final"   # tipo legado
    ok = _ip(tipo_anualizacion="CONSTANTE", metas_por_anio={2024: 1, 2025: 1, 2026: 1}, meta_final=1)
    assert "PLAN_CONSTANTE_METAS_DISTINTAS" not in _reglas_plan(_plan(ok))
    assert "PLAN_SUMA_METAS_VS_MF" in _reglas_plan(_plan(_ip(meta_final=90)))
    assert "PLAN_SUMA_METAS_VS_MF" not in _reglas_plan(_plan(_ip(meta_final=100)))
    cre = _ip(tipo_anualizacion="CRECIENTE", metas_por_anio={2024: 10, 2025: 20}, meta_final=25)
    assert "PLAN_ULTIMA_META_VS_MF" in _reglas_plan(_plan(cre))


def test_fecha_vacia_texto_y_fin_antes_de_inicio():
    assert "PLAN_FECHA_VACIA" in _reglas_plan(_plan(_ip(fecha_fin=None)))
    assert "PLAN_FECHA_VACIA" in _reglas_plan(_plan(_ip(fecha_inicio="")))
    assert "PLAN_FECHA_VACIA" not in _reglas_plan(_plan(_ip()))
    hs = {h.regla: h for h in evaluar(plan=_plan(_ip(fecha_inicio="01/01/2024")), parametros=TODO)}
    assert "PLAN_FECHA_COMO_TEXTO" in hs and hs["PLAN_FECHA_COMO_TEXTO"].severidad == "Info"
    assert "PLAN_FECHA_INVALIDA" not in hs
    assert "PLAN_FECHA_COMO_TEXTO" not in _reglas_plan(_plan(_ip(fecha_inicio=2024)))  # año suelto
    assert "PLAN_FECHA_INVALIDA" in _reglas_plan(_plan(_ip(fecha_inicio="31/02/2024")))
    hs = _reglas_plan(_plan(_ip(fecha_inicio=dt.datetime(2027, 1, 1))))
    assert "PLAN_FECHA_INICIO_MAYOR_FIN" in hs


def test_meta_antes_de_inicio_y_despues_de_fin():
    # Educación 4.5.3: inicia en 2023, meta en 2022.
    ip = _ip(fecha_inicio=dt.datetime(2023, 1, 1), metas_por_anio={2022: 5, 2024: 30, 2025: 30, 2026: 35})
    hs = {h.regla: h for h in evaluar(plan=_plan(ip), parametros=TODO)}
    assert "META_ANTES_INICIO" in hs and hs["META_ANTES_INICIO"].tipo == "meta_fuera_de_rango"
    assert "2022" in hs["META_ANTES_INICIO"].detalle and "PLAN_META_DESPUES_FIN" not in hs
    # Meta 0 antes del inicio no cuenta.
    ip0 = _ip(fecha_inicio=dt.datetime(2023, 1, 1), metas_por_anio={2022: 0, 2024: 30, 2025: 30, 2026: 40})
    assert "META_ANTES_INICIO" not in _reglas_plan(_plan(ip0))
    tarde = _ip(fecha_fin=dt.datetime(2025, 12, 31), metas_por_anio={2024: 30, 2025: 30, 2026: 40})
    r = _reglas_plan(_plan(tarde))
    assert "PLAN_META_DESPUES_FIN" in r and "META_ANTES_INICIO" not in r


def test_codigo_mal_escrito_vigencia_vacia_y_sin_responsable():
    assert "PLAN_CODIGO_MAL_ESCRITO" in _reglas_plan(_plan(_ip(producto_esperado="1..1.1 Producto")))
    assert "PLAN_CODIGO_MAL_ESCRITO" not in _reglas_plan(_plan(_ip(producto_esperado="1.1.1 Producto")))
    assert "PLAN_VIGENCIA_VACIA" in _reglas_plan(_plan(_ip(es_vigente=None)))
    assert "PLAN_VIGENCIA_VACIA" not in _reglas_plan(_plan(_ip()))
    assert "PLAN_SIN_RESPONSABLE" in _reglas_plan(_plan(_ip(entidad_responsable="")))
    assert "PLAN_SIN_RESPONSABLE" not in _reglas_plan(_plan(_ip(entidad_responsable="", es_vigente="No Vigente")))
    assert "PLAN_SIN_RESPONSABLE" not in _reglas_plan(_plan(_ip()))


def test_lb_faltante_en_decreciente():
    dec = _ip(tipo_anualizacion="DECRECIENTE", valor_linea_base=None, anio_linea_base=None,
              metas_por_anio={2024: 8, 2025: 6, 2026: 5}, meta_final=5)
    r = _reglas_plan(_plan(dec))
    assert "PLAN_LB_OBLIGATORIA_DECRECIENTE" in r
    dec.valor_linea_base = 10
    assert "PLAN_LB_OBLIGATORIA_DECRECIENTE" not in _reglas_plan(_plan(dec))


# ─────────────────────────── seguimiento: decisiones F0 ───────────────────────────


def test_sobreejecucion_info_hasta_250_y_advertencia_despues():
    # SUMA trimestral, meta 2026 = 40 → meta del periodo a Q2 = 20.
    s = _seg(_ind(avances={"2026_Q1": 15, "2026_Q2": 15}, pct_vigencia={"2026": 1.5}))   # 150 %
    hs = {h.regla: h for h in _hs(s)}
    assert hs["SEG_SOBREEJECUCION_VIG"].severidad == "Info"
    assert hs["SEG_SOBREEJECUCION_PCT"].severidad == "Info"
    s = _seg(_ind(avances={"2026_Q1": 30, "2026_Q2": 30}, pct_vigencia={"2026": 3.0}))   # 300 %
    hs = {h.regla: h for h in _hs(s)}
    assert hs["SEG_SOBREEJECUCION_VIG"].severidad == "Advertencia"
    assert hs["SEG_SOBREEJECUCION_PCT"].severidad == "Advertencia"
    assert hs["SEG_SOBREEJECUCION_VIG"].tipo == "ADVERTENCIA_LIMITE_VIG"   # tipo legado intacto
    s = _seg(_ind(avances={"2026_Q1": 10, "2026_Q2": 10}, pct_vigencia={"2026": 1.0}))   # 100 %
    assert "SEG_SOBREEJECUCION_VIG" not in _reglas_seg(s)
    # El techo lo pone el semáforo de quien valida.
    s = _seg(_ind(avances={"2026_Q1": 15, "2026_Q2": 15}, pct_vigencia={"2026": 1.5}))
    assert "SEG_SOBREEJECUCION_VIG" not in _reglas_seg(s, umbrales_semaforo={"naranja": 160})
    # Acumulados: Info ≤ 250 %, Advertencia > 250 %.
    s = _seg(_ind(acumulados={"2026": 120}))
    assert {h.regla: h.severidad for h in _hs(s)}["SEG_ACUMULADO_SOBRE_META_FINAL"] == "Info"
    s = _seg(_ind(acumulados={"2026": 300}))
    assert {h.regla: h.severidad for h in _hs(s)}["SEG_ACUMULADO_SOBRE_META_FINAL"] == "Advertencia"
    # % hasta la vigencia: bajo el rojo sigue siendo Advertencia.
    s = _seg(_ind(pct_vigencia={"2026": 0.2}, avances={"2026_Q1": 4}))
    assert {h.regla: h.severidad for h in _hs(s)}["SEG_PCT_HASTA_VIG_FUERA_RANGO"] == "Advertencia"


def test_meta_sin_reporte_usa_fin_efectivo_y_periodicidad_del_plan():
    # Anual que termina en junio de 2026: a Q2 no se le exige (espera a Q4); a Q4 sí.
    anual = _ind(periodicidad="Anual", fecha_fin="2026-06-30", avances={"2025_Q4": 30})
    assert "SEG_META_SIN_REPORTE" not in _reglas_seg(_seg(anual))
    assert "SEG_META_SIN_REPORTE" in _reglas_seg(_seg(anual), corte=(2026, 4))
    # Trimestral que termina en junio y reportó en Q2: en Q3 no se le exige nada.
    tri = _ind(fecha_fin="2026-06-30", avances={"2026_Q1": 10, "2026_Q2": 10})
    assert "SEG_META_SIN_REPORTE" not in _reglas_seg(_seg(tri), corte=(2026, 3))
    tri_sin = _ind(fecha_fin="2026-06-30", avances={"2026_Q1": 10})
    hs = {h.regla: h for h in _hs(_seg(tri_sin), corte=(2026, 3))}
    assert "SEG_META_SIN_REPORTE" in hs and "Q2" in hs["SEG_META_SIN_REPORTE"].periodo
    # Antes del primer reporte exigible no se exige (inicia en 2026-05, trimestral: Q2 sí).
    nuevo = _ind(fecha_inicio="2026-05-01", avances={})
    assert "SEG_META_SIN_REPORTE" in _reglas_seg(_seg(nuevo))
    assert "SEG_META_SIN_REPORTE" not in _reglas_seg(_seg(_ind(fecha_inicio="2026-05-01", periodicidad="Anual")))
    # Año sin meta programada: no se exige.
    assert "SEG_META_SIN_REPORTE" not in _reglas_seg(_seg(_ind(metas={"2025": 30}, avances={})))
    # Periodicidad del plan manda: el formato dice Anual (nada a Q2), el plan Trimestral.
    seg = _seg(_ind(periodicidad="Anual", avances={}))
    plan = _plan(_ip(periodicidad="Trimestral"))
    assert "SEG_META_SIN_REPORTE" not in _reglas_seg(seg)
    hs = {h.regla: h for h in _hs(seg, plan)}
    assert "SEG_META_SIN_REPORTE" in hs and "del plan de acción" in hs["SEG_META_SIN_REPORTE"].detalle
    assert "CRUCE_PERIODICIDAD_DISTINTA" in hs
    assert "SEG_META_SIN_REPORTE" not in _reglas_seg(seg, plan, periodicidad_de="seguimiento")
    # Misma regla por la fachada.
    assert any(h.tipo == "ADVERTENCIA_META_SIN_REP"
               for h in validar_archivo(seg, periodicidad_plan={"1.1.1": "Trimestral"}))


def test_no_vigentes_sin_alertas_de_reporte_pero_con_peso():
    nv = _ind(estado="No Vigente", avances={}, ponderacion=5)
    reglas = _reglas_seg(_seg(nv), incluir_no_vigentes=False)
    assert reglas == ["SEG_NO_VIGENTE_CON_PESO"]
    assert "SEG_NO_VIGENTE_CON_PESO" not in _reglas_seg(_seg(_ind(estado="No Vigente", ponderacion=0)))
    assert "SEG_NO_VIGENTE_CON_PESO" not in _reglas_seg(_seg(_ind(ponderacion=5)))
    con_todo = _reglas_seg(_seg(nv))   # TODO incluye los No Vigentes
    assert "SEG_META_SIN_REPORTE" in con_todo


# ─────────────────────────── seguimiento: reglas nuevas ───────────────────────────


def test_reporte_negativo():
    hs = {h.regla: h for h in _hs(_seg(_ind(avances={"2025_Q4": -3, "2026_Q1": 10})))}
    assert "SEG_REPORTE_NEGATIVO" in hs and hs["SEG_REPORTE_NEGATIVO"].cortes == ("2025 Q4",)
    assert "SEG_REPORTE_NEGATIVO" not in _reglas_seg(_seg(_ind(avances={"2026_Q1": 0})))
    # Fuera del corte no se mira.
    assert "SEG_REPORTE_NEGATIVO" not in _reglas_seg(_seg(_ind(avances={"2026_Q4": -1})))


def test_retroceso_del_indicador():
    cre = _ind(tipo_anualizacion="Creciente", avances={"2025_Q4": 20, "2026_Q1": 25, "2026_Q2": 18})
    hs = {h.regla: h for h in _hs(_seg(cre))}
    assert "SERIE_RETROCESO" in hs and hs["SERIE_RETROCESO"].cortes == ("2026 Q2",)
    ok = _ind(tipo_anualizacion="Creciente", avances={"2025_Q4": 20, "2026_Q1": 25, "2026_Q2": 25})
    assert "SERIE_RETROCESO" not in _reglas_seg(_seg(ok))
    dec = _ind(tipo_anualizacion="Decreciente", avances={"2025_Q4": 20, "2026_Q1": 22}, linea_base=30)
    assert "SERIE_RETROCESO" in _reglas_seg(_seg(dec))
    suma = _ind(avances={"2025_Q4": 20, "2026_Q1": 5})
    assert "SERIE_RETROCESO" not in _reglas_seg(_seg(suma))


def test_reporte_en_anio_sin_meta_en_la_serie():
    s = _seg(_ind(metas={"2025": 30, "2026": 40}, avances={"2024_Q4": 5, "2026_Q1": 10}))
    hs = {h.regla: h for h in _hs(s)}
    assert "SERIE_REPORTE_SIN_META" in hs and hs["SERIE_REPORTE_SIN_META"].cortes == ("2024",)
    assert "SERIE_REPORTE_SIN_META" not in _reglas_seg(_seg(_ind(avances={"2024_Q4": 5})))
    # El año del corte lo cubre la regla histórica.
    r = _reglas_seg(_seg(_ind(metas={"2025": 30}, avances={"2026_Q1": 10})))
    assert "SEG_REPORTE_SIN_META" in r and "SERIE_REPORTE_SIN_META" not in r


def test_escala_y_sobreejecucion_en_la_serie():
    s = _seg(_ind(avances={"2024_Q4": 100, "2026_Q1": 10}))          # 2024: 100/30 = 333 %
    hs = {h.regla: h for h in _hs(s)}
    assert "SERIE_ESCALA" in hs and hs["SERIE_ESCALA"].severidad == "Advertencia"
    s = _seg(_ind(avances={"2024_Q4": 45, "2026_Q1": 10}))           # 150 %
    hs = {h.regla: h for h in _hs(s)}
    assert "SERIE_SOBREEJECUCION" in hs and hs["SERIE_SOBREEJECUCION"].severidad == "Info"
    assert "SERIE_ESCALA" not in hs
    assert not {"SERIE_ESCALA", "SERIE_SOBREEJECUCION"} & set(_reglas_seg(_seg(_ind(avances={"2024_Q4": 30}))))
    # Meta en fracción y reporte en 0–100 en un año cerrado.
    frac = _ind(tipo_anualizacion="Constante", metas={"2025": 0.8, "2026": 0.8}, meta_final=0.8,
                avances={"2025_Q4": 80, "2026_Q1": 0.8})
    assert "SERIE_ESCALA" in _reglas_seg(_seg(frac))
    # El año del corte no entra aquí (lo cubre SEG_ESCALA / SEG_SOBREEJECUCION_*).
    assert "SERIE_ESCALA" not in _reglas_seg(_seg(_ind(avances={"2026_Q1": 100})))


def test_meta_antes_de_inicio_sobre_el_seguimiento_solo_sin_plan():
    ind = _ind(fecha_inicio="2025-01-01", metas={"2024": 10, "2025": 30, "2026": 40})
    hs = {h.regla: h for h in _hs(_seg(ind))}
    assert "META_ANTES_INICIO" in hs and hs["META_ANTES_INICIO"].aplica_a == "seguimiento"
    assert "la meta cuenta" in hs["META_ANTES_INICIO"].afecta_avance
    assert "META_ANTES_INICIO" not in _reglas_seg(_seg(_ind(metas={"2025": 30}, fecha_inicio="2025-01-01")))
    # Con plan, la regla corre sobre el plan y no se duplica.
    plan = _plan(_ip(fecha_inicio=dt.datetime(2025, 1, 1), metas_por_anio={2024: 10, 2025: 30, 2026: 60}))
    hs = [h for h in _hs(_seg(ind), plan) if h.regla == "META_ANTES_INICIO"]
    assert len(hs) == 1 and hs[0].aplica_a == "plan"


# ─────────────────────────── cruce ───────────────────────────


def test_cruce_plan_seguimiento():
    plan = _plan(_ip(), _ip(codigo_ip="1.1.2", nombre_indicador="Nunca reportado"),
                 _ip(codigo_ip="1.1.3", es_vigente="No Vigente", peso_pct=0),
                 _ip(codigo_ip="1.1.4", fecha_inicio=dt.datetime(2027, 1, 1)))
    seg = _seg(_ind(), _ind(codigo="1.1.9"), _ind(codigo="1.1.8", estado="No Vigente", ponderacion=0))
    hs = [h for h in _hs(seg, plan) if h.regla.startswith("CRUCE_")]
    por = {(h.regla, h.codigo) for h in hs}
    assert ("CRUCE_IND_NO_EN_PLAN", "1.1.9") in por
    assert ("CRUCE_IND_NO_EN_PLAN", "1.1.8") not in por          # No Vigente: normal
    assert ("CRUCE_IND_NO_EN_SEGUIMIENTO", "1.1.2") in por
    assert ("CRUCE_IND_NO_EN_SEGUIMIENTO", "1.1.3") not in por   # No Vigente sin peso
    assert ("CRUCE_IND_NO_EN_SEGUIMIENTO", "1.1.4") not in por   # aún no inicia
    h = next(h for h in hs if h.codigo == "1.1.2")
    assert h.severidad == "Advertencia" and h.entidad == "SDG" and h.cod_ip == "1.1.2"
    assert not any(h.regla.startswith("CRUCE_") for h in _hs(seg))  # sin plan no hay cruce


# ─────────────────────────── salidas para los consumidores ───────────────────────────


def test_observaciones_desde_para_el_pipeline():
    plan = _plan(_ip(es_vigente="No Vigente", peso_pct=100), _ip(codigo_ip="1.1.2", peso_pct=0))
    seg = _seg(_ind(avances={"2024_Q4": 100, "2026_Q1": 10}), _ind(codigo="1.1.7"))
    filas = observaciones_desde(plan, seg, corte=(2026, 2), politica_key="PP_X",
                                responsable_por_defecto="SDG líder")
    assert filas and all(list(f) == COLS_OBSERVACION for f in filas)
    temas = {f["tema"] for f in filas}
    assert {"Indicador No Vigente con ponderación", "Posible error de escala en la serie",
            "Indicador del seguimiento que no está en el plan"} <= temas
    cruce = next(f for f in filas if f["tema"] == "Indicador del seguimiento que no está en el plan")
    assert cruce["nivel"] == "Política" and "1.1.7" in cruce["evidencia"] and cruce["severidad"] == "Media"
    nv = next(f for f in filas if f["tema"] == "Indicador No Vigente con ponderación")
    assert nv["indicador_key"] == "PP_X_producto_1.1.1" and nv["severidad"] == "Alta"
    assert nv["fuente"] == "Plan de acción" and nv["responsable"] == "SDG"
    sin_agrupar = observaciones_desde(plan, seg, corte=(2026, 2), politica_key="PP_X", agrupar_cruce=False)
    assert any(f["indicador_key"] == "PP_X_producto_1.1.7" for f in sin_agrupar)


def test_alertas_plan_y_hallazgos_app():
    plan = _plan(_ip(peso_pct=0))
    al = alertas_plan(plan)
    assert al and all(hasattr(a, "tipo") and hasattr(a, "nivel") for a in al)
    assert any(a.tipo == "ponderacion_faltante" or a.tipo == "vigencia_ponderacion" for a in al)
    seg = _seg(_ind(avances={"2026_Q1": "x"}))
    fs = hallazgos_app(seg, parametros=ParametrosCalidad(umbrales_semaforo={"rojo": 40, "naranja": 130}))
    assert fs and all(set(f) == {"tipo", "severidad", "descripcion", "codigo", "politica", "sector",
                                 "entidad", "nombre", "campo", "val_base", "val_nuevo", "periodo",
                                 "detalle", "file_nuevo"} for f in fs)
    assert any(f["tipo"] == "ERROR_NO_NUMERICO" for f in fs)
