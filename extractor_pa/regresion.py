# -*- coding: utf-8 -*-
"""
Huellas (fingerprints) estables para pruebas de regresión / golden files.

Una "huella" es un resumen DETERMINISTA y pequeño del resultado de una
extracción (códigos, conteos, años, alertas por tipo). Sirve para:
- **Golden files**: fijar la huella esperada por archivo y detectar regresiones
  del propio maestro entre versiones.
- **Paridad**: comparar la huella del maestro con la de un extractor legado.

No incluye campos no deterministas (p. ej. el año de vigencia derivado de la
fecha del sistema).
"""

from __future__ import annotations

from collections import Counter


def _alertas_por_tipo(alertas) -> dict:
    return dict(sorted(Counter(a.tipo for a in alertas).items()))


def huella_plan(res) -> dict:
    """Huella estable de un `ResultadoExtraccion` (plan)."""
    m = res.metadatos
    return {
        "archivo": m.archivo_fuente,
        "politica": m.nombre_politica,
        "formato": m.formato_detectado,
        "anios": list(m.anios_detectados or []),
        "n_ir": len(res.indicadores_resultado),
        "n_ip": len(res.indicadores_producto),
        "n_financiero": len(res.financiero),
        "codigos_ir": sorted(i.codigo_ir for i in res.indicadores_resultado if i.codigo_ir),
        "codigos_ip": sorted(i.codigo_ip for i in res.indicadores_producto if i.codigo_ip),
        "alertas_por_tipo": _alertas_por_tipo(res.alertas),
    }


def huella_seguimiento(res) -> dict:
    """Huella estable de un `ResultadoSeguimiento`."""
    m = res.metadatos
    n_avances = sum(len(i.avances) for i in res.indicadores)
    n_cual = sum(len(i.cualitativos) for i in res.indicadores)
    return {
        "archivo": m.archivo_fuente,
        "politica": m.nombre_politica,
        "tipo_archivo": m.tipo_archivo,
        "anios": list(m.anios_detectados or []),
        "n_indicadores": len(res.indicadores),
        "codigos": sorted(i.codigo for i in res.indicadores if i.codigo),
        "n_avances_total": n_avances,
        "n_cualitativos_total": n_cual,
        "alertas_por_tipo": _alertas_por_tipo(res.alertas),
    }


def diferencias(esperado: dict, obtenido: dict) -> list:
    """Lista de diferencias campo a campo entre dos huellas (vacía si idénticas)."""
    difs = []
    for clave in sorted(set(esperado) | set(obtenido)):
        ve, vo = esperado.get(clave), obtenido.get(clave)
        if ve != vo:
            if isinstance(ve, list) and isinstance(vo, list):
                falta = sorted(set(map(str, ve)) - set(map(str, vo)))
                sobra = sorted(set(map(str, vo)) - set(map(str, ve)))
                difs.append(f"{clave}: faltan={falta[:8]} sobran={sobra[:8]}")
            else:
                difs.append(f"{clave}: esperado={ve!r} obtenido={vo!r}")
    return difs
