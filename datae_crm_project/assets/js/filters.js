const defaultState = {
  search: '',
  campus: 'Todos',
  supportType: 'Todos',
  supportStatus: 'Todos',
  quality: 'Todos',
};

export function createFilterState() {
  return { ...defaultState };
}

export function hydrateFilterOptions(records) {
  const campuses = ['Todos', ...new Set(records.map((r) => r.campus))].sort();
  const supportTypes = ['Todos', 'CIAC', 'Talleres', 'Mentorías', 'Atenciones', 'Sin apoyos'];
  const supportStatus = ['Todos', 'Con apoyo', 'Sin apoyo'];
  const quality = ['Todos', 'Con observaciones', 'Sin observaciones', 'Sin campus'];

  return { campuses, supportTypes, supportStatus, quality };
}

export function applyFilters(records, filters) {
  const search = filters.search.trim().toLowerCase();

  return records.filter((r) => {
    const matchesSearch =
      !search ||
      r.nombre.toLowerCase().includes(search) ||
      r.rut.toLowerCase().includes(search);

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
