# -*- coding: utf-8 -*-
"""
Adaptadores de salida del SEGUIMIENTO (Fase S4).

Convierte un `ResultadoSeguimiento` a tablas en **formato largo** (dim + fact),
ideal para BI, reutilizando los escritores genéricos de `..exportadores`:

- `metadatos`            : 1 fila (política, tipo, período, años…).
- `indicadores`          : 1 fila por indicador (dim: identificación + atributos).
- `avances_trimestrales` : 1 fila por indicador×año×trimestre (fact).
- `anual`                : 1 fila por indicador×año (acumulado, meta, % …).
- `cualitativo`          : 1 fila por indicador×año×trimestre (texto + enfoques).
- `alertas`              : 1 fila por alerta.

Exporta a JSON / CSV / Excel (por archivo o **consolidado multi-archivo**), y la
**consolidación por período** (`tabla_consolidado`).
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from ..exportadores import (
    _escribir_csv_tablas, _escribir_excel_tablas, exportar_json as _exportar_json_obj,
)
from .cruce import consolidar


def _base(meta):
    return {"politica": meta.nombre_politica or "", "archivo": meta.archivo_fuente or ""}


def _dim(ind, meta) -> dict:
    d = _base(meta)
    d.update({
        "tipo_archivo": ind.tipo_archivo or meta.tipo_archivo or "",
        "codigo": ind.codigo or "",
        "indicador_esperado": ind.indicador_esperado or "",
        "nombre": ind.nombre or "",
        "sector": ind.sector or "",
        "entidad": ind.entidad or "",
        "estado": ind.estado or "",
        "ponderacion": ind.ponderacion,
        "linea_base": ind.linea_base,
        "tipo_anualizacion": ind.tipo_anualizacion or "",
        "periodicidad": ind.periodicidad or "",
        "fecha_inicio": ind.fecha_inicio or "",
        "fecha_fin": ind.fecha_fin or "",
        "meta_final": ind.meta_final,
        "corte": ind.corte or "",
        "anio_reporte": ind.anio_reporte,
        "en_plan": ind.en_plan,
        "tipo_plan": ind.tipo_plan or "",
        "nombre_plan": ind.nombre_plan or "",
    })
    return d


def _split_clave(clave: str):
    """'2024_Q1' -> (2024, 1)."""
    anio, q = clave.split("_Q")
    return int(anio), int(q)


def tablas_seguimiento(res) -> dict:
    """Devuelve {nombre_tabla: [filas]} para un resultado de seguimiento."""
    m = res.metadatos
    meta_fila = dict(asdict(m))
    meta_fila["anios_detectados"] = ", ".join(str(a) for a in (m.anios_detectados or []))

    indicadores, avances, anual, cualitativo = [], [], [], []
    for ind in res.indicadores:
        indicadores.append(_dim(ind, m))
        for clave, val in ind.avances.items():
            anio, q = _split_clave(clave)
            avances.append({**_base(m), "codigo": ind.codigo, "anio": anio,
                            "trimestre": q, "valor": val})
        anios = (set(ind.acumulados) | set(ind.metas) | set(ind.pct_vigencia)
                 | set(ind.pct_acumulado) | set(ind.pct_total))
        for a in sorted(anios, key=lambda x: int(x)):
            anual.append({**_base(m), "codigo": ind.codigo, "anio": int(a),
                          "acumulado": ind.acumulados.get(a),
                          "meta_anual": ind.metas.get(a),
                          "pct_vigencia": ind.pct_vigencia.get(a),
                          "pct_acumulado": ind.pct_acumulado.get(a),
                          "pct_total": ind.pct_total.get(a)})
        for clave in sorted(set(ind.cualitativos) | set(ind.avance_enfoques)):
            anio, q = _split_clave(clave)
            cualitativo.append({**_base(m), "codigo": ind.codigo, "anio": anio,
                                "trimestre": q,
                                "texto_cualitativo": ind.cualitativos.get(clave),
                                "enfoques": ind.avance_enfoques.get(clave)})

    return {
        "metadatos": [meta_fila],
        "indicadores": indicadores,
        "avances_trimestrales": avances,
        "anual": anual,
        "cualitativo": cualitativo,
        "alertas": [asdict(a) for a in res.alertas],
    }


def tablas_seguimiento_consolidadas(resultados: Iterable) -> dict:
    """Apila las tablas de varios seguimientos (multi-archivo)."""
    out = {"metadatos": [], "indicadores": [], "avances_trimestrales": [],
           "anual": [], "cualitativo": [], "alertas": []}
    for res in resultados:
        for nombre, filas in tablas_seguimiento(res).items():
            out[nombre].extend(filas)
    return out


def tabla_consolidado(res, anio, periodo: str) -> list:
    """Tabla de la consolidación por período (1 fila por indicador con datos)."""
    m = res.metadatos
    out = []
    for fila in consolidar(res, anio, periodo):
        out.append({**_base(m), **fila})
    return out


# ─────────────────────────── escritura ───────────────────────────

def exportar_json_seguimiento(res, ruta: str | Path) -> str:
    return _exportar_json_obj(res, ruta)


def exportar_csv_seguimiento(res, carpeta: str | Path, prefijo: str = "seg_") -> list:
    return _escribir_csv_tablas(tablas_seguimiento(res), carpeta, prefijo)


def exportar_excel_seguimiento(res, ruta: str | Path) -> str:
    return _escribir_excel_tablas(tablas_seguimiento(res), ruta)


def exportar_csv_seguimiento_consolidado(resultados: Iterable, carpeta: str | Path,
                                         prefijo: str = "seg_consolidado_") -> list:
    return _escribir_csv_tablas(tablas_seguimiento_consolidadas(resultados), carpeta, prefijo)


def exportar_excel_seguimiento_consolidado(resultados: Iterable, ruta: str | Path) -> str:
    return _escribir_excel_tablas(tablas_seguimiento_consolidadas(resultados), ruta)
