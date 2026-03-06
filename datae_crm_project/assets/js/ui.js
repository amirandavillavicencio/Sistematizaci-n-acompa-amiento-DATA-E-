const formatNumber = (value) => Number(value || 0).toLocaleString('es-CL');

export function fillSelect(select, options) {
  select.innerHTML = options.map((opt) => `<option value="${opt}">${opt}</option>`).join('');
}

export function renderKpis(container, rows) {
  const totalEstudiantes = rows.length;
  const totalParticipaciones = rows.reduce((acc, row) => acc + Number(row.total_sesiones || row.total_apoyos || 0), 0);
  const estudiantesConApoyo = rows.filter((row) => row.tiene_apoyo).length;
  const cobertura = totalEstudiantes ? (estudiantesConApoyo / totalEstudiantes) * 100 : 0;

  const cards = [
    { label: 'Total estudiantes únicos en consolidado', value: formatNumber(totalEstudiantes), icon: '👥', priority: 'primary' },
    { label: 'Total participaciones en apoyos', value: formatNumber(totalParticipaciones), icon: '📊', priority: 'primary' },
    { label: 'Estudiantes con al menos un apoyo', value: formatNumber(estudiantesConApoyo), icon: '✅', priority: 'primary' },
    { label: 'Porcentaje de cobertura', value: `${cobertura.toFixed(1)}%`, icon: '📈', priority: 'primary' },
  ];

  container.innerHTML = cards.map(({ label, value, icon, priority }) => `
    <article class="kpi-card ${priority === 'primary' ? 'kpi-primary' : ''}">
      <div class="kpi-label-row">
        <div class="kpi-label">${label}</div>
        <span class="kpi-icon" aria-hidden="true">${icon}</span>
      </div>
      <div class="kpi-value">${value}</div>
    </article>
  `).join('');
}

export function renderDetail(container, record) {
  if (!record) {
    container.className = 'empty-state';
    container.innerHTML = '<div><strong>Sin estudiante seleccionado</strong><p class="mb-0">Selecciona un registro de las bases oficiales por campus para revisar su consolidación, fuentes y trazabilidad institucional.</p></div>';
    return;
  }

  container.className = 'detail-block';
  container.innerHTML = `
    <div class="detail-head">
      <p class="detail-name">${record.nombre}</p>
      <p class="detail-meta">RUT: ${record.rut} · Campus: ${record.campus}</p>
      <div class="detail-badges">
        <span class="detail-tag">Pertenece a base oficial por campus: ${record.presencia_lista_base ? 'Sí' : 'No'}</span>
        <span class="detail-tag">Origen: ${record.origen_base}</span>
        <span class="detail-tag">Con apoyo: ${record.tiene_apoyo ? 'Sí' : 'No'}</span>
        <span class="detail-tag">Intensidad: ${record.intensidad_apoyo}</span>
      </div>
    </div>
    <div class="detail-stats">
      <div class="stat-item"><span>CIAC</span><strong>${record.conteo_ciac}</strong></div>
      <div class="stat-item"><span>Talleres</span><strong>${record.conteo_talleres}</strong></div>
      <div class="stat-item"><span>Mentorías</span><strong>${record.conteo_mentorias}</strong></div>
      <div class="stat-item"><span>Atenciones</span><strong>${record.conteo_atenciones}</strong></div>
      <div class="stat-item"><span>Tutoría par</span><strong>${record.conteo_tutoria_par || 0}</strong></div>
      <div class="stat-item"><span>Total sesiones</span><strong>${record.total_sesiones}</strong></div>
    </div>
    <div class="detail-group">
      <p class="detail-group-label">Fuentes utilizadas para completar columnas</p>
      <div class="detail-panel-box">${record.fuentes_detectadas.join(', ') || 'Sin fuentes identificadas'}</div>
    </div>
    <div class="detail-group">
      <p class="detail-group-label">Observaciones metodológicas</p>
      <div class="detail-panel-box">${record.observacion_calidad || 'Sin observaciones registradas.'}</div>
    </div>
  `;
}

export function renderQualityChecks(container, campusRows, missingCampusRows, qualitySummary = {}, qualityStats = {}) {
  const nombresFaltantes = campusRows.filter((row) => !row.nombre || row.nombre === 'Sin nombre').length;

  container.innerHTML = `
    <div class="quality-list">
      <div class="quality-item"><span>RUT duplicados en base consolidada</span><strong>${formatNumber(qualityStats.duplicatedRuts)}</strong></div>
      <div class="quality-item"><span>RUT en externos sin campus identificado</span><strong>${formatNumber(missingCampusRows.length)}</strong></div>
      <div class="quality-item"><span>Registros con nombre faltante</span><strong>${formatNumber(nombresFaltantes)}</strong></div>
      <div class="quality-item"><span>Registros con estado/conteo inconsistente</span><strong>${formatNumber(qualityStats.inconsistentRecords)}</strong></div>
      <div class="quality-item"><span>Mezcla de conteos y marcas de participación</span><strong>${formatNumber(qualityStats.mixedCountMarkRecords)}</strong></div>
      <div class="quality-item"><span>RUT con issues de calidad reportados</span><strong>${formatNumber(qualitySummary.total_rut_con_issues)}</strong></div>
      <div class="quality-note">Nota metodológica oficial: los conteos corresponden a participaciones con respaldo de sesiones. Cuando no existe conteo robusto, se utiliza marca de participación (X/1) como evidencia de presencia.</div>
    </div>
  `;
}

export function renderMissingCampusAnalysis(container, rows) {
  const sourceTotals = rows.reduce((acc, row) => {
    const sources = row.fuentes_detectadas?.length ? row.fuentes_detectadas : ['Sin fuente'];
    sources.forEach((source) => {
      acc[source] = (acc[source] || 0) + 1;
    });
    return acc;
  }, {});

  const items = Object.entries(sourceTotals).sort((a, b) => b[1] - a[1]);
  if (!items.length) {
    container.innerHTML = '<p class="subtle mb-0">No hay registros sin campus para analizar por fuente.</p>';
    return;
  }

  container.innerHTML = `
    <div class="source-chip-grid">
      ${items.map(([source, count]) => `<span class="pill">${source}: <strong>${formatNumber(count)}</strong></span>`).join('')}
    </div>
  `;
}

export function updateCounters(recordsCounter, missingCounter, filteredRows, missingCampusRows) {
  recordsCounter.textContent = `${formatNumber(filteredRows.length)} registros del consolidado oficial por campus`;
  missingCounter.textContent = `${formatNumber(missingCampusRows.length)} RUT informados en sección separada sin campus`;
}
