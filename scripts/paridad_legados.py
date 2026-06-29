# -*- coding: utf-8 -*-
"""
Paridad del extractor MAESTRO vs los extractores LEGADOS.

Compara, sobre los mismos archivos reales, los CÓDIGOS de indicadores extraídos:
- Plan: maestro vs `extractor-planes-accion` (modulo_planes_accion).
- Seguimiento: maestro vs `alertas-seguimientos` (extractor.py / load_xlsb).

Imprime, por archivo, si los conjuntos de códigos coinciden (paridad) y las
diferencias si las hay. Es la evidencia para migrar con confianza.
"""
import sys, os, io, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
MAESTRO = r'C:\Users\RaulEsteban\Proyectos\extractor-pa-maestro'
LEGADO_PLAN = r'C:\Users\RaulEsteban\Proyectos\extractor-planes-accion'
LEGADO_SEG = r'C:\Users\RaulEsteban\Proyectos\alertas-seguimientos'
sys.path.insert(0, MAESTRO)

from extractor_pa import extraer_plan_accion
from extractor_pa.seguimiento import extraer_seguimiento

PLANES = r'C:\Users\RaulEsteban\Proyectos\sispp-gobierno\01_planes_accion'
SEG = r'C:\Users\RaulEsteban\Proyectos\sispp-gobierno\02_seguimientos'


def _cmp(nombre, set_m, set_l):
    falta = sorted(set_l - set_m)   # en legado, no en maestro
    sobra = sorted(set_m - set_l)   # en maestro, no en legado
    ok = "OK " if (not falta and not sobra) else "DIF"
    extra = "" if ok == "OK " else f" | falta_en_maestro={falta[:6]} extra_en_maestro={sobra[:6]}"
    print(f"  [{ok}] {nombre:34s} maestro={len(set_m):4d} legado={len(set_l):4d}{extra}")
    return ok == "OK "


def paridad_plan(archivos):
    print("=== PARIDAD PLAN: maestro vs extractor-planes-accion ===")
    sys.path.insert(0, LEGADO_PLAN)
    from modulo_planes_accion.extractor_nuevo import extraer_plan_nuevo
    oks = 0
    for ruta in archivos:
        nombre = os.path.basename(ruta)
        try:
            res = extraer_plan_accion(ruta)
            set_m = {i.codigo_ir for i in res.indicadores_resultado if i.codigo_ir} | \
                    {i.codigo_ip for i in res.indicadores_producto if i.codigo_ip}
            meta, ir, ip = extraer_plan_nuevo(ruta)
            set_l = {x.get("codigo_ir") for x in ir if x.get("codigo_ir")} | \
                    {x.get("codigo_ip") for x in ip if x.get("codigo_ip")}
            oks += _cmp(nombre, set_m, set_l)
        except Exception as e:
            print(f"  [ERR] {nombre}: {str(e)[:60]}")
    sys.path.remove(LEGADO_PLAN)
    print(f"  -> {oks}/{len(archivos)} con paridad total\n")


def paridad_seguimiento(archivos):
    print("=== PARIDAD SEGUIMIENTO: maestro vs alertas-seguimientos ===")
    sys.path.insert(0, LEGADO_SEG)
    import importlib
    leg = importlib.import_module("extractor")   # alertas-seguimientos/extractor.py
    oks = 0
    for ruta in archivos:
        nombre = os.path.basename(ruta)
        try:
            res = extraer_seguimiento(ruta)
            set_m = {i.codigo for i in res.indicadores if i.codigo}
            inds_l = leg.load_xlsb(ruta)
            set_l = {x.get("codigo") for x in inds_l if x.get("codigo")
                     and not str(x.get("codigo")).startswith("IND_")}
            oks += _cmp(nombre, set_m, set_l)
        except Exception as e:
            print(f"  [ERR] {nombre}: {str(e)[:60]}")
    sys.path.remove(LEGADO_SEG)
    print(f"  -> {oks}/{len(archivos)} con paridad total\n")


if __name__ == "__main__":
    planes = sorted(glob.glob(os.path.join(PLANES, "*.xlsx")))
    planes = [p for p in planes if not os.path.basename(p).startswith("~$")][:8]
    paridad_plan(planes)
    segs = sorted(glob.glob(os.path.join(SEG, "*.xlsb")))
    segs = [s for s in segs if not os.path.basename(s).startswith("~$")][:6]
    paridad_seguimiento(segs)
