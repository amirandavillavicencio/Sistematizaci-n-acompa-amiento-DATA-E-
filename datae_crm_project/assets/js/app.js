import { loadConsolidatedData } from './data-loader.js';
import { applyFilters, createFilterState, hydrateFilterOptions, resetFilterState } from './filters.js';
import { createMainTable } from './table.js';
import { createCharts, updateCharts } from './charts.js';
import { fillSelect, renderDetail, renderKpis, updateCounters } from './ui.js';

const state = {
  allRecords: [],
  filteredRecords: [],
  selectedRecord: null,
  filters: createFilterState(),
};

let table;
let charts;

function runUpdate(elements) {
  state.filteredRecords = applyFilters(state.allRecords, state.filters);
  renderKpis(elements.kpiGrid, state.filteredRecords);
  updateCounters(elements.recordsCounter, elements.missingCampusCounter, state.filteredRecords);
  table.setRows(state.filteredRecords);
  updateCharts(charts, state.filteredRecords);

  const stillVisible = state.selectedRecord
    ? state.filteredRecords.find((row) => row.id === state.selectedRecord.id)
    : null;

  if (!stillVisible) {
    state.selectedRecord = null;
    renderDetail(elements.detailPanel, null);
  }
}

function bindFilterEvents(elements) {
  elements.searchInput.addEventListener('input', (event) => {
    state.filters.search = event.target.value;
    runUpdate(elements);
  });

  elements.campusFilter.addEventListener('change', (event) => {
    state.filters.campus = event.target.value;
    runUpdate(elements);
  });

  elements.supportTypeFilter.addEventListener('change', (event) => {
    state.filters.supportType = event.target.value;
    runUpdate(elements);
  });

  elements.supportStatusFilter.addEventListener('change', (event) => {
    state.filters.supportStatus = event.target.value;
    runUpdate(elements);
  });

  elements.missingCampusFilter.addEventListener('change', (event) => {
    state.filters.missingCampus = event.target.value;
    runUpdate(elements);
  });

  elements.clearFiltersBtn.addEventListener('click', () => {
    state.filters = resetFilterState();
    elements.searchInput.value = '';
    elements.campusFilter.value = 'Todos';
    elements.supportTypeFilter.value = 'Todos';
    elements.supportStatusFilter.value = 'Todos';
    elements.missingCampusFilter.value = 'Todos';
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
    clearFiltersBtn: document.getElementById('clearFiltersBtn'),
    recordsCounter: document.getElementById('recordsCounter'),
    missingCampusCounter: document.getElementById('missingCampusCounter'),
    kpiGrid: document.getElementById('kpiGrid'),
    detailPanel: document.getElementById('detailPanel'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),
  };

  const data = await loadConsolidatedData();
  state.allRecords = data.records;
  elements.generatedAt.textContent = data.generatedAt;

  const options = hydrateFilterOptions(state.allRecords);
  fillSelect(elements.campusFilter, options.campuses);
  fillSelect(elements.supportTypeFilter, options.supportTypes);
  fillSelect(elements.supportStatusFilter, options.supportStatus);
  fillSelect(elements.missingCampusFilter, options.missingCampus);

  table = createMainTable('crmTable', (record) => {
    state.selectedRecord = record;
    renderDetail(elements.detailPanel, record);
  });

  charts = createCharts();

  elements.exportCsvBtn.addEventListener('click', () => {
    table.exportCsv('crm_academico_filtrado.csv');
  });

  bindFilterEvents(elements);
  runUpdate(elements);
}

init().catch((error) => {
  console.error(error);
  const app = document.querySelector('.crm-app');
  app.innerHTML = `<div class="alert alert-danger">Error al iniciar la aplicación: ${error.message}</div>`;
});
