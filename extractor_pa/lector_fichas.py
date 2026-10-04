# -*- coding: utf-8 -*-
"""
Lectura de las FICHAS TÉCNICAS (Fase 4a).

En el formato del plan, cada indicador puede tener una hoja propia con su ficha
técnica (metodología, unidad de medida, fuentes, días de rezago, descripción y
observaciones). El nombre de la hoja varía entre versiones del formato:
  «F IR#1.1», «Ficha técnica IR#1.1», «Ficha técnica IP 1.1.1.», …

Implementación portada de sispp-sdis (`leer_fichas`), la más tolerante del
análisis comparativo:
- Localiza el código tras «IR»/«IP» con una regex flexible (cualquier separador).
- Lee los campos de texto por su RÓTULO en la columna 1.
- Detecta la unidad de medida por la casilla marcada con «x» (incluido «Otro/¿cuál?»).

Devuelve {codigo: {metodologia, unidad_medida, fuente_datos, dias_rezago,
descripcion, observaciones}}; el pipeline enlaza cada ficha a su IR/IP por código.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from .utilidades import _norm


# Detección del CÓDIGO en el nombre de la hoja de ficha. Las plantillas reales
# usan convenciones muy distintas; el código (N.N para IR, N.N.N para IP) puede ir:
#   - tras «Ficha técnica IR#/IP#»  (BTI, Discapacidad)
#   - tras «F IR#/IP#»              (Juventud: «F IR#1.1.», «F IP#1.1.1.»)
#   - tras «R.»/«P.» o «R »/«P »    (Cultos, Salud Mental)
#   - tras «IR_»/«IP_» (guion bajo) (Pobreza, Talento Humano)
#   - al inicio, sin prefijo        (LEO «1.1.1. Desc», Hábitat «1.1.10»)
# «Ficha» puede venir abreviada como «F» (Juventud). La regex se ancla al inicio del
# nombre: sin esa abreviatura, la «F» suelta impedía reconocer las 136 fichas de ese
# plan y todos sus indicadores quedaban «sin ficha técnica». La «F» abreviada exige un
# espacio después, para no confundir un nombre que simplemente empieza por «F».
_RE_CODIGO_FICHA = re.compile(
    r"^\s*"
    r"(?:(?:ficha|f(?=\s))\s*(?:t[eé]cnica|de\s*producto)?\s*)?"   # «Ficha»/«F» (técnica/de producto) opcional
    r"(?:i[rp]|[rp])?"                                  # prefijo IR/IP o R/P opcional
    r"\s*[#:._\-]?\s*"                                  # separador opcional (incluye «_»)
    r"(\d+(?:\.\d+){1,2})\b",                           # código N.N (IR) o N.N.N (IP)
    re.I,
)

# Hojas que NUNCA son una ficha de indicador (se descartan antes de extraer código).
_HOJAS_NO_FICHA = ("plan de acc", "desplegable", "instructivo", "version")


def codigo_de_hoja_ficha(nombre: str) -> Optional[str]:
    """Devuelve el código (N.N / N.N.N) si el nombre de hoja es una ficha, o None.

    Tolera todas las convenciones de nombre observadas en los planes reales."""
    n = _norm(nombre)
    if any(k in n for k in _HOJAS_NO_FICHA):
        return None
    m = _RE_CODIGO_FICHA.match(str(nombre).strip())
    if not m:
        return None
    return m.group(1).rstrip(".")

# Campos de texto: (clave_modelo, palabra_clave_normalizada_del_rótulo).
_ROTULOS = [
    ("metodologia", "metodologia de medicion"),
    ("descripcion", "descripcion"),
    ("fuente_datos", "fuentes de informacion"),
    ("dias_rezago", "dias de rezago"),
    ("observaciones", "observaciones"),
]


def _texto(valor: Any) -> Optional[str]:
    if valor is None:
        return None
    s = re.sub(r"\s+", " ", str(valor)).strip()
    return s or None


def _a_int(valor: Any) -> Optional[int]:
    """Primer entero contenido en el texto (p. ej. '30 días' -> 30)."""
    if valor is None:
        return None
    m = re.search(r"-?\d+", str(valor))
    return int(m.group(0)) if m else None


# El bloque «Unidad de medida» de la ficha es una cuadrícula: cada fila trae varias
# opciones, cada una con su casilla a la derecha (la col 1 es el rótulo de la sección):
#
#     col 3        col 4   col 5        col 6   col 8                     col 9
#     Kilómetros   [ ]     kilos        [ ]     Tasa                      [ ]
#     Hectáreas    [ ]     Metros       [ ]     Unidad productiva rural   [ ]
#     Personas     [ ]     Porcentaje   [x]     otro                      [ ]
#     ¿Cuál?  ______
_COLS_UNIDAD = range(2, 13)
_ES_OTRO = ("otro", "otra")


def _es_marca(valor: Any) -> bool:
    return valor is not None and str(valor).strip().lower() == "x"


def _opcion_marcada(ws, r: int, c: int) -> Optional[str]:
    """Etiqueta de la opción a la que pertenece la «x» de (r, c): la celda con texto más
    cercana a su IZQUIERDA en la misma fila (la casilla va a la derecha de su opción);
    si no hay ninguna, la más cercana a la derecha."""
    for cc in list(range(c - 1, _COLS_UNIDAD.start - 1, -1)) + list(range(c + 1, _COLS_UNIDAD.stop)):
        valor = ws.cell(row=r, column=cc).value
        if _es_marca(valor):
            continue
        cand = _texto(valor)
        if cand:
            return cand
    return None


def _leer_unidad(ws) -> Optional[str]:
    """Unidad de medida de la ficha.

    Layout observado en planes reales (SDP gobierno): bajo el rótulo «Unidad de
    medida» hay una cuadrícula de opciones y una fila «¿Cuál?» para la unidad
    personalizada. La unidad seleccionada se determina así:
      1) Si alguna opción está marcada con «x», esa opción es la unidad: la que
         está pegada a la casilla marcada (ver `_opcion_marcada`). Si la marcada
         es «otro», la unidad es la respuesta escrita junto a «¿Cuál?».
      2) Si no hay marca, se toma la respuesta escrita junto a «¿Cuál?» (unidad
         libre, p. ej. «Puntaje», «Componentes»).
    El bloque se acota hasta el siguiente rótulo (Territorialización/Enfoque)
    para no invadir otras secciones de la ficha.

    Hasta la 0.19.0 la marca solo se buscaba en las columnas 1 a 6 y se devolvía
    primero la etiqueta de la columna 3: con «Porcentaje» marcado (casilla en la
    col 6) la ficha entregaba «Personas», y las opciones de la tercera columna
    («Tasa», «Unidad productiva rural») no se leían."""
    fila_u = None
    for r in range(1, 16):
        v = ws.cell(row=r, column=1).value
        if v and "unidad de medida" in _norm(v):
            fila_u = r
            break
    if fila_u is None:
        return None

    # Acotar el bloque: desde fila_u hasta antes de la siguiente sección.
    r_fin = fila_u + 8
    for r in range(fila_u + 1, fila_u + 10):
        etiqueta = _norm(ws.cell(row=r, column=1).value)
        if etiqueta and ("territorializ" in etiqueta or "enfoque" in etiqueta):
            r_fin = r - 1
            break

    def respuesta_a_cual() -> Optional[str]:
        """Lo escrito junto a «¿Cuál?» (unidad personalizada)."""
        for r in range(fila_u, r_fin + 1):
            for c in range(1, 7):
                v = ws.cell(row=r, column=c).value
                if v and "cual" in _norm(v):
                    for cc in range(c + 1, c + 5):
                        vr = _texto(ws.cell(row=r, column=cc).value)
                        if vr and not _es_marca(vr):
                            return vr
        return None

    # 1) Opción marcada con «x». Si hay varias marcas manda la primera en orden de
    #    lectura; una marca en «otro» remite a la respuesta de «¿Cuál?».
    for r in range(fila_u, r_fin + 1):
        for c in _COLS_UNIDAD:
            if not _es_marca(ws.cell(row=r, column=c).value):
                continue
            opcion = _opcion_marcada(ws, r, c)
            if not opcion:
                continue
            n = _norm(opcion)
            if n in _ES_OTRO or "cual" in n:
                libre = respuesta_a_cual()
                if libre:
                    return libre
                continue
            return opcion

    # 2) Sin marca: respuesta a «¿Cuál?».
    return respuesta_a_cual()


def leer_fichas(wb) -> dict[str, dict]:
    """Recorre las hojas de ficha técnica y devuelve {codigo: campos}."""
    fichas: dict[str, dict] = {}
    for nombre in wb.sheetnames:
        codigo = codigo_de_hoja_ficha(nombre)
        if not codigo:
            continue
        ws = wb[nombre]
        datos: dict = {}

        # Campos de texto por rótulo en la columna 1 (filas 1-40).
        for r in range(1, 41):
            rotulo = ws.cell(row=r, column=1).value
            if not rotulo:
                continue
            nr = _norm(rotulo)
            for clave, palabra in _ROTULOS:
                if clave in datos or palabra not in nr:
                    continue
                valor = _texto(ws.cell(row=r, column=2).value)
                if valor:
                    datos[clave] = valor

        # dias_rezago a entero.
        if "dias_rezago" in datos:
            datos["dias_rezago"] = _a_int(datos["dias_rezago"])

        unidad = _leer_unidad(ws)
        if unidad:
            datos["unidad_medida"] = unidad

        if datos:
            fichas[codigo] = datos
    return fichas


# Campos de la ficha que se copian al modelo del indicador.
_CAMPOS_FICHA = ["metodologia", "unidad_medida", "fuente_datos",
                 "dias_rezago", "descripcion", "observaciones"]


def enriquecer_con_fichas(indicadores, fichas: dict, atributo_codigo: str) -> int:
    """Copia los campos de la ficha a cada indicador que coincida por código.

    `atributo_codigo` es 'codigo_ir' o 'codigo_ip'. Devuelve cuántos se enriquecieron."""
    n = 0
    for ind in indicadores:
        cod = getattr(ind, atributo_codigo, None)
        ficha = fichas.get(cod) if cod else None
        if not ficha:
            continue
        for campo in _CAMPOS_FICHA:
            if ficha.get(campo) is not None and getattr(ind, campo, None) is None:
                setattr(ind, campo, ficha[campo])
        n += 1
    return n
