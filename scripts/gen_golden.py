# -*- coding: utf-8 -*-
"""Genera/actualiza los golden files (huellas esperadas) del corpus de regresión.

Uso:
    python scripts/gen_golden.py            # curado + completo (todas las políticas)
    python scripts/gen_golden.py --curado   # solo el corpus curado (rápido)

Crea tests/golden/<clave>.json con la huella estable de cada archivo presente.
"""
import sys, os, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.path.insert(0, r'C:\Users\RaulEsteban\Proyectos\extractor-pa-maestro')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa import extraer_plan_accion
from extractor_pa.regresion import huella_plan, huella_seguimiento
from tests.corpus import (CORPUS_PLAN, CORPUS_SEGUIMIENTO, GOLDEN_DIR,
                          descubrir_planes, descubrir_seguimientos)

solo_curado = "--curado" in sys.argv
os.makedirs(GOLDEN_DIR, exist_ok=True)

planes = dict(CORPUS_PLAN)
segs = dict(CORPUS_SEGUIMIENTO)
if not solo_curado:
    planes.update(descubrir_planes())
    segs.update(descubrir_seguimientos())

gen = 0
faltan = []

for clave, ruta in sorted(planes.items()):
    if not os.path.exists(ruta):
        faltan.append(clave); continue
    h = huella_plan(extraer_plan_accion(ruta))
    with open(os.path.join(GOLDEN_DIR, clave + ".json"), "w", encoding="utf-8") as fh:
        json.dump(h, fh, ensure_ascii=False, indent=2)
    gen += 1
    print(f"  plan  {clave:34s} IR={h['n_ir']:3d} IP={h['n_ip']:4d} fmt={h['formato']}")

try:
    import pyxlsb  # noqa: F401
    from extractor_pa.seguimiento import extraer_seguimiento
    for clave, ruta in sorted(segs.items()):
        if not os.path.exists(ruta):
            faltan.append(clave); continue
        h = huella_seguimiento(extraer_seguimiento(ruta))
        with open(os.path.join(GOLDEN_DIR, clave + ".json"), "w", encoding="utf-8") as fh:
            json.dump(h, fh, ensure_ascii=False, indent=2)
        gen += 1
        print(f"  seg   {clave:34s} indicadores={h['n_indicadores']:4d}")
except ImportError:
    print("  (pyxlsb no instalado: se omiten los seguimientos)")

print(f"\nGolden generados: {gen} | faltantes: {len(faltan)} | modo={'curado' if solo_curado else 'completo'}")
