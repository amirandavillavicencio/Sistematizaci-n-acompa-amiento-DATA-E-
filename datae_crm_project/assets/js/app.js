import { loadConsolidatedData } from './data-loader.js';
import { applyFilters, createFilterState, hydrateFilterOptions, resetFilterState } from './filters.js';
import { createMainTable, renderMissingCampusTable } from './table.js';
import { createCharts, updateCharts } from './charts.js';
import { fillSelect, renderDetail, renderKpis, updateCounters } from './ui.js';

const state = {
  records: [],
  filtered: [],
  filters: createFilterState(),
  selected: null,
};

let table;
let charts;

function runUpdate(elements) {
  state.filtered = applyFilters(state.records, state.filters);
  renderKpis(elements.kpiGrid, state.filtered);
  updateCounters(elements.recordsCounter, elements.missingCampusCounter, state.filtered);
  table.setRows(state.filtered);
  renderMissingCampusTable('missingCampusTable', state.filtered.filter((row) => row.sin_campus));
  updateCharts(charts, state.filtered);

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
    ['missingCampusFilter', 'missingCampus'],
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
    elements.missingCampusFilter.value = 'Todos';
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
    missingCampusFilter: document.getElementById('missingCampusFilter'),
    sourceFilter: document.getElementById('sourceFilter'),
    clearFiltersBtn: document.getElementById('clearFiltersBtn'),
    recordsCounter: document.getElementById('recordsCounter'),
    missingCampusCounter: document.getElementById('missingCampusCounter'),
    kpiGrid: document.getElementById('kpiGrid'),
    detailPanel: document.getElementById('detailPanel'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),
  };

  const data = await loadConsolidatedData();
  state.records = data.records;
  elements.generatedAt.textContent = new Date(data.generatedAt).toLocaleString('es-CL');

  const options = hydrateFilterOptions(state.records);
  fillSelect(elements.campusFilter, options.campuses);
  fillSelect(elements.supportTypeFilter, options.supportTypes);
  fillSelect(elements.supportStatusFilter, options.supportStatus);
  fillSelect(elements.missingCampusFilter, options.missingCampus);
  fillSelect(elements.sourceFilter, options.sources);

  table = createMainTable('crmTable', (record) => {
    state.selected = record;
    renderDetail(elements.detailPanel, record);
  });
  charts = createCharts();

  elements.exportCsvBtn.addEventListener('click', () => table.exportCsv('crm_academico_filtrado.csv'));

  bindFilters(elements);
  runUpdate(elements);
}

init().catch((error) => {
  const app = document.querySelector('.crm-app');
  app.innerHTML = `<div class="alert alert-danger">Error al iniciar CRM: ${error.message}</div>`;
  console.error(error);
});
