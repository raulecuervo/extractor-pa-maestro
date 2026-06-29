# -*- coding: utf-8 -*-
"""
Tablero de cumplimiento por política (Hito 5).

Ensambla, por política: extracción del PLAN + del SEGUIMIENTO, cruce (qué
indicadores reportados están en el plan), semáforo de avance por indicador y
conteo de hallazgos (reglas V0–V18 + consistencia). Produce un modelo de
resumen y un HTML navegable autocontenido.

Empareja los archivos por una clave normalizada del nombre (sigla de la
política): p. ej. `PA_BTI_V4-26_DP.xlsx` ↔ `BTI.xlsb`.
"""

from __future__ import annotations

import glob
import os
import re
import unicodedata
from collections import Counter

from . import extraer_plan_accion
from .modelo import NIVEL_ERROR, NIVEL_ADVERTENCIA

ANIO_DEFECTO = 2025
PERIODO_DEFECTO = "Anual"
_ORDEN_SEM = ["VERDE", "NARANJA", "AMARILLO", "ROJO", "SIN_DATO"]
_COLOR_SEM = {"VERDE": "#3fb950", "NARANJA": "#db8b2a", "AMARILLO": "#d4b106",
              "ROJO": "#e5534b", "SIN_DATO": "#6e7681"}


# Alias para abreviaturas que difieren entre plan y seguimiento (misma política).
# Conservador: solo casos verificados; NO se usa emparejamiento difuso porque
# produce falsos positivos (Acción Comunal≠Climática, Habitabilidad≠Hábitat).
_ALIAS = {"economiacircular": "econocircular"}
# Palabras vacías que se eliminan al normalizar (para que 'Servicio a la
# Ciudadanía' ≡ 'Servicio Ciudadanía').
_STOP = {"a", "la", "el", "de", "del", "los", "las", "y", "e", "en", "para",
         "con", "pp", "distrital", "politica", "publica"}


def clave_politica(nombre) -> str:
    """Clave normalizada (sigla) a partir del nombre de archivo, para emparejar:
    sin acentos, sin prefijos (PA_, Plan Acción PP_), sin sufijo de versión, sin
    dígitos ni palabras vacías. Tokeniza para no depender del orden de separadores."""
    s = os.path.splitext(os.path.basename(str(nombre)))[0].lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"^(pa[_ ]|plan ?accion ?pp[_ ]|plan_accion_pp_)", "", s)
    s = re.sub(r"[_ ]v\d.*$", "", s)          # quita sufijo de versión/fecha
    toks = [t for t in re.split(r"[^a-z0-9]+", s)
            if t and not t.isdigit() and t not in _STOP]
    clave = "".join(toks)
    return _ALIAS.get(clave, clave)


def emparejar(planes, seguimientos) -> list:
    """Devuelve [(clave, ruta_plan|None, ruta_seg|None)] uniendo por clave de sigla."""
    seg_map = {}
    for s in seguimientos:
        seg_map.setdefault(clave_politica(s), s)
    pares, usados = [], set()
    for p in planes:
        kp = clave_politica(p)
        match = seg_map.get(kp)
        if match is None:                      # emparejado laxo por prefijo común
            for ks, sp in seg_map.items():
                if ks and (ks in kp or kp in ks):
                    match, kp = sp, kp
                    break
        if match:
            usados.add(clave_politica(match))
        pares.append((kp, p, match))
    for s in seguimientos:                     # seguimientos sin plan
        if clave_politica(s) not in usados and s not in [m for _, _, m in pares]:
            pares.append((clave_politica(s), None, s))
    return pares


def _semaforo_seguimiento(res_seg, anio):
    from .seguimiento import semaforo_indicador
    c = Counter()
    pcts = []
    for ind in res_seg.indicadores:
        c[semaforo_indicador(ind, anio)] += 1
        from .seguimiento.validacion_seg import _a_porcentaje
        p = _a_porcentaje(ind.pct_vigencia.get(str(anio)))
        if p is not None:
            pcts.append(p)
    prom = round(sum(pcts) / len(pcts), 1) if pcts else None
    return c, prom


def resumen_politica(clave, ruta_plan, ruta_seg, anio=ANIO_DEFECTO,
                     periodo=PERIODO_DEFECTO) -> dict:
    """KPIs de una política (uno o ambos archivos pueden faltar)."""
    d = {"clave": clave, "politica": clave, "archivo_plan": os.path.basename(ruta_plan) if ruta_plan else None,
         "archivo_seg": os.path.basename(ruta_seg) if ruta_seg else None,
         "n_ir": 0, "n_ip": 0, "n_seg": 0, "n_asociados": 0, "n_error": 0,
         "n_advertencia": 0, "pct_promedio": None,
         "semaforo": {k: 0 for k in _ORDEN_SEM}}

    res_plan = None
    if ruta_plan:
        res_plan = extraer_plan_accion(ruta_plan, anio_vigencia=anio,
                                       incluir_reglas_negocio=True)
        d["politica"] = res_plan.metadatos.nombre_politica or clave
        d["n_ir"], d["n_ip"] = res_plan.metadatos.n_ir, res_plan.metadatos.n_ip
        for a in res_plan.alertas:
            if a.nivel == NIVEL_ERROR:
                d["n_error"] += 1
            elif a.nivel == NIVEL_ADVERTENCIA:
                d["n_advertencia"] += 1

    if ruta_seg:
        from .seguimiento import extraer_seguimiento, cruzar_con_plan
        res_seg = extraer_seguimiento(ruta_seg)
        d["n_seg"] = len(res_seg.indicadores)
        if res_plan is not None:
            cr = cruzar_con_plan(res_seg, res_plan)
            d["n_asociados"] = cr["asociados"]
            if not ruta_plan:
                d["politica"] = res_seg.metadatos.nombre_politica or clave
        elif d["politica"] == clave:
            d["politica"] = res_seg.metadatos.nombre_politica or clave
        sem, prom = _semaforo_seguimiento(res_seg, anio)
        for k, v in sem.items():
            d["semaforo"][k] = v
        d["pct_promedio"] = prom
    return d


def construir_tablero(planes_dir, seg_dir, anio=ANIO_DEFECTO,
                      periodo=PERIODO_DEFECTO, progreso=None) -> list:
    """Construye el tablero (lista de resúmenes por política) desde dos carpetas."""
    planes = [p for p in sorted(glob.glob(os.path.join(planes_dir, "*.xlsx")))
              if not os.path.basename(p).startswith("~$")]
    segs = [s for s in sorted(glob.glob(os.path.join(seg_dir, "*.xlsb")))
            if not os.path.basename(s).startswith("~$")]
    filas = []
    for clave, rp, rs in emparejar(planes, segs):
        if progreso:
            progreso(clave)
        filas.append(resumen_politica(clave, rp, rs, anio, periodo))
    filas.sort(key=lambda x: (-x["n_error"], -(x["n_ir"] + x["n_ip"])))
    return filas


# ───────────────────────────── render HTML ─────────────────────────────

def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if s is not None else "")


def _barra_semaforo(sem, total=None):
    total = total or sum(sem.values()) or 1
    seg = []
    for k in _ORDEN_SEM:
        n = sem.get(k, 0)
        if n:
            seg.append(f'<span title="{k}: {n}" style="width:{100*n/total:.1f}%;'
                       f'background:{_COLOR_SEM[k]}"></span>')
    return f'<span class="bar">{"".join(seg)}</span>'


def render_html(filas, anio=ANIO_DEFECTO, periodo=PERIODO_DEFECTO) -> str:
    """HTML autocontenido (abrible en el navegador) del tablero de cumplimiento."""
    tot_ind = sum(f["n_ir"] + f["n_ip"] for f in filas)
    tot_seg = sum(f["n_seg"] for f in filas)
    tot_err = sum(f["n_error"] for f in filas)
    tot_adv = sum(f["n_advertencia"] for f in filas)
    glob_sem = Counter()
    for f in filas:
        for k, v in f["semaforo"].items():
            glob_sem[k] += v

    leyenda = " ".join(
        f'<span class="lg"><i style="background:{_COLOR_SEM[k]}"></i>{k.title()} '
        f'({glob_sem.get(k,0)})</span>' for k in _ORDEN_SEM)

    filas_html = []
    for f in filas:
        npa = f["n_ir"] + f["n_ip"]
        cob = (f"{100*f['n_asociados']/f['n_seg']:.0f}%" if f["n_seg"] else "—")
        pct = f"{f['pct_promedio']}%" if f["pct_promedio"] is not None else "—"
        filas_html.append(
            f'<tr>'
            f'<td class="pol">{_esc(f["politica"])}</td>'
            f'<td class="num">{npa}<small> ({f["n_ir"]}/{f["n_ip"]})</small></td>'
            f'<td class="num">{f["n_seg"] or "—"}</td>'
            f'<td class="num">{cob}</td>'
            f'<td>{_barra_semaforo(f["semaforo"])}</td>'
            f'<td class="num">{pct}</td>'
            f'<td class="num err">{f["n_error"] or ""}</td>'
            f'<td class="num adv">{f["n_advertencia"] or ""}</td>'
            f'</tr>')

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tablero de cumplimiento por política</title>
<style>
 :root{{--bg:#0d1117;--card:#161b22;--bd:#30363d;--tx:#e6edf3;--mut:#8b949e}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--tx);
   font:14px/1.5 system-ui,Segoe UI,Roboto,sans-serif;padding:24px}}
 h1{{font-size:20px;margin:0 0 4px}} .sub{{color:var(--mut);margin-bottom:16px}}
 .kpis{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}}
 .kpi{{background:var(--card);border:1px solid var(--bd);border-radius:10px;
   padding:12px 16px;min-width:120px}} .kpi b{{font-size:22px;display:block}}
 .kpi span{{color:var(--mut);font-size:12px}}
 .leyenda{{margin:10px 0 16px;color:var(--mut);font-size:12px}}
 .lg{{margin-right:14px;white-space:nowrap}} .lg i{{display:inline-block;width:10px;
   height:10px;border-radius:2px;margin-right:5px;vertical-align:middle}}
 table{{width:100%;border-collapse:collapse;background:var(--card);
   border:1px solid var(--bd);border-radius:10px;overflow:hidden}}
 th,td{{padding:8px 10px;border-bottom:1px solid var(--bd);text-align:left}}
 th{{background:#1c2128;color:var(--mut);font-weight:600;cursor:pointer;
   position:sticky;top:0}} tr:last-child td{{border-bottom:none}}
 td.num{{text-align:right;font-variant-numeric:tabular-nums}}
 td.pol{{font-weight:600;max-width:340px}} small{{color:var(--mut)}}
 td.err{{color:#e5534b;font-weight:700}} td.adv{{color:#d4b106}}
 .bar{{display:flex;height:12px;width:140px;border-radius:6px;overflow:hidden;
   background:#21262d}} .bar span{{display:block;height:100%}}
 input{{background:var(--card);border:1px solid var(--bd);color:var(--tx);
   border-radius:8px;padding:7px 10px;margin-bottom:12px;width:280px}}
</style></head><body>
<h1>Tablero de cumplimiento por política</h1>
<div class="sub">Corte {periodo} {anio} · {len(filas)} políticas · generado por extractor_pa</div>
<div class="kpis">
 <div class="kpi"><b>{len(filas)}</b><span>políticas</span></div>
 <div class="kpi"><b>{tot_ind}</b><span>indicadores (plan)</span></div>
 <div class="kpi"><b>{tot_seg}</b><span>indicadores con seguimiento</span></div>
 <div class="kpi"><b style="color:#e5534b">{tot_err}</b><span>errores (V0–V18)</span></div>
 <div class="kpi"><b style="color:#d4b106">{tot_adv}</b><span>advertencias</span></div>
</div>
<div class="leyenda"><b>Semáforo de avance (% vigencia {anio}):</b> {leyenda}</div>
<input id="q" placeholder="Filtrar política…" onkeyup="filtrar()">
<table id="t"><thead><tr>
 <th onclick="ord(0,true)">Política</th><th onclick="ord(1)">Indicadores<small> (IR/IP)</small></th>
 <th onclick="ord(2)">Seguim.</th><th onclick="ord(3)">Cobertura</th>
 <th>Semáforo</th><th onclick="ord(5)">% prom</th>
 <th onclick="ord(6)">Errores</th><th onclick="ord(7)">Advert.</th>
</tr></thead><tbody>
{''.join(filas_html)}
</tbody></table>
<script>
 function filtrar(){{var q=document.getElementById('q').value.toLowerCase();
  document.querySelectorAll('#t tbody tr').forEach(function(r){{
   r.style.display=r.cells[0].innerText.toLowerCase().includes(q)?'':'none';}});}}
 function ord(i,txt){{var tb=document.querySelector('#t tbody');
  var rs=[].slice.call(tb.rows);var d=tb.getAttribute('d'+i)!=='1';
  rs.sort(function(a,b){{var x=a.cells[i].innerText,y=b.cells[i].innerText;
   if(!txt){{x=parseFloat(x.replace('%',''))||0;y=parseFloat(y.replace('%',''))||0;
    return d?y-x:x-y;}} return d?x.localeCompare(y):y.localeCompare(x);}});
  tb.setAttribute('d'+i,d?'1':'0');rs.forEach(function(r){{tb.appendChild(r);}});}}
</script></body></html>"""
