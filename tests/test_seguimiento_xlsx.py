# -*- coding: utf-8 -*-
"""
Seguimiento en `.xlsx` (formato 3.4 del SDP, 2026): misma estructura que el
`.xlsb`, mismo resultado. El lector entrega números como float y fechas como
serial de Excel, igual que pyxlsb, para que el extractor no distinga el formato.

El archivo de prueba se arma con openpyxl con la disposición del formato:
anclas en la fila de bloques (índice 2), años en la índice 3 y datos desde la 5.
"""
import datetime as dt
import shutil

import pytest

openpyxl = pytest.importorskip("openpyxl")

from extractor_pa.seguimiento import extraer_seguimiento  # noqa: E402
from extractor_pa.seguimiento.loader import _como_en_xlsb, formato_de  # noqa: E402


def _celda(ws, fila0, col0, valor):
    """Escribe con índices 0-based, los del extractor."""
    ws.cell(row=fila0 + 1, column=col0 + 1, value=valor)


def _libro_seguimiento(ruta):
    wb = openpyxl.Workbook()
    cuant = wb.active
    cuant.title = "Avance Cuantitativo"
    # Bloques: trimestres 2025-2026 en 15–22, acumulados 23–24, metas 25–26,
    # meta final 27, meta acumulada 28–29 y los tres porcentajes desde 30.
    for col, texto in {0: "INFORMACIÓN GENERAL ", 15: "AVANCE Y SEGUIMIENTO",
                       25: "METAS PROGRAMADAS",
                       30: "Avance Cuantitativo de la Vigencia / Meta programada de la vigencia ",
                       32: "Avance Acumulado / Meta acumulada hasta la Vigencia",
                       34: "Avance Acumulado del Año / Meta Final "}.items():
        _celda(cuant, 2, col, texto)
    _celda(cuant, 3, 15, 2025)
    _celda(cuant, 3, 19, 2026)
    fila = {0: 1, 2: "Vigente", 3: "1.1.1. Indicador demo", 4: "Nombre demo",
            5: "Sector X", 6: "Entidad Y", 7: 0.25, 8: 10, 9: "Creciente",
            10: "Trimestral", 11: dt.datetime(2025, 1, 1), 12: dt.datetime(2026, 12, 31),
            13: "Q2", 14: "2026",
            15: 12, 16: 14, 17: 16, 18: 18, 19: 20, 20: 22,     # avances
            23: 18, 24: 22,                                       # acumulados
            25: 20, 26: 30, 27: 40,                               # metas y meta final
            30: 0.8, 31: 0.6, 32: 0.8, 33: 0.6, 34: 0.27, 35: 0.4}
    for col, valor in fila.items():
        _celda(cuant, 5, col, valor)

    cual = wb.create_sheet("Avance Cualitativo")
    _celda(cual, 2, 15, 2026)                  # 2026: Q1 en 15–16, Q2 en 17–18
    _celda(cual, 5, 3, "1.1.1. Indicador demo")
    _celda(cual, 5, 17, "Avance del semestre")
    _celda(cual, 5, 18, "Enfoque de género")
    wb.save(ruta)
    return ruta


@pytest.fixture
def xlsx(tmp_path):
    return _libro_seguimiento(tmp_path / "Seguimiento a Productos PP Demo S1-26.xlsx")


def test_extrae_un_seguimiento_xlsx(xlsx):
    res = extraer_seguimiento(xlsx)
    assert res.alertas == []
    assert res.metadatos.tipo_archivo == "productos"
    assert (res.metadatos.periodo, res.metadatos.anio_reporte) == ("S1", 2026)
    assert res.metadatos.anios_detectados == [2025, 2026]
    [ind] = res.indicadores
    assert ind.codigo == "1.1.1"
    assert (ind.fecha_inicio, ind.fecha_fin) == ("2025-01-01", "2026-12-31")
    assert ind.avances == {"2025_Q1": 12.0, "2025_Q2": 14.0, "2025_Q3": 16.0,
                           "2025_Q4": 18.0, "2026_Q1": 20.0, "2026_Q2": 22.0}
    assert ind.acumulados == {"2025": 18.0, "2026": 22.0}
    assert ind.metas == {"2025": 20.0, "2026": 30.0}
    assert ind.meta_final == 40.0
    assert ind.pct_vigencia == {"2025": 0.8, "2026": 0.6}
    assert ind.cualitativos == {"2026_Q2": "Avance del semestre"}
    assert ind.avance_enfoques == {"2026_Q2": "Enfoque de género"}


def test_los_numeros_salen_como_en_el_xlsb(xlsx):
    """pyxlsb entrega todo número como float; openpyxl, los enteros como int."""
    [ind] = extraer_seguimiento(xlsx).indicadores
    for valor in (ind.linea_base, ind.meta_final, ind.ind_no, *ind.avances.values()):
        assert type(valor) is float


@pytest.mark.parametrize("valor, esperado", [
    (2018, 2018.0),
    (True, True),
    ("Q2", "Q2"),
    (0.25, 0.25),
    (dt.datetime(2024, 1, 1), 45292.0),        # serial que da pyxlsb
    (dt.datetime(2024, 1, 1, 12), 45292.5),
    (dt.date(2026, 12, 31), 46387.0),
    (dt.time(6), 0.25),
    (dt.timedelta(hours=36), 1.5),
])
def test_valores_con_el_tipo_de_pyxlsb(valor, esperado):
    v = _como_en_xlsb(valor)
    assert v == esperado and type(v) is type(esperado)


def test_el_formato_se_reconoce_por_el_contenido(xlsx, tmp_path):
    """Un .xlsx con la extensión cambiada a .xlsb se lee igual."""
    renombrado = tmp_path / "Seguimiento a Productos PP Demo S1-26.xlsb"
    shutil.copy(xlsx, renombrado)
    assert formato_de(xlsx) == formato_de(renombrado) == "xlsx"
    [ind] = extraer_seguimiento(renombrado).indicadores
    assert ind.avances["2026_Q2"] == 22.0


@pytest.mark.parametrize("nombre", ["dañado.xlsx", "dañado.xlsb"])
def test_un_archivo_que_no_es_excel_da_alerta_y_no_excepcion(tmp_path, nombre):
    ruta = tmp_path / nombre
    ruta.write_bytes(b"no soy un libro de Excel")
    res = extraer_seguimiento(ruta)
    assert res.indicadores == []
    assert [a.tipo for a in res.alertas] == ["apertura_seguimiento"]
