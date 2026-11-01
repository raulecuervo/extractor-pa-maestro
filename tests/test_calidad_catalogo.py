# -*- coding: utf-8 -*-
"""
Unificación de alertas (ADR-001): el motor ``calidad.evaluar`` envuelve las
validaciones existentes y devuelve EXACTAMENTE las mismas alertas que
``validar_reglas`` / ``validar_archivo`` / ``validar_consistencia`` (más las
reglas nuevas de la 0.29.0, que se prueban en ``test_calidad_reglas.py``).
"""

from __future__ import annotations

from dataclasses import asdict

import pytest

from extractor_pa import catalogo as catalogo_legado
from extractor_pa.calidad import (
    CATALOGO_CALIDAD, COLS_OBSERVACION, REGLAS, Hallazgo, ParametrosCalidad, evaluar,
    regla_de_tipo,
)
from extractor_pa.calidad.catalogo import SEVERIDAD_A_NIVEL
from extractor_pa.modelo import (
    IndicadorProducto, IndicadorResultado, Metadatos, Objetivo, ResultadoExtraccion,
)
from extractor_pa.seguimiento import (
    SEVERIDAD, TIPOS_HALLAZGO, IndicadorSeguimiento, MetadatosSeguimiento,
    ResultadoSeguimiento, validar_archivo, validar_consistencia,
)
from extractor_pa.validacion import validar_reglas

# ─────────────────────────── fixtures ───────────────────────────


def _plan_con_defectos() -> ResultadoExtraccion:
    """Un plan sintético que dispara buena parte de las reglas V0–V18."""
    irs = [
        IndicadorResultado(codigo_objetivo="1", codigo_ir="1.1", nombre_indicador="IR uno",
                           es_vigente="Vigente", peso_pct=50, peso_objetivo_pct=60,
                           tipo_anualizacion="CRECIENTE", periodicidad="Anual",
                           valor_linea_base=10, anio_linea_base=2020,
                           fecha_inicio="2024-01-01", fecha_fin="2027-12-31", meta_final=5,
                           metas_por_anio={2024: 1, 2025: 2, 2027: 5},
                           sector_responsable="Gobierno", entidad_responsable="SDG"),
        IndicadorResultado(codigo_objetivo="2", codigo_ir="2.1", nombre_indicador="IR dos",
                           es_vigente="No Vigente", peso_pct=30, peso_objetivo_pct=30,
                           tipo_anualizacion="DECRECIENTE", periodicidad="Rara",
                           fecha_inicio="31/02/2024", fecha_fin="2023-12-31", meta_final=None,
                           metas_por_anio={2024: 3}),
    ]
    ips = [
        IndicadorProducto(codigo_objetivo="1", codigo_ir="1.1", codigo_ip="1.1.1",
                          nombre_indicador="IP uno", es_vigente="Vigente", peso_pct=50,
                          tipo_anualizacion="SUMA", periodicidad="Trimestral",
                          fecha_inicio="2024-01-01", fecha_fin="2026-12-31", meta_final=100,
                          metas_por_anio={2022: 5, 2024: 10, 2025: 20, 2026: 30},
                          entidad_responsable="SDG"),
        IndicadorProducto(codigo_objetivo="1", codigo_ir="1.1", codigo_ip="1.1.2",
                          nombre_indicador="IP dos", es_vigente="Vigente", peso_pct=None,
                          tipo_anualizacion="CONSTANTE", periodicidad="Semestral",
                          fecha_inicio="2024-01-01", fecha_fin="2026-12-31", meta_final=1,
                          metas_por_anio={2024: 1, 2025: "x", 2026: 1}),
        IndicadorProducto(codigo_objetivo="3", codigo_ir="3.9", codigo_ip="3.9.1",
                          nombre_indicador="IP huérfano", es_vigente="Vigente", peso_pct=10,
                          tipo_anualizacion="RARO", metas_por_anio={}),
    ]
    return ResultadoExtraccion(
        Metadatos(nombre_politica="PP Demo", archivo_fuente="pa_demo.xlsx"),
        indicadores_resultado=irs, indicadores_producto=ips,
        objetivos=[Objetivo(codigo="1"), Objetivo(codigo="4")])


def _ind(**kw):
    base = dict(codigo="1.1.1", nombre="Indicador demo", sector="Sector X",
                entidad="Entidad Y", estado="Vigente", corte="Q2",
                anio_reporte=2026, tipo_anualizacion="Suma", periodicidad="Trimestral",
                ponderacion=5)
    base.update(kw)
    return IndicadorSeguimiento(**base)


def _res(*inds, archivo="nuevo.xlsb", politica="PP Demo"):
    return ResultadoSeguimiento(
        MetadatosSeguimiento(archivo_fuente=archivo, nombre_politica=politica), list(inds))


def _seguimiento_con_defectos():
    return _res(
        _ind(metas={"2025": 10, "2026": 10}, avances={"2026_Q1": "abc", "2026_Q2": 30},
             acumulados={"2026": 200}, meta_final=50, pct_vigencia={"2026": 3.0},
             cualitativos={}),
        _ind(codigo="1.1.2", tipo_anualizacion="Constante", metas={"2026": 0.5},
             avances={"2026_Q1": 60}, pct_vigencia={"2026": 0.2}, ponderacion=0),
        _ind(codigo="1.1.3", estado="No Vigente", metas={"2026": 10}, avances={}),
        _ind(codigo="1.1.4", metas={}, avances={"2026_Q1": 3}),
    )


# Sin el filtro de No Vigentes (RN-06), para comparar con las fachadas.
_TODO = ParametrosCalidad(incluir_no_vigentes=True)


def _legados(hs):
    """Solo los hallazgos de las reglas envueltas (tipo legado ≠ código canónico)."""
    return [h for h in hs if h.tipo != h.regla]


# ─────────────────────────── catálogo ───────────────────────────


def test_codigos_canonicos_unicos_y_con_forma():
    assert len(CATALOGO_CALIDAD) == len(REGLAS)
    for r in REGLAS:
        assert r.codigo.split("_")[0] in {"EXT", "PLAN", "SEG", "SERIE", "CARGA", "CRUCE", "META"}, r.codigo
        assert r.severidad in SEVERIDAD_A_NIVEL


def test_todo_tipo_implementado_del_catalogo_legado_tiene_regla():
    """Cada tipo que el extractor produce hoy está cubierto por una regla."""
    for t in catalogo_legado._TIPOS:
        if not t.implementado:
            continue
        r = regla_de_tipo(t.codigo)
        assert r.implementado, f"{t.codigo} sin regla en CATALOGO_CALIDAD"
        assert t.codigo in r.tipos_legados


def test_tipos_de_la_app_cubiertos_con_la_misma_severidad():
    for tipo, sev in SEVERIDAD.items():
        r = regla_de_tipo(tipo)
        assert tipo in r.tipos_legados, tipo
        assert r.severidad == sev, (tipo, r.codigo)
    assert set(TIPOS_HALLAZGO) == set(SEVERIDAD)


def test_severidad_de_las_reglas_del_plan_coincide_con_el_catalogo_legado():
    """La severidad de la regla y el nivel del tipo legado son la misma cosa."""
    for r in REGLAS:
        for tipo in r.tipos_legados:
            t = catalogo_legado.CATALOGO.get(tipo)
            if t is not None and t.implementado:
                assert r.nivel_alerta == t.nivel, (r.codigo, tipo)


def test_regla_de_tipo_desambigua_vigencia_ponderacion():
    assert regla_de_tipo("vigencia_ponderacion", "IP '1': No Vigente pero pondera 5%").codigo \
        == "PLAN_NO_VIGENTE_CON_PESO"
    assert regla_de_tipo("vigencia_ponderacion", "IP '1': Vigente pero pondera 0%").codigo \
        == "PLAN_VIGENTE_SIN_PESO"
    assert regla_de_tipo("tipo_inventado").implementado is False


# ─────────────────────────── no regresión: plan ───────────────────────────


def test_evaluar_plan_devuelve_las_mismas_alertas_que_validar_reglas():
    plan = _plan_con_defectos()
    esperadas = validar_reglas(plan)
    assert len(esperadas) >= 12  # el plan sintético sí dispara reglas
    hs = evaluar(plan=plan, aplica_a=["plan"], parametros=_TODO)
    assert [asdict(h.a_alerta()) for h in hs] == [asdict(a) for a in esperadas]
    assert all(isinstance(h, Hallazgo) and h.regla.startswith(("PLAN_", "META_")) for h in hs)
    assert {h.regla for h in hs} >= {"PLAN_PESO_OBJETIVOS", "PLAN_VIGENTE_SIN_PESO",
                                     "PLAN_NO_VIGENTE_CON_PESO", "PLAN_FECHA_INVALIDA",
                                     "PLAN_META_NO_NUMERICA", "PLAN_JERARQUIA_ROTA",
                                     "PLAN_TIPO_ANUALIZACION_INVALIDO"}


def test_evaluar_plan_incluye_las_estructurales_y_enriquece_con_el_plan():
    plan = _plan_con_defectos()
    from extractor_pa.alertas import crear_alerta
    plan.alertas.append(crear_alerta("sin_ip", "No se extrajo ningún IP.",
                                     archivo_fuente="pa_demo.xlsx", nombre_politica="PP Demo"))
    hs = evaluar(plan=plan, parametros=_TODO)
    est = [h for h in hs if h.aplica_a == "estructura_plan"]
    assert [h.regla for h in est] == ["EXT_SIN_IP"] and est[0].severidad == "Advertencia"
    assert asdict(est[0].a_alerta()) == asdict(plan.alertas[0])
    h = next(h for h in hs if h.regla == "PLAN_NO_VIGENTE_CON_PESO")
    assert h.codigo == "2.1" and h.cod_ir == "2.1" and h.nombre == "IR dos"
    assert evaluar(plan=plan, parametros=_TODO.con(incluir_estructurales=False)) == \
        [x for x in hs if x.aplica_a != "estructura_plan"]


def test_tolerancias_se_pasan_a_validar_reglas():
    plan = _plan_con_defectos()
    plan.indicadores_resultado[0].peso_objetivo_pct = 70.3  # objetivos suman 100,3
    # ADR-001: 0,1 pp por defecto → 100,3 % sí se alerta.
    assert any(h.regla == "PLAN_PESO_OBJETIVOS" for h in evaluar(plan=plan))
    laxo = _TODO.con(tolerancia_peso_pp=0.5)
    assert not any(h.regla == "PLAN_PESO_OBJETIVOS" for h in evaluar(plan=plan, parametros=laxo))
    assert [asdict(h.a_alerta()) for h in evaluar(plan=plan, parametros=laxo, aplica_a=["plan"])] \
        == [asdict(a) for a in validar_reglas(plan, tolerancia_peso_pp=0.5)]


# ─────────────────────────── no regresión: seguimiento ───────────────────────────


def test_evaluar_seguimiento_devuelve_los_mismos_findings_que_validar_archivo():
    res = _seguimiento_con_defectos()
    esperados = [h.as_finding() for h in validar_archivo(res)]
    assert len(esperados) >= 8
    hs = evaluar(seguimiento=res, parametros=_TODO)
    assert [h.as_finding() for h in _legados(hs)] == esperados
    assert all(h.regla.startswith(("SEG_", "SERIE_")) for h in hs)


def test_evaluar_con_base_devuelve_lo_mismo_que_validar_consistencia():
    base = _res(_ind(avances={"2025_Q4": 7}, acumulados={"2025": 7}, corte="Q4", anio_reporte=2025,
                     metas={"2025": 10, "2026": 10}, ponderacion=5),
                _ind(codigo="9.9.9", corte="Q4", anio_reporte=2025))
    nuevo = _res(_ind(avances={"2025_Q4": 8, "2026_Q1": 1}, acumulados={"2025": 8},
                      metas={"2025": 12, "2026": 10}, ponderacion=5, nombre="Otro nombre"),
                 _ind(codigo="1.1.5", metas={"2026": 10}))
    u = {"rojo": 40, "amarillo": 70, "naranja": 130}
    esperados = [h.as_finding() for h in validar_consistencia(base, nuevo, anio_min=2020, umbrales=u)]
    hs = evaluar(seguimiento=nuevo, base=base,
                 parametros=_TODO.con(anio_min=2020, umbrales_semaforo=u))
    assert [h.as_finding() for h in _legados(hs)] == esperados
    assert {h.regla for h in hs} >= {"CARGA_VALOR_HISTORICO", "CARGA_CAMBIO_META",
                                     "CARGA_CAMPO_INMUTABLE", "CARGA_INDICADOR_NUEVO",
                                     "CARGA_INDICADOR_FALTANTE"}
    assert {h.aplica_a for h in hs if h.regla.startswith("CARGA_")} == {"entre_cargas"}


def test_entidad_sector_llega_a_la_regla_de_sector():
    res = _res(_ind(entidad="SDG", sector="Salud", metas={}))
    mapa = {"sdg": "Gobierno"}
    with_rule = evaluar(seguimiento=res, parametros=ParametrosCalidad(entidad_sector=mapa))
    assert any(h.regla == "SEG_SECTOR_ENTIDAD" for h in with_rule)
    assert not any(h.regla == "SEG_SECTOR_ENTIDAD" for h in evaluar(seguimiento=res))


# ─────────────────────────── filtros y salidas ───────────────────────────


def test_filtros_por_regla_y_no_vigentes():
    res = _seguimiento_con_defectos()
    todos = evaluar(seguimiento=res, parametros=_TODO)
    assert any(h.codigo == "1.1.3" for h in todos)
    sin_nv = evaluar(seguimiento=res)  # por defecto (ADR-001) sin los No Vigentes…
    assert {h.regla for h in sin_nv if h.codigo == "1.1.3"} == {"SEG_NO_VIGENTE_CON_PESO"}  # …salvo esta
    solo = evaluar(seguimiento=res, codigos=["SEG_NO_NUMERICO"])
    assert solo and {h.regla for h in solo} == {"SEG_NO_NUMERICO"}
    apagada = evaluar(seguimiento=res, parametros=ParametrosCalidad(reglas_inactivas=frozenset({"SEG_NO_NUMERICO"})))
    assert not any(h.regla == "SEG_NO_NUMERICO" for h in apagada)
    activas = evaluar(seguimiento=res, parametros=ParametrosCalidad(reglas_activas=frozenset({"SEG_ESCALA"})))
    assert {h.regla for h in activas} == {"SEG_ESCALA"}


def test_a_observacion_tiene_las_columnas_del_tablero():
    res = _seguimiento_con_defectos()
    h = next(h for h in evaluar(seguimiento=res) if h.regla == "SEG_NO_NUMERICO")
    obs = h.a_observacion(politica_key="DEMO")
    assert list(obs) == COLS_OBSERVACION
    assert obs["indicador_key"] == "DEMO_producto_1.1.1" and obs["nivel"] == "Producto"
    assert obs["severidad"] == "Alta" and obs["origen"] == "automática"
    assert obs["responsable"] == "Entidad Y" and obs["tema"] == "Reporte no numérico"
    plan = _plan_con_defectos()
    hp = next(h for h in evaluar(plan=plan) if h.regla == "PLAN_PESO_OBJETIVOS")
    op = hp.a_observacion(politica_key="DEMO")
    assert op["nivel"] == "Política" and op["indicador_key"] == "" and op["fuente"] == "Plan de acción"
    hq = next(h for h in evaluar(plan=plan) if h.regla == "PLAN_PESO_CADENA_OBJ_IR")
    assert hq.a_observacion(politica_key="DEMO")["nivel"] == "Objetivo"


def test_as_finding_de_un_hallazgo_del_plan_tiene_el_shape_de_make_finding():
    h = evaluar(plan=_plan_con_defectos())[0]
    f = h.as_finding()
    assert list(f) == ["tipo", "severidad", "descripcion", "codigo", "politica", "sector",
                       "entidad", "nombre", "campo", "val_base", "val_nuevo", "periodo",
                       "detalle", "file_nuevo"]
    assert f["descripcion"] == CATALOGO_CALIDAD[h.regla].nombre


def test_corte_explicito_queda_en_los_parametros():
    p = ParametrosCalidad().con(corte=(2026, 2))
    assert p.corte == (2026, 2) and p.umbral_sobreejecucion == pytest.approx(1.25)
    assert ParametrosCalidad(umbrales_semaforo={"rojo": 40, "naranja": 150}).limites == (0.4, 1.5)
