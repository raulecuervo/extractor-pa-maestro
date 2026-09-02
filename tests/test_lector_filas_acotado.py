"""La lectura de filas no puede confiar en `ws.max_row`.

Excel arrastra en el «rango usado» toda fila que alguna vez tuvo formato, así que
`max_row` no dice dónde terminan los datos. El PA de Mujer (v6-26) declara **1.048.520
filas** en su hoja principal para 207 filas reales. Iterarlas todas tardaba minutos y
superaba 1,5 GB de memoria: en producción el contenedor de la API moría por OOM y la carga
del plan fallaba con «Error de conexión con el servidor».
"""
import openpyxl

from extractor_pa.lector_filas import FILAS_VACIAS_FIN, leer_filas


def _hoja(filas_datos, fila_inicio=1):
    wb = openpyxl.Workbook()
    ws = wb.active
    for i, valores in enumerate(filas_datos):
        for j, v in enumerate(valores, start=1):
            if v is not None:
                ws.cell(row=fila_inicio + i, column=j, value=v)
    return ws


def test_lee_las_filas_con_datos():
    ws = _hoja([["a", 1], ["b", 2], ["c", 3]])
    filas = leer_filas(ws, 1)
    assert [f[1][0] for f in filas] == ["a", "b", "c"]
    assert [f[0] for f in filas] == [1, 2, 3]


def test_un_hueco_corto_no_corta_la_tabla():
    """Una fila en blanco en medio del plan es normal y NO debe terminar la lectura."""
    ws = _hoja([["a"], [None], [None], ["b"]])
    assert [f[1][0] for f in leer_filas(ws, 1)] == ["a", "b"]


def test_para_tras_el_hueco_largo_y_no_recorre_el_resto():
    """El caso del PA de Mujer: datos arriba y un «rango usado» kilométrico debajo.

    Se comprueba contando cuántas filas pide la hoja, no el tiempo: es la medida
    determinista de que la iteración se detuvo."""
    ws = _hoja([["a"], ["b"]])
    pedidas = []
    original = ws.iter_rows

    def espia(*args, **kwargs):
        for fila in original(*args, **kwargs):
            pedidas.append(fila)
            yield fila

    ws.iter_rows = espia
    # La hoja miente sobre su tamaño, como hace Excel con el formato residual.
    ws._current_row = 1_048_576
    filas = leer_filas(ws, 1)

    assert [f[1][0] for f in filas] == ["a", "b"]
    assert len(pedidas) <= 2 + FILAS_VACIAS_FIN + 1, (
        f"recorrió {len(pedidas)} filas: la parada por filas vacías no funcionó"
    )
