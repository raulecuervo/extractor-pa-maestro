# -*- coding: utf-8 -*-
"""
Decisiones humanas de normalización de entidad/sector (F2).

Complementa B1 (`catalogo_oficial`): mientras B1 **sugiere** normalizaciones con
fuzzy, este módulo **persiste la decisión humana aprobada** y la **reaplica** de
forma determinista en cada corrida — sin depender del fuzzy ni del catálogo.

Flujo:  B1 sugiere  →  un humano decide (aprobar / nombre_nuevo / ignorar /
        eliminar)  →  `RegistroDecisiones` lo guarda  →  `aplicar_decisiones`
        reescribe el modelo canónico en cada extracción futura.

Store JSON  {valor_original: {accion, nombre_final, decidido_por, fecha}}  con
bitácora JSONL append-only (auditoría multi-operador), escritura atómica.
Destilado de `sispp-gobierno`, `app/storage/decisiones.py`; agnóstico de la app.
"""

from __future__ import annotations

import getpass
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

ACCIONES_VALIDAS = ("aprobar", "ignorar", "eliminar", "nombre_nuevo")

# Campos del modelo canónico (IR/IP) sobre los que se reaplican las decisiones.
CAMPOS_ENTIDAD = ("sector_responsable", "entidad_responsable")


class RegistroDecisiones:
    """Persiste decisiones sobre valores de entidad/sector y las reaplica.

    `ruta`      : JSON {valor_original: {accion, nombre_final, decidido_por, fecha}}.
    `ruta_audit`: JSONL append-only (por defecto, junto al JSON).
    """

    def __init__(self, ruta, ruta_audit=None, autor: Optional[str] = None):
        self.ruta = Path(ruta)
        self.ruta_audit = (Path(ruta_audit) if ruta_audit is not None
                           else self.ruta.with_name(self.ruta.stem + "_audit.jsonl"))
        self._autor = autor

    # -- lectura --
    def cargar(self) -> dict:
        if not self.ruta.exists():
            return {}
        try:
            with open(self.ruta, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def contar(self) -> int:
        return len(self.cargar())

    def obtener(self, valor_original: str) -> Optional[dict]:
        return self.cargar().get((valor_original or "").strip())

    # -- escritura --
    def guardar(self, valor_original: str, accion: str, nombre_final: str = "",
                autor: Optional[str] = None) -> None:
        """Registra una decisión sobre `valor_original`. Lanza ValueError si la
        acción no es válida o falta `nombre_final` cuando se requiere."""
        if accion not in ACCIONES_VALIDAS:
            raise ValueError(f"Acción inválida: {accion!r}. "
                             f"Válidas: {list(ACCIONES_VALIDAS)}")
        if not valor_original or not valor_original.strip():
            raise ValueError("valor_original no puede estar vacío")
        if accion in ("aprobar", "nombre_nuevo") and not nombre_final.strip():
            raise ValueError(f"acción {accion!r} requiere nombre_final no vacío")

        autor = autor or self._detectar_autor()
        decision = {"accion": accion, "nombre_final": nombre_final.strip(),
                    "decidido_por": autor,
                    "fecha": datetime.now().isoformat(timespec="seconds")}
        decisiones = self.cargar()
        decisiones[valor_original.strip()] = decision
        self._escribir_atomico(decisiones)
        self._append_audit({"evento": "decidir",
                            "valor_original": valor_original.strip(), **decision})

    def eliminar(self, valor_original: str, autor: Optional[str] = None) -> bool:
        """Elimina la decisión sobre `valor_original`. True si existía."""
        decisiones = self.cargar()
        clave = (valor_original or "").strip()
        if clave not in decisiones:
            return False
        decisiones.pop(clave)
        self._escribir_atomico(decisiones)
        self._append_audit({"evento": "deshacer", "valor_original": clave,
                            "decidido_por": autor or self._detectar_autor(),
                            "fecha": datetime.now().isoformat(timespec="seconds")})
        return True

    # -- proyección para reaplicación --
    def como_mapa(self) -> dict:
        """{valor_original: reemplazo} donde reemplazo es:
          str  → nombre a aplicar (aprobar / nombre_nuevo)
          None → ignorar (no cambiar)
          ""   → eliminar (vaciar el campo)
        """
        salida = {}
        for valor_original, d in self.cargar().items():
            accion = d.get("accion", "")
            if accion == "ignorar":
                salida[valor_original] = None
            elif accion == "eliminar":
                salida[valor_original] = ""
            elif accion in ("aprobar", "nombre_nuevo"):
                nombre = (d.get("nombre_final") or "").strip()
                if nombre:
                    salida[valor_original] = nombre
        return salida

    def aprobar_sugerencias(self, sugerencias, autor: Optional[str] = None) -> int:
        """Registra como `aprobar` las sugerencias de B1
        (`sugerencias_normalizacion`): dicts con `original`/`sugerido`.
        Devuelve cuántas decisiones nuevas se guardaron."""
        n = 0
        for s in sugerencias or []:
            orig, sug = s.get("original"), s.get("sugerido")
            if orig and sug and str(orig).strip():
                self.guardar(str(orig), "aprobar", str(sug), autor=autor)
                n += 1
        return n

    # -- helpers internos --
    def _escribir_atomico(self, datos: dict) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.ruta.with_suffix(self.ruta.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp, self.ruta)

    def _append_audit(self, evento: dict) -> None:
        self.ruta_audit.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta_audit, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento, ensure_ascii=False) + "\n")

    def _detectar_autor(self) -> str:
        if self._autor:
            return self._autor
        try:
            return getpass.getuser() or "operador"
        except Exception:
            return "operador"


def aplicar_decisiones(resultado, registro: RegistroDecisiones,
                       campos=CAMPOS_ENTIDAD) -> int:
    """Reaplica in-place las decisiones aprobadas sobre `sector_responsable` /
    `entidad_responsable` de los IR/IP del `resultado`. Devuelve cuántos campos
    cambió. Determinista (coincidencia exacta por valor, tolerante a espacios);
    no usa fuzzy ni catálogo. Complementa `aplicar_normalizacion` de B1."""
    mapa = registro.como_mapa()
    if not mapa:
        return 0
    n = 0
    grupos = (resultado.indicadores_resultado, resultado.indicadores_producto)
    for inds in grupos:
        for x in inds:
            for campo in campos:
                val = getattr(x, campo, None)
                if val is None:
                    continue
                clave = str(val).strip()
                if clave in mapa:
                    reemplazo = mapa[clave]
                    if reemplazo is None:            # ignorar
                        continue
                    if str(val) != str(reemplazo):
                        setattr(x, campo, reemplazo)  # nombre nuevo o "" (eliminar)
                        n += 1
    return n
