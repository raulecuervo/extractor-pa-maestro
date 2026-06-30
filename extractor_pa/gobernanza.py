# -*- coding: utf-8 -*-
"""
Gobernanza / triage persistente de alertas (B3).

Las reglas (V0–V18, consistencia, B2…) regeneran las alertas en CADA corrida.
Para que las decisiones humanas sobrevivan, cada alerta recibe una CLAVE
ESTABLE (hash de sus campos identitarios, SIN la descripción ni el nombre de la
política — que pueden cambiar de redacción) y su estado vive aparte en un store
JSON, con bitácora append-only para auditoría multi-operador.

Estados:  nueva (default, sin entrada) → en_gestion → resuelta | descartada.
          Volver a "nueva" elimina la entrada.

Autocierre: si una alerta DESAPARECE de la corrida (el dato se corrigió), deja
de mostrarse; su entrada en el store queda como historial. `reconciliar` la
reporta en `desaparecidas` para cerrarla explícitamente si se desea.

Diseño agnóstico de almacenamiento (heredado de `sispp-gobierno`,
`app/storage/alertas.py`): opera sobre el modelo canónico (`Alerta`) o sobre
dicts, sin pandas ni rutas fijas. El store es un archivo cuya ruta se inyecta.
"""

from __future__ import annotations

import getpass
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

ESTADOS_VALIDOS = ("nueva", "en_gestion", "resuelta", "descartada")
ESTADOS_PENDIENTES = ("nueva", "en_gestion")

# Campos que identifican una alerta entre corridas. `descripcion` y
# `nombre_politica` quedan FUERA a propósito: pueden cambiar de redacción sin
# que la alerta sea otra. Cada entrada acepta el nombre canónico (atributo de
# `Alerta`) y el alias del CSV legado (para interoperar con sispp-gobierno).
_CAMPOS_CLAVE = (
    ("archivo_fuente", "archivo_fuente"),
    ("tipo", "tipo_alerta"),
    ("codigo_objetivo", "codigo_objetivo"),
    ("codigo_ir", "codigo_ir"),
    ("codigo_ip", "codigo_ip"),
    ("campo", "campo"),
    ("valor", "valor_encontrado"),
)


def _leer_campo(alerta: Any, canonico: str, alias: str) -> str:
    """Lee un campo de un `Alerta`, un dict (claves canónicas o de CSV) o NaN."""
    val = None
    if isinstance(alerta, dict):
        val = alerta.get(canonico)
        if val is None:
            val = alerta.get(alias)
    else:
        val = getattr(alerta, canonico, None)
        if val is None:
            val = getattr(alerta, alias, None)
    if val is None:
        return ""
    # tolera NaN de pandas sin importar pandas
    if isinstance(val, float) and val != val:
        return ""
    return str(val).strip()


def clave_alerta(alerta: Any) -> str:
    """Hash estable (12 hex) de los campos identitarios de una alerta.

    Acepta un objeto `Alerta`, un dict canónico o un dict con los nombres del
    CSV de sispp-gobierno (`tipo_alerta`/`valor_encontrado`). Para los mismos
    valores identitarios produce la misma clave que `sispp-gobierno`.
    """
    partes = [_leer_campo(alerta, c, a) for c, a in _CAMPOS_CLAVE]
    crudo = "|".join(partes)
    return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:12]


# ── Item de triage / reconciliación ──────────────────────────────────────────

@dataclass
class ItemTriage:
    clave: str
    estado: str
    alerta: Any            # el `Alerta` (u objeto/dict original)


@dataclass
class Reconciliacion:
    """Estado de las alertas de una corrida frente al store persistente."""
    items: list = field(default_factory=list)          # list[ItemTriage]
    desaparecidas: list = field(default_factory=list)   # claves abiertas ausentes

    def por_estado(self) -> dict:
        out = {e: 0 for e in ESTADOS_VALIDOS}
        for it in self.items:
            out[it.estado] = out.get(it.estado, 0) + 1
        return out

    def pendientes(self) -> list:
        """Items en estado nueva o en_gestion (lo que requiere atención)."""
        return [it for it in self.items if it.estado in ESTADOS_PENDIENTES]

    def claves(self) -> set:
        return {it.clave for it in self.items}


# ── Store persistente ────────────────────────────────────────────────────────

class RegistroGobernanza:
    """Persiste el estado de cada alerta por su clave estable.

    `ruta_estado`: JSON {clave: {estado, nota, autor, fecha, resumen}}.
    `ruta_audit` : JSONL append-only (por defecto, junto al estado).
    Escrituras atómicas (os.replace) para no corromper ante escritura concurrente.
    """

    def __init__(self, ruta_estado, ruta_audit=None, autor: Optional[str] = None):
        self.ruta_estado = Path(ruta_estado)
        self.ruta_audit = (Path(ruta_audit) if ruta_audit is not None
                           else self.ruta_estado.with_name(
                               self.ruta_estado.stem + "_audit.jsonl"))
        self._autor = autor

    # -- lectura --
    def cargar(self) -> dict:
        if not self.ruta_estado.exists():
            return {}
        try:
            with open(self.ruta_estado, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def estado_de(self, clave: str, estados: Optional[dict] = None) -> str:
        estados = estados if estados is not None else self.cargar()
        entrada = estados.get(clave)
        if isinstance(entrada, dict) and entrada.get("estado") in ESTADOS_VALIDOS:
            return entrada["estado"]
        return "nueva"

    # -- escritura --
    def set_estado(self, claves, estado: str, nota: str = "",
                   resumen: str = "", autor: Optional[str] = None) -> int:
        """Aplica `estado` a todas las claves (acción en bloque).

        estado="nueva" elimina las entradas (vuelve al default).
        Devuelve cuántas claves cambió. Lanza ValueError si el estado no es válido.
        """
        if estado not in ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido: {estado!r}. "
                             f"Válidos: {list(ESTADOS_VALIDOS)}")
        claves = [str(c).strip() for c in (claves or []) if str(c).strip()]
        if not claves:
            return 0

        autor = autor or self._detectar_autor()
        estados = self.cargar()
        if estado == "nueva":
            for c in claves:
                estados.pop(c, None)
        else:
            base = {
                "estado": estado,
                "nota": (nota or "").strip(),
                "autor": autor,
                "fecha": datetime.now().isoformat(timespec="seconds"),
                "resumen": (resumen or "").strip()[:120],
            }
            for c in claves:
                estados[c] = dict(base)

        self._escribir_atomico(estados)
        self._append_audit({"evento": "set_estado", "estado": estado,
                            "n_alertas": len(claves), "claves": claves[:50],
                            "nota": (nota or "").strip(), "resumen": resumen,
                            "autor": autor})
        return len(claves)

    # -- reconciliación entre corridas --
    def reconciliar(self, alertas: Iterable) -> Reconciliacion:
        """Clasifica las alertas de una corrida frente al store.

        Cada alerta recibe su clave y estado. Las claves que estaban ABIERTAS
        (nueva/en_gestion) en el store pero NO aparecen en la corrida se listan
        en `desaparecidas` (candidatas a autocierre: el dato se corrigió).
        """
        estados = self.cargar()
        items, vistas = [], set()
        for al in alertas:
            c = clave_alerta(al)
            vistas.add(c)
            items.append(ItemTriage(clave=c, estado=self.estado_de(c, estados),
                                    alerta=al))
        desaparecidas = sorted(
            c for c, e in estados.items()
            if isinstance(e, dict)
            and e.get("estado") in ESTADOS_PENDIENTES
            and c not in vistas
        )
        return Reconciliacion(items=items, desaparecidas=desaparecidas)

    # -- helpers internos --
    def _escribir_atomico(self, datos: dict) -> None:
        self.ruta_estado.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta_estado.with_suffix(self.ruta_estado.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, self.ruta_estado)

    def _append_audit(self, evento: dict) -> None:
        self.ruta_audit.parent.mkdir(parents=True, exist_ok=True)
        evento = {**evento, "fecha": datetime.now().isoformat(timespec="seconds")}
        with open(self.ruta_audit, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")

    def _detectar_autor(self) -> str:
        if self._autor:
            return self._autor
        try:
            return getpass.getuser() or "operador"
        except Exception:
            return "operador"
