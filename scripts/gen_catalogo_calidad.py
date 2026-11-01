# -*- coding: utf-8 -*-
"""Genera docs/CATALOGO_CALIDAD.md desde extractor_pa/calidad/catalogo.py (fuente única)."""
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from extractor_pa.calidad.catalogo import REGLAS  # noqa: E402

BT = chr(96)
ORDEN = [
    ("estructura_plan", "Estructura del plan (extracción)"),
    ("estructura_seguimiento", "Estructura del seguimiento (extracción)"),
    ("plan", "Plan de acción"),
    ("seguimiento", "Seguimiento: año del corte"),
    ("serie", "Seguimiento: serie histórica"),
    ("entre_cargas", "Seguimiento: entre cargas"),
    ("cruce", "Cruce plan ↔ seguimiento"),
]

L = ["# Catálogo de reglas de calidad", "",
     f"> Generado desde {BT}extractor_pa/calidad/catalogo.py{BT} (fuente única; ADR-001).",
     "> Severidad: Error · Advertencia · Info (en `observaciones_politica`: Alta · Media · Baja).",
     "", f"**{len(REGLAS)} reglas** · {sum(1 for r in REGLAS if r.implementado)} implementadas · "
     f"{sum(1 for r in REGLAS if not r.por_defecto)} apagadas por defecto.", ""]
for aplica, titulo in ORDEN:
    items = [r for r in REGLAS if r.aplica_a == aplica]
    if not items:
        continue
    L += ["", f"## {titulo}", "",
          "| código | nombre | severidad | nivel | familia | sustituye a | acción | origen |",
          "|---|---|---|---|---|---|---|---|"]
    for r in items:
        leg = ", ".join(f"{BT}{t}{BT}" for t in r.tipos_legados) or "—"
        marca = "" if r.por_defecto else " (apagada)"
        L.append(f"| {BT}{r.codigo}{BT}{marca} | {r.nombre} | {r.severidad} | {r.nivel} | "
                 f"{r.familia} | {leg} | {r.accion or '—'} | {r.origen or '—'} |")
out = os.path.join(RAIZ, "docs", "CATALOGO_CALIDAD.md")
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("OK:", out, "|", len(REGLAS), "reglas")
