# -*- coding: utf-8 -*-
"""B2 — objetivo como entidad: jerarquia_ip + objetivo_sin_resultados.

Verifica que ambas alertas DISPARAN con jerarquía rota y que NO disparan
cuando la jerarquía objetivo→resultado→producto es consistente. También que el
peso del objetivo en V0/V1 sale de su IR vigente, no del primer IR.
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


if __name__ == "__main__":
    test_jerarquia_ip_dispara_si_falta_el_ir_padre()
    test_objetivo_sin_resultados_dispara_si_no_tiene_ir()
    test_jerarquia_consistente_no_dispara()
    test_peso_objetivo_sale_del_ir_vigente()
    test_peso_objetivo_sin_ir_vigente_que_lo_traiga_usa_el_primero()
    test_peso_objetivo_vigente_que_no_cuadra_alerta()
    print("B2 OK")
