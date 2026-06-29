# -*- coding: utf-8 -*-
"""B2 — objetivo como entidad: jerarquia_ip + objetivo_sin_resultados.

Verifica que ambas alertas DISPARAN con jerarquía rota y que NO disparan
cuando la jerarquía objetivo→resultado→producto es consistente.
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


if __name__ == "__main__":
    test_jerarquia_ip_dispara_si_falta_el_ir_padre()
    test_objetivo_sin_resultados_dispara_si_no_tiene_ir()
    test_jerarquia_consistente_no_dispara()
    print("B2 OK")
