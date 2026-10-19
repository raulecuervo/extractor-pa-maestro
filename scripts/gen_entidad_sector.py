# -*- coding: utf-8 -*-
"""Regenera extractor_pa/data/entidad_sector.json desde el listado único.

`entidad_sector.json` ({«Nombre, SIGLA»: sector}) fue hasta la 0.22.0 el mapa
curado entidad → sector. Desde la 0.23.0 la librería no lo lee (usa
`catalogo_entidades.entidad_sector_norm()`), pero los `.spec` de PyInstaller de
sispp-gobierno y sispp-SDP lo nombran por ruta, así que se conserva como un
DERIVADO del listado: la etiqueta de cada entidad y su sector. La prueba
`tests/test_catalogo_oficial.py::test_entidad_sector_json_es_un_derivado_sincronizado`
falla si se desincroniza; este script lo vuelve a generar.
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# El repo es la carpeta padre de scripts/: así funciona desde cualquier copia o worktree.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from extractor_pa.catalogo_entidades import RUTA_LISTADO, cargar  # noqa: E402


def derivado() -> dict:
    """{etiqueta: sector} de todas las entidades del listado, en orden de etiqueta."""
    return {e.etiqueta: e.sector for e in sorted(cargar().entidades, key=lambda e: e.etiqueta)}


def main() -> None:
    ruta = RUTA_LISTADO.with_name("entidad_sector.json")
    mapa = derivado()
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        json.dump(mapa, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"{ruta}: {len(mapa)} entidades (listado {cargar().version})")


if __name__ == "__main__":
    main()
