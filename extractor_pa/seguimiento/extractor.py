# -*- coding: utf-8 -*-
"""
Extractor de seguimiento consolidado (Fase S1).

Combina lo mejor de los 3 extractores revisados:
- Lectura por **anclas dinámicas** (de generador-seguimiento / sispp-gobierno).
- **Histórico completo** por indicador (de alertas-seguimientos).
- **Metadatos desde el nombre del archivo** (de alertas-seguimientos).

`extraer_seguimiento(ruta)` devuelve un `ResultadoSeguimiento` con el histórico
cuantitativo + cualitativo de cada indicador. Nunca lanza por errores de datos:
los reporta como alertas.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
from collections import Counter
from pathlib import Path
from typing import Optional

from ..alertas import crear_alerta
from ..utilidades import a_int, extraer_codigo, limpiar
from . import loader, metadatos as meta_mod, resolutor as R
from .modelo import IndicadorSeguimiento, MetadatosSeguimiento, ResultadoSeguimiento


def _series(fila: dict, col: Optional[int]):
    """Valor de una columna de la fila (o None)."""
    if col is None:
        return None
    v = fila.get(col)
    return v if v not in (None, "") else None


def _fecha(valor):
    """Convierte un serial de Excel (o texto) a fecha ISO 'YYYY-MM-DD'."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        try:
            d = _dt.datetime(1899, 12, 30) + _dt.timedelta(days=float(valor))
            if 1900 <= d.year <= 2100:
                return d.date().isoformat()
        except (ValueError, OverflowError):
            return None
    return limpiar(valor)


def _leer_cuantitativo(mapa, meta, alertas):
    """Construye los indicadores con su histórico cuantitativo."""
    fila_bloques = mapa.get(R.FILA_BLOQUES, {})
    fila_anios = mapa.get(R.FILA_ANIOS, {})
    anclas = R.detectar_anclas(fila_bloques)  # lanza AnclasNoEncontradas
    (anios, mapa_trim, mapa_acum, mapa_meta, col_meta_final,
     mapa_pct_vig, mapa_pct_acum, mapa_pct_total) = R.construir_mapas_cuant(fila_anios, anclas)
    meta.anios_detectados = anios

    indicadores: list = []
    indice: dict = {}
    sin_codigo = 0
    for fn in sorted(f for f in mapa if f >= R.FILA_DATOS):
        fila = mapa[fn]
        ind_esp = limpiar(fila.get(R.COL_CODIGO))
        if not ind_esp:
            continue
        codigo = extraer_codigo(ind_esp)
        if not codigo:
            sin_codigo += 1
        ind = IndicadorSeguimiento(
            codigo=codigo,
            indicador_esperado=ind_esp,
            nombre=limpiar(fila.get(R.COL_NOMBRE)),
            sector=limpiar(fila.get(R.COL_SECTOR)),
            entidad=limpiar(fila.get(R.COL_ENTIDAD)),
            tipo_archivo=meta.tipo_archivo,
            ind_no=fila.get(0),
            meta_final=_series(fila, col_meta_final),
            estado=limpiar(fila.get(R.COL_ESTADO)),
            ponderacion=_series(fila, R.COL_PONDERACION),
            linea_base=_series(fila, R.COL_LINEA_BASE),
            tipo_anualizacion=limpiar(fila.get(R.COL_TIPO_ANUAL)),
            periodicidad=limpiar(fila.get(R.COL_PERIODICIDAD)),
            fecha_inicio=_fecha(fila.get(R.COL_FECHA_INI)),
            fecha_fin=_fecha(fila.get(R.COL_FECHA_FIN)),
            corte=limpiar(fila.get(R.COL_CORTE)),
            anio_reporte=_series(fila, R.COL_ANIO_REPORTE),
        )
        for anio in anios:
            sa = str(anio)
            acum = _series(fila, mapa_acum.get(anio))
            if acum is not None:
                ind.acumulados[sa] = acum
            m = _series(fila, mapa_meta.get(anio))
            if m is not None:
                ind.metas[sa] = m
            pv = _series(fila, mapa_pct_vig.get(anio))
            if pv is not None:
                ind.pct_vigencia[sa] = pv
            pa = _series(fila, mapa_pct_acum.get(anio))
            if pa is not None:
                ind.pct_acumulado[sa] = pa
            pt = _series(fila, mapa_pct_total.get(anio))
            if pt is not None:
                ind.pct_total[sa] = pt
            for q, col in mapa_trim[anio].items():
                val = _series(fila, col)
                if val is not None:
                    ind.avances[f"{anio}_Q{q}"] = val
        indicadores.append(ind)
        if codigo:
            indice[codigo] = ind

    if sin_codigo:
        alertas.append(crear_alerta(
            "indicador_seguimiento_sin_codigo",
            f"{sin_codigo} fila(s) de seguimiento sin código de indicador reconocible.",
            archivo_fuente=meta.archivo_fuente, nombre_politica=meta.nombre_politica))
    return indicadores, indice


def _leer_cualitativo(mapa_cual, indice, meta):
    """Adjunta el reporte cualitativo (texto + enfoques) a cada indicador por código."""
    if not mapa_cual:
        return
    fila_anios_cual = mapa_cual.get(R.FILA_BLOQUES, {})
    mapa_cols = R.construir_mapa_cual(fila_anios_cual)
    if not mapa_cols:
        return
    for fn in sorted(f for f in mapa_cual if f >= R.FILA_DATOS):
        fila = mapa_cual[fn]
        ind_esp = limpiar(fila.get(R.COL_CODIGO))
        if not ind_esp:
            continue
        codigo = extraer_codigo(ind_esp)
        ind = indice.get(codigo)
        if ind is None:
            continue
        for anio, trims in mapa_cols.items():
            for q, cols in trims.items():
                cual = limpiar(fila.get(cols["cualitativo"]))
                enf = limpiar(fila.get(cols["enfoques"]))
                if cual:
                    ind.cualitativos[f"{anio}_Q{q}"] = cual
                if enf:
                    ind.avance_enfoques[f"{anio}_Q{q}"] = enf


def extraer_seguimiento(ruta: str | Path) -> ResultadoSeguimiento:
    """Extrae un `.xlsb` de seguimiento a `ResultadoSeguimiento`."""
    nombre = os.path.basename(str(ruta))
    meta = MetadatosSeguimiento(
        archivo_fuente=nombre,
        tipo_archivo=meta_mod.tipo_desde_nombre(nombre),
        nombre_politica=meta_mod.politica_desde_nombre(nombre),
    )
    meta.periodo, meta.anio_reporte = meta_mod.periodo_desde_nombre(nombre)
    alertas: list = []

    try:
        wb_cm = loader.abrir(ruta)
    except ImportError:
        raise  # pyxlsb no instalado: error de entorno, no de datos
    except Exception as e:  # noqa: BLE001
        alertas.append(crear_alerta("apertura_seguimiento",
                                    f"No se pudo abrir el archivo: {e}",
                                    archivo_fuente=nombre))
        return ResultadoSeguimiento(meta, [], alertas)

    try:
        with wb_cm as wb:
            hoja_cuant = loader.localizar_hoja(wb, "avance", "cuantitativo")
            if hoja_cuant is None:
                alertas.append(crear_alerta("hoja_seguimiento_no_encontrada",
                                            "No se encontró la hoja 'Avance Cuantitativo'.",
                                            archivo_fuente=nombre, nombre_politica=meta.nombre_politica))
                return ResultadoSeguimiento(meta, [], alertas)
            meta.hoja_usada = hoja_cuant
            mapa = loader.leer_hoja(wb, hoja_cuant)

            try:
                indicadores, indice = _leer_cuantitativo(mapa, meta, alertas)
            except R.AnclasNoEncontradas as e:
                alertas.append(crear_alerta("anclas_no_encontradas", str(e),
                                            archivo_fuente=nombre, nombre_politica=meta.nombre_politica))
                return ResultadoSeguimiento(meta, [], alertas)

            hoja_cual = loader.localizar_hoja(wb, "avance", "cualitativo")
            if hoja_cual:
                try:
                    mapa_cual = loader.leer_hoja(wb, hoja_cual)
                    _leer_cualitativo(mapa_cual, indice, meta)
                except Exception:  # noqa: BLE001 — el cualitativo es opcional
                    pass
    except Exception as e:  # noqa: BLE001
        alertas.append(crear_alerta("apertura_seguimiento",
                                    f"Error leyendo el archivo: {e}",
                                    archivo_fuente=nombre, nombre_politica=meta.nombre_politica))
        return ResultadoSeguimiento(meta, [], alertas)

    # D2: respaldo de período/año desde las columnas cuando el nombre no los trae
    # (p. ej. "BTI.xlsb" sin sufijo S1-25). El corte ("Q4") da el período y la
    # columna de año de reporte da el año.
    if meta.periodo is None:
        cortes = [str(i.corte).strip().upper() for i in indicadores if i.corte]
        cortes = [c for c in cortes if re.fullmatch(r"[SQ][1-4]", c)]
        if cortes:
            meta.periodo = Counter(cortes).most_common(1)[0][0]
    if meta.anio_reporte is None:
        anios = [a for a in (a_int(i.anio_reporte) for i in indicadores)
                 if a and 1900 <= a <= 2100]
        if anios:
            meta.anio_reporte = Counter(anios).most_common(1)[0][0]

    if not indicadores:
        alertas.append(crear_alerta("sin_indicadores_seguimiento",
                                    "No se extrajo ningún indicador de seguimiento.",
                                    archivo_fuente=nombre, nombre_politica=meta.nombre_politica))
    return ResultadoSeguimiento(meta, indicadores, alertas)
