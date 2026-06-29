# -*- coding: utf-8 -*-
"""Genera docs/CATALOGO_ALERTAS.md desde extractor_pa/catalogo.py (fuente única)."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'C:\Users\RaulEsteban\Proyectos\extractor-pa-maestro')

from extractor_pa.catalogo import (
    _TIPOS, CAPA_EXTRACCION, CAPA_VALIDACION_PLAN, CAPA_SEGUIMIENTO,
    CAPA_OPERATIVA, CAPA_CUALITATIVA, CAPA_CALIDAD,
)

BT = chr(96)  # backtick, para no pelear con el shell

ORDEN = [
    (CAPA_EXTRACCION, "1. Extracción / Estructura",
     "Las produce el extractor maestro al leer el Excel."),
    (CAPA_VALIDACION_PLAN, "2. Validación del plan (reglas de negocio V0–V18)",
     f"Las produce {BT}validar_reglas(){BT} sobre el modelo canónico."),
    (CAPA_SEGUIMIENTO, "3. Consistencia del seguimiento",
     f"De {BT}alertas-seguimientos{BT} (capa de seguimiento, fuera del extractor de plan)."),
    (CAPA_OPERATIVA, "4. Operativas / temporales",
     f"De {BT}sispp-sdis{BT} (notificaciones del ciclo de reporte)."),
    (CAPA_CUALITATIVA, "5. Cualitativas",
     f"Justificaciones obligatorias ({BT}sispp-sdis{BT}, RN-CUL)."),
    (CAPA_CALIDAD, "6. Calidad declarativa",
     f"De {BT}sistema-seguimiento-v3{BT} (Q001–Q003)."),
]

L = []
L.append("# Catálogo CONSOLIDADO de alertas, errores y chequeos")
L.append("")
L.append("> Consolidado de TODOS los chequeos revisados en los 9 aplicativos de política pública.")
L.append(f"> Generado automáticamente desde {BT}extractor_pa/catalogo.py{BT} (única fuente de verdad).")
L.append("> Niveles unificados: **ERROR** (bloquea / dato inutilizable) · "
         "**ADVERTENCIA** (revisar) · **INFO** (informativo).")
L.append("")
tot = len(_TIPOS)
impl = sum(1 for t in _TIPOS if t.implementado)
L.append(f"**{tot} tipos** catalogados · **{impl} implementados** en el extractor maestro.")
L.append("")
L.append(f"Leyenda {BT}Impl.{BT}: ✅ lo produce el maestro · ⬜ documentado "
         "(vive en otro aplicativo o pendiente).")

for capa, titulo, desc in ORDEN:
    items = [t for t in _TIPOS if t.capa == capa]
    if not items:
        continue
    L.append("")
    L.append("## " + titulo)
    L.append("")
    L.append(desc)
    L.append("")
    fams = []
    for t in items:
        if t.familia not in fams:
            fams.append(t.familia)
    L.append("| tipo | nivel | regla | familia | descripción | Impl. |")
    L.append("|---|---|---|---|---|:---:|")
    for fam in fams:
        for t in [x for x in items if x.familia == fam]:
            flag = "✅" if t.implementado else "⬜"
            reg = t.regla or "—"
            L.append(f"| {BT}{t.codigo}{BT} | {t.nivel} | {reg} | {t.familia} | {t.descripcion} | {flag} |")

L.append("")
L.append("## Notas")
L.append("")
L.append("- El **nivel** y la **descripción** de cada tipo viven en "
         f"{BT}extractor_pa/catalogo.py{BT}; {BT}crear_alerta(tipo, ...){BT} toma el nivel de ahí.")
L.append("- Las capas 3–6 (seguimiento, operativas, cualitativas, calidad) se documentan "
         "para el consolidado pero pertenecen a los aplicativos de seguimiento/operación, "
         "no al extractor del plan.")

out = r"C:\Users\RaulEsteban\Proyectos\extractor-pa-maestro\docs\CATALOGO_ALERTAS.md"
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("OK:", out, "|", tot, "tipos,", impl, "implementados")
