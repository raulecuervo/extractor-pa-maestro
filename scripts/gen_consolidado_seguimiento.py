# -*- coding: utf-8 -*-
"""Extrae todos los .xlsb de seguimiento y exporta un consolidado (Excel+CSV+JSON)."""
import sys, glob, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
sys.path.insert(0, r'C:\Users\RaulEsteban\Proyectos\extractor-pa-maestro')

from extractor_pa.seguimiento import (
    extraer_seguimiento,
    exportar_excel_seguimiento_consolidado,
    exportar_csv_seguimiento_consolidado,
    tablas_seguimiento_consolidadas,
)
from extractor_pa.exportadores import exportar_json_consolidado

BASES = [
    r'C:\Users\RaulEsteban\Proyectos\sispp-gobierno\02_seguimientos',
    r'C:\Users\RaulEsteban\Proyectos\alertas-seguimientos\archivos_base',
    r'C:\Users\RaulEsteban\Proyectos\alertas-seguimientos\archivos_nuevos',
]
SALIDA = r'C:\Users\RaulEsteban\Proyectos\_codigo_extraido_pp\salida_seguimiento'
os.makedirs(SALIDA, exist_ok=True)

archivos = []
for b in BASES:
    archivos += [f for f in glob.glob(os.path.join(b, '*.xlsb'))
                 if not os.path.basename(f).startswith('~$')]

resultados = [extraer_seguimiento(a) for a in sorted(archivos)]

xls = exportar_excel_seguimiento_consolidado(resultados, os.path.join(SALIDA, 'consolidado_seguimiento.xlsx'))
csvs = exportar_csv_seguimiento_consolidado(resultados, SALIDA)
js = exportar_json_consolidado(resultados, os.path.join(SALIDA, 'consolidado_seguimiento.json'))

t = tablas_seguimiento_consolidadas(resultados)
print(f'Archivos: {len(resultados)}')
print(f"  indicadores: {len(t['indicadores'])} | avances_trim: {len(t['avances_trimestrales'])} "
      f"| anual: {len(t['anual'])} | cualitativo: {len(t['cualitativo'])} | alertas: {len(t['alertas'])}")
print('Excel:', xls)
print('CSV  :', len(csvs), 'archivos')
print('JSON :', round(os.path.getsize(js)/1024/1024, 1), 'MB')
