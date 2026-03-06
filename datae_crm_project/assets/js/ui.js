const formatNumber = (value) => Number(value || 0).toLocaleString('es-CL');

export function fillSelect(select, options) {
  select.innerHTML = options.map((opt) => `<option value="${opt}">${opt}</option>`).join('');
}

export function renderKpis(container, rows) {
  const baseSJ = rows.filter((row) => row.origen_base === 'San Joaquín').length;
  const baseVit = rows.filter((row) => row.origen_base === 'Vitacura').length;
  const total = rows.length;
  const conApoyo = rows.filter((row) => row.tiene_apoyo).length;
  const sinApoyo = total - conApoyo;
  const ciac = rows.reduce((acc, row) => acc + row.conteo_ciac, 0);
  const talleres = rows.reduce((acc, row) => acc + row.conteo_talleres, 0);
  const mentorias = rows.reduce((acc, row) => acc + row.conteo_mentorias, 0);
  const atenciones = rows.reduce((acc, row) => acc + row.conteo_atenciones, 0);
  const sinCampus = rows.filter((row) => row.sin_campus).length;
  const pct = total ? ((conApoyo / total) * 100).toFixed(1) : '0.0';

  const cards = [
    ['Base San Joaquín', formatNumber(baseSJ)],
    ['Base Vitacura', formatNumber(baseVit)],
    ['Total estudiantes únicos', formatNumber(total)],
    ['Total con apoyo', formatNumber(conApoyo)],
    ['Total sin apoyo', formatNumber(sinApoyo)],
    ['Participaciones CIAC', formatNumber(ciac)],
    ['Participaciones Talleres', formatNumber(talleres)],
    ['Participaciones Mentorías', formatNumber(mentorias)],
    ['Participaciones Atenciones', formatNumber(atenciones)],
    ['Total RUT sin campus', formatNumber(sinCampus)],
    ['% estudiantes con apoyo', `${pct}%`],
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
      <p class="detail-meta">Presencia en lista base: ${record.presencia_lista_base ? 'Sí' : 'No'} · Origen base: ${record.origen_base}</p>
    </div>
    <div class="detail-stats">
      <div class="stat-item"><span>CIAC</span><strong>${record.conteo_ciac}</strong></div>
      <div class="stat-item"><span>Talleres</span><strong>${record.conteo_talleres}</strong></div>
      <div class="stat-item"><span>Mentorías</span><strong>${record.conteo_mentorias}</strong></div>
      <div class="stat-item"><span>Atenciones</span><strong>${record.conteo_atenciones}</strong></div>
      <div class="stat-item"><span>Total apoyos</span><strong>${record.total_apoyos}</strong></div>
      <div class="stat-item"><span>Estado</span><strong>${record.estado}</strong></div>
    </div>
    <div>
      <small class="text-muted d-block mb-1">Fuentes detectadas</small>
      <div>${record.fuentes_detectadas.join(', ') || 'Sin fuentes identificadas'}</div>
    </div>
    <div>
      <small class="text-muted d-block mb-1">Observaciones/calidad</small>
      <div>${record.observacion_calidad || 'Sin observaciones registradas.'}</div>
    </div>
  `;
}

export function updateCounters(recordsCounter, missingCounter, rows) {
  recordsCounter.textContent = `${formatNumber(rows.length)} resultados`;
  missingCounter.textContent = `${formatNumber(rows.filter((row) => row.sin_campus).length)} sin campus`;
}
