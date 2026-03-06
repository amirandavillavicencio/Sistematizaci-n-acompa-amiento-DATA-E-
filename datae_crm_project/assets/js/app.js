import { loadConsolidatedData } from './data-loader.js';
import { applyFilters, createFilterState, hydrateFilterOptions, resetFilterState } from './filters.js';
import { createMainTable, updateMainTable } from './table.js';
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

function bindFilterEvents(elements, runUpdate) {
  elements.searchInput.addEventListener('input', (event) => {
    state.filters.search = event.target.value;
    runUpdate();
  });

  elements.campusFilter.addEventListener('change', (event) => {
    state.filters.campus = event.target.value;
    runUpdate();
  });

  elements.supportTypeFilter.addEventListener('change', (event) => {
    state.filters.supportType = event.target.value;
    runUpdate();
  });

  elements.supportStatusFilter.addEventListener('change', (event) => {
    state.filters.supportStatus = event.target.value;
    runUpdate();
  });

  elements.qualityFilter.addEventListener('change', (event) => {
    state.filters.quality = event.target.value;
    runUpdate();
  });

  elements.clearFiltersBtn.addEventListener('click', () => {
    state.filters = resetFilterState();
    elements.searchInput.value = '';
    elements.campusFilter.value = 'Todos';
    elements.supportTypeFilter.value = 'Todos';
    elements.supportStatusFilter.value = 'Todos';
    elements.qualityFilter.value = 'Todos';
    runUpdate();
  });
}

function runUpdate(elements) {
  state.filteredRecords = applyFilters(state.allRecords, state.filters);
  renderKpis(elements.kpiGrid, state.filteredRecords);
  updateCounters(elements.recordsCounter, elements.missingCampusCounter, state.filteredRecords);
  updateMainTable(table, state.filteredRecords);
  updateCharts(charts, state.filteredRecords);

  if (!state.selectedRecord || !state.filteredRecords.find((record) => record.id === state.selectedRecord.id)) {
    state.selectedRecord = null;
    renderDetail(elements.detailPanel, null);
  }
}

async function init() {
  const elements = {
    generatedAt: document.getElementById('generatedAt'),
    searchInput: document.getElementById('searchInput'),
    campusFilter: document.getElementById('campusFilter'),
    supportTypeFilter: document.getElementById('supportTypeFilter'),
    supportStatusFilter: document.getElementById('supportStatusFilter'),
    qualityFilter: document.getElementById('qualityFilter'),
    clearFiltersBtn: document.getElementById('clearFiltersBtn'),
    recordsCounter: document.getElementById('recordsCounter'),
    missingCampusCounter: document.getElementById('missingCampusCounter'),
    kpiGrid: document.getElementById('kpiGrid'),
    detailPanel: document.getElementById('detailPanel'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),
  };

  const data = await loadConsolidatedData();
  state.allRecords = data.records;
  elements.generatedAt.textContent = data.generatedAt || 'Sin metadato';

  const options = hydrateFilterOptions(state.allRecords);
  fillSelect(elements.campusFilter, options.campuses);
  fillSelect(elements.supportTypeFilter, options.supportTypes);
  fillSelect(elements.supportStatusFilter, options.supportStatus);
  fillSelect(elements.qualityFilter, options.quality);

  table = createMainTable('#crmTable', (record) => {
    state.selectedRecord = record;
    renderDetail(elements.detailPanel, record);
  });

  charts = createCharts();

  elements.exportCsvBtn.addEventListener('click', () => {
    table.download('csv', 'crm_academico_filtrado.csv');
  });

  bindFilterEvents(elements, () => runUpdate(elements));
  runUpdate(elements);
}

init().catch((error) => {
  console.error(error);
  const app = document.querySelector('.crm-app');
  app.innerHTML = `<div class="alert alert-danger">Error al iniciar la aplicación: ${error.message}</div>`;
});
