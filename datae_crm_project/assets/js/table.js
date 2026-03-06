const COLUMNS = [
  { key: 'rut', label: 'RUT', type: 'text' },
  { key: 'nombre', label: 'Nombre', type: 'text' },
  { key: 'campus', label: 'Campus', type: 'text' },
  { key: 'ciac', label: 'CIAC', type: 'number' },
  { key: 'talleres', label: 'Talleres', type: 'number' },
  { key: 'mentorias', label: 'Mentorías', type: 'number' },
  { key: 'atenciones', label: 'Atenciones', type: 'number' },
  { key: 'total_apoyos', label: 'Total apoyos', type: 'number' },
  { key: 'estado', label: 'Estado', type: 'text' },
];

function sortRows(rows, field, direction, type) {
  const sorted = [...rows].sort((a, b) => {
    if (type === 'number') return Number(a[field]) - Number(b[field]);
    return String(a[field]).localeCompare(String(b[field]), 'es');
  });
  return direction === 'asc' ? sorted : sorted.reverse();
}

function statusCell(state) {
  const klass = state === 'Con apoyo' ? 'status-badge status-ok' : 'status-badge status-empty';
  return `<span class="${klass}">${state}</span>`;
}

function buildExportCsv(rows) {
  const headers = ['RUT', 'Nombre', 'Campus', 'CIAC', 'Talleres', 'Mentorías', 'Atenciones', 'Total apoyos', 'Estado'];
  const lines = [headers.join(',')];
  rows.forEach((row) => {
    const values = [
      row.rut,
      row.nombre,
      row.campus,
      row.ciac,
      row.talleres,
      row.mentorias,
      row.atenciones,
      row.total_apoyos,
      row.estado,
    ].map((value) => `"${String(value).replaceAll('"', '""')}"`);
    lines.push(values.join(','));
  });
  return lines.join('\n');
}

function downloadBlob(content, filename) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

export function createMainTable(containerId, onRowSelected) {
  const container = document.getElementById(containerId);
  const state = {
    rows: [],
    sortedRows: [],
    pageSize: 20,
    page: 1,
    sortField: 'total_apoyos',
    sortDirection: 'desc',
  };

  function render() {
    const column = COLUMNS.find((item) => item.key === state.sortField) || COLUMNS[0];
    state.sortedRows = sortRows(state.rows, state.sortField, state.sortDirection, column.type);
    const totalPages = Math.max(1, Math.ceil(state.sortedRows.length / state.pageSize));
    state.page = Math.min(state.page, totalPages);

    const start = (state.page - 1) * state.pageSize;
    const currentRows = state.sortedRows.slice(start, start + state.pageSize);

    const headers = COLUMNS.map(
      (columnDef) => `<th><button class="sort-button" data-sort="${columnDef.key}">${columnDef.label}</button></th>`,
    ).join('');

    const body = currentRows.length
      ? currentRows
          .map(
            (row) => `
      <tr>
        <td>${row.rut}</td>
        <td>${row.nombre}</td>
        <td>${row.campus}</td>
        <td class="numeric">${row.ciac}</td>
        <td class="numeric">${row.talleres}</td>
        <td class="numeric">${row.mentorias}</td>
        <td class="numeric">${row.atenciones}</td>
        <td class="numeric">${row.total_apoyos}</td>
        <td>${statusCell(row.estado)}</td>
        <td><button class="btn btn-sm btn-outline-primary" data-detail="${row.id}">Ver detalle</button></td>
      </tr>`,
          )
          .join('')
      : '<tr><td colspan="10" class="text-center py-4 text-muted">Sin registros para los filtros aplicados.</td></tr>';

    container.innerHTML = `
      <div class="table-shell">
        <table class="crm-table">
          <thead><tr>${headers}<th>Detalle</th></tr></thead>
          <tbody>${body}</tbody>
        </table>
      </div>
      <div class="table-footer">
        <small class="text-muted">Página ${state.page} de ${totalPages} · ${state.sortedRows.length} resultados</small>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-outline-secondary" data-page="prev">Anterior</button>
          <button class="btn btn-sm btn-outline-secondary" data-page="next">Siguiente</button>
        </div>
      </div>`;

    container.querySelectorAll('[data-sort]').forEach((button) => {
      button.addEventListener('click', () => {
        const field = button.dataset.sort;
        if (state.sortField === field) {
          state.sortDirection = state.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
          state.sortField = field;
          state.sortDirection = 'asc';
        }
        render();
      });
    });

    container.querySelectorAll('[data-detail]').forEach((button) => {
      button.addEventListener('click', () => {
        const id = Number(button.dataset.detail);
        const selected = state.rows.find((item) => item.id === id);
        if (selected) onRowSelected(selected);
      });
    });

    container.querySelectorAll('[data-page]').forEach((button) => {
      button.addEventListener('click', () => {
        if (button.dataset.page === 'prev') state.page = Math.max(1, state.page - 1);
        if (button.dataset.page === 'next') state.page = Math.min(totalPages, state.page + 1);
        render();
      });
    });
  }

  return {
    setRows(rows) {
      state.rows = rows;
      state.page = 1;
      render();
    },
    exportCsv(filename = 'crm_academico_filtrado.csv') {
      downloadBlob(buildExportCsv(state.sortedRows), filename);
    },
  };
}
