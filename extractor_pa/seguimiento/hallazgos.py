# -*- coding: utf-8 -*-
"""
Catálogo y modelo de hallazgos de seguimiento (capa 2 de la convergencia).

Copia fiel del catálogo de ``alertas-seguimientos/validation/catalog.py``.
``HallazgoSeguimiento.as_finding()`` reproduce EXACTAMENTE el shape del
``make_finding`` de producción (incluidos los truncados ``[:120]``/``[:200]``
y el campo ``descripcion`` = etiqueta del catálogo, con el mensaje específico
en ``detalle``). Ese dict es el contrato de la tabla ``alertas`` de
Alertas-Seguimientos y del gate de paridad ``comparar_alertas.py``.

Compatibilidad: expone como propiedades los atributos de la antigua ``Alerta``
que retornaba ``validacion_seg`` v1 (``nivel``, ``valor``, ``codigo_ip``,
``codigo_ir``), para que los consumidores internos (scripts, tablero) sigan
funcionando sin cambios.
"""

from __future__ import annotations

from dataclasses import dataclass

UMBRAL_AVANCE = 1.25  # 125%

TIPOS_HALLAZGO = {
    "ERROR_ESTABILIDAD":           "Error – Campo inmutable modificado",
    "ERROR_PONDERACION_OBLIGATORIA": "Error – Indicador vigente sin ponderación",
    "ERROR_RETROACTIVO":           "Error – Valor histórico modificado",
    "ERROR_NO_NUMERICO":           "Error – Reporte cuantitativo con valor no numérico",
    "ADVERTENCIA_AVANCE":          "Advertencia – Avance supera meta + 25%",
    "ADVERTENCIA_SECTOR_ENTIDAD":  "Advertencia – El sector del archivo no es el oficial de la entidad",
    "ADVERTENCIA_CUAL":            "Advertencia – Cualitativo vacío (Vigente)",
    "ADVERTENCIA_ESCALA":          "Advertencia – Incoherencia de escala reporte vs meta",
    "ADVERTENCIA_LIMITE_VIG":      "Advertencia – Reporte/suma vigencia supera 125% meta programada",
    "ADVERTENCIA_ACUM_META_VIG":   "Advertencia – Acumulado supera meta acumulada de la vigencia",
    "ADVERTENCIA_ACUM_META_FIN":   "Advertencia – Acumulado supera meta final",
    "ADVERTENCIA_META_SIN_REP":    "Advertencia – Existe meta para la vigencia pero no hay reporte",
    "ADVERTENCIA_REP_SIN_META":    "Advertencia – Existe reporte pero la meta es 0 o no existe",
    "ADVERTENCIA_PCT_HASTA_VIG":   "Advertencia – % Avance hasta la vigencia fuera de rango (< 50% o > 125%)",
    "ADVERTENCIA_DISCREPANCIA_PCT": "Advertencia – % Avance vigencia reportado difiere del calculado (acumulado / meta anual)",
    "INFO_IND_NUEVO":              "Info – Indicador nuevo (no existía en el archivo base cargado, se creará automáticamente)",
    "INFO_IND_FALTANTE":           "Info – Indicador faltante (existía en base pero no aparece en este archivo)",
}

SEVERIDAD = {
    "ERROR_ESTABILIDAD":           "Error",
    "ERROR_PONDERACION_OBLIGATORIA": "Error",
    "ADVERTENCIA_SECTOR_ENTIDAD":  "Advertencia",
    "ERROR_RETROACTIVO":           "Error",
    "ERROR_NO_NUMERICO":           "Error",
    "ADVERTENCIA_AVANCE":          "Advertencia",
    "ADVERTENCIA_CUAL":            "Advertencia",
    "ADVERTENCIA_ESCALA":          "Advertencia",
    "ADVERTENCIA_LIMITE_VIG":      "Advertencia",
    "ADVERTENCIA_ACUM_META_VIG":   "Advertencia",
    "ADVERTENCIA_ACUM_META_FIN":   "Advertencia",
    "ADVERTENCIA_META_SIN_REP":    "Advertencia",
    "ADVERTENCIA_REP_SIN_META":    "Advertencia",
    "ADVERTENCIA_PCT_HASTA_VIG":   "Advertencia",
    "ADVERTENCIA_DISCREPANCIA_PCT": "Advertencia",
    "INFO_IND_NUEVO":              "Info",
    "INFO_IND_FALTANTE":           "Info",
}

_NIVEL_DE_SEVERIDAD = {"Error": "ERROR", "Advertencia": "ADVERTENCIA", "Info": "INFO"}


@dataclass
class HallazgoSeguimiento:
    """Un hallazgo de validación de seguimiento (shape de ``make_finding``)."""
    tipo: str
    severidad: str = ""
    codigo: str = ""
    politica: str = ""
    sector: str = ""
    entidad: str = ""
    nombre: str = ""           # ya truncado a 120, como make_finding
    campo: str = ""
    val_base: str = ""         # ya truncado a 200, como make_finding
    val_nuevo: str = ""        # ya truncado a 200, como make_finding
    periodo: str = ""
    detalle: str = ""
    archivo: str = ""          # 'file_nuevo' en el finding

    @property
    def descripcion(self) -> str:
        """Etiqueta del catálogo (campo ``descripcion`` de make_finding)."""
        return TIPOS_HALLAZGO.get(self.tipo, self.tipo)

    # ── compatibilidad con la Alerta de validacion_seg v1 ──
    @property
    def nivel(self) -> str:
        return _NIVEL_DE_SEVERIDAD.get(self.severidad, "INFO")

    @property
    def codigo_ip(self) -> str:
        return self.codigo or ""

    @property
    def codigo_ir(self) -> str:
        return ""

    @property
    def valor(self) -> str:
        if self.val_base and self.val_nuevo:
            return f"{self.val_base} | {self.val_nuevo}"
        return self.val_nuevo or self.val_base

    def as_finding(self) -> dict:
        """Dict con el shape EXACTO de ``make_finding`` (gate de paridad)."""
        return {
            "tipo": self.tipo,
            "severidad": self.severidad,
            "descripcion": self.descripcion,
            "codigo": self.codigo,
            "politica": self.politica,
            "sector": self.sector,
            "entidad": self.entidad,
            "nombre": self.nombre,
            "campo": self.campo,
            "val_base": self.val_base,
            "val_nuevo": self.val_nuevo,
            "periodo": self.periodo,
            "detalle": self.detalle,
            "file_nuevo": self.archivo,
        }


def crear_hallazgo(tipo, *, codigo=None, politica=None, sector=None, entidad=None,
                   nombre=None, campo=None, val_base=None, val_nuevo=None,
                   periodo=None, detalle=None, archivo=None) -> HallazgoSeguimiento:
    """Factory con la MISMA semántica de coerción/truncado de ``make_finding``.

    Los campos identitarios (codigo/politica/sector/entidad) se pasan CRUDOS —
    make_finding no los coerciona, así que un ``None`` se conserva como ``None``
    (paridad byte a byte verificada por el gate de MS-32b); ``nombre`` se trunca
    a 120 y los valores a 200; los opcionales vacíos quedan como ``""``."""
    return HallazgoSeguimiento(
        tipo=tipo,
        severidad=SEVERIDAD[tipo],
        codigo=codigo,
        politica=politica,
        sector=sector,
        entidad=entidad,
        nombre=(nombre or "")[:120],
        campo=campo or "",
        val_base=str(val_base)[:200] if val_base is not None else "",
        val_nuevo=str(val_nuevo)[:200] if val_nuevo is not None else "",
        periodo=periodo or "",
        detalle=detalle or "",
        archivo=archivo or "",
    )
