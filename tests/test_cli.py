# -*- coding: utf-8 -*-
"""Pruebas de humo de la CLI (Hito 1)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa.__main__ import main, construir_parser
from tests.corpus import CORPUS_PLAN


def test_version_sale_codigo_cero():
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_sin_subcomando_devuelve_1():
    assert main([]) == 1


def test_parser_subcomandos():
    p = construir_parser()
    args = p.parse_args(["plan", "x.xlsx", "--reglas", "--anio", "2026"])
    assert args.cmd == "plan" and args.reglas is True and args.anio == 2026


def test_cli_plan_real(tmp_path, capsys):
    ruta = CORPUS_PLAN[0][1]   # plan_bti
    if not os.path.exists(ruta):
        pytest.skip("plan de referencia no disponible")
    salida = tmp_path / "bti.json"
    rc = main(["plan", ruta, "--reglas", "--anio", "2026", "--json", str(salida)])
    assert rc == 0
    assert salida.exists()
    out = capsys.readouterr().out
    assert "PLAN extraído" in out and "IR / IP" in out


def test_cli_validar_real(capsys):
    ruta = CORPUS_PLAN[0][1]
    if not os.path.exists(ruta):
        pytest.skip("plan de referencia no disponible")
    rc = main(["validar", ruta, "--anio", "2026"])
    assert rc == 0
    assert "hallazgos por tipo" in capsys.readouterr().out
