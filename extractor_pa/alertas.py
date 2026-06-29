# -*- coding: utf-8 -*-
"""
Constructor de alertas, centralizado en el catálogo consolidado.

`crear_alerta(tipo, descripcion, ...)` toma el **nivel** del catálogo
(`catalogo.CATALOGO`) según el `tipo`, de modo que la nomenclatura ERROR /
ADVERTENCIA / INFO es consistente en todo el sistema y vive en un solo lugar.
Se puede forzar el nivel con `nivel=...` si hace falta.
"""

from __future__ import annotations

from typing import Any, Optional

from .catalogo import nivel_de
from .modelo import Alerta


def crear_alerta(
    tipo: str,
    descripcion: str,
    *,
    nivel: Optional[str] = None,
    archivo_fuente: str = "",
    nombre_politica: Optional[str] = None,
    codigo_objetivo: Optional[str] = None,
    codigo_ir: Optional[str] = None,
    codigo_ip: Optional[str] = None,
    campo: Optional[str] = None,
    valor: Any = None,
) -> Alerta:
    """Crea una `Alerta`. El nivel se toma del catálogo salvo que se fuerce."""
    return Alerta(
        nivel=nivel or nivel_de(tipo),
        tipo=tipo,
        descripcion=descripcion,
        archivo_fuente=archivo_fuente or "",
        nombre_politica=nombre_politica or "",
        codigo_objetivo=codigo_objetivo or "",
        codigo_ir=codigo_ir or "",
        codigo_ip=codigo_ip or "",
        campo=campo or "",
        valor="" if valor is None else str(valor),
    )
