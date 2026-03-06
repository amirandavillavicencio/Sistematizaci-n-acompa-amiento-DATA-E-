function buildChart(canvasId, config) {
  const canvas = document.getElementById(canvasId);
  return new Chart(canvas, {
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
    byCampus: buildChart('chartCampus', {
      type: 'bar',
      data: { labels: [], datasets: [{ label: 'Estudiantes', data: [], backgroundColor: '#1d4ed8' }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } },
    }),
    byType: buildChart('chartSupportType', {
      type: 'doughnut',
      data: {
        labels: ['CIAC', 'Talleres', 'Mentorías', 'Atenciones'],
        datasets: [{ data: [0, 0, 0, 0], backgroundColor: ['#1d4ed8', '#2563eb', '#3b82f6', '#93c5fd'] }],
      },
    }),
    supportStatus: buildChart('chartSupportStatus', {
      type: 'pie',
      data: { labels: ['Con apoyo', 'Sin apoyo'], datasets: [{ data: [0, 0], backgroundColor: ['#0f766e', '#cbd5e1'] }] },
    }),
    missingCampus: buildChart('chartMissingCampus', {
      type: 'bar',
      data: {
        labels: ['Con campus', 'Sin campus'],
        datasets: [{ data: [0, 0], backgroundColor: ['#1e40af', '#f59e0b'] }],
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

  const campusData = Object.entries(campusMap).sort((a, b) => b[1] - a[1]);
  charts.byCampus.data.labels = campusData.map(([name]) => name);
  charts.byCampus.data.datasets[0].data = campusData.map(([, count]) => count);

  charts.byType.data.datasets[0].data = [
    rows.reduce((acc, row) => acc + row.ciac, 0),
    rows.reduce((acc, row) => acc + row.talleres, 0),
    rows.reduce((acc, row) => acc + row.mentorias, 0),
    rows.reduce((acc, row) => acc + row.atenciones, 0),
  ];

  const withSupport = rows.filter((row) => row.total_apoyos > 0).length;
  charts.supportStatus.data.datasets[0].data = [withSupport, rows.length - withSupport];

  const missingCampus = rows.filter((row) => !row.tiene_campus).length;
  charts.missingCampus.data.datasets[0].data = [rows.length - missingCampus, missingCampus];

  Object.values(charts).forEach((chart) => chart.update());
}
