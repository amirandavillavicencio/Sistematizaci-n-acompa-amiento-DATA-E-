const DATA_PATH = './data/apoyos_consolidados.json';

export async function loadConsolidatedData() {
  const response = await fetch(DATA_PATH, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`No se pudo cargar ${DATA_PATH}: ${response.status}`);
  }

  const payload = await response.json();
  if (!payload || !Array.isArray(payload.records)) {
    throw new Error('El JSON consolidado no contiene el arreglo records.');
  }

  return {
    generatedAt: payload.meta?.generated_at ?? null,
    sourceFiles: payload.meta?.source_files ?? [],
    inconsistencies: payload.quality_summary ?? {},
    records: payload.records.map((item, index) => ({
      id: item.id ?? index + 1,
      rut: item.rut ?? '',
      nombre: item.nombre ?? 'Sin nombre',
      campus: item.campus ?? 'Sin Campus',
      ciac: Number(item.ciac || 0),
      talleres: Number(item.talleres || 0),
      mentorias: Number(item.mentorias || 0),
      atenciones: Number(item.atenciones || 0),
      total_apoyos: Number(item.total_apoyos || 0),
      estado: item.estado ?? 'Sin apoyo',
      tiene_campus: Boolean(item.tiene_campus),
      calidad: item.calidad ?? 'Sin observaciones',
      observaciones: item.observaciones ?? '',
      issues_count: Number(item.issues_count || 0),
    })),
  };
}
