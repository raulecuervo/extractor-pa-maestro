# -*- coding: utf-8 -*-
"""
Pipeline orquestador del extractor maestro.

Encadena: cargar → localizar hoja → detectar formato → extraer metadatos →
elegir estrategia → extraer → ensamblar `ResultadoExtraccion`. Cada paso que
falla agrega una alerta de extracción en lugar de lanzar la excepción al
llamador (salvo casos irrecuperables, que también se reportan como alerta).
"""

from __future__ import annotations

import os
import re
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Optional

from .alertas import crear_alerta
from .config import MapeoColumnas, MAPEO_ANTIGUO, MAPEO_NUEVO
from .detector_formato import detectar_formato
from .estrategias import ExtractorNuevo
from .lector_fichas import enriquecer_con_fichas, leer_fichas
from .loader import abrir_workbook
from .localizador_hoja import localizar_hoja
from .modelo import Metadatos, ResultadoExtraccion
from .resolutor_columnas import EstructuraNoReconocida
from .utilidades import _norm, limpiar


# Motor de extracción único (la diferencia entre formatos vive en el MapeoColumnas).
_MOTOR = ExtractorNuevo()


_RE_DECRETO = re.compile(r"^\s*n?[ºo°]?\.?\s*\d+\s*(de|/)\s*\d{2,4}\s*$", re.I)
_NO_NOMBRE = {"no aplica", "n/a", "na", "ninguno", "ninguna", "sin nombre", "-", "."}


def _es_nombre_politica(valor) -> bool:
    """True si el texto parece el NOMBRE de la política (no un decreto, CONPES,
    fecha, 'No aplica' ni un rótulo/instrucción)."""
    if not isinstance(valor, str):
        return False
    t = valor.strip()
    n = _norm(t)
    if len(t) < 8 or n in _NO_NOMBRE:
        return False
    if _RE_DECRETO.match(t) or "conpes" in n:          # "233 de 2023", "01/2018"
        return False
    if re.fullmatch(r"[\d\W]+", t):                     # solo números/símbolos
        return False
    # Rótulos/instrucciones que contienen "política pública" pero no son el nombre.
    if n.startswith(("a.", "b.", "c.", "objetivo", "formato", "decreto",
                     "documento", "nombre de la pol")):
        return False
    return True


def _buscar_nombre_politica(celda) -> "str | None":
    """Busca en la cabecera la celda que EMPIEZA por 'Política Pública' (el nombre),
    descartando título, objetivo e instrucciones. Devuelve el primero hallado."""
    for r in range(1, 11):
        for c in range(1, 9):
            cand = celda(r, c)
            if (isinstance(cand, str) and len(cand) < 250
                    and _norm(cand).startswith("politica publica")
                    and _es_nombre_politica(cand)):
                return cand.strip()
    return None


_ANCLA_FILA_MEDIA = _norm("Resultado esperado")


def _ubicar_encabezados(ws, mapeo: MapeoColumnas) -> MapeoColumnas:
    """Ajusta las filas de encabezado y de datos a donde de verdad están.

    La plantilla vigente trae «Resultado esperado» en la fila 10 (encabezados
    9–11, datos desde la 12), pero las versiones anteriores lo bajan: a la fila
    11 en los planes 2021–2025 y a la 25 cuando la cabecera lista los
    corresponsables. Con las filas fijas esos planes perdían metas, línea base
    y bloque financiero, o no se extraían. Si el ancla no aparece en las
    primeras 40 filas se deja el mapeo como está."""
    for fila in range(1, 41):
        for col in range(1, 11):
            if _norm(ws.cell(row=fila, column=col).value) == _ANCLA_FILA_MEDIA:
                if fila == mapeo.filas_encabezado[1]:
                    return mapeo
                return replace(mapeo, filas_encabezado=(fila - 1, fila, fila + 1),
                               fila_datos=fila + 2)
    return mapeo


def _extraer_metadatos(ws, mapeo: MapeoColumnas, nombre_archivo: str) -> Metadatos:
    """Lee la cabecera de la política (nombre, CONPES, líderes, objetivo general)."""
    def celda(r: int, c: int):
        return limpiar(ws.cell(row=r, column=c).value)

    datos = {clave: celda(r, c) for clave, r, c in mapeo.celdas_metadatos}

    # Nombre de política: la celda fija a veces trae el Decreto/CONPES, 'No aplica'
    # o está vacía. Si no parece un nombre, se busca en la cabecera la celda que
    # empieza por 'Política Pública'.
    if not _es_nombre_politica(datos.get("nombre_politica")):
        datos["nombre_politica"] = _buscar_nombre_politica(celda)

    # Documento CONPES: buscar "CONPES <número>" en las filas de cabecera.
    documento = None
    for r in range(1, 9):
        for c in range(1, 12):
            v = celda(r, c)
            if v and "conpes" in _norm(v):
                documento = v
                break
        if documento:
            break

    return Metadatos(
        nombre_politica=datos.get("nombre_politica"),
        documento_conpes=documento,
        sector_lider=datos.get("sector_lider"),
        entidad_lider=datos.get("entidad_lider"),
        objetivo_general=datos.get("objetivo_general"),
        archivo_fuente=nombre_archivo,
    )


def extraer_plan_accion(
    ruta: str | Path,
    mapeo: Optional[MapeoColumnas] = None,
    anio_vigencia: Optional[int] = None,
    leer_fichas_tecnicas: bool = True,
    incluir_reglas_negocio: bool = False,
    catalogo_oficial=None,
) -> ResultadoExtraccion:
    """Extrae un archivo de plan de acción y devuelve el modelo canónico.

    Nunca lanza por el contenido del archivo: los errores de datos se reportan
    como alertas dentro del `ResultadoExtraccion`, y una excepción inesperada en
    la extracción queda como la alerta fatal `error_extraccion` (en las etapas
    opcionales, fichas y reglas, como `error_etapa_opcional`, sin perder el plan).
    - `mapeo`: permite sobreescribir las anclas por defecto.
    - `anio_vigencia`: año de corte para `meta_vigencia_actual/_anterior`. Sin
      él se usa el año del reloj del sistema, así que el mismo archivo da otro
      resultado al cambiar el año; el usado queda en `metadatos.anio_corte`.
    - `leer_fichas_tecnicas`: si True, lee las hojas «Ficha técnica IR#/IP#» y
      completa metodología, unidad de medida, fuentes y días de rezago.
    - `incluir_reglas_negocio`: si True, ejecuta además las reglas V0–V18
      (`validacion.validar_reglas`) y agrega sus alertas al resultado."""
    # Si el usuario no pasa un mapeo, se elige automáticamente según el formato
    # detectado (nuevo / antiguo). Si lo pasa, se respeta tal cual.
    mapeo_usuario = mapeo
    base_mapeo = mapeo_usuario or MAPEO_NUEVO
    nombre_archivo = os.path.basename(str(ruta))
    anio_corte = anio_vigencia if anio_vigencia is not None else datetime.now().year
    meta = Metadatos(archivo_fuente=nombre_archivo, anio_corte=anio_corte)

    # 1) Abrir el libro.
    try:
        wb = abrir_workbook(ruta)
    except Exception as e:  # noqa: BLE001 — cualquier fallo de apertura se reporta
        return ResultadoExtraccion(meta, [], [], [crear_alerta(
            "apertura",
            f"No se pudo abrir el archivo: {e}", archivo_fuente=nombre_archivo)])

    try:
        return _extraer_libro(wb, nombre_archivo, mapeo_usuario, base_mapeo, anio_corte,
                              leer_fichas_tecnicas, incluir_reglas_negocio, catalogo_oficial)
    except Exception as e:  # noqa: BLE001 — un fallo inesperado no tumba al llamador
        return ResultadoExtraccion(meta, [], [], [crear_alerta(
            "error_extraccion",
            f"Fallo inesperado al extraer el plan ({type(e).__name__}: {e}).",
            archivo_fuente=nombre_archivo)])
    finally:
        wb.close()


def _extraer_libro(wb, nombre_archivo, mapeo_usuario, base_mapeo, anio_corte,
                   leer_fichas_tecnicas, incluir_reglas_negocio, catalogo_oficial):
    """Pasos 2–9 de `extraer_plan_accion` sobre el libro ya abierto."""
    meta = Metadatos(archivo_fuente=nombre_archivo, anio_corte=anio_corte)
    # 2) Localizar la hoja del plan.
    nombre_hoja = localizar_hoja(wb, base_mapeo.hoja)
    if nombre_hoja is None:
        return ResultadoExtraccion(meta, [], [], [crear_alerta(
            "hoja_no_encontrada",
            f"No se encontró la hoja del plan de acción. "
            f"Hojas disponibles: {wb.sheetnames[:8]}",
            archivo_fuente=nombre_archivo)])
    ws = wb[nombre_hoja]

    # 3) Detectar formato y elegir el mapeo efectivo.
    veredicto = detectar_formato(ws, wb)
    if mapeo_usuario is not None:
        mapeo = mapeo_usuario
    else:
        mapeo = _ubicar_encabezados(
            ws, MAPEO_ANTIGUO if veredicto.formato == "antiguo" else MAPEO_NUEVO)

    # 4) Metadatos de cabecera.
    meta = _extraer_metadatos(ws, mapeo, nombre_archivo)
    meta.anio_corte = anio_corte
    meta.hoja_usada = nombre_hoja
    meta.formato_detectado = veredicto.formato

    alertas = []
    if veredicto.formato is None:
        alertas.append(crear_alerta(
            "formato_no_reconocido",
            f"No se pudo determinar el formato del plan ({veredicto.motivo}).",
            archivo_fuente=nombre_archivo,
            nombre_politica=meta.nombre_politica))
        return ResultadoExtraccion(meta, [], [], alertas)

    # 5) Extraer con el motor único.
    try:
        irs, ips, financiero, alertas_ext, objetivos = _MOTOR.extraer(
            ws, mapeo, nombre_archivo, meta.nombre_politica, anio_corte)
    except EstructuraNoReconocida as e:
        alertas.append(crear_alerta(
            "estructura",
            f"Estructura de columnas no reconocida: {e}",
            archivo_fuente=nombre_archivo,
            nombre_politica=meta.nombre_politica))
        return ResultadoExtraccion(meta, [], [], alertas)

    alertas.extend(alertas_ext)

    # 5b) Enriquecer con fichas técnicas (hojas «Ficha técnica IR#/IP#»).
    if leer_fichas_tecnicas:
        try:
            fichas = leer_fichas(wb)
            if fichas:
                enriquecer_con_fichas(irs, fichas, "codigo_ir")
                enriquecer_con_fichas(ips, fichas, "codigo_ip")
        except Exception as e:  # noqa: BLE001 — sin fichas el plan sigue sirviendo
            alertas.append(_alerta_etapa_opcional("fichas técnicas", e, meta))

    # 6) Años detectados (unión de las metas de todos los indicadores).
    anios = set()
    for ind in irs + ips:
        anios.update(ind.metas_por_anio.keys())
    meta.anios_detectados = sorted(anios)

    # 7) Avisos de extracción vacía.
    if not irs:
        alertas.append(crear_alerta(
            "sin_ir",
            "No se extrajeron indicadores de resultado (0 IR).",
            archivo_fuente=nombre_archivo, nombre_politica=meta.nombre_politica))
    if not ips:
        alertas.append(crear_alerta(
            "sin_ip",
            "No se extrajeron indicadores de producto (0 IP).",
            archivo_fuente=nombre_archivo, nombre_politica=meta.nombre_politica))

    res = ResultadoExtraccion(meta, irs, ips, alertas, financiero, objetivos)

    # 8) Reglas de negocio V0–V18 (opcional).
    if incluir_reglas_negocio:
        from .validacion import validar_reglas
        try:
            res.alertas.extend(validar_reglas(res, catalogo_oficial=catalogo_oficial))
        except Exception as e:  # noqa: BLE001 — sin reglas el plan sigue sirviendo
            res.alertas.append(_alerta_etapa_opcional("reglas de negocio", e, meta))

    # 9) Métricas de extracción.
    meta.n_ir = len(irs)
    meta.n_ip = len(ips)
    meta.n_alertas = len(res.alertas)
    if irs:
        con_lb = sum(1 for i in irs if i.valor_linea_base not in (None, ""))
        meta.pct_ir_con_linea_base = round(100.0 * con_lb / len(irs), 1)

    return res


def _alerta_etapa_opcional(etapa: str, e: Exception, meta: Metadatos):
    return crear_alerta(
        "error_etapa_opcional",
        f"Falló la etapa de {etapa} ({type(e).__name__}: {e}); "
        f"el resto de la extracción se conserva.",
        archivo_fuente=meta.archivo_fuente, nombre_politica=meta.nombre_politica)
