const defaultState = {
  search: '',
  campus: 'Todos',
  supportType: 'Todos',
  supportStatus: 'Todos',
  missingCampus: 'Todos',
  source: 'Todas',
};

const normalizeText = (value = '') => value.toString().trim().toLowerCase();
const normalizeRut = (value = '') => value.toString().replace(/\./g, '').trim().toLowerCase();

export const createFilterState = () => ({ ...defaultState });
export const resetFilterState = () => ({ ...defaultState });

export function hydrateFilterOptions(records) {
  const campuses = ['Todos', ...new Set(records.map((row) => row.campus).sort((a, b) => a.localeCompare(b)))];
  const sources = ['Todas', ...new Set(records.flatMap((row) => row.fuentes_detectadas).sort((a, b) => a.localeCompare(b)))];

  return {
    campuses,
    supportTypes: ['Todos', 'CIAC', 'Talleres', 'Mentorías', 'Atenciones', 'Sin apoyos'],
    supportStatus: ['Todos', 'Con apoyo', 'Sin apoyo'],
    missingCampus: ['Todos', 'Solo sin campus', 'Solo con campus'],
    sources,
  };
}

export function applyFilters(records, filters) {
  const search = normalizeText(filters.search);
  const rutSearch = normalizeRut(filters.search);

  return records.filter((row) => {
    const bySearch = !search || normalizeText(row.nombre).includes(search) || normalizeRut(row.rut).includes(rutSearch);
    const byCampus = filters.campus === 'Todos' || row.campus === filters.campus;

    const byType =
      filters.supportType === 'Todos'
      || (filters.supportType === 'CIAC' && row.conteo_ciac > 0)
      || (filters.supportType === 'Talleres' && row.conteo_talleres > 0)
      || (filters.supportType === 'Mentorías' && row.conteo_mentorias > 0)
      || (filters.supportType === 'Atenciones' && row.conteo_atenciones > 0)
      || (filters.supportType === 'Sin apoyos' && row.total_apoyos === 0);

    const byStatus =
      filters.supportStatus === 'Todos'
      || (filters.supportStatus === 'Con apoyo' && row.tiene_apoyo)
      || (filters.supportStatus === 'Sin apoyo' && !row.tiene_apoyo);

    const byMissingCampus =
      filters.missingCampus === 'Todos'
      || (filters.missingCampus === 'Solo sin campus' && row.sin_campus)
      || (filters.missingCampus === 'Solo con campus' && !row.sin_campus);

    const bySource = filters.source === 'Todas' || row.fuentes_detectadas.includes(filters.source);

    return bySearch && byCampus && byType && byStatus && byMissingCampus && bySource;
  });
}
