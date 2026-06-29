# -*- coding: utf-8 -*-
"""
Corpus de regresión (golden files).

Dos niveles:
- **Curado** (`CORPUS_PLAN` / `CORPUS_SEGUIMIENTO`): pocos archivos representativos,
  se prueban por defecto (rápido).
- **Completo** (`descubrir_planes` / `descubrir_seguimientos`): todas las políticas,
  para la regresión exhaustiva previa a la migración (pruebas marcadas `slow`).

Las rutas son del entorno del usuario; las pruebas se saltan los archivos que no
existan, manteniendo la suite portable. `clave` es el id estable del golden
(`tests/golden/<clave>.json`).
"""

import glob
import os
import re

_PLANES = r"C:\Users\RaulEsteban\Proyectos\sispp-gobierno\01_planes_accion"
_SEG_G = r"C:\Users\RaulEsteban\Proyectos\sispp-gobierno\02_seguimientos"
_SEG_A = r"C:\Users\RaulEsteban\Proyectos\alertas-seguimientos\archivos_base"

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")


def _clave(prefijo: str, ruta: str) -> str:
    """clave estable y portable a partir del nombre de archivo."""
    stem = os.path.splitext(os.path.basename(ruta))[0]
    slug = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    return f"{prefijo}_{slug}"


def _descubrir(carpeta: str, ext: str, prefijo: str):
    if not os.path.isdir(carpeta):
        return []
    rutas = sorted(glob.glob(os.path.join(carpeta, f"*.{ext}")))
    return [(_clave(prefijo, r), r) for r in rutas
            if not os.path.basename(r).startswith("~$")]


def descubrir_planes():
    """Todos los planes (.xlsx) — corpus completo."""
    return _descubrir(_PLANES, "xlsx", "plan")


def descubrir_seguimientos():
    """Todos los seguimientos (.xlsb) — corpus completo."""
    return _descubrir(_SEG_G, "xlsb", "seg")


# ── Corpus curado (rápido, por defecto) ──
CORPUS_PLAN = [
    ("plan_bti", os.path.join(_PLANES, "PA_BTI_V4-26_DP.xlsx")),
    ("plan_educacion", os.path.join(_PLANES, "PA_Educacion_V2_26_DP.xlsx")),
    ("plan_lgbti", os.path.join(_PLANES, "PA_LGBTI_V1-26.xlsx")),
    ("plan_cti_antiguo", os.path.join(_PLANES, "plan_accion_pp_cti_v4-25.xlsx")),
    ("plan_negra_afro", os.path.join(_PLANES, "Plan Accion PP_Negra-Afro_V3_2025 15.12.2025.xlsx")),
]

CORPUS_SEGUIMIENTO = [
    ("seg_bti_gob", os.path.join(_SEG_G, "BTI.xlsb")),
    ("seg_educacion_gob", os.path.join(_SEG_G, "Educación.xlsb")),
    ("seg_bti_productos", os.path.join(_SEG_A, "Seguimiento a Productos PP BTI S1-25.xlsb")),
]
