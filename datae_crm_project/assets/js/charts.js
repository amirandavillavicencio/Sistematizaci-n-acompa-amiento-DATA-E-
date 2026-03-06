function buildChart(id, config) {
  return new Chart(document.getElementById(id), {
    ...config,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
      ...config.options,
    },
  });
}

export function createCharts() {
  return {
    campus: buildChart('chartCampus', {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Participaciones totales', data: [], backgroundColor: ['#1d4ed8', '#2563eb', '#64748b'] }] },
      options: { scales: { y: { beginAtZero: true } }, plugins: { legend: { display: false } } },
    }),
    supportType: buildChart('chartSupportType', {
      type: 'doughnut',
      data: { labels: ['CIAC', 'Talleres', 'Mentorías', 'Atenciones'], datasets: [{ data: [0, 0, 0, 0], backgroundColor: ['#1d4ed8', '#3b82f6', '#0ea5e9', '#93c5fd'] }] },
    }),
    status: buildChart('chartSupportStatus', {
      type: 'pie',
      data: { labels: ['Con apoyo', 'Sin apoyo'], datasets: [{ data: [0, 0], backgroundColor: ['#0f766e', '#cbd5e1'] }] },
    }),
    quality: buildChart('chartQuality', {
      type: 'bar',
      data: { labels: ['RUT sin campus', 'Con observaciones calidad'], datasets: [{ data: [0, 0], backgroundColor: ['#f59e0b', '#ef4444'] }] },
      options: { scales: { y: { beginAtZero: true } }, plugins: { legend: { display: false } } },
    }),
  };
}

export function updateCharts(charts, rows) {
  const campusTotals = rows.reduce((acc, row) => {
    const campus = row.campus || 'Sin Campus';
    acc[campus] = (acc[campus] || 0) + row.total_apoyos;
    return acc;
  }, {});
  const campusEntries = Object.entries(campusTotals).sort((a, b) => b[1] - a[1]);
  charts.campus.data.labels = campusEntries.map(([label]) => label);
  charts.campus.data.datasets[0].data = campusEntries.map(([, value]) => value);

  charts.supportType.data.datasets[0].data = [
    rows.reduce((acc, row) => acc + row.conteo_ciac, 0),
    rows.reduce((acc, row) => acc + row.conteo_talleres, 0),
    rows.reduce((acc, row) => acc + row.conteo_mentorias, 0),
    rows.reduce((acc, row) => acc + row.conteo_atenciones, 0),
  ];

  const withSupport = rows.filter((row) => row.tiene_apoyo).length;
  charts.status.data.datasets[0].data = [withSupport, rows.length - withSupport];

  charts.quality.data.datasets[0].data = [
    rows.filter((row) => row.sin_campus).length,
    rows.filter((row) => row.issues_count > 0 || row.observacion_calidad).length,
  ];

  Object.values(charts).forEach((chart) => chart.update());
}
