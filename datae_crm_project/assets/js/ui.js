export function renderKpis(container, rows) {
  const totalStudents = rows.length;
  const totalCIAC = rows.reduce((sum, r) => sum + r.ciac, 0);
  const totalTalleres = rows.reduce((sum, r) => sum + r.talleres, 0);
  const totalMentorias = rows.reduce((sum, r) => sum + r.mentorias, 0);
  const totalAtenciones = rows.reduce((sum, r) => sum + r.atenciones, 0);
  const withSupport = rows.filter((r) => r.total_apoyos > 0).length;
  const withoutSupport = totalStudents - withSupport;
  const pctSupport = totalStudents ? ((withSupport / totalStudents) * 100).toFixed(1) : '0.0';
  const withoutCampus = rows.filter((r) => !r.tiene_campus).length;

  const cards = [
    ['Total estudiantes únicos', totalStudents, 'Registros únicos en vista actual'],
    ['Total CIAC', totalCIAC, 'Participaciones CIAC'],
    ['Total talleres', totalTalleres, 'Asistencias a talleres'],
    ['Total mentorías', totalMentorias, 'Sesiones de mentoría'],
    ['Total atenciones', totalAtenciones, 'Atenciones individuales'],
    ['% estudiantes con apoyo', `${pctSupport}%`, 'Con al menos una participación'],
    ['Total estudiantes con apoyo', withSupport, 'Estado Con apoyo'],
    ['Total estudiantes sin apoyo', withoutSupport, 'Estado Sin apoyo'],
    ['Registros sin campus', withoutCampus, 'Pendientes de clasificación campus'],
  ];

  container.innerHTML = cards
    .map(
      ([label, value, hint]) => `
        <article class="kpi-card">
          <div class="kpi-label">${label}</div>
          <div class="kpi-value">${value.toLocaleString?.() ?? value}</div>
          <div class="kpi-hint">${hint}</div>
        </article>`,
    )
    .join('');
}

export function renderDetail(panel, record) {
  if (!record) {
    panel.innerHTML = 'Selecciona una fila para ver información del estudiante.';
    panel.className = 'empty-state';
    return;
  }

  panel.className = 'detail-block';
  panel.innerHTML = `
    <div class="detail-top">
      <p class="detail-name">${record.nombre}</p>
      <div class="detail-meta">RUT: ${record.rut} · Campus: ${record.campus}</div>
    </div>
    <div class="detail-stats">
      <div class="stat-item"><span>CIAC</span><strong>${record.ciac}</strong></div>
      <div class="stat-item"><span>Talleres</span><strong>${record.talleres}</strong></div>
      <div class="stat-item"><span>Mentorías</span><strong>${record.mentorias}</strong></div>
      <div class="stat-item"><span>Atenciones</span><strong>${record.atenciones}</strong></div>
      <div class="stat-item"><span>Total participaciones</span><strong>${record.total_apoyos}</strong></div>
      <div class="stat-item"><span>Estado</span><strong>${record.estado}</strong></div>
    </div>
    <div>
      <small class="text-muted d-block mb-1">Observaciones de calidad</small>
      <div>${record.observaciones || record.calidad || 'Sin observaciones registradas.'}</div>
    </div>
  `;
}

export function updateCounters(recordsCounter, missingCounter, rows) {
  const missing = rows.filter((r) => !r.tiene_campus).length;
  recordsCounter.textContent = `${rows.length.toLocaleString()} resultados`;
  missingCounter.textContent = `${missing.toLocaleString()} sin campus`;
}

export function fillSelect(select, values) {
  select.innerHTML = values.map((value) => `<option value="${value}">${value}</option>`).join('');
}
