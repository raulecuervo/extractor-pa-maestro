# -*- coding: utf-8 -*-
"""B3 — gobernanza/triage persistente de alertas.

Cubre: clave estable (insensible a redacción), interoperabilidad con el CSV
legado de sispp-gobierno, máquina de estados con store atómico + auditoría, y
reconciliación entre corridas (autocierre de alertas desaparecidas).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extractor_pa import (
    Alerta, clave_alerta, RegistroGobernanza, NIVEL_ERROR, NIVEL_ADVERTENCIA,
)


def _alerta(**kw):
    base = dict(nivel=NIVEL_ERROR, tipo="tipo_anualizacion_invalido",
                descripcion="tipo_anualizacion='ND' no reconocido",
                archivo_fuente="PA_BTI_V4-26_DP.xlsx",
                nombre_politica="PP de Bogotá Territorio Inteligente",
                codigo_objetivo="2", codigo_ir="2.1", codigo_ip="",
                campo="tipo_anualizacion", valor="ND")
    base.update(kw)
    return Alerta(**base)


# ── Clave estable ────────────────────────────────────────────────────────────

def test_clave_estable_y_longitud():
    a = _alerta()
    assert clave_alerta(a) == clave_alerta(_alerta())
    assert len(clave_alerta(a)) == 12


def test_clave_ignora_descripcion_y_nombre():
    a = _alerta()
    otra = _alerta(descripcion="REDACCIÓN NUEVA", nombre_politica="BTI corto")
    assert clave_alerta(otra) == clave_alerta(a)


def test_clave_distingue_campos_identitarios():
    a = _alerta()
    for campo, valor in [("archivo_fuente", "PA_OTRO.xlsx"),
                         ("tipo", "meta_no_numerica"),
                         ("codigo_ir", "2.2"),
                         ("valor", "N.A")]:
        assert clave_alerta(_alerta(**{campo: valor})) != clave_alerta(a), campo


def test_clave_interopera_con_csv_legado():
    """Un dict con los nombres del CSV de sispp-gobierno produce la misma
    clave que el objeto Alerta canónico (mismos valores identitarios)."""
    a = _alerta()
    fila = {"archivo_fuente": "PA_BTI_V4-26_DP.xlsx",
            "tipo_alerta": "tipo_anualizacion_invalido",
            "codigo_objetivo": "2", "codigo_ir": "2.1", "codigo_ip": "",
            "campo": "tipo_anualizacion", "valor_encontrado": "ND",
            "descripcion": "otra redacción"}
    assert clave_alerta(fila) == clave_alerta(a)


def test_clave_tolera_nan():
    import math
    a = clave_alerta(_alerta(codigo_ip=""))
    b = clave_alerta({"archivo_fuente": "PA_BTI_V4-26_DP.xlsx",
                      "tipo": "tipo_anualizacion_invalido",
                      "codigo_objetivo": "2", "codigo_ir": "2.1",
                      "codigo_ip": math.nan, "campo": "tipo_anualizacion",
                      "valor": "ND"})
    assert a == b


# ── Estados / store ──────────────────────────────────────────────────────────

def test_estado_default_nueva(tmp_path):
    reg = RegistroGobernanza(tmp_path / "estado.json")
    assert reg.estado_de("abc123") == "nueva"


def test_set_estado_en_bloque_y_transiciones(tmp_path):
    reg = RegistroGobernanza(tmp_path / "estado.json")
    n = reg.set_estado(["k1", "k2", "k3"], "en_gestion", nota="correo enviado",
                       resumen="meta_no_numerica · BTI", autor="ana")
    assert n == 3
    estados = reg.cargar()
    assert all(estados[k]["estado"] == "en_gestion" for k in ("k1", "k2", "k3"))
    assert estados["k1"]["nota"] == "correo enviado" and estados["k1"]["autor"] == "ana"

    reg.set_estado(["k1"], "resuelta")
    assert reg.estado_de("k1") == "resuelta"
    assert reg.estado_de("k2") == "en_gestion"

    # volver a nueva elimina la entrada
    reg.set_estado(["k2"], "nueva")
    assert "k2" not in reg.cargar()
    assert reg.estado_de("k2") == "nueva"


def test_set_estado_invalido_y_vacio(tmp_path):
    reg = RegistroGobernanza(tmp_path / "estado.json")
    with pytest.raises(ValueError):
        reg.set_estado(["k1"], "cerrada")
    assert reg.set_estado([], "resuelta") == 0


def test_auditoria_append(tmp_path):
    reg = RegistroGobernanza(tmp_path / "estado.json")
    reg.set_estado(["k9"], "descartada", nota="falso positivo")
    audit = reg.ruta_audit.read_text(encoding="utf-8")
    assert "set_estado" in audit and "descartada" in audit


# ── Reconciliación entre corridas ────────────────────────────────────────────

def test_reconciliar_clasifica_y_autocierra(tmp_path):
    reg = RegistroGobernanza(tmp_path / "estado.json")
    a1 = _alerta()                        # k1
    a2 = _alerta(codigo_ir="3.1")         # k2
    a3 = _alerta(codigo_ir="4.1")         # k3 (aparecerá luego como en_gestion y desaparecerá)
    k1, k2, k3 = clave_alerta(a1), clave_alerta(a2), clave_alerta(a3)

    reg.set_estado([k1], "resuelta")
    reg.set_estado([k2], "en_gestion")
    reg.set_estado([k3], "en_gestion")

    # corrida actual: a1 y a2 siguen; a3 desapareció (se corrigió el dato)
    rec = reg.reconciliar([a1, a2])
    estados = {it.clave: it.estado for it in rec.items}
    assert estados[k1] == "resuelta"
    assert estados[k2] == "en_gestion"
    assert rec.por_estado()["en_gestion"] == 1
    assert {it.clave for it in rec.pendientes()} == {k2}   # k1 resuelta no es pendiente
    assert rec.desaparecidas == [k3]                        # autocierre candidato


def test_reconciliar_nuevas_por_defecto(tmp_path):
    reg = RegistroGobernanza(tmp_path / "estado.json")
    rec = reg.reconciliar([_alerta(), _alerta(codigo_ir="9.9")])
    assert all(it.estado == "nueva" for it in rec.items)
    assert rec.desaparecidas == []


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-q"]))
