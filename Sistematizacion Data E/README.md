# DATA-E 2025 · Pipeline de apoyos académicos (Key = RUT)

Este repositorio automatiza la **limpieza, validación y consolidación** de registros de apoyos académicos del programa **DATA-E 2025**.

**Regla principal:** el identificador (key) para integrar todas las fuentes es el **RUT**.

---

## Objetivo del pipeline

A partir de múltiples archivos Excel/CSV (talleres, atenciones, mentorías, CIAC, etc.), el pipeline:

1. Lee automáticamente los archivos desde `/data`
2. Normaliza el **RUT** a un formato estándar
3. Ejecuta validaciones de calidad de datos (QA)
4. Clasifica y agrega participaciones por tipo de actividad
5. Consolida resultados por campus usando las listas base
6. Genera salidas finales listas para entregar en `/output`

---

## Estructura del repositorio
