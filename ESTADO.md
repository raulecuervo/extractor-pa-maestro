# Estado del proyecto — extractor-pa

Estado y pendientes vigentes. Los planes de trabajo anteriores (fases, hitos,
runbook de cierre de la migración) están en [`docs/historico/`](docs/historico/);
los cambios por versión, en [`CHANGELOG.md`](CHANGELOG.md).

## Hecho

- **Plan de acción (.xlsx):** formato nuevo y antiguo con un solo motor. El
  antiguo incluye bloque financiero y las plantillas 2021–2025, que traen los
  encabezados una fila más abajo, o 15 más abajo cuando la cabecera lista los
  corresponsables. Celdas combinadas en 4 capas con ascensión de la fila vigente,
  año de vigencia, fichas técnicas, objetivos como entidad, consistencia y
  reglas V0–V18. Opcionales: catálogo oficial (V4), gobernanza de alertas y
  decisiones humanas.
- **Seguimiento (.xlsb y .xlsx 3.4):** extracción, cruce con el plan,
  consolidación por período, métricas al corte (PAF, TID, PAV, MES, brecha), las
  15 alertas de consistencia y el semáforo con los umbrales de cada aplicativo.
- **Salidas:** JSON, CSV, Excel y DataFrame, por plan o consolidadas; tablero HTML.
- **Migración (Fase 8):** los aplicativos extraen con el maestro.
  `python scripts/pines_consumidores.py` muestra qué versión fija cada uno.
- **Calidad:** CI con ruff y pruebas en Python 3.10–3.14; contrato con los
  consumidores (`tests/test_contrato_consumidores.py`); golden de seguimiento sobre
  todas las políticas; cada tag publica su wheel en un Release.

## Pendiente

Prioridad: 🔴 alta · 🟠 media · 🟢 baja.

| # | Pendiente | Prio |
|---|---|:--:|
| 1 | **Alinear los pines de los aplicativos.** Hoy van de v0.9.11 a v0.17.0, y con las fórmulas del seguimiento cambiando entre versiones, dos aplicativos muestran cifras distintas para el mismo indicador. Subir juntos los que se comparan entre sí, revisando en el CHANGELOG las versiones marcadas «Cambia cifras». | 🔴 |
| 2 | **Golden de planes:** sus claves dependen del nombre del archivo y el corpus se renombró, así que hoy los 47 planes se saltan (se corrige aparte, rama `fix/golden-claves-robustas`). | 🔴 |
| 3 | **sispp-gobierno y sispp-SDP:** retirar `dashboard_pp/parche_extractor.py` cuando fijen la versión que tolera los prefijos de código «P1.1.1», «R1.1» y «OE1.» (rama `fix/codigo-prefijo-tipo`). | 🟠 |
| 4 | **alertas-seguimientos:** importar `suma_metas_anteriores_suma` en lugar del alias privado `_suma_metas_prev_suma`, y los helpers (`safe_float`, `parse_period`, `limites_de_semaforo`) desde `extractor_pa.seguimiento`. El alias se mantiene mientras tanto. | 🟢 |
| 5 | **Correr la suite de cada aplicativo en su entorno** con la versión que fije, y luego **retirar los extractores legados** que quedaron como respaldo. | 🟠 |
| 6 | **Decidir el destino de las capas sin consumidores** (reglas V0–V18, V4, gobernanza, decisiones, tablero, CLI): adoptarlas en los aplicativos o dejarlas como experimentales (así figuran en el README). | 🟠 |
| 7 | Alertas operativas y cualitativas (vencimiento, RN-CUL, Q001–Q003) y adaptador ORM: viven en los aplicativos de operación. | 🟢 |
| 8 | Limitación conocida: las metas anuales y `meta_final` del IR se leen de su primera fila física, no de la fila vigente promovida (sin pérdida numérica en la auditoría). | 🟢 |
| 9 | Seguimiento: respaldo a posiciones fijas si faltan las anclas y un único criterio de escala. | 🟢 |

## Documentos

- `README.md`: uso, instalación, estabilidad por capa y política de versiones.
- `docs/CONSUMIDORES.md`: qué aplicativo usa qué funcionalidad, versión fijada y archivos de entrada.
- `docs/CATALOGO_ALERTAS.md`: catálogo de alertas (regenerable con `scripts/gen_catalogo.py`).
- `docs/MEJORAS_Y_LIMITACIONES.md`, `docs/REGRESION_Y_PARIDAD.md`, `docs/REVERSA_v0.12.0.md`.
- Reportes de calidad del dato por política: `../_codigo_extraido_pp/`.
