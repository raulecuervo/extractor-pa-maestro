# -*- coding: utf-8 -*-
"""Extrae los 38 planes y exporta un consolidado (Excel + CSV + JSON)."""
import sys, glob, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.path.insert(0, r'C:\Users\RaulEsteban\Proyectos\extractor-pa-maestro')

from extractor_pa import (
    extraer_plan_accion, exportar_excel_consolidado,
    exportar_csv_consolidado, exportar_json_consolidado, tablas_consolidadas,
)

CARPETA = r'C:\Users\RaulEsteban\Proyectos\sispp-gobierno\01_planes_accion'
SALIDA = r'C:\Users\RaulEsteban\Proyectos\_codigo_extraido_pp\salida_consolidada'
os.makedirs(SALIDA, exist_ok=True)

archivos = [a for a in sorted(glob.glob(os.path.join(CARPETA, '*.xlsx')))
            if not os.path.basename(a).startswith('~$')]   # ignora locks de Excel

resultados = []
for a in archivos:
    res = extraer_plan_accion(a, anio_vigencia=2026, incluir_reglas_negocio=True)
    resultados.append(res)

xls = exportar_excel_consolidado(resultados, os.path.join(SALIDA, 'consolidado_planes.xlsx'))
csvs = exportar_csv_consolidado(resultados, SALIDA)
js = exportar_json_consolidado(resultados, os.path.join(SALIDA, 'consolidado_planes.json'))

t = tablas_consolidadas(resultados)
print(f'Planes: {len(resultados)}')
print(f'  IR: {len(t["indicadores_resultado"])} | IP: {len(t["indicadores_producto"])} '
      f'| alertas: {len(t["alertas"])} | financiero: {len(t["financiero"])}')
print('Excel:', xls)
print('CSV  :', len(csvs), 'archivos en', SALIDA)
print('JSON :', js, '(', round(os.path.getsize(js)/1024/1024, 1), 'MB )')
