const DATA_FILES = {
  consolidatedJson: './data/apoyos_consolidados.json',
  sanJoaquin: './data/SAN_JOAQUIN_APOYOS_2025_FINAL.csv',
  vitacura: './data/VITACURA_APOYOS_2025_FINAL.csv',
  sinCampus: './data/RUT_SIN_CAMPUS.csv',
  calidad: './data/REPORTE_CALIDAD_DATOS.csv',
};

const REQUIRED_FIELDS = ['rut', 'nombre', 'campus', 'ciac', 'talleres', 'mentorias', 'atenciones'];

function parseCsv(text) {
  const rows = [];
  let current = '';
  let row = [];
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      row.push(current);
      current = '';
    } else if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && nextChar === '\n') i += 1;
      row.push(current);
      if (row.some((value) => value.trim().length > 0)) rows.push(row);
      row = [];
      current = '';
    } else {
      current += char;
    }
  }

  if (current.length > 0 || row.length > 0) {
    row.push(current);
    if (row.some((value) => value.trim().length > 0)) rows.push(row);
  }

  if (!rows.length) return [];

  const headers = rows[0].map((h) => h.trim());
  return rows.slice(1).map((values) => {
    const item = {};
    headers.forEach((header, index) => {
      item[header] = (values[index] ?? '').trim();
    });
    return item;
  });
}

function normalizeRut(value = '') {
  return value.toString().replace(/\./g, '').trim().toUpperCase();
}

function cleanName(value = '') {
  const normalized = value.toString().trim();
  return normalized || 'Sin nombre';
}

function toCount(value) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeRecord(record, index) {
  const ciac = toCount(record.ciac);
  const talleres = toCount(record.talleres);
  const mentorias = toCount(record.mentorias);
  const atenciones = toCount(record.atenciones);
  const totalApoyos = toCount(record.total_apoyos) || ciac + talleres + mentorias + atenciones;

  return {
    id: toCount(record.id) || index + 1,
    rut: normalizeRut(record.rut),
    nombre: cleanName(record.nombre),
    campus: cleanName(record.campus),
    tiene_campus: typeof record.tiene_campus === 'boolean' ? record.tiene_campus : cleanName(record.campus) !== 'Sin Campus',
    ciac,
    talleres,
    mentorias,
    atenciones,
    total_apoyos: totalApoyos,
    estado: totalApoyos > 0 ? 'Con apoyo' : 'Sin apoyo',
    calidad: record.calidad || 'Sin observaciones',
    observaciones: record.observaciones || '',
    issues_count: toCount(record.issues_count),
    issue_types: Array.isArray(record.issue_types) ? record.issue_types : [],
  };
}

function validateConsolidatedJson(payload) {
  if (!payload || !Array.isArray(payload.records)) return false;
  if (!payload.records.length) return true;
  return REQUIRED_FIELDS.every((field) => field in payload.records[0]);
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`No se pudo cargar ${url}: ${response.status}`);
  }
  return response.json();
}

async function fetchCsv(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`No se pudo cargar ${url}: ${response.status}`);
  }
  const text = await response.text();
  return parseCsv(text);
}

function buildQualityMap(rows) {
  return rows.reduce((acc, row) => {
    const rut = normalizeRut(row.rut_norm || row.rut_raw || '');
    if (!rut) return acc;
    if (!acc[rut]) acc[rut] = { count: 0, details: [] };
    acc[rut].count += 1;
    if (row.details) acc[rut].details.push(row.details);
    return acc;
  }, {});
}

function mergeCampusRows(accumulator, rows, campus) {
  rows.forEach((row) => {
    const rut = normalizeRut(row.RUT);
    if (!rut) return;

    if (!accumulator[rut]) {
      accumulator[rut] = {
        rut,
        nombre: 'Sin nombre',
        campus,
        tiene_campus: campus !== 'Sin Campus',
        ciac: 0,
        talleres: 0,
        mentorias: 0,
        atenciones: 0,
      };
    }

    const item = accumulator[rut];
    if (item.nombre === 'Sin nombre' && row.Nombre?.trim()) item.nombre = row.Nombre.trim();

    item.ciac += toCount(row.SRC_CIAC_COUNT);
    item.talleres += toCount(row.SRC_KATH_TALLER_COUNT) + toCount(row.SRC_PI_S1_COUNT) + toCount(row.SRC_PI_S2_COUNT);
    item.mentorias += toCount(row.SRC_GLEU_MENT_COUNT);
    item.atenciones += toCount(row.SRC_KATH_ATENC_COUNT) + toCount(row.SRC_GLEU_ATENC_COUNT);
  });
}

async function loadFromCsvFallback() {
  const [sanRows, vitRows, sinCampusRows, qualityRows] = await Promise.all([
    fetchCsv(DATA_FILES.sanJoaquin),
    fetchCsv(DATA_FILES.vitacura),
    fetchCsv(DATA_FILES.sinCampus),
    fetchCsv(DATA_FILES.calidad),
  ]);

  const grouped = {};
  mergeCampusRows(grouped, sanRows, 'San Joaquín');
  mergeCampusRows(grouped, vitRows, 'Vitacura');
  mergeCampusRows(grouped, sinCampusRows, 'Sin Campus');

  const qualityMap = buildQualityMap(qualityRows);

  const records = Object.values(grouped).map((record, index) => {
    const quality = qualityMap[record.rut] || { count: 0, details: [] };
    return normalizeRecord({
      ...record,
      id: index + 1,
      total_apoyos: record.ciac + record.talleres + record.mentorias + record.atenciones,
      observaciones: quality.details.join(' | '),
      issues_count: quality.count,
      calidad: quality.count > 0 ? 'Con observaciones' : 'Sin observaciones',
    }, index);
  });

  return {
    generatedAt: new Date().toLocaleString('es-CL'),
    source: 'CSV fallback',
    records,
  };
}

export async function loadConsolidatedData() {
  try {
    const payload = await fetchJson(DATA_FILES.consolidatedJson);
    if (!validateConsolidatedJson(payload)) {
      throw new Error('El JSON consolidado no cumple estructura mínima.');
    }

    const records = payload.records.map((record, index) => normalizeRecord(record, index));
    return {
      generatedAt: payload.meta?.generated_at || new Date().toISOString(),
      source: 'JSON consolidado',
      records,
    };
  } catch (error) {
    console.warn('Fallo carga de JSON consolidado, usando fallback CSV.', error);
    return loadFromCsvFallback();
  }
}
