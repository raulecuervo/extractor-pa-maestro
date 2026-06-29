# -*- coding: utf-8 -*-
"""Interfaz de línea de comandos del extractor maestro.

Uso:
    extractor-pa plan PLAN.xlsx [--reglas] [--anio 2026] [--json out.json]
                                [--csv carpeta] [--excel out.xlsx] [--no-fichas]
    extractor-pa seguimiento SEG.xlsb [--json out.json] [--csv carpeta] [--excel out.xlsx]
    extractor-pa validar PLAN.xlsx [--anio 2026]
    extractor-pa --version

También: `python -m extractor_pa ...`
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from . import __version__


def _print_resumen_plan(res) -> None:
    m = res.metadatos
    porn = Counter(a.nivel for a in res.alertas)
    print(f"  archivo   : {m.archivo_fuente}")
    print(f"  política  : {m.nombre_politica}")
    print(f"  formato   : {m.formato_detectado} | hoja: {m.hoja_usada}")
    print(f"  años      : {m.anios_detectados}")
    print(f"  IR / IP   : {m.n_ir} / {m.n_ip}   (financiero: {len(res.financiero)})")
    print(f"  LB en IR  : {m.pct_ir_con_linea_base}%")
    print(f"  alertas   : {len(res.alertas)}  "
          f"(ERROR {porn.get('ERROR', 0)}, ADVERTENCIA {porn.get('ADVERTENCIA', 0)}, "
          f"INFO {porn.get('INFO', 0)})")


def _print_resumen_seg(res) -> None:
    m = res.metadatos
    print(f"  archivo      : {m.archivo_fuente}")
    print(f"  política     : {m.nombre_politica}")
    print(f"  tipo archivo : {m.tipo_archivo}")
    print(f"  años         : {m.anios_detectados}")
    print(f"  indicadores  : {len(res.indicadores)}")
    print(f"  alertas      : {len(res.alertas)}")


def _exportar(res, args, *, seguimiento=False) -> None:
    if seguimiento:
        from .seguimiento import (exportar_json_seguimiento as ejson,
                                  exportar_csv_seguimiento as ecsv,
                                  exportar_excel_seguimiento as exls)
    else:
        from . import (exportar_json as ejson, exportar_csv as ecsv,
                       exportar_excel as exls)
    if args.json:
        print(f"  -> JSON  {ejson(res, args.json)}")
    if args.csv:
        rutas = ecsv(res, args.csv)
        print(f"  -> CSV   {len(rutas)} archivos en {args.csv}")
    if args.excel:
        print(f"  -> Excel {exls(res, args.excel)}")


def _cmd_plan(args) -> int:
    from . import extraer_plan_accion
    res = extraer_plan_accion(args.archivo, anio_vigencia=args.anio,
                              leer_fichas_tecnicas=not args.no_fichas,
                              incluir_reglas_negocio=args.reglas)
    print("PLAN extraído:")
    _print_resumen_plan(res)
    _exportar(res, args)
    return 0 if res.exitoso else 2


def _cmd_seguimiento(args) -> int:
    try:
        from .seguimiento import extraer_seguimiento
    except ImportError:
        print("ERROR: la lectura de .xlsb requiere 'pyxlsb' "
              "(pip install extractor-pa[xlsb]).", file=sys.stderr)
        return 3
    res = extraer_seguimiento(args.archivo)
    print("SEGUIMIENTO extraído:")
    _print_resumen_seg(res)
    _exportar(res, args, seguimiento=True)
    return 0 if res.exitoso else 2


def _cmd_validar(args) -> int:
    from . import extraer_plan_accion
    res = extraer_plan_accion(args.archivo, anio_vigencia=args.anio,
                              incluir_reglas_negocio=True)
    print("VALIDACIÓN del plan:")
    _print_resumen_plan(res)
    por_tipo = Counter((a.nivel, a.tipo) for a in res.alertas)
    orden = {"ERROR": 0, "ADVERTENCIA": 1, "INFO": 2}
    print("  hallazgos por tipo:")
    for (niv, tipo), n in sorted(por_tipo.items(), key=lambda kv: (orden.get(kv[0][0], 9), -kv[1])):
        print(f"    [{niv:11s}] {tipo:28s} x {n}")
    return 0


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="extractor-pa",
                                description="Extractor maestro de planes de acción y "
                                            "seguimiento de política pública.")
    p.add_argument("--version", action="version", version=f"extractor-pa {__version__}")
    sub = p.add_subparsers(dest="cmd")

    def _add_salidas(sp):
        sp.add_argument("--json", metavar="ARCHIVO", help="exportar a JSON")
        sp.add_argument("--csv", metavar="CARPETA", help="exportar a CSV (varias tablas)")
        sp.add_argument("--excel", metavar="ARCHIVO", help="exportar a Excel (varias hojas)")

    sp = sub.add_parser("plan", help="extraer un plan de acción (.xlsx)")
    sp.add_argument("archivo")
    sp.add_argument("--reglas", action="store_true", help="incluir reglas de negocio V0–V18")
    sp.add_argument("--anio", type=int, default=None, help="año de vigencia (corte)")
    sp.add_argument("--no-fichas", action="store_true", help="no leer fichas técnicas")
    _add_salidas(sp)
    sp.set_defaults(func=_cmd_plan)

    sp = sub.add_parser("seguimiento", help="extraer un seguimiento (.xlsb)")
    sp.add_argument("archivo")
    _add_salidas(sp)
    sp.set_defaults(func=_cmd_seguimiento)

    sp = sub.add_parser("validar", help="extraer un plan y listar hallazgos V0–V18")
    sp.add_argument("archivo")
    sp.add_argument("--anio", type=int, default=None, help="año de vigencia (corte)")
    sp.set_defaults(func=_cmd_validar)
    return p


def main(argv=None) -> int:
    # En Windows la consola suele ser cp1252; emitir UTF-8 sin romper por acentos.
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = construir_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
