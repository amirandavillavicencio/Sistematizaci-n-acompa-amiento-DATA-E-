# DATA-E 2025 · Pipeline de apoyos académicos

Pipeline para consolidar apoyos por RUT con reglas corregidas de auditoría (mentorías, atenciones, CIAC, campus, RUT inválidos y trazabilidad por fuente).

## Ejecución

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## Qué genera

### Versionado (texto/CSV)
- `output/SAN_JOAQUIN_APOYOS_2025_FINAL.csv`
- `output/VITACURA_APOYOS_2025_FINAL.csv`
- `output/RUT_SIN_CAMPUS.csv`
- `output/auditoria_resumen_corregido.csv`
- `output/auditoria_detalle_corregido.csv`

### No versionado (binario)
- Excel consolidado en `./_artifacts/DATAE_APOYOS_2025_INFORME_CORREGIDO.xlsx`

La consola imprime siempre la ruta exacta del Excel generado.

## Validaciones que aplica

- Normalización y validación robusta de RUT (7-8 dígitos + DV válido).
- RUT inválidos se excluyen del consolidado y van a `auditoria_detalle_corregido.csv`.
- CIAC se calcula exclusivamente desde fuentes CIAC (sin falsos positivos por otras hojas).
- Atenciones individuales = `Katherine(total de sesiones)` + `Gleudys(N° de atenciones)`.
- Talleres = Proyecto Inicial S1 + Proyecto Inicial S2 + Katherine Talleres.
- Mentorías = filas de hoja `Mentorías` de Gleudys.
- Regla de campus: padrón > autodeclarado claro > `SIN_CAMPUS`.
- Columnas técnicas de trazabilidad por fuente: `SRC_*` y `SRC_FLAGS`.
