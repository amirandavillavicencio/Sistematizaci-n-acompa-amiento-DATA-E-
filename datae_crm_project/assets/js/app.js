import { loadConsolidatedData } from './data-loader.js';
import { applyFilters, createFilterState, hydrateFilterOptions, resetFilterState } from './filters.js';
import { createMainTable, createCompactCampusTable, renderMissingCampusTable } from './table.js';
import { createCharts, updateCharts } from './charts.js';
import { fillSelect, renderDetail, renderKpis, renderQualityChecks, updateCounters } from './ui.js';

const state = {
  records: [],
  missingCampusRecords: [],
  filtered: [],
  filters: createFilterState(),
  selected: null,
  summary: {},
  qualitySummary: {},
};

let table;
let sjTable;
let vitTable;
let charts;

function runUpdate(elements) {
  state.filtered = applyFilters(state.records, state.filters);
  renderKpis(elements.kpiGrid, state.summary);
  updateCounters(elements.recordsCounter, elements.missingCampusCounter, state.filtered, state.missingCampusRecords);
  table.setRows(state.filtered);

  const campusRows = state.filters.search || state.filters.supportType !== 'Todos' || state.filters.supportStatus !== 'Todos' || state.filters.source !== 'Todas'
    ? state.filtered
    : state.records;
  sjTable.setRows(campusRows.filter((row) => row.origen_base === 'San Joaquín'));
  vitTable.setRows(campusRows.filter((row) => row.origen_base === 'Vitacura'));

  renderMissingCampusTable('missingCampusTable', state.missingCampusRecords);
  updateCharts(charts, state.filtered, state.missingCampusRecords);

  const stillVisible = state.selected ? state.filtered.find((row) => row.id === state.selected.id) : null;
  if (!stillVisible) {
    state.selected = null;
    renderDetail(elements.detailPanel, null);
  }
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
  ].forEach(([id, key]) => {
    elements[id].addEventListener('change', (e) => {
      state.filters[key] = e.target.value;
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
    clearFiltersBtn: document.getElementById('clearFiltersBtn'),
    recordsCounter: document.getElementById('recordsCounter'),
    missingCampusCounter: document.getElementById('missingCampusCounter'),
    kpiGrid: document.getElementById('kpiGrid'),
    detailPanel: document.getElementById('detailPanel'),
    qualityPanel: document.getElementById('qualityPanel'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),
  };

  const data = await loadConsolidatedData();
  state.records = data.records.filter((row) => !row.sin_campus);
  state.missingCampusRecords = data.missingCampus;
  state.summary = data.summary || {};
  state.qualitySummary = data.qualitySummary || {};
  elements.generatedAt.textContent = new Date(data.generatedAt).toLocaleString('es-CL');

  const options = hydrateFilterOptions(state.records);
  fillSelect(elements.campusFilter, options.campuses);
  fillSelect(elements.supportTypeFilter, options.supportTypes);
  fillSelect(elements.supportStatusFilter, options.supportStatus);
  fillSelect(elements.sourceFilter, options.sources);

  table = createMainTable('crmTable', (record) => {
    state.selected = record;
    renderDetail(elements.detailPanel, record);
  });
  sjTable = createCompactCampusTable('sjTable');
  vitTable = createCompactCampusTable('vitTable');
  charts = createCharts();

  renderQualityChecks(elements.qualityPanel, state.records, state.missingCampusRecords, state.qualitySummary);

  elements.exportCsvBtn.addEventListener('click', () => table.exportCsv('consolidado_datae_2025_filtrado.csv'));

  bindFilters(elements);
  runUpdate(elements);
}

init().catch((error) => {
  const app = document.querySelector('.crm-app');
  app.innerHTML = `<div class="alert alert-danger">Error al iniciar consolidado DATA-E: ${error.message}</div>`;
  console.error(error);
});
