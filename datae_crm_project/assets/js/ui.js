const formatNumber = (value) => Number(value || 0).toLocaleString('es-CL');

export function fillSelect(select, options) {
  select.innerHTML = options.map((opt) => `<option value="${opt}">${opt}</option>`).join('');
}

export function renderKpis(container, summary) {
  const cards = [
    ['Total estudiantes base', formatNumber(summary.total_estudiantes_unicos)],
    ['Total estudiantes base San Joaquín', formatNumber(summary.base_san_joaquin)],
    ['Total estudiantes base Vitacura', formatNumber(summary.base_vitacura)],
    ['Estudiantes con al menos un apoyo', formatNumber(summary.total_con_apoyo)],
    ['% estudiantes con apoyo', `${Number(summary.porcentaje_estudiantes_con_apoyo || 0).toFixed(1)}%`],
    ['Total participaciones CIAC', formatNumber(summary.total_participaciones_ciac)],
    ['Total participaciones en talleres', formatNumber(summary.total_participaciones_talleres)],
    ['Total participaciones en mentorías', formatNumber(summary.total_participaciones_mentorias)],
    ['Total participaciones en atenciones individuales', formatNumber(summary.total_participaciones_atenciones)],
    ['Total registros sin campus', formatNumber(summary.total_rut_sin_campus)],
  ];

  container.innerHTML = cards.map(([label, value]) => `
    <article class="kpi-card">
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value}</div>
    </article>
  `).join('');
}

export function renderDetail(container, record) {
  if (!record) {
    container.className = 'empty-state';
    container.textContent = 'Selecciona una fila para ver detalle.';
    return;
  }

  container.className = 'detail-block';
  container.innerHTML = `
    <div>
      <p class="detail-name">${record.nombre}</p>
      <p class="detail-meta">RUT: ${record.rut} · Campus: ${record.campus}</p>
      <p class="detail-meta">Base oficial campus: ${record.presencia_lista_base ? 'Sí' : 'No'} · Origen: ${record.origen_base}</p>
    </div>
    <div class="detail-stats">
      <div class="stat-item"><span>CIAC</span><strong>${record.conteo_ciac}</strong></div>
      <div class="stat-item"><span>Talleres</span><strong>${record.conteo_talleres}</strong></div>
      <div class="stat-item"><span>Mentorías</span><strong>${record.conteo_mentorias}</strong></div>
      <div class="stat-item"><span>Atenciones</span><strong>${record.conteo_atenciones}</strong></div>
      <div class="stat-item"><span>Total apoyos</span><strong>${record.total_apoyos}</strong></div>
      <div class="stat-item"><span>Con apoyo</span><strong>${record.tiene_apoyo ? 'Sí' : 'No'}</strong></div>
    </div>
    <div>
      <small class="text-muted d-block mb-1">Origen / trazabilidad resumida</small>
      <div>${record.fuentes_detectadas.join(', ') || 'Sin fuentes identificadas'}</div>
    </div>
    <div>
      <small class="text-muted d-block mb-1">Observaciones de consolidación</small>
      <div>${record.observacion_calidad || 'Sin observaciones registradas.'}</div>
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
