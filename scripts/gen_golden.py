# -*- coding: utf-8 -*-
"""Genera/actualiza los golden files (huellas esperadas) del corpus de regresión.

Uso:
    python scripts/gen_golden.py            # curado + completo (todas las políticas)
    python scripts/gen_golden.py --curado   # solo el corpus curado (rápido)
    python scripts/gen_golden.py --revisar  # muestra qué cambiaría, sin escribir
    python scripts/gen_golden.py --podar    # además borra los golden huérfanos

Crea tests/golden/<clave>.json con la huella estable de cada archivo presente.
Antes de escribir compara con el golden anterior y lista las diferencias: una
diferencia puede ser una regresión real, no se regenera a ciegas.

Raíz del corpus (`EXTRACTOR_PA_CORPUS`) y convención de claves: ver tests/corpus.py.
"""
import sys, os, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa import extraer_plan_accion
from extractor_pa.regresion import huella_plan, huella_seguimiento
from tests.corpus import (CORPUS_PLAN, CORPUS_SEGUIMIENTO, GOLDEN_DIR, RAIZ,
                          cargar_golden, claves_duplicadas, claves_golden,
                          comparar_golden, descubrir_planes, descubrir_seguimientos,
                          ruta_golden)

solo_curado = "--curado" in sys.argv
revisar = "--revisar" in sys.argv
podar = "--podar" in sys.argv
os.makedirs(GOLDEN_DIR, exist_ok=True)
print(f"Corpus: {RAIZ}")

planes = list(CORPUS_PLAN)
segs = list(CORPUS_SEGUIMIENTO)
if not solo_curado:
    for corpus in (descubrir_planes(), descubrir_seguimientos()):
        dup = claves_duplicadas(corpus)
        if dup:
            sys.exit(f"Claves repetidas (¿dos versiones del mismo plan?), "
                     f"dejar una sola por política: {dup}")
    planes += descubrir_planes()
    segs += descubrir_seguimientos()

gen = 0
cambian = []
faltan = []


def _guardar(clave, h, resumen):
    """Compara con el golden anterior, informa y (salvo --revisar) escribe."""
    global gen
    previo = cargar_golden(clave)
    difs = comparar_golden(previo, h) if previo is not None else []
    estado = "+ nuevo" if previo is None else ("~ CAMBIA" if difs else "=")
    if difs:
        cambian.append(clave)
    print(f"  {estado:9s} {clave:34s} {resumen}")
    if previo is not None and previo.get("archivo") != h["archivo"]:
        print(f"            archivo: {previo.get('archivo')} -> {h['archivo']}")
    for d in difs:
        print(f"            {d}")
    gen += 1
    if not revisar:
        with open(ruta_golden(clave), "w", encoding="utf-8") as fh:
            json.dump(h, fh, ensure_ascii=False, indent=2)


for clave, ruta in dict(planes).items():
    if not ruta or not os.path.exists(ruta):
        faltan.append(clave); continue
    h = huella_plan(extraer_plan_accion(ruta))
    _guardar(clave, h, f"IR={h['n_ir']:3d} IP={h['n_ip']:4d} fmt={h['formato']}")

try:
    import pyxlsb  # noqa: F401
    from extractor_pa.seguimiento import extraer_seguimiento
    for clave, ruta in dict(segs).items():
        if not ruta or not os.path.exists(ruta):
            faltan.append(clave); continue
        h = huella_seguimiento(extraer_seguimiento(ruta))
        _guardar(clave, h, f"indicadores={h['n_indicadores']:4d}")
except ImportError:
    print("  (pyxlsb no instalado: se omiten los seguimientos)")

huerfanos = []
if not solo_curado:
    usadas = {c for c, _ in planes} | {c for c, _ in segs}
    huerfanos = sorted((claves_golden("plan") | claves_golden("seg")) - usadas)
    for c in huerfanos:
        accion = "borrado" if podar and not revisar else "huérfano"
        print(f"  - {accion:8s} {c}")
        if podar and not revisar:
            os.remove(ruta_golden(c))

print(f"\nGolden {'revisados (sin escribir)' if revisar else 'generados'}: {gen}"
      f" | cambian: {len(cambian)} | faltantes: {len(faltan)} | huérfanos: {len(huerfanos)}"
      f" | modo={'curado' if solo_curado else 'completo'}")
if faltan:
    print(f"Faltantes (archivo no disponible): {faltan}")
if huerfanos and not podar:
    print("Para borrar los huérfanos: python scripts/gen_golden.py --podar")
