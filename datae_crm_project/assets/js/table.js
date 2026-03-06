const COLUMNS = [
  { key: 'rut', label: 'RUT', type: 'text' },
  { key: 'nombre', label: 'Nombre', type: 'text' },
  { key: 'campus', label: 'Campus', type: 'text' },
  { key: 'conteo_atenciones', label: 'Atención individual', type: 'number' },
  { key: 'conteo_talleres', label: 'Talleres', type: 'number' },
  { key: 'conteo_mentorias', label: 'Mentoría', type: 'number' },
  { key: 'conteo_ciac', label: 'Apoyo CIAC', type: 'number' },
  { key: 'conteo_tutoria_par', label: 'Tutoría par', type: 'number' },
  { key: 'total_sesiones', label: 'Total sesiones', type: 'number' },
  { key: 'intensidad_apoyo', label: 'Intensidad', type: 'text' },
  { key: 'matriz_participacion', label: 'Matriz participación', type: 'text' },
  { key: 'estado', label: 'Con apoyo', type: 'text' },
  { key: 'fuentes_detectadas', label: 'Origen registro', type: 'text' },
  { key: 'observacion_calidad', label: 'Notas consolidación', type: 'text' },
];

const escapeHtml = (value = '') => value.toString()
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;');

const supportBadgeMap = [
  { key: 'conteo_talleres', flag: 'talleres', label: 'Talleres', short: 'T' },
  { key: 'conteo_mentorias', flag: 'mentorias', label: 'Mentoría', short: 'M' },
  { key: 'conteo_ciac', flag: 'ciac', label: 'CIAC', short: 'C' },
  { key: 'conteo_atenciones', flag: 'atenciones', label: 'Atención individual', short: 'A' },
  { key: 'conteo_tutoria_par', flag: 'tutoria_par', label: 'Tutoría par', short: 'TP' },
];

function renderParticipationBadges(row) {
  return supportBadgeMap.map((item) => {
    const active = Number(row[item.key] || 0) > 0 || Boolean(row[item.flag]);
    return `<span class="matrix-badge ${active ? 'matrix-on' : 'matrix-off'}" title="${item.label}: ${active ? 'Participa' : 'Sin registro'}">${item.short}</span>`;
  }).join('');
}

function sortRows(rows, key, direction, type) {
  const data = [...rows].sort((a, b) => {
    if (type === 'number') return Number(a[key] || 0) - Number(b[key] || 0);
    const aVal = Array.isArray(a[key]) ? a[key].join(', ') : String(a[key] || '');
    const bVal = Array.isArray(b[key]) ? b[key].join(', ') : String(b[key] || '');
    return aVal.localeCompare(bVal, 'es');
  });
  return direction === 'asc' ? data : data.reverse();
}

function toCsv(rows) {
  const headers = ['rut', 'nombre', 'campus', 'atencion_individual', 'talleres', 'tutoria_par', 'mentoria', 'apoyo_ciac', 'total_sesiones', 'intensidad', 'con_apoyo', 'origen_registro', 'observaciones'];
  const lines = [headers.join(',')];
  rows.forEach((row) => {
    const cells = [
      row.rut,
      row.nombre,
      row.campus,
      row.conteo_atenciones,
      row.conteo_talleres,
      row.conteo_tutoria_par || 0,
      row.conteo_mentorias,
      row.conteo_ciac,
      row.total_sesiones,
      row.intensidad_apoyo,
      row.tiene_apoyo ? 1 : 0,
      (row.fuentes_detectadas || []).join(' | '),
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

function buildSimpleTable(rows, emptyMessage = 'No hay registros para los filtros seleccionados') {
  if (!rows.length) return `<div class="empty-state"><div><strong>Sin registros disponibles</strong><p class="mb-0">${emptyMessage}</p></div></div>`;
  const body = rows.slice(0, 200).map((row) => `
    <tr>
      <td>${escapeHtml(row.rut)}</td>
      <td title="${escapeHtml(row.nombre)}">${escapeHtml(row.nombre)}</td>
      <td class="numeric">${row.total_apoyos}</td>
      <td title="${escapeHtml((row.fuentes_detectadas || []).join(', ') || '—')}">${escapeHtml((row.fuentes_detectadas || []).join(', ') || '—')}</td>
      <td title="${escapeHtml(row.observacion_calidad || '—')}">${escapeHtml(row.observacion_calidad || '—')}</td>
    </tr>
  `).join('');

  return `<div class="table-shell"><table class="crm-table crm-table-compact"><thead><tr>
    <th>RUT</th><th>Nombre</th><th>Total apoyos</th><th>Origen</th><th>Observaciones</th>
  </tr></thead><tbody>${body}</tbody></table></div>`;
}

export function createMainTable(containerId, onRowSelected) {
  const container = document.getElementById(containerId);
  const state = { rows: [], sortedRows: [], sortKey: 'total_sesiones', sortDirection: 'desc', page: 1, pageSize: 20 };

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
            <td title="${escapeHtml(row.nombre)}">${escapeHtml(row.nombre)}</td>
            <td>${escapeHtml(row.campus)}</td>
            <td class="numeric">${row.conteo_atenciones}</td>
            <td class="numeric">${row.conteo_talleres}</td>
            <td class="numeric">${row.conteo_mentorias}</td>
            <td class="numeric">${row.conteo_ciac}</td>
            <td class="numeric">${row.conteo_tutoria_par || 0}</td>
            <td class="numeric">${row.total_sesiones}</td>
            <td><span class="intensity-badge intensity-${escapeHtml((row.intensidad_apoyo || 'Sin apoyo').toLowerCase().replace(/\s+/g, '-'))}">${escapeHtml(row.intensidad_apoyo)}</span></td>
            <td><div class="matrix-cell">${renderParticipationBadges(row)}</div></td>
            <td><span class="status-badge ${row.tiene_apoyo ? 'status-ok' : 'status-empty'}">${row.tiene_apoyo ? 'Sí' : 'No'}</span></td>
            <td title="${escapeHtml((row.fuentes_detectadas || []).join(', ') || '—')}">${escapeHtml((row.fuentes_detectadas || []).join(', ') || '—')}</td>
            <td title="${escapeHtml(row.observacion_calidad || '—')}">${escapeHtml(row.observacion_calidad || '—')}</td>
            <td><button class="btn btn-sm btn-outline-primary table-action" data-detail="${row.id}">Detalle</button></td>
          </tr>`).join('')
      : '<tr><td colspan="16" class="text-center py-4 text-muted">No hay registros para los filtros seleccionados</td></tr>';

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

export function createCompactCampusTable(containerId) {
  const container = document.getElementById(containerId);
  return {
    setRows(rows) {
      container.innerHTML = buildSimpleTable(rows, 'Sin registros para este campus con los filtros actuales.');
    },
  };
}

export function renderMissingCampusTable(containerId, rows) {
  const container = document.getElementById(containerId);
  container.innerHTML = buildSimpleTable(rows, 'Sin registros sin campus disponibles.');
}
