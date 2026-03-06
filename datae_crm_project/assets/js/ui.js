const formatNumber = (value) => Number(value || 0).toLocaleString('es-CL');

export function fillSelect(select, options) {
  select.innerHTML = options.map((opt) => `<option value="${opt}">${opt}</option>`).join('');
}

export function renderKpis(container, summary) {
  const cards = [
    { label: 'Total estudiantes base', value: formatNumber(summary.total_estudiantes_unicos), icon: '👥', priority: 'primary' },
    { label: 'Estudiantes con al menos un apoyo', value: formatNumber(summary.total_con_apoyo), icon: '✅', priority: 'primary' },
    { label: '% estudiantes con apoyo', value: `${Number(summary.porcentaje_estudiantes_con_apoyo || 0).toFixed(1)}%`, icon: '📈', priority: 'primary' },
    { label: 'Total registros sin campus', value: formatNumber(summary.total_rut_sin_campus), icon: '⚠️', priority: 'primary' },
    { label: 'Total estudiantes base San Joaquín', value: formatNumber(summary.base_san_joaquin), icon: '🏫', priority: 'secondary' },
    { label: 'Total estudiantes base Vitacura', value: formatNumber(summary.base_vitacura), icon: '🏫', priority: 'secondary' },
    { label: 'Total participaciones CIAC', value: formatNumber(summary.total_participaciones_ciac), icon: '📚', priority: 'secondary' },
    { label: 'Total participaciones en talleres', value: formatNumber(summary.total_participaciones_talleres), icon: '🧩', priority: 'secondary' },
    { label: 'Total participaciones en mentorías', value: formatNumber(summary.total_participaciones_mentorias), icon: '🤝', priority: 'secondary' },
    { label: 'Total participaciones en atenciones individuales', value: formatNumber(summary.total_participaciones_atenciones), icon: '🗂️', priority: 'secondary' },
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
    container.innerHTML = '<p class="mb-0">Selecciona una fila para desplegar un resumen detallado del estudiante, su trazabilidad y sus apoyos registrados.</p>';
    return;
  }

  container.className = 'detail-block';
  container.innerHTML = `
    <div class="detail-head">
      <p class="detail-name">${record.nombre}</p>
      <p class="detail-meta">RUT: ${record.rut} · Campus: ${record.campus}</p>
      <div class="detail-badges">
        <span class="detail-tag">Base oficial campus: ${record.presencia_lista_base ? 'Sí' : 'No'}</span>
        <span class="detail-tag">Origen: ${record.origen_base}</span>
        <span class="detail-tag">Con apoyo: ${record.tiene_apoyo ? 'Sí' : 'No'}</span>
      </div>
    </div>
    <div class="detail-stats">
      <div class="stat-item"><span>CIAC</span><strong>${record.conteo_ciac}</strong></div>
      <div class="stat-item"><span>Talleres</span><strong>${record.conteo_talleres}</strong></div>
      <div class="stat-item"><span>Mentorías</span><strong>${record.conteo_mentorias}</strong></div>
      <div class="stat-item"><span>Atenciones</span><strong>${record.conteo_atenciones}</strong></div>
      <div class="stat-item"><span>Total apoyos</span><strong>${record.total_apoyos}</strong></div>
      <div class="stat-item"><span>Estado</span><strong>${record.tiene_apoyo ? 'Con apoyo' : 'Sin apoyo'}</strong></div>
    </div>
    <div>
      <small class="text-muted d-block mb-1">Origen / trazabilidad resumida</small>
      <div class="detail-panel-box">${record.fuentes_detectadas.join(', ') || 'Sin fuentes identificadas'}</div>
    </div>
    <div>
      <small class="text-muted d-block mb-1">Observaciones de consolidación</small>
      <div class="detail-panel-box">${record.observacion_calidad || 'Sin observaciones registradas.'}</div>
    </div>
  `;
}

export function renderQualityChecks(container, campusRows, missingCampusRows, qualitySummary = {}) {
  const ruts = campusRows.map((row) => row.rut);
  const duplicatedRuts = ruts.length - new Set(ruts).size;
  const nombresFaltantes = campusRows.filter((row) => !row.nombre || row.nombre === 'Sin nombre').length;
  const inconsistenciasConteo = campusRows.filter((row) => row.total_apoyos < 0).length;

  container.innerHTML = `
    <div class="quality-list">
      <div class="quality-item"><span>RUT duplicados en base consolidada</span><strong>${formatNumber(duplicatedRuts)}</strong></div>
      <div class="quality-item"><span>RUT en externos sin campus identificado</span><strong>${formatNumber(missingCampusRows.length)}</strong></div>
      <div class="quality-item"><span>Registros con nombre faltante</span><strong>${formatNumber(nombresFaltantes)}</strong></div>
      <div class="quality-item"><span>Posibles inconsistencias de conteo</span><strong>${formatNumber(inconsistenciasConteo)}</strong></div>
      <div class="quality-item"><span>RUT con issues de calidad reportados</span><strong>${formatNumber(qualitySummary.total_rut_con_issues)}</strong></div>
      <div class="quality-note">Advertencia metodológica: cuando no existe conteo robusto por sesión, el consolidado usa marca de participación para no perder trazabilidad.</div>
    </div>
  `;
}

export function updateCounters(recordsCounter, missingCounter, filteredRows, missingCampusRows) {
  recordsCounter.textContent = `${formatNumber(filteredRows.length)} resultados filtrados en consolidado`;
  missingCounter.textContent = `${formatNumber(missingCampusRows.length)} registros sin campus`;
}
