# DATA-E CRM académico (estático)

Aplicación web tipo CRM para seguimiento de apoyos académicos 2025 en DATA-E, desplegable como sitio estático (Vercel o cualquier hosting de archivos).

## Estructura del proyecto

```text
/
├── index.html
├── README.md
├── requirements.txt
├── vercel.json
├── assets/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── app.js
│       ├── data-loader.js
│       ├── filters.js
│       ├── table.js
│       ├── charts.js
│       └── ui.js
├── data/
│   ├── apoyos_consolidados.json
│   ├── DATEapoyosFInal.xlsx
│   ├── REPORTE_CALIDAD_DATOS.csv
│   ├── RESUMEN_DATAE_2025.csv
│   ├── RUT_SIN_CAMPUS.csv
│   ├── SAN_JOAQUIN_APOYOS_2025_FINAL.csv
│   └── VITACURA_APOYOS_2025_FINAL.csv
└── scripts/
    └── build_data.py
```

## Cómo funciona la app

- **Fuente principal frontend:** `./data/apoyos_consolidados.json`.
- **Tecnologías:** Bootstrap 5 (layout), Tabulator (tabla CRM), Chart.js (gráficos), JavaScript modular ES.
- **Comportamiento CRM:**
  - filtros globales (búsqueda, campus, tipo de apoyo, estado, calidad)
  - KPIs ejecutivos actualizados por filtros
  - tabla principal con paginación, orden y exportación CSV
  - panel de detalle por estudiante (click en fila)
  - gráficos de apoyo y calidad

## Fuente de datos y consolidación

El JSON consolidado se crea con `scripts/build_data.py`, integrando:

- `SAN_JOAQUIN_APOYOS_2025_FINAL.csv`
- `VITACURA_APOYOS_2025_FINAL.csv`
- `RUT_SIN_CAMPUS.csv`
- `REPORTE_CALIDAD_DATOS.csv`

Además, en metadatos se deja trazabilidad con:
- `RESUMEN_DATAE_2025.csv`
- `DATEapoyosFInal.xlsx`

### Re-generar `apoyos_consolidados.json`

1. Crear entorno y dependencias:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. Ejecutar script:

```bash
python scripts/build_data.py
```

3. Resultado:

- Se actualiza `data/apoyos_consolidados.json` con:
  - `meta` (fecha, fuentes, conteo)
  - `quality_summary`
  - `records` (1 registro consolidado por RUT)

## Inconsistencias detectadas y documentadas

Durante la consolidación se detectan y/o reflejan estas inconsistencias de origen:

1. **RUT sin campus asociado**
   - Existen registros en `RUT_SIN_CAMPUS.csv` (ej. casos sin clasificación campus).
2. **Nombres faltantes en registros sin campus**
   - Algunos RUT vienen sin `Nombre`; se normaliza como `Sin nombre`.
3. **Issues de calidad explícitos**
   - `REPORTE_CALIDAD_DATOS.csv` contiene múltiples tipos de issue (p. ej. `REGISTRO_SIN_RUT`).
4. **Campos heterogéneos de apoyo**
   - En columnas de apoyo existen marcas tipo `X` y/o valores numéricos; la consolidación usa conteos `SRC_*` para consistencia.

## Despliegue en Vercel

Este proyecto es estático:

1. Importar repo en Vercel.
2. Configurar **Root Directory** al directorio del proyecto (`datae_crm_project`, si corresponde en tu repo).
3. No requiere build command.
4. Publicar.

`vercel.json` mantiene `cleanUrls: true` y rutas relativas (`./assets/...`, `./data/...`) compatibles con el despliegue.

## Desarrollo local rápido

Puedes abrir `index.html` con un servidor estático para evitar restricciones de `fetch` en `file://`:

```bash
python -m http.server 8000
```

Luego visitar: `http://localhost:8000`.
