# -*- coding: utf-8 -*-
"""
Carga de archivos de seguimiento: `.xlsb` (pyxlsb) y `.xlsx` (openpyxl).

Desde el formato 3.4 (2026) el SDP entrega el seguimiento en `.xlsx` con la
misma estructura que el `.xlsb`: mismas hojas, mismas filas de bloques, años y
encabezados, mismas columnas. Los dos lectores devuelven lo mismo —números como
`float` y fechas como serial de Excel, que es lo que entrega pyxlsb—, así que el
resto del extractor no distingue el formato.

`pyxlsb` es dependencia opcional de la librería (extra `xlsb`); se importa en
tiempo de ejecución para no obligar a instalarlo si solo se usa el plan.
`openpyxl` ya es dependencia base.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import warnings
import zipfile
from pathlib import Path
from typing import Optional

from ..utilidades import _norm

# Extensiones de un archivo de seguimiento.
EXTENSIONES = (".xlsb", ".xlsx")

_EPOCA_EXCEL = _dt.datetime(1899, 12, 30)
_UN_DIA = _dt.timedelta(days=1)


def _open_workbook(ruta):
    try:
        from pyxlsb import open_workbook
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "La extracción de seguimiento requiere pyxlsb. "
            "Instala con: pip install extractor-pa[xlsb]  (o pip install pyxlsb)."
        ) from e
    return open_workbook(str(ruta))


def formato_de(ruta) -> str:
    """'xlsb' o 'xlsx' según el CONTENIDO del archivo: el libro binario trae
    ``xl/workbook.bin`` y el de Open XML ``xl/workbook.xml``. Así un archivo con
    la extensión equivocada se lee igual. Si no es un zip legible, decide la
    extensión (y el lector correspondiente reporta el error)."""
    try:
        with zipfile.ZipFile(str(ruta)) as z:
            nombres = set(z.namelist())
    except (zipfile.BadZipFile, OSError):
        nombres = set()
    if "xl/workbook.bin" in nombres:
        return "xlsb"
    if "xl/workbook.xml" in nombres:
        return "xlsx"
    return "xlsx" if Path(str(ruta)).suffix.lower() == ".xlsx" else "xlsb"


def _como_en_xlsb(valor):
    """Valor de openpyxl con el tipo que entrega pyxlsb para la misma celda:
    números `float` y fechas/horas como serial de Excel."""
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, int):
        return float(valor)
    if isinstance(valor, _dt.datetime):
        return (valor - _EPOCA_EXCEL) / _UN_DIA
    if isinstance(valor, _dt.date):
        return float((valor - _EPOCA_EXCEL.date()).days)
    if isinstance(valor, _dt.time):
        return (_dt.datetime.combine(_EPOCA_EXCEL.date(), valor) - _EPOCA_EXCEL) / _UN_DIA
    if isinstance(valor, _dt.timedelta):
        return valor / _UN_DIA
    return valor


class _LibroXlsx:
    """Libro `.xlsx` con la interfaz del de pyxlsb que usa el extractor
    (``sheets`` y uso como context manager)."""

    def __init__(self, ruta):
        import openpyxl
        # Se abre como flujo: con la ruta, openpyxl rechaza un .xlsx que llegue
        # con otra extensión (p. ej. renombrado a .xlsb).
        self._fh = open(str(ruta), "rb")
        try:
            with _sin_avisos_de_openpyxl():
                # data_only: los valores que calculó y guardó Excel, no las fórmulas.
                self._wb = openpyxl.load_workbook(self._fh, read_only=True, data_only=True)
        except Exception:
            self._fh.close()
            raise
        self.sheets = list(self._wb.sheetnames)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._wb.close()
        self._fh.close()
        return False

    def leer_hoja(self, nombre_hoja: str) -> dict:
        ws = self._wb[nombre_hoja]
        ws.reset_dimensions()   # la dimensión que declara la hoja puede quedarse corta
        mapa: dict = {}
        with _sin_avisos_de_openpyxl():   # en modo read_only la hoja se lee aquí
            for fila, row in enumerate(ws.iter_rows(min_row=1, min_col=1, values_only=True)):
                vals = {c: _como_en_xlsb(v) for c, v in enumerate(row)
                        if v is not None and v != ""}
                if vals:
                    mapa[fila] = vals
        return mapa


@contextlib.contextmanager
def _sin_avisos_de_openpyxl():
    """Calla «Data Validation extension is not supported»: las listas
    desplegables del formato no afectan la lectura."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        yield


def localizar_hoja(wb, *contiene: str) -> Optional[str]:
    """Devuelve el nombre de hoja cuyo nombre contiene TODOS los términos dados
    (normalizados). Ej.: localizar_hoja(wb, 'avance', 'cuantitativo')."""
    objetivos = [_norm(t) for t in contiene]
    for nombre in wb.sheets:
        n = _norm(nombre)
        if all(o in n for o in objetivos):
            return nombre
    return None


def leer_hoja(wb, nombre_hoja: str) -> dict:
    """Lee una hoja a un dict {indice_fila: {indice_col: valor}}.

    Índices 0-based (los de pyxlsb). Solo guarda celdas no vacías."""
    if isinstance(wb, _LibroXlsx):
        return wb.leer_hoja(nombre_hoja)
    mapa: dict = {}
    with wb.get_sheet(nombre_hoja) as ws:
        for row in ws.rows():
            if not row:
                continue
            fila = row[0].r
            vals = {c.c: c.v for c in row if c.v is not None and c.v != ""}
            if vals:
                mapa[fila] = vals
    return mapa


def abrir(ruta: str | Path):
    """Context manager del libro de seguimiento, `.xlsb` o `.xlsx`."""
    if formato_de(ruta) == "xlsx":
        return _LibroXlsx(ruta)
    return _open_workbook(ruta)
