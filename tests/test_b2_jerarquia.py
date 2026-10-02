# -*- coding: utf-8 -*-
"""B2 — objetivo como entidad: jerarquia_ip + objetivo_sin_resultados.

Verifica que ambas alertas DISPARAN con jerarquía rota y que NO disparan
cuando la jerarquía objetivo→resultado→producto es consistente. También que el
peso del objetivo en V0/V1 sale de su IR vigente, no del primer IR.

Al final, V0/V1/V2: las sumas de ponderación a lo largo de la misma jerarquía
cuando el plan mezcla escalas (decimales y texto con «%»).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractor_pa import (
    ResultadoExtraccion, Metadatos, IndicadorResultado, IndicadorProducto,
    Objetivo, validar_reglas,
)


def _res(objetivos, irs, ips):
    return ResultadoExtraccion(
        metadatos=Metadatos(nombre_politica="P", archivo_fuente="x.xlsx"),
        indicadores_resultado=irs, indicadores_producto=ips, objetivos=objetivos)


def _tipos(res):
    return [a.tipo for a in validar_reglas(res)]


def test_jerarquia_ip_dispara_si_falta_el_ir_padre():
    # IP 2.3.1 cuelga de un IR 2.3 inexistente (solo existe el 2.1).
    irs = [IndicadorResultado(codigo_objetivo="2", codigo_ir="2.1",
                              nombre_indicador="IR ok")]
    ips = [IndicadorProducto(codigo_ir="2.1", codigo_ip="2.1.1", nombre_indicador="ok"),
           IndicadorProducto(codigo_ir="2.3", codigo_ip="2.3.1", nombre_indicador="huerfano")]
    res = _res([Objetivo(codigo="2", descripcion="Obj 2")], irs, ips)
    tipos = _tipos(res)
    assert tipos.count("jerarquia_ip") == 1, tipos
    rotas = [a for a in validar_reglas(res) if a.tipo == "jerarquia_ip"]
    assert "2.3.1" in rotas[0].descripcion and "2.3" in rotas[0].descripcion


def test_objetivo_sin_resultados_dispara_si_no_tiene_ir():
    # Objetivo 3 declarado pero sin ningún IR debajo.
    irs = [IndicadorResultado(codigo_objetivo="1", codigo_ir="1.1",
                              nombre_indicador="IR")]
    ips = [IndicadorProducto(codigo_ir="1.1", codigo_ip="1.1.1", nombre_indicador="ok")]
    objetivos = [Objetivo(codigo="1", descripcion="Obj 1"),
                 Objetivo(codigo="3", descripcion="Obj 3 sin resultados")]
    res = _res(objetivos, irs, ips)
    tipos = _tipos(res)
    assert tipos.count("objetivo_sin_resultados") == 1, tipos


def test_jerarquia_consistente_no_dispara():
    irs = [IndicadorResultado(codigo_objetivo="1", codigo_ir="1.1",
                              nombre_indicador="IR")]
    ips = [IndicadorProducto(codigo_ir="1.1", codigo_ip="1.1.1", nombre_indicador="ok")]
    res = _res([Objetivo(codigo="1", descripcion="Obj 1")], irs, ips)
    tipos = _tipos(res)
    assert "jerarquia_ip" not in tipos, tipos
    assert "objetivo_sin_resultados" not in tipos, tipos


def _ir(obj, cod, vigente, peso, peso_obj):
    return IndicadorResultado(codigo_objetivo=obj, codigo_ir=cod, nombre_indicador="IR",
                              es_vigente=vigente, peso_pct=peso, peso_objetivo_pct=peso_obj)


def _ponderacion(irs):
    objetivos = [Objetivo(codigo=c) for c in dict.fromkeys(i.codigo_objetivo for i in irs)]
    return [(a.tipo, a.codigo_objetivo) for a in validar_reglas(_res(objetivos, irs, []))
            if a.tipo in ("ponderacion_objetivos", "ponderacion_ir")]


def test_peso_objetivo_sale_del_ir_vigente():
    # Trabajo Decente OE2: el IR 2.1 No Vigente encabeza el objetivo con peso 0;
    # el peso del objetivo es el de los IR vigentes (V0 y V1 no deben disparar).
    irs = [_ir("1", "1.1", "Vigente", 0.5, 0.5),
           _ir("2", "2.1", "No Vigente", 0, 0),
           _ir("2", "2.2", "Vigente", 0.25, 0.5),
           _ir("2", "2.3", "Vigente", 0.25, 0.5)]
    assert _ponderacion(irs) == []


def test_peso_objetivo_sin_ir_vigente_que_lo_traiga_usa_el_primero():
    # Espacio Público OE2: el peso solo viene en la fila del IR No Vigente.
    irs = [_ir("1", "1.1", "Vigente", 0.5, 0.5),
           _ir("2", "2.1", "No vigente", 0, 0.5),
           _ir("2", "2.2", "Vigente", 0.5, None)]
    assert _ponderacion(irs) == []


def test_peso_objetivo_vigente_que_no_cuadra_alerta():
    # Manda el peso vigente aunque el histórico sí cuadre: el objetivo 2 vigente
    # dice 30%, sus IR suman 50% y los objetivos 80%. Con el primer IR (50%, No
    # Vigente) el error no salía.
    irs = [_ir("1", "1.1", "Vigente", 0.5, 0.5),
           _ir("2", "2.1", "No Vigente", 0, 0.5),
           _ir("2", "2.2", "Vigente", 0.5, 0.3)]
    assert sorted(_ponderacion(irs)) == [("ponderacion_ir", "2"),
                                         ("ponderacion_objetivos", "")]


# ── V0/V1/V2: ponderación con escalas mezcladas ──

def _plan_pesos(pesos_obj, pesos_ir, pesos_ip):
    """Plan vigente con esos pesos ({código: peso}); el padre sale del código."""
    objetivos = [Objetivo(codigo=o, descripcion=f"Obj {o}", peso_pct=p)
                 for o, p in pesos_obj.items()]
    irs = [IndicadorResultado(codigo_objetivo=c.split(".")[0],
                              peso_objetivo_pct=pesos_obj[c.split(".")[0]],
                              codigo_ir=c, nombre_indicador=f"IR {c}",
                              es_vigente="Vigente", peso_pct=p)
           for c, p in pesos_ir.items()]
    ips = [IndicadorProducto(codigo_objetivo=c.split(".")[0], codigo_ir=c.rsplit(".", 1)[0],
                             codigo_ip=c, nombre_indicador=f"IP {c}",
                             es_vigente="Vigente", peso_pct=p)
           for c, p in pesos_ip.items()]
    return _res(objetivos, irs, ips)


def _alertas_ponderacion(res):
    return [a for a in validar_reglas(res) if a.tipo.startswith("ponderacion")]


def test_ponderacion_texto_pct_en_plan_decimal_no_cambia_la_escala():
    # Un solo peso escrito como texto «24.72%» entre decimales. Antes pasaba
    # todo el plan a la escala de porcentaje: «Los 2 objetivo(s) suman 1.00%».
    res = _plan_pesos({"1": 0.6, "2": 0.4},
                      {"1.1": 0.3528, "1.2": "24.72%", "2.1": 0.4},
                      {"1.1.1": 0.3528, "1.2.1": "24.72%", "2.1.1": 0.2, "2.1.2": "20%"})
    assert _alertas_ponderacion(res) == []


def test_ponderacion_mezclada_sigue_detectando_el_descuadre_real():
    # Juventud v9-26, objetivo 7: el IR 7.5 («2.86%», texto) se agregó sin
    # rebajar el peso del objetivo. Antes: «suman 3.00% … es 0.14%» y además
    # un V0 falso de 1.00%.
    res = _plan_pesos({"6": 0.8582, "7": 0.1418},
                      {"6.1": 0.8582, "7.1": 0.0377, "7.2": 0.0286, "7.3": 0.0303,
                       "7.4": 0.0452, "7.5": "2.86%"},
                      {"6.1.1": 0.8582, "7.1.1": 0.0377, "7.2.1": 0.0286,
                       "7.3.1": 0.0303, "7.4.1": 0.0452, "7.5.2": "2.86%"})
    alertas = _alertas_ponderacion(res)
    assert [a.tipo for a in alertas] == ["ponderacion_ir"], alertas
    assert alertas[0].codigo_objetivo == "7"
    assert "suman 17.04%" in alertas[0].descripcion
    assert "el peso del objetivo es 14.18%" in alertas[0].descripcion


def test_ponderacion_texto_pct_menor_que_uno_no_se_multiplica():
    # Seguridad Alimentaria v7-26, IR 2.2: «0,5%» es medio punto, no el 50 %.
    # Antes: «Pesos de IPs del IR '2.2' suman 101.00% pero el peso del IR es 2.00%».
    res = _plan_pesos({"2": 1.0}, {"2.2": 0.02, "2.3": 0.98},
                      {"2.2.1": 0.01, "2.2.2": "0,5%", "2.2.3": "0,5%", "2.3.1": 0.98})
    assert _alertas_ponderacion(res) == []


def test_ponderacion_todo_texto_pct():
    res = _plan_pesos({"1": "60%", "2": "40%"},
                      {"1.1": "60%", "2.1": "39.5%", "2.2": "0.5%"},
                      {"1.1.1": "30%", "1.1.2": "30%", "2.1.1": "39.5%", "2.2.1": "0.5%"})
    assert _alertas_ponderacion(res) == []


def test_ponderacion_escala_porcentaje():
    # Ruralidad v5-26: números sueltos > 1, con pesos de IP ≤ 1 que NO son
    # decimales. Un peso en texto con «%» convive con ellos.
    res = _plan_pesos({"1": 84.19, "2": 14.7, "3": 1.11},
                      {"1.1": 84.19, "2.1": "14.7%", "3.1": 1.11},
                      {"1.1.1": 83.69, "1.1.2": 0.5, "2.1.1": 14.7, "3.1.1": 0.61,
                       "3.1.2": "0.5%"})
    assert _alertas_ponderacion(res) == []


def test_ponderacion_descuadre_en_cada_escala():
    # Los objetivos suman 90 en las tres escalas; IR e IP cuadran con ellos.
    for p1, p2 in ((0.6, 0.3), (60, 30), ("60%", 0.3)):
        res = _plan_pesos({"1": p1, "2": p2}, {"1.1": p1, "2.1": p2},
                          {"1.1.1": p1, "2.1.1": p2})
        alertas = _alertas_ponderacion(res)
        assert [(a.tipo, a.valor) for a in alertas] == [("ponderacion_objetivos", "90.0")], (
            p1, p2, alertas)


def test_ponderacion_peso_objetivo_vigente_en_texto_pct():
    # Las dos cosas a la vez: el peso del objetivo 2 sale de su fila vigente
    # (no del IR 2.1 No Vigente con 0) y viene como texto «50%» en un plan
    # decimal. Sin una u otra, V0 da 50.00% o 50.50%.
    irs = [_ir("1", "1.1", "Vigente", 0.5, 0.5),
           _ir("2", "2.1", "No Vigente", 0, 0),
           _ir("2", "2.2", "Vigente", "25%", "50%"),
           _ir("2", "2.3", "Vigente", 0.25, "50%")]
    assert _ponderacion(irs) == []


if __name__ == "__main__":
    test_jerarquia_ip_dispara_si_falta_el_ir_padre()
    test_objetivo_sin_resultados_dispara_si_no_tiene_ir()
    test_jerarquia_consistente_no_dispara()
    test_peso_objetivo_sale_del_ir_vigente()
    test_peso_objetivo_sin_ir_vigente_que_lo_traiga_usa_el_primero()
    test_peso_objetivo_vigente_que_no_cuadra_alerta()
    test_ponderacion_texto_pct_en_plan_decimal_no_cambia_la_escala()
    test_ponderacion_mezclada_sigue_detectando_el_descuadre_real()
    test_ponderacion_texto_pct_menor_que_uno_no_se_multiplica()
    test_ponderacion_todo_texto_pct()
    test_ponderacion_escala_porcentaje()
    test_ponderacion_descuadre_en_cada_escala()
    test_ponderacion_peso_objetivo_vigente_en_texto_pct()
    print("B2 OK")
