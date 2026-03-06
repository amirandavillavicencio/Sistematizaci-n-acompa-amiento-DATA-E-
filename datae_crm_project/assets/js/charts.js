function buildChart(id, config) {
  return new Chart(document.getElementById(id), {
    ...config,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      events: ['mousemove', 'mouseout', 'click', 'touchstart', 'touchmove'],
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 10, boxHeight: 10, color: '#475569', font: { size: 11, weight: 600 } },
        },
        tooltip: { enabled: true },
      },
      ...config.options,
    },
  });
}

export function createCharts() {
  return {
    campus: buildChart('chartCampus', {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Estudiantes con apoyo', data: [], backgroundColor: ['#1e40af', '#3b82f6'], borderRadius: 6 }] },
      options: { scales: { y: { beginAtZero: true, grid: { color: '#e2e8f0' } }, x: { grid: { display: false } } }, plugins: { legend: { display: false } } },
    }),
    supportType: buildChart('chartSupportType', {
      type: 'doughnut',
      data: { labels: ['CIAC', 'Talleres', 'Mentorías', 'Atenciones'], datasets: [{ data: [0, 0, 0, 0], backgroundColor: ['#1e40af', '#2563eb', '#0ea5e9', '#93c5fd'], borderWidth: 0 }] },
    }),
    status: buildChart('chartSupportStatus', {
      type: 'pie',
      data: { labels: ['Con apoyo', 'Sin apoyo'], datasets: [{ data: [0, 0], backgroundColor: ['#16a34a', '#cbd5e1'], borderWidth: 0 }] },
    }),
    quality: buildChart('chartQuality', {
      type: 'bar',
      data: { labels: ['RUT sin campus', 'Con observaciones calidad'], datasets: [{ data: [0, 0], backgroundColor: ['#f59e0b', '#ef4444'], borderRadius: 6 }] },
      options: { scales: { y: { beginAtZero: true, grid: { color: '#e2e8f0' } }, x: { grid: { display: false } } }, plugins: { legend: { display: false } } },
    }),
  };
}

export function updateCharts(charts, rows, missingCampusRows = []) {
  const campusTotals = rows.reduce((acc, row) => {
    if (!row.origen_base || row.origen_base === 'Sin base campus') return acc;
    if (!acc[row.origen_base]) acc[row.origen_base] = { total: 0, withSupport: 0 };
    acc[row.origen_base].total += 1;
    if (row.tiene_apoyo) acc[row.origen_base].withSupport += 1;
    return acc;
  }, {});

  const campusEntries = Object.entries(campusTotals).sort((a, b) => b[1].withSupport - a[1].withSupport);
  charts.campus.data.labels = campusEntries.map(([label]) => label);
  charts.campus.data.datasets[0].data = campusEntries.map(([, value]) => value.withSupport);

  charts.supportType.data.datasets[0].data = [
    rows.reduce((acc, row) => acc + row.conteo_ciac, 0),
    rows.reduce((acc, row) => acc + row.conteo_talleres, 0),
    rows.reduce((acc, row) => acc + row.conteo_mentorias, 0),
    rows.reduce((acc, row) => acc + row.conteo_atenciones, 0),
  ];

  const withSupport = rows.filter((row) => row.tiene_apoyo).length;
  charts.status.data.datasets[0].data = [withSupport, rows.length - withSupport];

  charts.quality.data.datasets[0].data = [
    missingCampusRows.length,
    rows.filter((row) => row.issues_count > 0 || row.observacion_calidad).length,
  ];

  Object.values(charts).forEach((chart) => chart.update());
}
