# DATA-E CRM académico (estático y desplegable en Vercel)

Mini CRM académico para seguimiento de apoyos DATA-E. Está construido como aplicación estática con JavaScript modular y consume datos desde `./data/`.

## Qué incluye

- KPIs dinámicos de operación académica.
- Filtros globales (nombre/RUT, campus, tipo de apoyo, con/sin apoyo y registros sin campus).
- Tabla CRM principal con ordenamiento, paginación, búsqueda global (por filtro), exportación CSV y botón de detalle.
- Panel de detalle por estudiante con observaciones de calidad.
- Gráficos de apoyo por campus, tipo de apoyo, estado de apoyo y registros sin campus.

## Stack

- **Bootstrap 5 (CDN)** para layout y componentes.
- **Chart.js (CDN)** para visualizaciones.
- **JavaScript ES Modules** sin dependencias pesadas adicionales.

## Estructura relevante

```text
datae_crm_project/
├── index.html
├── vercel.json
├── assets/
│   ├── css/styles.css
│   └── js/
│       ├── app.js
│       ├── data-loader.js
│       ├── filters.js
│       ├── table.js
│       ├── charts.js
│       └── ui.js
├── data/
│   ├── apoyos_consolidados.json
│   ├── SAN_JOAQUIN_APOYOS_2025_FINAL.csv
│   ├── VITACURA_APOYOS_2025_FINAL.csv
│   ├── RUT_SIN_CAMPUS.csv
│   └── REPORTE_CALIDAD_DATOS.csv
└── scripts/build_data.py
```

## Flujo de datos (prioridad y fallback)

1. Frontend intenta cargar **`./data/apoyos_consolidados.json`** (fuente prioritaria).
2. Si el JSON no existe o no cumple estructura mínima, frontend usa fallback y consolida en runtime desde:
   - `SAN_JOAQUIN_APOYOS_2025_FINAL.csv`
   - `VITACURA_APOYOS_2025_FINAL.csv`
   - `RUT_SIN_CAMPUS.csv`
   - `REPORTE_CALIDAD_DATOS.csv`

## Script de consolidación

`python scripts/build_data.py`

### Qué hace

- Valida columnas esperadas de los CSV de campus.
- Normaliza RUT y nombres.
- Consolida por RUT en un único registro por estudiante.
- Calcula métricas (`ciac`, `talleres`, `mentorias`, `atenciones`, `total_apoyos`).
- Integra observaciones desde `SRC_FLAGS` y `REPORTE_CALIDAD_DATOS.csv`.
- Genera `data/apoyos_consolidados.json` con:
  - `meta`
  - `quality_summary`
  - `records`

## Inconsistencias de origen tratadas

- **RUT sin campus**: se mantiene como `Sin Campus`.
- **Nombres vacíos**: se normaliza a `Sin nombre`.
- **Campos de conteo con formatos heterogéneos**: se convierten de forma segura a entero (`safe_int`).
- **Calidad de datos**: se agregan issues por RUT y se concatenan detalles para contexto operativo.

## Desarrollo local

Para evitar restricciones de `fetch` en `file://`, levantar un servidor estático:

```bash
cd datae_crm_project
python -m http.server 8000
```

Abrir: `http://localhost:8000`

## Despliegue en Vercel

- Proyecto estático (sin build).
- Configurar root directory en `datae_crm_project`.
- Rutas relativas (`./assets/...`, `./data/...`) compatibles con Vercel.
