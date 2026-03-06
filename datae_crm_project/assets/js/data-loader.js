const DATA_FILE = './data/apoyos_consolidados.json';

function toInt(value) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeRut(value = '') {
  return value.toString().replace(/\./g, '').trim().toUpperCase();
}

function normalizeRecord(raw, index) {
  const conteoCiac = toInt(raw.conteo_ciac);
  const conteoTalleres = toInt(raw.conteo_talleres);
  const conteoMentorias = toInt(raw.conteo_mentorias);
  const conteoAtenciones = toInt(raw.conteo_atenciones);
  const total = toInt(raw.total_apoyos) || conteoCiac + conteoTalleres + conteoMentorias + conteoAtenciones;

  return {
    id: toInt(raw.id) || index + 1,
    rut: normalizeRut(raw.rut),
    nombre: raw.nombre || 'Sin nombre',
    campus: raw.campus || 'Sin Campus',
    origen_base: raw.origen_base || 'Sin base campus',
    presencia_lista_base: Boolean(raw.presencia_lista_base),
    ciac: Boolean(raw.ciac),
    talleres: Boolean(raw.talleres),
    mentorias: Boolean(raw.mentorias),
    atenciones: Boolean(raw.atenciones),
    conteo_ciac: conteoCiac,
    conteo_talleres: conteoTalleres,
    conteo_mentorias: conteoMentorias,
    conteo_atenciones: conteoAtenciones,
    total_apoyos: total,
    tiene_apoyo: Boolean(raw.tiene_apoyo ?? total > 0),
    sin_campus: Boolean(raw.sin_campus),
    estado: raw.estado || (total > 0 ? 'Con apoyo' : 'Sin apoyo'),
    observacion_calidad: raw.observacion_calidad || '',
    fuentes_detectadas: Array.isArray(raw.fuentes_detectadas) ? raw.fuentes_detectadas : [],
    issues_count: toInt(raw.issues_count),
    issue_types: Array.isArray(raw.issue_types) ? raw.issue_types : [],
  };
}

export async function loadConsolidatedData() {
  const response = await fetch(DATA_FILE, { cache: 'no-store' });
  if (!response.ok) throw new Error(`No se pudo cargar ${DATA_FILE}: ${response.status}`);

  const payload = await response.json();
  if (!payload || !Array.isArray(payload.records)) {
    throw new Error('Estructura inválida de apoyos_consolidados.json');
  }

  const records = payload.records.map((row, index) => normalizeRecord(row, index));
  const missingCampus = Array.isArray(payload.rut_sin_campus)
    ? payload.rut_sin_campus.map((row, index) => normalizeRecord(row, index))
    : records.filter((row) => row.sin_campus);

  return {
    generatedAt: payload.meta?.generated_at || new Date().toISOString(),
    summary: payload.summary || {},
    qualitySummary: payload.quality_summary || {},
    records,
    missingCampus,
  };
}
