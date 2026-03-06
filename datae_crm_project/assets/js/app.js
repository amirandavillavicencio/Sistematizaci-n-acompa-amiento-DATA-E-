import { loadConsolidatedData } from './data-loader.js';
import { applyFilters, createFilterState, hydrateFilterOptions, normalizeText, resetFilterState } from './filters.js';
import { createMainTable, createCompactCampusTable, renderMissingCampusTable } from './table.js';
import { createCharts, updateCharts } from './charts.js';
import { fillSelect, renderDetail, renderKpis, renderQualityChecks, renderMissingCampusAnalysis, updateCounters } from './ui.js';

const state = {
  records: [],
  missingCampusRecords: [],
  filtered: [],
  filters: createFilterState(),
  selected: null,
  summary: {},
  qualitySummary: {},
  qualityStats: {},
};

let table;
let sjTable;
let vitTable;
let charts;

function computeIntensity(totalSesiones) {
  if (totalSesiones >= 4) return 'Alto apoyo';
  if (totalSesiones >= 2) return 'Medio apoyo';
  if (totalSesiones >= 1) return 'Bajo apoyo';
  return 'Sin apoyo';
}

function enrichRecord(row) {
  const totalSesiones = Number(row.conteo_ciac || 0)
    + Number(row.conteo_talleres || 0)
    + Number(row.conteo_mentorias || 0)
    + Number(row.conteo_atenciones || 0)
    + Number(row.conteo_tutoria_par || 0);
  return {
    ...row,
    total_sesiones: totalSesiones,
    intensidad_apoyo: computeIntensity(totalSesiones),
  };
}

function buildQualityStats(rows) {
  const rutList = rows.map((row) => row.rut).filter(Boolean);
  const duplicatedRuts = rutList.length - new Set(rutList).size;

  const inconsistentRecords = rows.filter((row) => {
    const totalByComponents = Number(row.conteo_ciac || 0)
      + Number(row.conteo_talleres || 0)
      + Number(row.conteo_mentorias || 0)
      + Number(row.conteo_atenciones || 0)
      + Number(row.conteo_tutoria_par || 0);
    return (row.tiene_apoyo && totalByComponents === 0) || (!row.tiene_apoyo && totalByComponents > 0);
  }).length;

  const mixedCountMarkRecords = rows.filter((row) => {
    const hasMarkWithoutCount = (row.ciac && Number(row.conteo_ciac || 0) === 0)
      || (row.talleres && Number(row.conteo_talleres || 0) === 0)
      || (row.mentorias && Number(row.conteo_mentorias || 0) === 0)
      || (row.atenciones && Number(row.conteo_atenciones || 0) === 0)
      || (row.tutoria_par && Number(row.conteo_tutoria_par || 0) === 0);
    const hasCountWithoutMark = (!row.ciac && Number(row.conteo_ciac || 0) > 0)
      || (!row.talleres && Number(row.conteo_talleres || 0) > 0)
      || (!row.mentorias && Number(row.conteo_mentorias || 0) > 0)
      || (!row.atenciones && Number(row.conteo_atenciones || 0) > 0)
      || (!row.tutoria_par && Number(row.conteo_tutoria_par || 0) > 0);
    return hasMarkWithoutCount || hasCountWithoutMark;
  }).length;

  return { duplicatedRuts, inconsistentRecords, mixedCountMarkRecords };
}

function runUpdate(elements) {
  state.filtered = applyFilters(state.records, state.filters);
  renderKpis(elements.kpiGrid, state.filtered);
  updateCounters(elements.recordsCounter, elements.missingCampusCounter, state.filtered, state.missingCampusRecords);
  table.setRows(state.filtered);

  const hasActiveFilter = state.filters.search || state.filters.supportType !== 'Todos' || state.filters.supportStatus !== 'Todos' || state.filters.source !== 'Todas' || state.filters.semester !== 'Todos';
  const campusRows = hasActiveFilter ? state.filtered : state.records;
  sjTable.setRows(campusRows.filter((row) => normalizeText(row.origen_base || row.campus) === normalizeText('San Joaquín')));
  vitTable.setRows(campusRows.filter((row) => normalizeText(row.origen_base || row.campus) === normalizeText('Vitacura')));

  renderMissingCampusTable('missingCampusTable', state.missingCampusRecords);
  renderMissingCampusAnalysis(elements.missingCampusSources, state.missingCampusRecords);
  updateCharts(charts, state.filtered, state.missingCampusRecords, state.qualityStats);

  const stillVisible = state.selected ? state.filtered.find((row) => row.id === state.selected.id) : null;
  if (!stillVisible) {
    state.selected = null;
    renderDetail(elements.detailPanel, null);
  }
}

function syncCampusSelectorButtons(elements) {
  const selectedCampus = state.filters.campus || 'Todos';
  elements.campusButtons.forEach((button) => {
    const isActive = button.dataset.campus === selectedCampus;
    button.classList.toggle('active', isActive);
    button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
  });
}

function bindFilters(elements) {
  elements.searchInput.addEventListener('input', (e) => {
    state.filters.search = e.target.value;
    runUpdate(elements);
  });

  [
    ['campusFilter', 'campus'],
    ['supportTypeFilter', 'supportType'],
    ['supportStatusFilter', 'supportStatus'],
    ['sourceFilter', 'source'],
    ['semesterFilter', 'semester'],
  ].forEach(([id, key]) => {
    elements[id].addEventListener('change', (e) => {
      state.filters[key] = e.target.value;
      if (key === 'campus') syncCampusSelectorButtons(elements);
      runUpdate(elements);
    });
  });

  elements.campusButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const selectedCampus = button.dataset.campus;
      state.filters.campus = selectedCampus;
      elements.campusFilter.value = selectedCampus;
      syncCampusSelectorButtons(elements);
      runUpdate(elements);
    });
  });

  elements.clearFiltersBtn.addEventListener('click', () => {
    state.filters = resetFilterState();
    elements.searchInput.value = '';
    elements.campusFilter.value = 'Todos';
    elements.supportTypeFilter.value = 'Todos';
    elements.supportStatusFilter.value = 'Todos';
    elements.sourceFilter.value = 'Todas';
    elements.semesterFilter.value = 'Todos';
    syncCampusSelectorButtons(elements);
    runUpdate(elements);
  });
}

async function init() {
  const elements = {
    generatedAt: document.getElementById('generatedAt'),
    searchInput: document.getElementById('searchInput'),
    campusFilter: document.getElementById('campusFilter'),
    supportTypeFilter: document.getElementById('supportTypeFilter'),
    supportStatusFilter: document.getElementById('supportStatusFilter'),
    sourceFilter: document.getElementById('sourceFilter'),
    semesterFilter: document.getElementById('semesterFilter'),
    campusButtons: Array.from(document.querySelectorAll('.campus-btn')),
    clearFiltersBtn: document.getElementById('clearFiltersBtn'),
    recordsCounter: document.getElementById('recordsCounter'),
    missingCampusCounter: document.getElementById('missingCampusCounter'),
    kpiGrid: document.getElementById('kpiGrid'),
    detailPanel: document.getElementById('detailPanel'),
    qualityPanel: document.getElementById('qualityPanel'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),
    missingCampusSources: document.getElementById('missingCampusSources'),
  };

  const data = await loadConsolidatedData();
  state.records = data.records.filter((row) => !row.sin_campus).map(enrichRecord);
  state.missingCampusRecords = data.missingCampus.map(enrichRecord);
  state.summary = data.summary || {};
  state.qualitySummary = data.qualitySummary || {};
  state.qualityStats = buildQualityStats(state.records);
  elements.generatedAt.textContent = new Date(data.generatedAt).toLocaleString('es-CL');

  const options = hydrateFilterOptions(state.records);
  fillSelect(elements.campusFilter, options.campuses);
  elements.campusFilter.value = state.filters.campus;
  syncCampusSelectorButtons(elements);
  fillSelect(elements.supportTypeFilter, options.supportTypes);
  fillSelect(elements.supportStatusFilter, options.supportStatus);
  fillSelect(elements.sourceFilter, options.sources);
  fillSelect(elements.semesterFilter, options.semesters.length > 1 ? options.semesters : ['Todos']);
  elements.semesterFilter.disabled = options.semesters.length <= 1;

  table = createMainTable('crmTable', (record) => {
    state.selected = record;
    renderDetail(elements.detailPanel, record);
  });
  sjTable = createCompactCampusTable('sjTable');
  vitTable = createCompactCampusTable('vitTable');
  charts = createCharts();

  renderQualityChecks(elements.qualityPanel, state.records, state.missingCampusRecords, state.qualitySummary, state.qualityStats);

  elements.exportCsvBtn.addEventListener('click', () => table.exportCsv('consolidado_datae_2025_filtrado.csv'));

  bindFilters(elements);
  runUpdate(elements);
}

init().catch((error) => {
  const app = document.querySelector('.crm-app');
  app.innerHTML = `<div class="alert alert-danger">Error al iniciar consolidado DATA-E: ${error.message}</div>`;
  console.error(error);
});
