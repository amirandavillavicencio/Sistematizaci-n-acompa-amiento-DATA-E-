function formatNumber(value) {
  return Number(value).toLocaleString('es-CL');
}

export function fillSelect(selectElement, values) {
  selectElement.innerHTML = values.map((value) => `<option value="${value}">${value}</option>`).join('');
}

export function renderKpis(container, rows) {
  const totalStudents = rows.length;
  const totalCiac = rows.reduce((acc, row) => acc + row.ciac, 0);
  const totalTalleres = rows.reduce((acc, row) => acc + row.talleres, 0);
  const totalMentorias = rows.reduce((acc, row) => acc + row.mentorias, 0);
  const totalAtenciones = rows.reduce((acc, row) => acc + row.atenciones, 0);
  const withSupport = rows.filter((row) => row.total_apoyos > 0).length;
  const withoutSupport = totalStudents - withSupport;
  const withoutCampus = rows.filter((row) => !row.tiene_campus).length;
  const supportPercent = totalStudents ? ((withSupport / totalStudents) * 100).toFixed(1) : '0.0';

  const cards = [
    ['Total estudiantes únicos', formatNumber(totalStudents), 'Registros únicos en el filtro actual'],
    ['Total CIAC', formatNumber(totalCiac), 'Participaciones CIAC acumuladas'],
    ['Total talleres', formatNumber(totalTalleres), 'Participaciones en talleres'],
    ['Total mentorías', formatNumber(totalMentorias), 'Sesiones de mentoría'],
    ['Total atenciones', formatNumber(totalAtenciones), 'Atenciones individuales'],
    ['% estudiantes con apoyo', `${supportPercent}%`, 'Con al menos un apoyo registrado'],
    ['Total con apoyo', formatNumber(withSupport), 'Estado: Con apoyo'],
    ['Total sin apoyo', formatNumber(withoutSupport), 'Estado: Sin apoyo'],
    ['Registros sin campus', formatNumber(withoutCampus), 'Pendientes de clasificación'],
  ];

  container.innerHTML = cards
    .map(
      ([label, value, hint]) => `
      <article class="kpi-card">
        <div class="kpi-label">${label}</div>
        <div class="kpi-value">${value}</div>
        <div class="kpi-hint">${hint}</div>
      </article>`,
    )
    .join('');
}

export function renderDetail(container, record) {
  if (!record) {
    container.className = 'empty-state';
    container.textContent = 'Selecciona una fila para ver información del estudiante.';
    return;
  }

  container.className = 'detail-block';
  container.innerHTML = `
    <div>
      <p class="detail-name">${record.nombre}</p>
      <p class="detail-meta">RUT: ${record.rut} · Campus: ${record.campus}</p>
    </div>
    <div class="detail-stats">
      <div class="stat-item"><span>CIAC</span><strong>${record.ciac}</strong></div>
      <div class="stat-item"><span>Talleres</span><strong>${record.talleres}</strong></div>
      <div class="stat-item"><span>Mentorías</span><strong>${record.mentorias}</strong></div>
      <div class="stat-item"><span>Atenciones</span><strong>${record.atenciones}</strong></div>
      <div class="stat-item"><span>Total apoyos</span><strong>${record.total_apoyos}</strong></div>
      <div class="stat-item"><span>Estado</span><strong>${record.estado}</strong></div>
    </div>
    <div>
      <small class="text-muted d-block mb-1">Observaciones de calidad</small>
      <div>${record.observaciones || 'Sin observaciones registradas.'}</div>
    </div>`;
}

export function updateCounters(recordsCounter, missingCampusCounter, rows) {
  const missing = rows.filter((row) => !row.tiene_campus).length;
  recordsCounter.textContent = `${formatNumber(rows.length)} resultados`;
  missingCampusCounter.textContent = `${formatNumber(missing)} sin campus`;
}
