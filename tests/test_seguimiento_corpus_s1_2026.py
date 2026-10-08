# -*- coding: utf-8 -*-
"""
Cuatro defectos que aparecieron al cruzar las actas de revisión de S1-2026 con
lo que el motor sacaba de los mismos archivos:

1. Una celda con error de fórmula llegaba de pyxlsb como ``'0x17'`` y el aviso
   decía «el valor '0x17' no es numérico» en vez de nombrar el ``#REF!``.
2. Un año escrito suelto en una columna de fecha («2024») se leía como el
   serial 2024: 16 de julio de 1905. En el corpus eran 244 fechas.
3. ``ADVERTENCIA_ACUM_META_FIN`` comparaba sin tolerancia: un acumulado de
   0.1 + 0.2 = 0.30000000000000004 «superaba» una meta final de 0.3.
4. Un formato de entidad sin los bloques de porcentaje (Movilidad Cero) se
   rechazaba entero, aunque avances, acumulados y metas estaban completos.
"""
import datetime as dt
import types

import pytest

openpyxl = pytest.importorskip("openpyxl")

from extractor_pa.seguimiento import extraer_seguimiento, validar_archivo  # noqa: E402
from extractor_pa.seguimiento import loader  # noqa: E402
from extractor_pa.seguimiento.extractor import _fecha  # noqa: E402
from extractor_pa.seguimiento.modelo import (  # noqa: E402
    IndicadorSeguimiento, MetadatosSeguimiento, ResultadoSeguimiento)


def _celda(ws, fila0, col0, valor):
    ws.cell(row=fila0 + 1, column=col0 + 1, value=valor)


def _libro(ruta, *, con_porcentajes=True, celdas=None):
    """Seguimiento mínimo con la disposición del formato (ver test_seguimiento_xlsx)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Avance Cuantitativo"
    bloques = {0: "INFORMACIÓN GENERAL ", 15: "AVANCE Y SEGUIMIENTO", 25: "METAS PROGRAMADAS"}
    if con_porcentajes:
        bloques.update({
            30: "Avance Cuantitativo de la Vigencia / Meta programada de la vigencia ",
            32: "Avance Acumulado / Meta acumulada hasta la Vigencia",
            34: "Avance Acumulado del Año / Meta Final "})
    for col, texto in bloques.items():
        _celda(ws, 2, col, texto)
    _celda(ws, 3, 15, 2025)
    _celda(ws, 3, 19, 2026)
    fila = {0: 1, 2: "Vigente", 3: "1.1.1. Indicador demo", 4: "Nombre demo",
            5: "Sector X", 6: "Entidad Y", 7: 0.25, 8: 10, 9: "Creciente",
            10: "Trimestral", 11: dt.datetime(2025, 1, 1), 12: dt.datetime(2026, 12, 31),
            13: "Q2", 14: "2026",
            15: 12, 16: 14, 17: 16, 18: 18, 19: 20, 20: 22,
            23: 18, 24: 22, 25: 20, 26: 30, 27: 40}
    if con_porcentajes:
        fila.update({30: 0.8, 31: 0.6, 32: 0.8, 33: 0.6, 34: 0.27, 35: 0.4})
    fila.update(celdas or {})
    for col, valor in fila.items():
        _celda(ws, 5, col, valor)
    wb.save(ruta)
    return ruta


def _resultado(ind):
    meta = MetadatosSeguimiento(archivo_fuente="demo.xlsb", tipo_archivo="productos",
                                nombre_politica="Demo")
    return ResultadoSeguimiento(meta, [ind], [])


# ─────────────────────── 1. errores de fórmula de Excel ───────────────────────

@pytest.mark.parametrize("crudo, texto", [
    ("0x17", "#REF!"), ("0x2a", "#N/A"), ("0x7", "#DIV/0!"), ("0xf", "#VALUE!"),
    ("0x1d", "#NAME?"), ("0x24", "#NUM!"), ("0x0", "#NULL!"),
])
def test_el_error_de_pyxlsb_sale_como_lo_escribe_excel(crudo, texto):
    assert loader._valor_xlsb(crudo) == texto


@pytest.mark.parametrize("valor", ["Q2", "0x99", "N/A", 12.0, None])
def test_lo_que_no_es_un_error_no_se_toca(valor):
    assert loader._valor_xlsb(valor) == valor


def test_leer_hoja_xlsb_traduce_los_errores():
    """Con un libro falso con la interfaz de pyxlsb (sin necesitar un .xlsb)."""
    celda = lambda r, c, v: types.SimpleNamespace(r=r, c=c, v=v)  # noqa: E731

    class Hoja:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def rows(self):
            return [[celda(5, 0, 1.0), celda(5, 15, 611107.0), celda(5, 16, "0x17")]]

    libro = types.SimpleNamespace(get_sheet=lambda nombre: Hoja())
    assert loader.leer_hoja(libro, "Avance Cuantitativo") == {
        5: {0: 1.0, 15: 611107.0, 16: "#REF!"}}


def test_el_aviso_nombra_el_error_de_formula(tmp_path):
    ruta = _libro(tmp_path / "Seguimiento a Productos PP Demo S1-26.xlsx",
                  celdas={21: "#REF!"})          # 2026 Q3 con la fórmula rota
    res = extraer_seguimiento(ruta)
    [ind] = res.indicadores
    assert ind.avances["2026_Q3"] == "#REF!"
    [h] = [h for h in validar_archivo(res) if h.tipo == "ERROR_NO_NUMERICO"]
    assert "error de fórmula de Excel (#REF!)" in h.detalle
    assert "0x17" not in h.detalle


# ─────────────────────── 2. un año suelto no es 1905 ───────────────────────

@pytest.mark.parametrize("valor, esperado", [
    (2024.0, "2024-01-01"),        # año escrito suelto, como lo entrega pyxlsb
    (2024, "2024-01-01"),
    (45292.0, "2024-01-01"),       # serial de Excel de verdad
    (46387.0, "2026-12-31"),
    ("2023-10-01", "2023-10-01"),
    (None, None),
    # Fecha escrita como texto día/mes/año (Educación 3.1.5, S1-2026).
    ("01/01/2024", "2024-01-01"),
    ("15/05/2024", "2024-05-15"),
    ("1/7/2025", "2025-07-01"),
    ("2024/05/01", "2024-05-01"),
    ("sin fecha", "sin fecha"),    # el texto que no es fecha se conserva
])
def test_fecha(valor, esperado):
    assert _fecha(valor) == esperado


def test_un_anio_en_la_columna_de_fecha_no_queda_en_1905(tmp_path):
    ruta = _libro(tmp_path / "Seguimiento a Productos PP Demo S1-26.xlsx",
                  celdas={11: 2024, 12: 2030})
    [ind] = extraer_seguimiento(ruta).indicadores
    assert (ind.fecha_inicio, ind.fecha_fin) == ("2024-01-01", "2030-01-01")


# ─────────────────── 3. tolerancia de punto flotante ───────────────────

def _con_acumulado(acumulado, meta_final):
    return IndicadorSeguimiento(
        codigo="4.3.9", nombre="Demo", sector="S", entidad="E", estado="Vigente",
        corte="Q2", anio_reporte=2026, tipo_anualizacion="Suma", periodicidad="Anual",
        meta_final=meta_final, acumulados={"2026": acumulado}, metas={"2026": meta_final})


def test_un_redondeo_no_supera_la_meta_final():
    acumulado = 0.1 + 0.2
    assert acumulado > 0.3                      # el ruido que disparaba la alerta
    tipos = [h.tipo for h in validar_archivo(_resultado(_con_acumulado(acumulado, 0.3)))]
    assert "ADVERTENCIA_ACUM_META_FIN" not in tipos


def test_un_exceso_real_sigue_alertando():
    tipos = [h.tipo for h in validar_archivo(_resultado(_con_acumulado(0.31, 0.3)))]
    assert "ADVERTENCIA_ACUM_META_FIN" in tipos


# ──────────────── 4. formato sin bloques de porcentaje ────────────────

def test_sin_bloques_de_porcentaje_se_leen_avances_y_metas(tmp_path):
    ruta = _libro(tmp_path / "Seguimiento a Productos PP Demo S1-26.xlsx",
                  con_porcentajes=False)
    res = extraer_seguimiento(ruta)
    assert [a.tipo for a in res.alertas] == ["anclas_porcentaje_ausentes"]
    assert res.alertas[0].nivel == "ADVERTENCIA"
    [ind] = res.indicadores
    assert ind.avances["2026_Q2"] == 22.0
    assert ind.acumulados == {"2025": 18.0, "2026": 22.0}
    assert ind.metas == {"2025": 20.0, "2026": 30.0}
    assert ind.meta_final == 40.0
    assert ind.pct_vigencia == ind.pct_acumulado == ind.pct_total == {}
    assert ind.metas_acumuladas == {}


def test_con_bloques_de_porcentaje_no_hay_aviso(tmp_path):
    res = extraer_seguimiento(_libro(tmp_path / "Seguimiento a Productos PP Demo S1-26.xlsx"))
    assert res.alertas == []


def test_sin_avance_o_metas_sigue_siendo_un_error(tmp_path):
    ruta = tmp_path / "Seguimiento a Productos PP Demo S1-26.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Avance Cuantitativo"
    _celda(ws, 2, 0, "INFORMACIÓN GENERAL ")
    _celda(ws, 2, 25, "METAS PROGRAMADAS")      # sin "AVANCE Y SEGUIMIENTO"
    wb.save(ruta)
    res = extraer_seguimiento(ruta)
    assert res.indicadores == []
    assert [a.tipo for a in res.alertas] == ["anclas_no_encontradas"]
