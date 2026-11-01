# -*- coding: utf-8 -*-
"""
Hallazgo común de calidad y sus tres salidas.

``Hallazgo`` extiende ``HallazgoSeguimiento`` (los campos y el truncado de
``make_finding`` no cambian) con el código canónico de la regla, el objeto
observado (objetivo / IR / IP) y los campos que piden los consumidores:

- :meth:`as_finding`  → dict de la tabla ``alertas`` de alertas-seguimientos
  (heredado tal cual: el gate de paridad sigue en verde).
- :meth:`a_alerta`    → ``Alerta`` del plan (``res.alertas``,
  ``alertas_planes_accion.csv`` del pipeline).
- :meth:`a_observacion` → fila de ``observaciones_politica`` del tablero de
  sispp-gobierno (columnas :data:`COLS_OBSERVACION`).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..alertas import crear_alerta
from ..modelo import Alerta
from ..seguimiento.hallazgos import TIPOS_HALLAZGO, HallazgoSeguimiento
from .catalogo import (
    NIV_INDICADOR, NIV_POLITICA, NIV_PRODUCTO, NIV_RESULTADO, NIVEL_A_SEVERIDAD,
    SEVERIDAD_A_NIVEL, SEVERIDAD_A_OBSERVACION, CATALOGO_CALIDAD, Regla, regla_de_tipo,
)

# Columnas de ``observaciones_politica`` (sispp-gobierno, dashboard_pp/observaciones.py).
COLS_OBSERVACION = [
    "politica_key", "nombre_politica", "nivel", "indicador_key", "codigo",
    "tema", "observacion", "evidencia", "fuente", "accion", "responsable",
    "afecta_avance", "cortes", "severidad", "origen",
]

FUENTE_PLAN = "Plan de acción"
FUENTE_SEGUIMIENTO = "Formato de seguimiento"
FUENTE_CRUCE = "Plan de acción vs. formato de seguimiento"

_NIVEL_OBS = {NIV_POLITICA: "Política", "objetivo": "Objetivo", NIV_RESULTADO: "Resultado",
              NIV_PRODUCTO: "Producto", "archivo": "Archivo"}


@dataclass
class Hallazgo(HallazgoSeguimiento):
    """Un hallazgo de calidad: los campos de ``make_finding`` más los del catálogo."""
    regla: str = ""              # código canónico (CATALOGO_CALIDAD)
    aplica_a: str = ""           # plan | seguimiento | serie | entre_cargas | cruce | estructura_*
    nivel_objeto: str = ""       # politica | objetivo | resultado | producto | indicador | archivo
    cod_objetivo: str = ""
    cod_ir: str = ""
    cod_ip: str = ""
    accion: str = ""
    afecta_avance: str = ""      # texto para el analista («Sí, desde los cortes de 2026»)
    cortes: tuple = ()           # cortes con el problema (reglas de serie)
    fuente: str = ""             # «Plan de acción», «Formato de seguimiento»…
    tipo_indicador: str = ""     # 'producto' | 'resultado' (si se conoce)

    # ── compatibilidad con la Alerta del plan / HallazgoSeguimiento v1 ──
    @property
    def codigo_ip(self) -> str:
        if self.cod_ip:
            return self.cod_ip
        if self.aplica_a in ("plan", "estructura_plan"):
            return ""
        return self.codigo or ""

    @property
    def codigo_ir(self) -> str:
        return self.cod_ir or ""

    @property
    def codigo_objetivo(self) -> str:
        return self.cod_objetivo or ""

    @property
    def descripcion(self) -> str:
        """Etiqueta: la de ``make_finding`` para los tipos de la app (paridad);
        el nombre de la regla para los demás."""
        if self.tipo in TIPOS_HALLAZGO:
            return TIPOS_HALLAZGO[self.tipo]
        r = CATALOGO_CALIDAD.get(self.regla)
        return r.nombre if r else self.tipo

    @property
    def regla_catalogo(self) -> Regla:
        return CATALOGO_CALIDAD.get(self.regla) or regla_de_tipo(self.tipo, self.detalle)

    # ── salidas ──
    def a_alerta(self) -> Alerta:
        """``Alerta`` del plan (esquema de ``res.alertas`` y de
        ``alertas_planes_accion.csv``). El nivel sale de la severidad del hallazgo."""
        return crear_alerta(
            self.tipo, self.detalle, nivel=SEVERIDAD_A_NIVEL.get(self.severidad),
            archivo_fuente=self.archivo, nombre_politica=self.politica,
            codigo_objetivo=self.cod_objetivo, codigo_ir=self.cod_ir,
            codigo_ip=self.codigo_ip, campo=self.campo, valor=self.valor or None)

    def a_observacion(self, politica_key: str = "", responsable: str = "",
                      origen: str = "automática") -> dict:
        """Fila de ``observaciones_politica`` (:data:`COLS_OBSERVACION`).

        ``politica_key`` es la clave del pipeline; con ella se arma
        ``indicador_key`` = ``<politica_key>_<producto|resultado>_<codigo>``.
        Severidad: Error → Alta, Advertencia → Media, Info → Baja."""
        r = self.regla_catalogo
        codigo = self.codigo or self.cod_ip or self.cod_ir or self.cod_objetivo or ""
        tipo_ind = self.tipo_indicador or _tipo_por_codigo(codigo)
        nivel = r.nivel if r.nivel != NIV_INDICADOR else (tipo_ind or "producto")
        key = f"{politica_key}_{tipo_ind}_{codigo}" if politica_key and codigo and tipo_ind else ""
        evidencia = self.detalle or ""
        if self.val_base or self.val_nuevo:
            partes = [p for p in (self.val_base, self.val_nuevo) if p]
            evidencia = (evidencia + " " if evidencia else "") + "(" + " → ".join(partes) + ")"
        afecta = self.afecta_avance or ("Sí" if r.afecta_avance else "No")
        return {
            "politica_key": politica_key or "",
            "nombre_politica": self.politica or "",
            "nivel": _NIVEL_OBS.get(nivel, str(nivel).capitalize()),
            "indicador_key": key,
            "codigo": codigo,
            "tema": r.nombre,
            "observacion": r.descripcion,
            "evidencia": evidencia,
            "fuente": self.fuente or (FUENTE_PLAN if self.aplica_a.endswith("plan") else FUENTE_SEGUIMIENTO),
            "accion": self.accion or r.accion,
            "responsable": responsable or self.entidad or "",
            "afecta_avance": afecta,
            "cortes": ", ".join(str(c) for c in self.cortes) if self.cortes else (self.periodo or ""),
            "severidad": SEVERIDAD_A_OBSERVACION.get(self.severidad, "Baja"),
            "origen": origen,
        }


def _tipo_por_codigo(codigo: str) -> str:
    n = str(codigo or "").count(".")
    return "producto" if n >= 2 else ("resultado" if n == 1 else "")


# ─────────────────────────── adaptadores de entrada ───────────────────────────

def desde_alerta(alerta: Alerta, *, aplica_a: str = "plan", sector: str = "",
                 entidad: str = "", nombre: str = "", fuente: str = FUENTE_PLAN) -> Hallazgo:
    """``Alerta`` del plan (o estructural) → ``Hallazgo``. ``a_alerta()`` devuelve
    la misma alerta (ida y vuelta sin pérdida)."""
    r = regla_de_tipo(alerta.tipo, alerta.descripcion)
    codigo = alerta.codigo_ip or alerta.codigo_ir or alerta.codigo_objetivo or ""
    return Hallazgo(
        tipo=alerta.tipo, severidad=NIVEL_A_SEVERIDAD.get(alerta.nivel, "Info"),
        codigo=codigo, politica=alerta.nombre_politica or "", sector=sector or "",
        entidad=entidad or "", nombre=str(nombre or "")[:120], campo=alerta.campo or "",
        val_nuevo=str(alerta.valor)[:200] if alerta.valor else "", detalle=alerta.descripcion or "",
        archivo=alerta.archivo_fuente or "", regla=r.codigo, aplica_a=aplica_a,
        nivel_objeto=r.nivel, cod_objetivo=alerta.codigo_objetivo or "",
        cod_ir=alerta.codigo_ir or "", cod_ip=alerta.codigo_ip or "", accion=r.accion,
        fuente=fuente,
        tipo_indicador="producto" if alerta.codigo_ip else ("resultado" if alerta.codigo_ir else ""))


def desde_hallazgo_seguimiento(h: HallazgoSeguimiento, *, aplica_a: str = "",
                               fuente: str = FUENTE_SEGUIMIENTO) -> Hallazgo:
    """``HallazgoSeguimiento`` → ``Hallazgo``; ``as_finding()`` da el mismo dict."""
    if isinstance(h, Hallazgo):
        return h
    r = regla_de_tipo(h.tipo, h.detalle)
    return Hallazgo(
        tipo=h.tipo, severidad=h.severidad, codigo=h.codigo, politica=h.politica,
        sector=h.sector, entidad=h.entidad, nombre=h.nombre, campo=h.campo,
        val_base=h.val_base, val_nuevo=h.val_nuevo, periodo=h.periodo, detalle=h.detalle,
        archivo=h.archivo, regla=r.codigo, aplica_a=aplica_a or r.aplica_a,
        nivel_objeto=r.nivel, accion=r.accion, fuente=fuente,
        tipo_indicador=_tipo_por_codigo(h.codigo or ""))
