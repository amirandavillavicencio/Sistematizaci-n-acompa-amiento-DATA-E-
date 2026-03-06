const defaultState = {
  search: '',
  campus: 'Todos',
  supportType: 'Todos',
  supportStatus: 'Todos',
  missingCampus: 'Todos',
};

function normalizeText(value = '') {
  return value.toString().trim().toLowerCase();
}

function normalizeRut(value = '') {
  return value.toString().replace(/\./g, '').trim().toLowerCase();
}

export function createFilterState() {
  return { ...defaultState };
}

export function resetFilterState() {
  return { ...defaultState };
}

export function hydrateFilterOptions(records) {
  const campuses = ['Todos', ...new Set(records.map((row) => row.campus).sort((a, b) => a.localeCompare(b)))];

  return {
    campuses,
    supportTypes: ['Todos', 'CIAC', 'Talleres', 'Mentorías', 'Atenciones', 'Sin apoyos'],
    supportStatus: ['Todos', 'Con apoyo', 'Sin apoyo'],
    missingCampus: ['Todos', 'Solo sin campus', 'Solo con campus'],
  };
}

export function applyFilters(records, filters) {
  const search = normalizeText(filters.search);
  const searchRut = normalizeRut(search);

  return records.filter((row) => {
    const matchesSearch =
      !search || normalizeText(row.nombre).includes(search) || normalizeRut(row.rut).includes(searchRut);

    const matchesCampus = filters.campus === 'Todos' || row.campus === filters.campus;

    const matchesSupportType =
      filters.supportType === 'Todos' ||
      (filters.supportType === 'CIAC' && row.ciac > 0) ||
      (filters.supportType === 'Talleres' && row.talleres > 0) ||
      (filters.supportType === 'Mentorías' && row.mentorias > 0) ||
      (filters.supportType === 'Atenciones' && row.atenciones > 0) ||
      (filters.supportType === 'Sin apoyos' && row.total_apoyos === 0);

    const matchesStatus =
      filters.supportStatus === 'Todos' ||
      (filters.supportStatus === 'Con apoyo' && row.total_apoyos > 0) ||
      (filters.supportStatus === 'Sin apoyo' && row.total_apoyos === 0);

    const matchesMissingCampus =
      filters.missingCampus === 'Todos' ||
      (filters.missingCampus === 'Solo sin campus' && !row.tiene_campus) ||
      (filters.missingCampus === 'Solo con campus' && row.tiene_campus);

    return matchesSearch && matchesCampus && matchesSupportType && matchesStatus && matchesMissingCampus;
  });
}
