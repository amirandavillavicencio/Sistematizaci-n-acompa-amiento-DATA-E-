# DATA-E CRM académico (estático para Vercel)

Aplicación web estática para consolidar apoyos académicos DATA-E con **entidad principal por estudiante** (lista base por campus), no por evento aislado.

## Lógica institucional implementada

1. **Listas base por campus (fuente maestra):**
   - `SAN_JOAQUIN_APOYOS_2025_FINAL.csv`
   - `VITACURA_APOYOS_2025_FINAL.csv`
2. **Fuentes complementarias incluidas en columnas `SRC_*`:**
   - Katherine: atenciones + talleres.
   - Gleudys: atenciones + talleres + mentorías.
3. **Talleres Proyecto Inicial (S1/S2):** sumados en `conteo_talleres` mediante `SRC_PI_S1_COUNT` + `SRC_PI_S2_COUNT`.
4. **CIAC:** consolidado desde `SRC_CIAC_COUNT`.
5. **RUT sin campus:** quedan en dataset/vista separada (`rut_sin_campus`) y en tabla dedicada en UI.
6. **Prioridad por conteos:** se exponen `conteo_*` por tipo de apoyo y además banderas booleanas derivadas.

> **Microgrupo no se considera** en la consolidación.

## Campos del consolidado por estudiante

`apoyos_consolidados.json` contiene para cada estudiante:

- `rut`, `nombre`, `campus`, `origen_base`, `presencia_lista_base`
- `ciac`, `talleres`, `mentorias`, `atenciones` (**booleanos**)
- `conteo_ciac`, `conteo_talleres`, `conteo_mentorias`, `conteo_atenciones` (**conteos**)
- `total_apoyos`, `tiene_apoyo`, `sin_campus`
- `observacion_calidad`, `fuentes_detectadas`, `issues_count`, `issue_types`

Además:
- `summary` con KPIs globales.
- `rut_sin_campus` para la vista separada.
- `meta.field_semantics` para trazabilidad de definición de campos.

## Estructura de la app

- `index.html`: layout principal CRM (KPIs, filtros, tablas, gráficos, detalle).
- `assets/js/data-loader.js`: carga JSON consolidado.
- `assets/js/filters.js`: filtros por búsqueda, campus, tipo, estado, sin campus y fuente.
- `assets/js/table.js`: tabla principal por estudiante + tabla separada RUT sin campus + export CSV.
- `assets/js/charts.js`: gráficos ejecutivos con Chart.js.
- `assets/js/ui.js`: KPIs, detalle y contadores.
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

## Deploy en Vercel

- Proyecto estático (sin build step obligatorio).
- Root directory: `datae_crm_project`.
- Rutas relativas (`./assets/...`, `./data/...`) compatibles con Vercel.
