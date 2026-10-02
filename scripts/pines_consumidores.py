# -*- coding: utf-8 -*-
"""Lista qué versión de extractor-pa fija cada aplicativo hermano.

Recorre los `requirements*.txt` y `pyproject.toml` de las carpetas vecinas de
este repo y muestra el tag que cada una pide frente a la versión actual. Las
fórmulas del seguimiento cambian entre versiones, así que dos aplicativos con
pines distintos pueden mostrar cifras distintas para el mismo indicador: los
cambios que mueven cifras se marcan en CHANGELOG.md.

Uso:
    python scripts/pines_consumidores.py            # carpeta padre del repo
    python scripts/pines_consumidores.py --raiz D:/otra/carpeta
Sale con código 1 si algún aplicativo no fija la versión actual.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractor_pa import __version__  # noqa: E402

_RE_PIN = re.compile(r"extractor-pa-maestro\.git@v?([\w.\-]+)")
_ARCHIVOS = re.compile(r"^(requirements[\w\-]*\.txt|pyproject\.toml)$")
_SALTAR = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist",
           "site-packages", ".claude"}


def _version(v: str) -> tuple:
    return tuple(int(p) if p.isdigit() else 0 for p in v.split("."))


def pines(raiz: str, propio: str) -> list[tuple[str, str, str]]:
    """[(aplicativo, archivo relativo, versión fijada)] bajo `raiz`."""
    out = []
    for base, dirs, archivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in _SALTAR
                   and os.path.abspath(os.path.join(base, d)) != propio]
        for nombre in archivos:
            if not _ARCHIVOS.match(nombre):
                continue
            ruta = os.path.join(base, nombre)
            try:
                texto = open(ruta, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for linea in texto.splitlines():
                if linea.lstrip().startswith("#"):
                    continue
                m = _RE_PIN.search(linea)
                if m:
                    rel = os.path.relpath(ruta, raiz)
                    out.append((rel.split(os.sep)[0], rel, m.group(1)))
    return sorted(set(out))


def main(argv=None) -> int:
    propio = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raiz", default=os.path.dirname(propio),
                    help="carpeta que contiene los aplicativos (por defecto, la padre)")
    args = ap.parse_args(argv)

    encontrados = pines(args.raiz, propio)
    if not encontrados:
        print(f"Ningún aplicativo bajo {args.raiz} fija extractor-pa.")
        return 0
    actual = _version(__version__)
    print(f"Versión actual de extractor-pa: v{__version__}\n")
    ancho = max(len(r) for _, r, _ in encontrados)
    atrasados = 0
    for _, rel, ver in encontrados:
        estado = "al día" if _version(ver) >= actual else "ATRASADO"
        atrasados += estado != "al día"
        print(f"  {rel:<{ancho}}  v{ver:<9} {estado}")
    if atrasados:
        print(f"\n{atrasados} archivo(s) fijan una versión anterior. Revisar en "
              f"CHANGELOG.md los cambios marcados «Cambia cifras» antes de subirlos.")
    return 1 if atrasados else 0


if __name__ == "__main__":
    sys.exit(main())
