# -*- coding: utf-8 -*-
"""Genera el Tablero de cumplimiento por política (Hito 5): HTML navegable + CSV.

Uso:  python scripts/gen_tablero.py [anio] [periodo]
Salida en ../_codigo_extraido_pp/.
"""
import sys, os, io, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.path.insert(0, r'C:\Users\RaulEsteban\Proyectos\extractor-pa-maestro')

from extractor_pa.tablero import construir_tablero, render_html, _ORDEN_SEM

PLANES = r'C:\Users\RaulEsteban\Proyectos\sispp-gobierno\01_planes_accion'
SEG = r'C:\Users\RaulEsteban\Proyectos\sispp-gobierno\02_seguimientos'
SALIDA = r'C:\Users\RaulEsteban\Proyectos\_codigo_extraido_pp'
ANIO = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
PERIODO = sys.argv[2] if len(sys.argv) > 2 else "Anual"

os.makedirs(SALIDA, exist_ok=True)
filas = construir_tablero(PLANES, SEG, ANIO, PERIODO,
                          progreso=lambda c: print("  procesando:", c))

html = render_html(filas, ANIO, PERIODO)
ruta_html = os.path.join(SALIDA, "TABLERO_CUMPLIMIENTO.html")
with open(ruta_html, "w", encoding="utf-8") as fh:
    fh.write(html)

ruta_csv = os.path.join(SALIDA, "tablero_cumplimiento.csv")
with open(ruta_csv, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["politica", "archivo_plan", "archivo_seg", "n_ir", "n_ip", "n_seg",
                "n_asociados", "pct_promedio", "n_error", "n_advertencia"] + _ORDEN_SEM)
    for f in filas:
        w.writerow([f["politica"], f["archivo_plan"], f["archivo_seg"], f["n_ir"],
                    f["n_ip"], f["n_seg"], f["n_asociados"], f["pct_promedio"],
                    f["n_error"], f["n_advertencia"]] + [f["semaforo"][k] for k in _ORDEN_SEM])

con_plan = sum(1 for f in filas if f["archivo_plan"])
con_seg = sum(1 for f in filas if f["archivo_seg"])
print(f"\nTablero: {len(filas)} políticas | con plan {con_plan} | con seguimiento {con_seg}")
print("HTML:", ruta_html)
print("CSV :", ruta_csv)
