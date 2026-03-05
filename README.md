# DATA-E 2025 · Pipeline de apoyos académicos

Pipeline para consolidar apoyos por RUT con reglas de auditoría corregidas (mentorías, atenciones, CIAC, talleres, campus, RUT inválidos y trazabilidad por fuente).

## Ejecución

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

## Salidas

### Versionado (texto/CSV)
- `output/SAN_JOAQUIN_APOYOS_2025_FINAL.csv`
- `output/VITACURA_APOYOS_2025_FINAL.csv`
- `output/RUT_SIN_CAMPUS.csv`
- `output/auditoria_resumen_corregido.csv`
- `output/auditoria_detalle_corregido.csv`

### No versionado (binario)
- `./_artifacts/RESUMEN_DATAE_2025_CORREGIDO.xlsx`

> El script imprime en consola: `Excel generado en: <ruta>`.

## Qué valida el pipeline

- Normalización robusta de RUT: sin puntos, con guion y DV en mayúscula.
- Validación de RUT (cuerpo 7-8 dígitos + DV correcto).
- RUT inválidos excluidos de los consolidados y enviados a la hoja `RUT_INVALIDOS`.
- Atenciones individuales sumadas entre Katherine (`Total de sesiones`) y Gleudys (`N° de atenciones`) por RUT.
- Mentorías desde Gleudys (`Mentorías`) con conteo por filas por RUT.
- CIAC recalculado como conteo exacto de filas por RUT de CIAC SJ + CIAC VIT.
- Talleres sumados entre Proyecto Inicial S1 + S2 + Katherine Talleres.
- Regla de campus: padrón SJ/VIT > autodeclarado claro > `RUT_SIN_CAMPUS`.
- Trazabilidad técnica por columnas `SRC_*` y `SRC_FLAGS`.
