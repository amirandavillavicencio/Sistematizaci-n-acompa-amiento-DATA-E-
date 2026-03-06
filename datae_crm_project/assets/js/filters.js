const defaultState = {
  search: '',
  campus: 'Todos',
  supportType: 'Todos',
  supportStatus: 'Todos',
  quality: 'Todos',
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

export function hydrateFilterOptions(records) {
  const uniqueCampuses = [...new Set(records.map((r) => r.campus))].sort((a, b) => a.localeCompare(b));
  const campuses = ['Todos', ...uniqueCampuses];
  const supportTypes = ['Todos', 'CIAC', 'Talleres', 'Mentorías', 'Atenciones', 'Sin apoyos'];
  const supportStatus = ['Todos', 'Con apoyo', 'Sin apoyo'];
  const quality = ['Todos', 'Con observaciones', 'Sin observaciones', 'Sin campus'];

  return { campuses, supportTypes, supportStatus, quality };
}

export function applyFilters(records, filters) {
  const rawSearch = normalizeText(filters.search);
  const searchRut = normalizeRut(rawSearch);

  return records.filter((r) => {
    const matchesSearch =
      !rawSearch ||
      normalizeText(r.nombre).includes(rawSearch) ||
      normalizeRut(r.rut).includes(searchRut);

    const matchesCampus = filters.campus === 'Todos' || r.campus === filters.campus;

    const matchesSupportType =
      filters.supportType === 'Todos' ||
      (filters.supportType === 'CIAC' && r.ciac > 0) ||
      (filters.supportType === 'Talleres' && r.talleres > 0) ||
      (filters.supportType === 'Mentorías' && r.mentorias > 0) ||
      (filters.supportType === 'Atenciones' && r.atenciones > 0) ||
      (filters.supportType === 'Sin apoyos' && r.total_apoyos === 0);

    const matchesStatus =
      filters.supportStatus === 'Todos' ||
      (filters.supportStatus === 'Con apoyo' && r.total_apoyos > 0) ||
      (filters.supportStatus === 'Sin apoyo' && r.total_apoyos === 0);

    const hasObservations = (r.observaciones && r.observaciones.trim().length > 0) || r.issues_count > 0;
    const matchesQuality =
      filters.quality === 'Todos' ||
      (filters.quality === 'Con observaciones' && hasObservations) ||
      (filters.quality === 'Sin observaciones' && !hasObservations) ||
      (filters.quality === 'Sin campus' && !r.tiene_campus);

    return matchesSearch && matchesCampus && matchesSupportType && matchesStatus && matchesQuality;
  });
}

export function resetFilterState() {
  return { ...defaultState };
}
