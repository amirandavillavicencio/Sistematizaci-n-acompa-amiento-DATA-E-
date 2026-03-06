function buildChart(ctx, config) {
  return new Chart(ctx, {
    ...config,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' },
      },
      ...config.options,
    },
  });
}

export function createCharts() {
  return {
    byCampus: buildChart(document.getElementById('chartCampus'), {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Estudiantes', data: [], backgroundColor: '#2563eb' }] },
      options: { scales: { y: { beginAtZero: true } }, plugins: { legend: { display: false } } },
    }),
    byType: buildChart(document.getElementById('chartSupportType'), {
      type: 'doughnut',
      data: {
        labels: ['CIAC', 'Talleres', 'Mentorías', 'Atenciones'],
        datasets: [{ data: [0, 0, 0, 0], backgroundColor: ['#1d4ed8', '#2563eb', '#3b82f6', '#93c5fd'] }],
      },
    }),
    supportStatus: buildChart(document.getElementById('chartSupportStatus'), {
      type: 'pie',
      data: {
        labels: ['Con apoyo', 'Sin apoyo'],
        datasets: [{ data: [0, 0], backgroundColor: ['#0f766e', '#cbd5e1'] }],
      },
    }),
    missingCampus: buildChart(document.getElementById('chartMissingCampus'), {
      type: 'bar',
      data: {
        labels: ['Con campus', 'Sin campus'],
        datasets: [{ data: [0, 0], backgroundColor: ['#1e40af', '#f59e0b'] }],
      },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    }),
    intensity: buildChart(document.getElementById('chartIntensity'), {
      type: 'bar',
      data: {
        labels: ['0', '1-2', '3-5', '6+'],
        datasets: [{ label: 'Estudiantes', data: [0, 0, 0, 0], backgroundColor: '#334155' }],
      },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    }),
  };
}

export function updateCharts(charts, rows) {
  const campusMap = rows.reduce((acc, row) => {
    const campus = row.campus || 'Sin Campus';
    acc[campus] = (acc[campus] || 0) + 1;
    return acc;
  }, {});

  const orderedCampuses = Object.entries(campusMap).sort((a, b) => b[1] - a[1]);
  charts.byCampus.data.labels = orderedCampuses.map(([name]) => name);
  charts.byCampus.data.datasets[0].data = orderedCampuses.map(([, value]) => value);

  charts.byType.data.datasets[0].data = [
    rows.reduce((sum, r) => sum + r.ciac, 0),
    rows.reduce((sum, r) => sum + r.talleres, 0),
    rows.reduce((sum, r) => sum + r.mentorias, 0),
    rows.reduce((sum, r) => sum + r.atenciones, 0),
  ];

  const withSupport = rows.filter((r) => r.total_apoyos > 0).length;
  charts.supportStatus.data.datasets[0].data = [withSupport, rows.length - withSupport];

  const missingCampusCount = rows.filter((r) => !r.tiene_campus).length;
  charts.missingCampus.data.datasets[0].data = [rows.length - missingCampusCount, missingCampusCount];

  const intensityBins = [0, 0, 0, 0];
  rows.forEach((r) => {
    if (r.total_apoyos === 0) intensityBins[0] += 1;
    else if (r.total_apoyos <= 2) intensityBins[1] += 1;
    else if (r.total_apoyos <= 5) intensityBins[2] += 1;
    else intensityBins[3] += 1;
  });
  charts.intensity.data.datasets[0].data = intensityBins;

  Object.values(charts).forEach((chart) => chart.update());
}
