# -*- coding: utf-8 -*-
"""
Estrategia de extracción del FORMATO NUEVO del plan de acción (SDP).

Estructura: encabezados en filas 9-11, datos desde la fila 12, bloque IR seguido
del bloque IP (separados por la columna 'Producto esperado'). El IR se repite en
cada fila de sus IP, por lo que se deduplica por (política, código_ir).

Combina: resolución de columnas por encabezado, pre-filtro de filas espurias,
forward-fill de las columnas del IR, lectura de metas respetando la escala % y
extracción de códigos tolerante.
"""

from __future__ import annotations

from .base import EstrategiaExtraccion
from ..alertas import crear_alerta
from ..config import MapeoColumnas
from ..consistencia import chequear_consistencia_ir, chequear_duplicados_ip
from ..lector_filas import leer_filas, prefiltrar_filas
from ..normalizador import normalizar_celdas_combinadas
from ..modelo import (
    NIVEL_ADVERTENCIA,
    IndicadorProducto,
    IndicadorResultado,
    RegistroFinanciero,
)
from ..resolutor_columnas import resolver_columnas
from ..utilidades import extraer_codigo, leer_celda_escala, limpiar
from ..vigencia import calcular_vigencia


class ExtractorNuevo(EstrategiaExtraccion):
    nombre_formato = "nuevo"

    def extraer(self, ws, mapeo: MapeoColumnas, nombre_archivo, nombre_politica,
                anio_vigencia=None):
        alertas = []
        financiero: list = []
        cols, metas_ir_cols, metas_ip_cols, financiero_cols = resolver_columnas(ws, mapeo)

        # 1) Leer filas (con índice absoluto) y descartar filas espurias.
        filas = leer_filas(ws, mapeo.fila_datos)
        filas = prefiltrar_filas(filas, cols.get("resultado"), cols.get("producto"))
        if not filas:
            return [], [], financiero, alertas

        # 2) Snapshot de los valores ORIGINALES (antes de normalizar) para el
        #    chequeo de consistencia; la normalización uniformizaría las filas.
        snapshots = [list(valores) for _, valores in filas]

        # 3) Normalización de celdas combinadas (4 capas + ascensión de fila
        #    vigente). Las metas anuales quedan excluidas (se leen por celda).
        normalizar_celdas_combinadas([f for _, f in filas], cols)

        # Helpers de lectura de una fila (lista de valores).
        def g(valores, clave):
            c = cols.get(clave)
            if not c:
                return None
            i = c - 1
            return limpiar(valores[i]) if i < len(valores) else None

        def gc(valores, col):
            """Lee por número de columna (1-based), con limpieza."""
            if not col:
                return None
            i = col - 1
            return limpiar(valores[i]) if i < len(valores) else None

        def metas_de(fila_abs, columnas):
            """Lee {año: valor} respetando la escala % de cada celda. Conserva el
            texto crudo de las metas NO numéricas (C4: p. ej. 'más 0.01 punto',
            'Levantamiento línea base') para no perder dato y poder validarlo."""
            metas, es_pct = {}, False
            for anio, col in columnas.items():
                celda = ws.cell(row=fila_abs, column=col)
                valor, pct = leer_celda_escala(celda)
                if valor is not None:
                    metas[anio] = valor
                    es_pct = es_pct or pct
                else:
                    crudo = limpiar(celda.value)
                    if crudo not in (None, ""):
                        metas[anio] = crudo
            return metas, es_pct

        def meta_final_de(fila_abs, clave_col):
            col = cols.get(clave_col)
            if not col:
                return None, False
            celda = ws.cell(row=fila_abs, column=col)
            valor, pct = leer_celda_escala(celda)
            if valor is None:                      # C4: conservar meta final no numérica
                crudo = limpiar(celda.value)
                if crudo not in (None, ""):
                    return crudo, False
            return valor, pct

        irs: dict[tuple, IndicadorResultado] = {}
        ips: list[IndicadorProducto] = []

        # 3) Recorrer filas y construir IR (dedup) e IP.
        for fila_abs, valores in filas:
            codigo_ir = extraer_codigo(g(valores, "resultado"), niveles=2)
            clave_ir = (nombre_politica, codigo_ir)

            if codigo_ir and clave_ir not in irs:
                nombre_ir = g(valores, "nombre_ir")
                if not nombre_ir:
                    alertas.append(crear_alerta(
                        "ir_sin_nombre",
                        f"IR '{codigo_ir}' sin nombre de indicador; se omitió.",
                        archivo_fuente=nombre_archivo, nombre_politica=nombre_politica,
                        codigo_ir=codigo_ir))
                else:
                    metas, m_pct = metas_de(fila_abs, metas_ir_cols)
                    mf, mf_pct = meta_final_de(fila_abs, "meta_final_ir")
                    av, av_ant, mv, mv_ant = calcular_vigencia(metas, anio_vigencia)
                    irs[clave_ir] = IndicadorResultado(
                        codigo_objetivo=extraer_codigo(g(valores, "objetivo"), niveles=1),
                        objetivo_especifico=g(valores, "objetivo"),
                        peso_objetivo_pct=g(valores, "peso_objetivo"),
                        codigo_ir=codigo_ir,
                        resultado_esperado=g(valores, "resultado"),
                        nombre_indicador=nombre_ir,
                        es_vigente=g(valores, "vigente_ir"),
                        peso_pct=g(valores, "peso_ir"),
                        formula=g(valores, "formula_ir"),
                        sector_responsable=g(valores, "sector_ir"),
                        entidad_responsable=g(valores, "entidad_ir"),
                        ods=g(valores, "ods"),
                        meta_ods=g(valores, "meta_ods"),
                        tipo_anualizacion=g(valores, "tipo_anual_ir"),
                        periodicidad=g(valores, "periodicidad_ir"),
                        valor_linea_base=g(valores, "lb_valor_ir"),
                        anio_linea_base=g(valores, "lb_anio_ir"),
                        fuente_linea_base=g(valores, "lb_fuente_ir"),
                        fecha_inicio=g(valores, "fecha_inicio_ir"),
                        fecha_fin=g(valores, "fecha_fin_ir"),
                        meta_final=mf,
                        escala_pct=m_pct or mf_pct,
                        metas_por_anio=metas,
                        anio_vigencia=av,
                        anio_vigencia_anterior=av_ant,
                        meta_vigencia_actual=mv,
                        meta_vigencia_anterior=mv_ant,
                    )

            # IP: una entrada por fila con código de producto.
            codigo_ip = extraer_codigo(g(valores, "producto"), niveles=3)
            if not codigo_ip:
                continue
            nombre_ip = g(valores, "nombre_ip")
            if not nombre_ip:
                alertas.append(crear_alerta(
                    "ip_sin_nombre",
                    f"IP '{codigo_ip}' sin nombre de indicador; se omitió.",
                    archivo_fuente=nombre_archivo, nombre_politica=nombre_politica,
                    codigo_ir=codigo_ir, codigo_ip=codigo_ip))
                continue
            metas, m_pct = metas_de(fila_abs, metas_ip_cols)
            mf, mf_pct = meta_final_de(fila_abs, "meta_final_ip")
            av, av_ant, mv, mv_ant = calcular_vigencia(metas, anio_vigencia)
            ips.append(IndicadorProducto(
                codigo_objetivo=extraer_codigo(g(valores, "objetivo"), niveles=1),
                codigo_ir=codigo_ir,
                codigo_ip=codigo_ip,
                producto_esperado=g(valores, "producto"),
                nombre_indicador=nombre_ip,
                es_vigente=g(valores, "vigente_ip"),
                peso_pct=g(valores, "peso_ip"),
                formula=g(valores, "formula_ip"),
                tipo_anualizacion=g(valores, "tipo_anual_ip"),
                periodicidad=g(valores, "periodicidad_ip"),
                valor_linea_base=g(valores, "lb_valor_ip"),
                anio_linea_base=g(valores, "lb_anio_ip"),
                fuente_linea_base=g(valores, "lb_fuente_ip"),
                fecha_inicio=g(valores, "fecha_inicio_ip"),
                fecha_fin=g(valores, "fecha_fin_ip"),
                meta_final=mf,
                escala_pct=m_pct or mf_pct,
                metas_por_anio=metas,
                anio_vigencia=av,
                anio_vigencia_anterior=av_ant,
                meta_vigencia_actual=mv,
                meta_vigencia_anterior=mv_ant,
                sector_responsable=g(valores, "sector_resp"),
                entidad_responsable=g(valores, "entidad_resp"),
                direccion_responsable=g(valores, "dir_resp"),
                sector_corresponsable=g(valores, "sector_corresp"),
                entidad_corresponsable=g(valores, "entidad_corresp"),
                direccion_corresponsable=g(valores, "dir_corresp"),
                objetivo_pdd=g(valores, "objetivo_pdd"),
                meta_pdd=g(valores, "meta_pdd"),
                proyecto_inversion=g(valores, "proyecto_inv"),
                enfoque_principal=g(valores, "enfoque_princ"),
                enfoque_secundario=g(valores, "enfoque_sec"),
            ))

            # Bloque financiero (formato antiguo): un registro por IP y año.
            for anio, grupo in financiero_cols:
                costo = gc(valores, grupo["costo_estimado"])
                recurso = gc(valores, grupo["recurso_disponible"])
                fuente = gc(valores, grupo["fuente_financiacion"])
                proyecto = gc(valores, grupo["codigo_proyecto"])
                if any(x is not None for x in (costo, recurso, fuente, proyecto)):
                    financiero.append(RegistroFinanciero(
                        codigo_ip=codigo_ip, anio=anio,
                        costo_estimado=costo, recurso_disponible=recurso,
                        fuente_financiacion=fuente, codigo_proyecto=proyecto,
                    ))

        # 4) Chequeos de consistencia (Fase 5): inconsistencias entre filas del
        #    mismo IR (sobre valores ORIGINALES) y códigos de IP duplicados.
        pares = list(zip((f for _, f in filas), snapshots))
        alertas.extend(chequear_consistencia_ir(
            pares, cols, metas_ir_cols, nombre_archivo, nombre_politica))
        alertas.extend(chequear_duplicados_ip(ips, nombre_archivo, nombre_politica))

        return list(irs.values()), ips, financiero, alertas
