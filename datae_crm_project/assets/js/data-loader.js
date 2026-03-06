const DATA_FILES = {
  sanJoaquin: './data/SAN_JOAQUIN_APOYOS_2025_FINAL.csv',
  vitacura: './data/VITACURA_APOYOS_2025_FINAL.csv',
  sinCampus: './data/RUT_SIN_CAMPUS.csv',
  calidad: './data/REPORTE_CALIDAD_DATOS.csv',
};

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
      if (char === '\r' && nextChar === '\n') {
        i += 1;
      }
      row.push(current);
      const hasValues = row.some((value) => value.trim().length > 0);
      if (hasValues) rows.push(row);
      row = [];
      current = '';
    } else {
      current += char;
    }
  }

  if (current.length > 0 || row.length > 0) {
    row.push(current);
    const hasValues = row.some((value) => value.trim().length > 0);
    if (hasValues) rows.push(row);
  }

  if (!rows.length) return [];

  const headers = rows[0].map((h) => h.trim());
  return rows.slice(1).map((values) => {
    const record = {};
    headers.forEach((header, idx) => {
      record[header] = (values[idx] ?? '').trim();
    });
    return record;
  });
}

function normalizeRut(value = '') {
  return value.toString().replace(/\./g, '').trim().toUpperCase();
}

function toCount(value) {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function pickName(currentName, nextName) {
  if (currentName && currentName !== 'Sin nombre') return currentName;
  if (nextName) return nextName;
  return currentName || 'Sin nombre';
}

function campusFromLabel(label) {
  if (label === 'SAN_JOAQUIN') return 'San Joaquín';
  if (label === 'VITACURA') return 'Vitacura';
  return 'Sin Campus';
}

async function fetchCsv(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`No se pudo cargar ${url}: ${response.status}`);
  }
  const text = await response.text();
  return parseCsv(text);
}

function buildQualityMap(qualityRows) {
  return qualityRows.reduce((acc, row) => {
    const rut = normalizeRut(row.rut_norm || row.rut_raw || '');
    if (!rut) return acc;

    if (!acc[rut]) {
      acc[rut] = { count: 0, details: [] };
    }

    acc[rut].count += 1;
    if (row.details) {
      acc[rut].details.push(row.details);
    }

    return acc;
  }, {});
}

function mergeCampusRows(groupedRecords, rows, campusLabel) {
  rows.forEach((row) => {
    const rut = normalizeRut(row.RUT);
    if (!rut) return;

    if (!groupedRecords[rut]) {
      groupedRecords[rut] = {
        id: rut,
        rut,
        nombre: 'Sin nombre',
        campus: campusFromLabel(campusLabel),
        ciac: 0,
        talleres: 0,
        mentorias: 0,
        atenciones: 0,
        total_apoyos: 0,
        estado: 'Sin apoyo',
        tiene_campus: campusLabel !== 'SIN_CAMPUS',
        calidad: 'Sin observaciones',
        observaciones: '',
        issues_count: 0,
      };
    }

    const target = groupedRecords[rut];
    target.nombre = pickName(target.nombre, row.Nombre?.trim());

    if (target.campus === 'Sin Campus' && campusLabel !== 'SIN_CAMPUS') {
      target.campus = campusFromLabel(campusLabel);
      target.tiene_campus = true;
    }

    target.ciac += toCount(row.SRC_CIAC_COUNT);
    target.talleres += toCount(row.SRC_KATH_TALLER_COUNT) + toCount(row.SRC_PI_S1_COUNT) + toCount(row.SRC_PI_S2_COUNT);
    target.mentorias += toCount(row.SRC_GLEU_MENT_COUNT);
    target.atenciones += toCount(row.SRC_KATH_ATENC_COUNT) + toCount(row.SRC_GLEU_ATENC_COUNT);
  });
}

export async function loadConsolidatedData() {
  const [sanRows, vitRows, sinCampusRows, qualityRows] = await Promise.all([
    fetchCsv(DATA_FILES.sanJoaquin),
    fetchCsv(DATA_FILES.vitacura),
    fetchCsv(DATA_FILES.sinCampus),
    fetchCsv(DATA_FILES.calidad),
  ]);

  const groupedRecords = {};
  mergeCampusRows(groupedRecords, sanRows, 'SAN_JOAQUIN');
  mergeCampusRows(groupedRecords, vitRows, 'VITACURA');
  mergeCampusRows(groupedRecords, sinCampusRows, 'SIN_CAMPUS');

  const qualityMap = buildQualityMap(qualityRows);

  const records = Object.values(groupedRecords)
    .map((record, index) => {
      const qualityInfo = qualityMap[record.rut] || { count: 0, details: [] };
      const totalApoyos = record.ciac + record.talleres + record.mentorias + record.atenciones;

      return {
        ...record,
        id: index + 1,
        total_apoyos: totalApoyos,
        estado: totalApoyos > 0 ? 'Con apoyo' : 'Sin apoyo',
        issues_count: qualityInfo.count,
        observaciones: qualityInfo.details.slice(0, 3).join(' | '),
        calidad: qualityInfo.count > 0 ? 'Con observaciones' : 'Sin observaciones',
      };
    })
    .sort((a, b) => b.total_apoyos - a.total_apoyos);

  return {
    generatedAt: new Date().toLocaleString('es-CL'),
    sourceFiles: Object.values(DATA_FILES),
    records,
  };
}
