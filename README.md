# DATA-E 2025 · Pipeline de apoyos académicos (Key = RUT)

Este repositorio automatiza la **limpieza, validación y consolidación** de registros de apoyos académicos del programa **DATA-E 2025**.

**Regla principal:** el identificador (key) para integrar todas las fuentes es el **RUT** normalizado.

---

## Objetivo del pipeline

A partir de múltiples archivos Excel/CSV (talleres, atenciones, mentorías, CIAC, etc.), el pipeline:

1. Lee automáticamente los archivos desde `/data`
2. Normaliza el **RUT** a un formato estándar (`########-X`)
3. Ejecuta validaciones de calidad de datos (QA)
4. Clasifica y agrega participaciones por tipo de actividad
5. Consolida resultados por campus usando las listas base
6. Genera salidas finales listas para entregar en `/output`

---

## Estructura del repositorio

- `data/`
- `output/`
- `main.py`
- `requirements.txt`
- `README.md`

---

## Ejecución

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

---

## Archivos de salida esperados

- `output/SAN_JOAQUIN_APOYOS_2025_FINAL.csv`
- `output/VITACURA_APOYOS_2025_FINAL.csv`
- `output/RUT_SIN_CAMPUS.csv`
- `output/REPORTE_CALIDAD_DATOS.csv`
- `output/RESUMEN_DATAE_2025.csv`
- `output/datae_apoyos_2025.db` (SQLite con tablas `san_joaquin_apoyos`, `vitacura_apoyos`, `rut_sin_campus`, `reporte_calidad`)

Las bases finales contienen estas columnas:

- `RUT`
- `Nombre`
- `Apoyo_Academico_CIAC`
- `Talleres`
- `Mentorias`
- `Atenciones_Individuales`
