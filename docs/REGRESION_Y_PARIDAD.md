# Fase 7 — Regresión (golden files) y paridad con los legados

Asegura que el extractor maestro (a) no sufra **regresiones** entre versiones y
(b) produzca resultados **equivalentes** a los extractores legados — la evidencia
para migrar con confianza.

## A. Golden files (regresión del maestro)

- **Huella estable** por archivo (`extractor_pa/regresion.py`): códigos IR/IP,
  conteos, años y alertas por tipo (sin campos no deterministas como el año de
  vigencia).
- **Corpus** representativo (`tests/corpus.py`): 5 planes (nuevo, antiguo CTI,
  étnico, grandes) + 3 seguimientos `.xlsb`.
- **Golden** en `tests/golden/<clave>.json` (generados con `scripts/gen_golden.py`).
- **Prueba** `tests/test_golden.py`: re-ejecuta el maestro y compara contra la
  huella esperada; falla ante cualquier deriva. Se salta si el archivo no está.

Actualizar tras un cambio intencional:
```
python scripts/gen_golden.py
```

## B. Paridad con los extractores legados

`scripts/paridad_legados.py` compara los **conjuntos de códigos** de indicadores
extraídos por el maestro vs el legado, sobre los mismos archivos reales.

### Resultado plan (maestro vs `extractor-planes-accion`)
- **8/8** archivos con el **mismo número** de indicadores.
- **7/8** con conjuntos de códigos **idénticos**.
- 1 diferencia (**PA_Bicicleta**): el maestro extrae `5.1`, el legado `5`. La
  celda real es `"5. 1 Aumento de la productividad…"` (con espacio); el maestro
  **normaliza correctamente** a `5.1` (confirmado porque sus productos son
  `5.1.1`–`5.1.6`), mientras el legado se queda en `5`. → **el maestro es más
  correcto**; paridad efectiva **8/8**.

### Resultado seguimiento (maestro vs `alertas-seguimientos`)
- **6/6** archivos con conjuntos de códigos **idénticos** (maestro por anclas
  dinámicas vs legado por columnas fijas → mismos resultados).

## Conclusión

El maestro **reproduce** los resultados de los extractores legados (e incluso
corrige un caso de código con espacio). Junto con los golden files, esto da la
base para la **Fase 8 — migración**: reemplazar cada extractor legado por la
librería, comparando su salida contra el golden antes de retirarlo.
