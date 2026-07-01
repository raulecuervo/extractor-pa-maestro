# -*- coding: utf-8 -*-
"""F2 — decisiones humanas de entidad/sector: persistencia + reaplicación.

Cubre: máquina de acciones (aprobar/nombre_nuevo/ignorar/eliminar), store
atómico + auditoría, proyección `como_mapa`, reaplicación determinista sobre el
modelo, y el puente desde las sugerencias de B1.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractor_pa import (
    ResultadoExtraccion, Metadatos, IndicadorResultado, IndicadorProducto,
    RegistroDecisiones, aplicar_decisiones,
)


def _res():
    ir = IndicadorResultado(codigo_ir="1.1", nombre_indicador="IR",
                            sector_responsable="Ambiente",
                            entidad_responsable="Sec. Ambiente")
    ip = IndicadorProducto(codigo_ir="1.1", codigo_ip="1.1.1", nombre_indicador="IP",
                           entidad_responsable="  Sec. Ambiente  ")  # con espacios
    return ResultadoExtraccion(
        metadatos=Metadatos(nombre_politica="P", archivo_fuente="x.xlsx"),
        indicadores_resultado=[ir], indicadores_producto=[ip])


# ── Persistencia / acciones ──────────────────────────────────────────────────

def test_guardar_y_obtener(tmp_path):
    reg = RegistroDecisiones(tmp_path / "dec.json", autor="ana")
    reg.guardar("Sec. Ambiente", "aprobar", "Secretaría Distrital de Ambiente")
    d = reg.obtener("Sec. Ambiente")
    assert d["accion"] == "aprobar"
    assert d["nombre_final"] == "Secretaría Distrital de Ambiente"
    assert d["decidido_por"] == "ana"
    assert reg.contar() == 1


def test_acciones_invalidas(tmp_path):
    reg = RegistroDecisiones(tmp_path / "dec.json")
    with pytest.raises(ValueError):
        reg.guardar("X", "borrar")               # acción inexistente
    with pytest.raises(ValueError):
        reg.guardar("X", "aprobar")              # falta nombre_final
    with pytest.raises(ValueError):
        reg.guardar("  ", "ignorar")             # valor vacío


def test_eliminar_y_auditoria(tmp_path):
    reg = RegistroDecisiones(tmp_path / "dec.json")
    reg.guardar("Ambiente", "nombre_nuevo", "Sector Ambiente")
    assert reg.eliminar("Ambiente") is True
    assert reg.eliminar("Ambiente") is False
    audit = reg.ruta_audit.read_text(encoding="utf-8")
    assert "decidir" in audit and "deshacer" in audit


def test_como_mapa(tmp_path):
    reg = RegistroDecisiones(tmp_path / "dec.json")
    reg.guardar("Sec. Ambiente", "aprobar", "Secretaría Distrital de Ambiente")
    reg.guardar("Basura", "eliminar")
    reg.guardar("No tocar", "ignorar")
    mapa = reg.como_mapa()
    assert mapa["Sec. Ambiente"] == "Secretaría Distrital de Ambiente"
    assert mapa["Basura"] == ""
    assert mapa["No tocar"] is None


# ── Reaplicación sobre el modelo ─────────────────────────────────────────────

def test_aplicar_reescribe_ir_e_ip_con_espacios(tmp_path):
    reg = RegistroDecisiones(tmp_path / "dec.json")
    reg.guardar("Sec. Ambiente", "aprobar", "Secretaría Distrital de Ambiente")
    res = _res()
    n = aplicar_decisiones(res, reg)
    assert n == 2                                  # IR.entidad + IP.entidad (con espacios)
    assert res.indicadores_resultado[0].entidad_responsable == "Secretaría Distrital de Ambiente"
    assert res.indicadores_producto[0].entidad_responsable == "Secretaría Distrital de Ambiente"
    # sector no estaba en el mapa → intacto
    assert res.indicadores_resultado[0].sector_responsable == "Ambiente"


def test_aplicar_eliminar_vacia_campo(tmp_path):
    reg = RegistroDecisiones(tmp_path / "dec.json")
    reg.guardar("Ambiente", "eliminar")
    res = _res()
    n = aplicar_decisiones(res, reg)
    assert n == 1
    assert res.indicadores_resultado[0].sector_responsable == ""


def test_aplicar_ignorar_no_cambia(tmp_path):
    reg = RegistroDecisiones(tmp_path / "dec.json")
    reg.guardar("Sec. Ambiente", "ignorar")
    res = _res()
    assert aplicar_decisiones(res, reg) == 0
    assert res.indicadores_resultado[0].entidad_responsable == "Sec. Ambiente"


def test_sin_decisiones_no_hace_nada(tmp_path):
    reg = RegistroDecisiones(tmp_path / "dec.json")
    assert aplicar_decisiones(_res(), reg) == 0


# ── Puente B1 → F2 ───────────────────────────────────────────────────────────

def test_aprobar_sugerencias_de_b1(tmp_path):
    reg = RegistroDecisiones(tmp_path / "dec.json")
    sugerencias = [
        {"tipo": "IR", "campo": "entidad_responsable",
         "original": "Sec. Ambiente", "sugerido": "Secretaría Distrital de Ambiente"},
        {"tipo": "IR", "campo": "sector_responsable",
         "original": "GestiónPública", "sugerido": "Gestión Pública"},
    ]
    n = reg.aprobar_sugerencias(sugerencias)
    assert n == 2
    assert reg.obtener("Sec. Ambiente")["accion"] == "aprobar"
    assert reg.como_mapa()["GestiónPública"] == "Gestión Pública"


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
