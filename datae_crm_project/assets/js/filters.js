const defaultState = {
  search: '',
  campus: 'Todos',
  supportType: 'Todos',
  supportStatus: 'Todos',
  source: 'Todas',
};

export const normalizeText = (value = '') => value
  .toString()
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/\s+/g, ' ')
  .trim()
  .toLowerCase();

const normalizeRut = (value = '') => normalizeText(value).replace(/\./g, '');

const hasAnySupport = (row) => Number(row.total_apoyos || 0) > 0
  || Number(row.conteo_ciac || 0) > 0
  || Number(row.conteo_talleres || 0) > 0
  || Number(row.conteo_mentorias || 0) > 0
  || Number(row.conteo_atenciones || 0) > 0;

const supportTypePredicates = {
  ciac: (row) => Number(row.conteo_ciac || 0) > 0 || Boolean(row.ciac),
  talleres: (row) => Number(row.conteo_talleres || 0) > 0 || Boolean(row.talleres),
  mentorias: (row) => Number(row.conteo_mentorias || 0) > 0 || Boolean(row.mentorias),
  atenciones: (row) => Number(row.conteo_atenciones || 0) > 0 || Boolean(row.atenciones),
  'sin apoyos': (row) => !hasAnySupport(row),
};

export const createFilterState = () => ({ ...defaultState });
export const resetFilterState = () => ({ ...defaultState });

export function hydrateFilterOptions(records) {
  const campuses = ['Todos', ...new Set(records.map((row) => row.campus).sort((a, b) => a.localeCompare(b)))];
  const sources = ['Todas', ...new Set(records.flatMap((row) => row.fuentes_detectadas).sort((a, b) => a.localeCompare(b)))];

  return {
    campuses,
    supportTypes: ['Todos', 'CIAC', 'Talleres', 'Mentorías', 'Atenciones', 'Sin apoyos'],
    supportStatus: ['Todos', 'Con apoyo', 'Sin apoyo'],
    sources,
  };
}

function matchCampus(rowCampus, selectedCampus) {
  if (selectedCampus === 'Todos') return true;
  return normalizeText(rowCampus) === normalizeText(selectedCampus);
}

function matchSupportType(row, selectedType) {
  if (selectedType === 'Todos') return true;
  const predicate = supportTypePredicates[normalizeText(selectedType)];
  return predicate ? predicate(row) : true;
}

function matchSupportStatus(row, selectedStatus) {
  if (selectedStatus === 'Todos') return true;
  const normalizedStatus = normalizeText(selectedStatus);
  const withSupport = hasAnySupport(row);
  if (normalizedStatus === 'con apoyo') return withSupport;
  if (normalizedStatus === 'sin apoyo') return !withSupport;
  return true;
}

function matchSource(row, selectedSource) {
  if (selectedSource === 'Todas') return true;
  const normalizedSource = normalizeText(selectedSource);
  return (row.fuentes_detectadas || []).some((source) => normalizeText(source) === normalizedSource);
}

export function applyFilters(records, filters) {
  const search = normalizeText(filters.search);
  const rutSearch = normalizeRut(filters.search);

  return records.filter((row) => {
    const bySearch = !search || normalizeText(row.nombre).includes(search) || normalizeRut(row.rut).includes(rutSearch);
    const byCampus = matchCampus(row.campus, filters.campus);
    const byType = matchSupportType(row, filters.supportType);
    const byStatus = matchSupportStatus(row, filters.supportStatus);
    const bySource = matchSource(row, filters.source);

    return bySearch && byCampus && byType && byStatus && bySource;
  });
}
