# -*- coding: utf-8 -*-
"""Reporte accionable de hallazgos (V0–V18 + consistencia + extracción) por política."""
import sys, glob, os, io, csv
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.path.insert(0, r'C:\Users\RaulEsteban\Proyectos\extractor-pa-maestro')

from extractor_pa import extraer_plan_accion
from extractor_pa.catalogo import CATALOGO

CARPETA = r'C:\Users\RaulEsteban\Proyectos\sispp-gobierno\01_planes_accion'
SALIDA = r'C:\Users\RaulEsteban\Proyectos\_codigo_extraido_pp'
ORDEN_NIVEL = {"ERROR": 0, "ADVERTENCIA": 1, "INFO": 2}


def fam_reg(tipo):
    t = CATALOGO.get(tipo)
    return (t.familia if t else "—", t.regla or "" if t else "")


filas = []                       # detalle CSV
por_pol = defaultdict(list)      # (pol,arch) -> alertas
resumen = []                     # (pol, arch, nE, nA, nI, total)

archivos = [a for a in sorted(glob.glob(os.path.join(CARPETA, "*.xlsx")))
            if not os.path.basename(a).startswith("~$")]

for a in archivos:
    name = os.path.basename(a)
    res = extraer_plan_accion(a, anio_vigencia=2026, incluir_reglas_negocio=True)
    pol = res.metadatos.nombre_politica or name
    nE = nA = nI = 0
    for al in res.alertas:
        fam, reg = fam_reg(al.tipo)
        if al.nivel == "ERROR": nE += 1
        elif al.nivel == "ADVERTENCIA": nA += 1
        else: nI += 1
        por_pol[(pol, name)].append((al, fam, reg))
        filas.append({
            "archivo": name, "politica": pol, "nivel": al.nivel, "familia": fam,
            "tipo": al.tipo, "regla": reg, "codigo_objetivo": al.codigo_objetivo,
            "codigo_ir": al.codigo_ir, "codigo_ip": al.codigo_ip, "campo": al.campo,
            "valor": al.valor, "descripcion": al.descripcion,
        })
    resumen.append((pol, name, nE, nA, nI, nE + nA + nI))

# ── CSV ──
os.makedirs(SALIDA, exist_ok=True)
csv_path = os.path.join(SALIDA, "hallazgos_por_politica.csv")
with open(csv_path, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["archivo", "politica", "nivel", "familia",
        "tipo", "regla", "codigo_objetivo", "codigo_ir", "codigo_ip", "campo",
        "valor", "descripcion"])
    w.writeheader(); w.writerows(filas)

# ── MD ──
tot = len(filas)
tE = sum(r[2] for r in resumen); tA = sum(r[3] for r in resumen); tI = sum(r[4] for r in resumen)
glob_tipos = Counter((f["tipo"], f["regla"], f["nivel"]) for f in filas)

L = []
L.append("# Reporte de hallazgos por política (reglas V0–V18 + consistencia + extracción)")
L.append("")
L.append("> Hallazgos del extractor maestro sobre cada plan de acción, con las reglas")
L.append("> de negocio V0–V18 activadas (corte 2026). Para revisión y corrección por")
L.append("> política. Detalle completo en `hallazgos_por_politica.csv`.")
L.append("")
L.append(f"**Totales:** {len(resumen)} políticas · {tot} hallazgos "
         f"(**{tE} ERROR**, {tA} ADVERTENCIA, {tI} INFO).")
L.append("")
L.append("## Resumen por política (ordenado por ERROR)")
L.append("")
L.append("| Política | Archivo | ERROR | ADVERT | INFO | Total |")
L.append("|---|---|---:|---:|---:|---:|")
for pol, name, nE, nA, nI, t in sorted(resumen, key=lambda x: (-x[2], -x[5])):
    flag = " ⚠️" if nE else ""
    L.append(f"| {pol[:46]}{flag} | {name} | {nE} | {nA} | {nI} | {t} |")

L.append("")
L.append("## Hallazgos por tipo (global)")
L.append("")
L.append("| tipo | regla | nivel | total |")
L.append("|---|---|---|---:|")
for (tipo, reg, niv), n in sorted(glob_tipos.items(), key=lambda kv: (ORDEN_NIVEL.get(kv[0][2], 9), -kv[1])):
    L.append(f"| `{tipo}` | {reg or '—'} | {niv} | {n} |")

L.append("")
L.append("## Detalle por política")
for (pol, name) in sorted(por_pol, key=lambda k: -len(por_pol[k])):
    items = por_pol[(pol, name)]
    L.append(f"\n### {pol}")
    L.append(f"`{name}` · {len(items)} hallazgos\n")
    # agrupar por tipo
    por_tipo = defaultdict(list)
    for al, fam, reg in items:
        por_tipo[(al.nivel, al.tipo, reg)].append(al)
    for (niv, tipo, reg), als in sorted(por_tipo.items(), key=lambda kv: (ORDEN_NIVEL.get(kv[0][0], 9), -len(kv[1]))):
        codigos = [c for c in (a.codigo_ir or a.codigo_ip or a.codigo_objetivo for a in als) if c]
        ej = ", ".join(sorted(set(codigos))[:8])
        ej = f" — códigos: {ej}" if ej else ""
        L.append(f"- **{tipo}** ({niv}{', '+reg if reg else ''}) × {len(als)}{ej}")

md_path = os.path.join(SALIDA, "REPORTE_HALLAZGOS_POR_POLITICA.md")
with open(md_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")

print("OK")
print("CSV:", csv_path, "(", len(filas), "filas )")
print("MD :", md_path)
print(f"Totales: {tot} hallazgos | {tE} ERROR | {tA} ADVERTENCIA | {tI} INFO")
