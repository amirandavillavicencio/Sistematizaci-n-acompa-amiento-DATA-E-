# Consolidado de apoyos DATA-E 2025 (estático para Vercel)

Aplicación web estática para visualizar el **consolidado oficial DATA-E 2025** con entidad principal por estudiante y base oficial por campus (San Joaquín / Vitacura).

## Lógica institucional implementada

1. **Listas base por campus (fuente maestra):**
   - `SAN_JOAQUIN_APOYOS_2025_FINAL.csv`
   - `VITACURA_APOYOS_2025_FINAL.csv`
2. **Fuentes complementarias solo completan columnas en estudiantes existentes de base:**
   - Katherine: atenciones + talleres.
   - Gleudys: atenciones + talleres + mentorías.
   - Proyecto Inicial S1/S2: talleres.
   - CIAC: apoyo académico CIAC.
3. **RUT sin campus:** se visualizan en sección separada (`RUT_SIN_CAMPUS.csv` / `rut_sin_campus`), sin mezclarse con el consolidado oficial por campus.
4. **Prioridad por conteos:** cuando hay conteo fiable se usa número; si no, marca de participación consolidada.
5. **Microgrupo no se considera** en la consolidación.

## Archivos principales

- `data/apoyos_consolidados.json`: payload de visualización (records, summary, quality_summary, rut_sin_campus).
- `data/SAN_JOAQUIN_APOYOS_2025_consolidado.csv`: consolidado oficial campus San Joaquín.
- `data/VITACURA_APOYOS_2025_consolidado.csv`: consolidado oficial campus Vitacura.
- `data/RUT_SIN_CAMPUS.csv`: registros externos sin campus identificado.
- `data/MAESTRO_APOYOS_DATA_E_2025.xlsx`: maestro oficial.

## Estructura de la app

- `index.html`: encabezado ejecutivo, KPIs, consolidado filtrable, vistas por campus, sección sin campus, metodología, calidad y exportaciones.
- `assets/js/data-loader.js`: carga JSON consolidado.
- `assets/js/filters.js`: filtros por búsqueda, campus, tipo, estado y fuente.
- `assets/js/table.js`: tabla principal y tablas compactas por campus/sin campus + export CSV filtrado.
- `assets/js/charts.js`: gráficos ejecutivos (sin zoom/pan/toolbar invasiva).
- `assets/js/ui.js`: KPIs, detalle y controles de calidad.
- `scripts/build_data.py`: regeneración del consolidado.

## Regenerar consolidado

```bash
cd datae_crm_project
python scripts/build_data.py
```

## Levantar local

```bash
cd datae_crm_project
python -m http.server 8000
```

Abrir: `http://localhost:8000`

## Probar exportaciones (CSV y Excel)

1. Abrir la app local o en Vercel.
2. En bloque **Exportaciones oficiales**, usar cada botón de descarga.
3. Validar que se descargan:
   - `SAN_JOAQUIN_APOYOS_2025_consolidado.csv`
   - `VITACURA_APOYOS_2025_consolidado.csv`
   - `RUT_SIN_CAMPUS.csv`
   - `MAESTRO_APOYOS_DATA_E_2025.xlsx`
4. Botón **Exportar CSV filtrado** descarga el consolidado visible según filtros actuales.

## Deploy en Vercel

- Proyecto estático (sin build step obligatorio).
- Root directory: `datae_crm_project`.
- Rutas relativas (`./assets/...`, `./data/...`) compatibles con Vercel.
