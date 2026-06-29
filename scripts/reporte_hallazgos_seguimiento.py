# -*- coding: utf-8 -*-
"""Reporte accionable de hallazgos de SEGUIMIENTO por política.

Para cada .xlsb ejecuta `validar_archivo` (consistencia de un solo archivo:
avance vs meta, escala, % fuera de rango, acumulados, no numérico, cualitativo)
y agrupa por política. Si existen pares base/nuevo (mismo nombre en archivos_base
y archivos_nuevos), corre además `validar_consistencia` (estabilidad/retroactividad).
"""
import sys, glob, os, io, csv
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.path.insert(0, r'C:\Users\RaulEsteban\Proyectos\extractor-pa-maestro')

from extractor_pa.seguimiento import extraer_seguimiento, validar_archivo, validar_consistencia
from extractor_pa.catalogo import CATALOGO

SALIDA = r'C:\Users\RaulEsteban\Proyectos\_codigo_extraido_pp'
SEG_G = r'C:\Users\RaulEsteban\Proyectos\sispp-gobierno\02_seguimientos'
BASE = r'C:\Users\RaulEsteban\Proyectos\alertas-seguimientos\archivos_base'
NUEVO = r'C:\Users\RaulEsteban\Proyectos\alertas-seguimientos\archivos_nuevos'
ORDEN_NIVEL = {"ERROR": 0, "ADVERTENCIA": 1, "INFO": 2}


def nivel_de(tipo):
    t = CATALOGO.get(tipo)
    return t.nivel if t else "ADVERTENCIA"


filas = []
resumen = []           # (etiqueta, archivo, nE, nA, nI, total)
por_archivo = defaultdict(list)


def registrar(etiqueta, archivo, alertas):
    nE = nA = nI = 0
    for al in alertas:
        if al.nivel == "ERROR": nE += 1
        elif al.nivel == "ADVERTENCIA": nA += 1
        else: nI += 1
        por_archivo[(etiqueta, archivo)].append(al)
        filas.append({"politica": etiqueta, "archivo": archivo, "nivel": al.nivel,
                      "tipo": al.tipo, "codigo": al.codigo_ip or al.codigo_ir,
                      "campo": al.campo, "valor": al.valor, "descripcion": al.descripcion})
    resumen.append((etiqueta, archivo, nE, nA, nI, nE + nA + nI))


# 1) Validación de un solo archivo para los 50 .xlsb de gobierno.
for a in sorted(glob.glob(os.path.join(SEG_G, "*.xlsb"))):
    if os.path.basename(a).startswith("~$"):
        continue
    res = extraer_seguimiento(a)
    registrar(res.metadatos.nombre_politica or os.path.basename(a),
              os.path.basename(a), validar_archivo(res))

# 2) Pares base/nuevo (estabilidad/retroactividad).
pares = 0
for nuevo_p in sorted(glob.glob(os.path.join(NUEVO, "*.xlsb"))):
    base_p = os.path.join(BASE, os.path.basename(nuevo_p).replace("S2", "S1"))
    if not os.path.exists(base_p):
        continue
    base, nuevo = extraer_seguimiento(base_p), extraer_seguimiento(nuevo_p)
    registrar((nuevo.metadatos.nombre_politica or "?") + " (base→nuevo)",
              os.path.basename(nuevo_p), validar_consistencia(base, nuevo))
    pares += 1

# ── CSV ──
os.makedirs(SALIDA, exist_ok=True)
csv_path = os.path.join(SALIDA, "hallazgos_seguimiento_por_politica.csv")
with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["politica", "archivo", "nivel", "tipo",
        "codigo", "campo", "valor", "descripcion"])
    w.writeheader(); w.writerows(filas)

# ── MD ──
tot = len(filas)
tE = sum(r[2] for r in resumen); tA = sum(r[3] for r in resumen); tI = sum(r[4] for r in resumen)
glob_tipos = Counter((f["tipo"], f["nivel"]) for f in filas)
L = []
L.append("# Reporte de hallazgos de SEGUIMIENTO por política")
L.append("")
L.append("> Consistencia del reporte de seguimiento por archivo `.xlsb` "
         "(avance vs meta, escala, % fuera de rango, acumulados, no numérico, "
         "cualitativo) y, donde hay par base→nuevo, estabilidad/retroactividad.")
L.append("> Detalle completo en `hallazgos_seguimiento_por_politica.csv`.")
L.append("")
L.append(f"**Totales:** {len(resumen)} archivos · {tot} hallazgos "
         f"(**{tE} ERROR**, {tA} ADVERTENCIA, {tI} INFO) · {pares} pares base→nuevo.")
L.append("")
L.append("## Resumen por archivo (ordenado por total)")
L.append("")
L.append("| Política | Archivo | ERROR | ADVERT | INFO | Total |")
L.append("|---|---|---:|---:|---:|---:|")
for et, name, nE, nA, nI, t in sorted(resumen, key=lambda x: (-x[5], -x[2])):
    L.append(f"| {str(et)[:40]} | {name} | {nE} | {nA} | {nI} | {t} |")
L.append("")
L.append("## Hallazgos por tipo (global)")
L.append("")
L.append("| tipo | nivel | total |")
L.append("|---|---|---:|")
for (tipo, niv), n in sorted(glob_tipos.items(), key=lambda kv: (ORDEN_NIVEL.get(kv[0][1], 9), -kv[1])):
    L.append(f"| `{tipo}` | {niv} | {n} |")

md_path = os.path.join(SALIDA, "REPORTE_HALLAZGOS_SEGUIMIENTO_POR_POLITICA.md")
with open(md_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")

print("OK | CSV:", csv_path, "(", len(filas), "filas )")
print("Totales:", tot, "hallazgos |", tE, "ERROR |", tA, "ADVERTENCIA |", tI, "INFO |", pares, "pares")
