# -*- coding: utf-8 -*-
"""
Corpus de regresión (golden files).

Dos niveles:
- **Curado** (`CORPUS_PLAN` / `CORPUS_SEGUIMIENTO`): pocos archivos representativos,
  se prueban por defecto (rápido).
- **Completo** (`descubrir_planes` / `descubrir_seguimientos`): todas las políticas,
  para la regresión exhaustiva previa a la migración (pruebas marcadas `slow`).

Raíz del corpus
---------------
Los archivos reales viven fuera del repo, en los proyectos hermanos. La raíz se
toma de la variable de entorno `EXTRACTOR_PA_CORPUS`; sin ella, la del equipo
del usuario (`_RAIZ_DEFECTO`). Dentro de la raíz:

    sispp-gobierno/01_planes_accion/*.xlsx                  planes
    sispp-gobierno/02_seguimientos/*.xlsb                   seguimientos
    alertas-seguimientos/archivos_base/*.xlsb               seguimientos de productos
    alertas-seguimientos/archivos_nuevos/*.xlsb
    alertas-seguimientos/Repositorio_Documentos_Politicas/data/<n>/planes_accion/
                                                            plan en formato antiguo

Si una carpeta no existe (p. ej. en el CI) sus pruebas se saltan y la suite
sigue siendo portable. Si existe pero ningún archivo tiene golden,
`test_golden.py::test_corpus_cubierto_por_golden` **falla**: es la señal de que
la regresión quedó apagada.

Convención de claves
--------------------
`clave` es el id del golden (`tests/golden/<clave>.json`): `<prefijo>_<slug>`,
con prefijo `plan` o `seg`. El slug es la política, sacada del nombre del
archivo sin lo que cambia al renombrar o versionar (`slug_politica`):

1. acentos y mayúsculas;
2. el prefijo del catálogo SISPP: `29__` o `Decreto_193_de_2022__`;
3. el prefijo del tipo de archivo (`PA_`, `PA_PP_`, `Plan Accion PP_`,
   `plan_accion_pp_`) y el número de catálogo que a veces le sigue (`PA_42_…`);
4. desde el sufijo de versión hasta el final (`_V4-26_DP_v1`, `_v3_2025 15.12.2025`),
   y los números o fechas sueltos al final.

    29__pa_bti_v4-26_dp_v1.xlsx                       → plan_bti
    PA_BTI_V4-26_DP.xlsx                              → plan_bti
    Decreto_193_de_2022__pa_trata_v4-26_dp_c_v1.xlsx  → plan_trata
    Plan Accion PP_Negra-Afro_V3_2025 15.12.2025.xlsx → plan_negra_afro
    Acción Climática.xlsb                             → seg_accion_climatica

Así un renombrado, o una versión nueva del mismo plan, conserva la clave: el
golden se sigue comparando y, si el contenido cambió, la prueba falla con las
diferencias en vez de saltarse. La comparación ignora el campo `archivo` de la
huella (el nombre del archivo no es salida del extractor). Si cambia el nombre
de la política misma (`Trabajo_Digno` → `trabajo_decente`) cambia la clave: se
renombra el golden a mano o se regenera, y `scripts/gen_golden.py --podar`
borra el que queda huérfano.

Dos archivos con el mismo slug en una carpeta (dos versiones del mismo plan)
chocan: `test_corpus_claves_unicas` falla y `gen_golden.py` se niega a correr.
"""

import glob
import json
import ntpath
import os
import re
import unicodedata
from collections import Counter

from extractor_pa.regresion import diferencias

_RAIZ_DEFECTO = r"C:\Users\RaulEsteban\Proyectos"
RAIZ = os.environ.get("EXTRACTOR_PA_CORPUS") or _RAIZ_DEFECTO

DIR_PLANES = os.path.join(RAIZ, "sispp-gobierno", "01_planes_accion")
DIR_SEG_GOB = os.path.join(RAIZ, "sispp-gobierno", "02_seguimientos")
DIR_SEG_BASE = os.path.join(RAIZ, "alertas-seguimientos", "archivos_base")
DIR_SEG_NUEVOS = os.path.join(RAIZ, "alertas-seguimientos", "archivos_nuevos")
DIR_REPO_DOCS = os.path.join(RAIZ, "alertas-seguimientos",
                             "Repositorio_Documentos_Politicas", "data")

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")

_PREFIJO_CATALOGO = re.compile(r"^(?:\d+__|decreto_\d+_de_\d{4}__)")
_PREFIJO_PLAN = re.compile(r"^(?:pa|plan[ _]accion)(?:[ _]pp)?[ _-]+(?:\d+[ _-]+)?")
_VERSION = re.compile(r"[ _-]v\d.*$")
_NUMEROS_FINALES = re.compile(r"(?:[ _.-]+\d+)+$")


def slug_politica(nombre: str) -> str:
    """Slug de la política a partir del nombre de archivo (ver la convención arriba)."""
    s = os.path.splitext(ntpath.basename(str(nombre)))[0]
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = _PREFIJO_CATALOGO.sub("", s)
    s = _PREFIJO_PLAN.sub("", s)
    s = _VERSION.sub("", s)
    s = _NUMEROS_FINALES.sub("", s)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _descubrir(carpeta: str, ext: str, prefijo: str):
    if not os.path.isdir(carpeta):
        return []
    rutas = sorted(glob.glob(os.path.join(carpeta, f"*.{ext}")))
    return [(f"{prefijo}_{slug_politica(r)}", r) for r in rutas
            if not os.path.basename(r).startswith("~$")]


def descubrir_planes():
    """Todos los planes (.xlsx) — corpus completo."""
    return _descubrir(DIR_PLANES, "xlsx", "plan")


def descubrir_seguimientos():
    """Todos los seguimientos (.xlsb) — corpus completo."""
    return _descubrir(DIR_SEG_GOB, "xlsb", "seg")


def claves_duplicadas(corpus) -> dict:
    """{clave: [rutas]} de las claves que apuntan a más de un archivo."""
    n = Counter(c for c, _ in corpus)
    return {c: [r for k, r in corpus if k == c] for c in sorted(n) if n[c] > 1}


def _curado(slugs, descubiertos, prefijo):
    """[(clave, ruta|None)] de las políticas curadas; None si no está en el corpus."""
    por_clave = dict(descubiertos)
    return [(f"{prefijo}_{s}", por_clave.get(f"{prefijo}_{s}")) for s in slugs]


def _buscar(carpeta: str, ext: str, slug: str) -> str:
    """Archivo de esa política en `carpeta` (la última versión si hay varias).

    Si no está, devuelve una ruta que no existe: la prueba se salta con su nombre."""
    rutas = [r for r in sorted(glob.glob(os.path.join(carpeta, f"*.{ext}")))
             if slug_politica(r) == slug]
    return rutas[-1] if rutas else os.path.join(carpeta, f"<{slug}>.{ext}")


# ── Corpus curado (rápido, por defecto) ──
# Por slug de política, no por nombre de archivo: sobrevive a los renombrados.
# Si la carpeta del corpus existe y una política curada no aparece, su prueba falla.
CURADO_PLAN = [
    "bti",           # formato nuevo, sin alertas
    "educacion",     # grande, muchas inconsistencias en IR
    "lgbti",         # 180 IP
    "cti",           # el formato antiguo hasta v4-25; nuevo desde v5-26
    "negra_afro",    # étnico, el más grande (236 IP)
]
CURADO_SEGUIMIENTO = ["bti", "educacion"]

# El formato antiguo (con bloque financiero) ya no aparece en 01_planes_accion
# desde las versiones 2026: se toma de un plan SDIS del repositorio de documentos.
PLAN_ANTIGUO = _buscar(os.path.join(DIR_REPO_DOCS, "21", "planes_accion"), "xlsx", "adultez")

# Archivos de alertas-seguimientos usados por las pruebas de integración.
SEG_BTI_S1_25 = os.path.join(DIR_SEG_BASE, "Seguimiento a Productos PP BTI S1-25.xlsb")
SEG_BTI_S2_25 = os.path.join(DIR_SEG_NUEVOS, "Seguimiento a Productos PP BTI S2-25.xlsb")

CORPUS_PLAN = _curado(CURADO_PLAN, descubrir_planes(), "plan") + [
    ("plan_antiguo_adultez", PLAN_ANTIGUO),
]

CORPUS_SEGUIMIENTO = _curado(CURADO_SEGUIMIENTO, descubrir_seguimientos(), "seg") + [
    ("seg_bti_productos", SEG_BTI_S1_25),
]


def ruta_plan(slug: str):
    """Ruta del plan de una política en el corpus, o None si no está."""
    return dict(descubrir_planes()).get(f"plan_{slug}")


# ── Golden ──

def ruta_golden(clave: str) -> str:
    return os.path.join(GOLDEN_DIR, clave + ".json")


def cargar_golden(clave: str):
    """Huella esperada guardada, o None si no se ha generado."""
    if not os.path.exists(ruta_golden(clave)):
        return None
    with open(ruta_golden(clave), encoding="utf-8") as fh:
        return json.load(fh)


def claves_golden(prefijo: str) -> set:
    """Claves de los golden guardados con ese prefijo (`plan` o `seg`)."""
    return {f[:-5] for f in os.listdir(GOLDEN_DIR)
            if f.startswith(prefijo + "_") and f.endswith(".json")}


def comparar_golden(esperado: dict, obtenido: dict) -> list:
    """Diferencias entre dos huellas, sin contar el nombre del archivo fuente."""
    sin_archivo = lambda h: {k: v for k, v in h.items() if k != "archivo"}
    return diferencias(sin_archivo(esperado), sin_archivo(obtenido))


def mensaje_regresion(clave: str, esperado: dict, obtenido: dict, difs: list) -> str:
    msg = f"Regresión en {clave}:\n  " + "\n  ".join(difs)
    if esperado.get("archivo") != obtenido.get("archivo"):
        msg += (f"\n  (el golden salió de {esperado.get('archivo')!r} y ahora se leyó "
                f"{obtenido.get('archivo')!r}: si es una versión nueva del plan, revisar "
                f"las diferencias y regenerar con scripts/gen_golden.py)")
    return msg
