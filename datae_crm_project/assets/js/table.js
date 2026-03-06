const COLUMNS = [
  { key: 'rut', label: 'RUT', type: 'text' },
  { key: 'nombre', label: 'Nombre', type: 'text' },
  { key: 'campus', label: 'Campus', type: 'text' },
  { key: 'conteo_ciac', label: 'CIAC', type: 'number' },
  { key: 'conteo_talleres', label: 'Talleres', type: 'number' },
  { key: 'conteo_mentorias', label: 'Mentorías', type: 'number' },
  { key: 'conteo_atenciones', label: 'Atenciones', type: 'number' },
  { key: 'total_apoyos', label: 'Total apoyos', type: 'number' },
  { key: 'estado', label: 'Estado', type: 'text' },
  { key: 'observacion_calidad', label: 'Observaciones/calidad', type: 'text' },
];

const escapeHtml = (value = '') => value.toString()
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;');

function sortRows(rows, key, direction, type) {
  const data = [...rows].sort((a, b) => {
    if (type === 'number') return Number(a[key] || 0) - Number(b[key] || 0);
    return String(a[key] || '').localeCompare(String(b[key] || ''), 'es');
  });
  return direction === 'asc' ? data : data.reverse();
}

function toCsv(rows) {
  const headers = ['RUT', 'Nombre', 'Campus', 'CIAC', 'Talleres', 'Mentorías', 'Atenciones', 'Total apoyos', 'Estado', 'Observación'];
  const lines = [headers.join(',')];
  rows.forEach((row) => {
    const cells = [
      row.rut,
      row.nombre,
      row.campus,
      row.conteo_ciac,
      row.conteo_talleres,
      row.conteo_mentorias,
      row.conteo_atenciones,
      row.total_apoyos,
      row.estado,
      row.observacion_calidad || '',
    ].map((v) => `"${String(v).replaceAll('"', '""')}"`);
    lines.push(cells.join(','));
  });
  return lines.join('\n');
}

function download(content, filename) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function buildSimpleTable(rows) {
  if (!rows.length) return '<div class="text-muted">Sin registros sin campus para los filtros actuales.</div>';
  const body = rows.slice(0, 200).map((row) => `
    <tr>
      <td>${escapeHtml(row.rut)}</td>
      <td>${escapeHtml(row.nombre)}</td>
      <td class="numeric">${row.total_apoyos}</td>
      <td>${escapeHtml((row.fuentes_detectadas || []).join(', ') || '—')}</td>
      <td>${escapeHtml(row.observacion_calidad || '—')}</td>
    </tr>
  `).join('');

  return `<div class="table-shell"><table class="crm-table"><thead><tr>
    <th>RUT</th><th>Nombre</th><th>Total apoyos</th><th>Fuentes</th><th>Observaciones</th>
  </tr></thead><tbody>${body}</tbody></table></div>`;
}

export function createMainTable(containerId, onRowSelected) {
  const container = document.getElementById(containerId);
  const state = { rows: [], sortedRows: [], sortKey: 'total_apoyos', sortDirection: 'desc', page: 1, pageSize: 20 };

  function render() {
    const column = COLUMNS.find((col) => col.key === state.sortKey) || COLUMNS[0];
    state.sortedRows = sortRows(state.rows, state.sortKey, state.sortDirection, column.type);

    const totalPages = Math.max(1, Math.ceil(state.sortedRows.length / state.pageSize));
    state.page = Math.min(state.page, totalPages);
    const start = (state.page - 1) * state.pageSize;
    const currentRows = state.sortedRows.slice(start, start + state.pageSize);

    const headers = COLUMNS.map((col) => `<th><button class="sort-button" data-sort="${col.key}">${col.label}</button></th>`).join('');
    const body = currentRows.length
      ? currentRows.map((row) => `<tr>
            <td>${escapeHtml(row.rut)}</td>
            <td>${escapeHtml(row.nombre)}</td>
            <td>${escapeHtml(row.campus)}</td>
            <td class="numeric">${row.conteo_ciac}</td>
            <td class="numeric">${row.conteo_talleres}</td>
            <td class="numeric">${row.conteo_mentorias}</td>
            <td class="numeric">${row.conteo_atenciones}</td>
            <td class="numeric">${row.total_apoyos}</td>
            <td><span class="status-badge ${row.tiene_apoyo ? 'status-ok' : 'status-empty'}">${row.estado}</span></td>
            <td>${escapeHtml(row.observacion_calidad || '—')}</td>
            <td><button class="btn btn-sm btn-outline-primary" data-detail="${row.id}">Detalle</button></td>
          </tr>`).join('')
      : '<tr><td colspan="11" class="text-center py-4 text-muted">Sin resultados para los filtros actuales.</td></tr>';

    container.innerHTML = `
      <div class="table-shell"><table class="crm-table"><thead><tr>${headers}<th>Acción</th></tr></thead><tbody>${body}</tbody></table></div>
      <div class="table-footer">
        <small class="text-muted">Página ${state.page} de ${totalPages} · ${state.sortedRows.length} registros</small>
        <div class="btn-group btn-group-sm">
          <button class="btn btn-outline-secondary" data-page="prev" ${state.page <= 1 ? 'disabled' : ''}>Anterior</button>
          <button class="btn btn-outline-secondary" data-page="next" ${state.page >= totalPages ? 'disabled' : ''}>Siguiente</button>
        </div>
      </div>`;

    container.querySelectorAll('[data-sort]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const key = btn.getAttribute('data-sort');
        state.sortDirection = state.sortKey === key && state.sortDirection === 'asc' ? 'desc' : 'asc';
        state.sortKey = key;
        render();
      });
    });

    container.querySelectorAll('[data-detail]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const id = Number(btn.getAttribute('data-detail'));
        const selected = state.sortedRows.find((row) => row.id === id);
        if (selected) onRowSelected(selected);
      });
    });

    container.querySelectorAll('[data-page]').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.page += btn.getAttribute('data-page') === 'next' ? 1 : -1;
        render();
      });
    });
  }

  return {
    setRows(rows) {
      state.rows = [...rows];
      state.page = 1;
      render();
    },
    exportCsv(filename) {
      download(toCsv(state.sortedRows), filename);
    },
  };
}

export function renderMissingCampusTable(containerId, rows) {
  const container = document.getElementById(containerId);
  container.innerHTML = buildSimpleTable(rows);
}
