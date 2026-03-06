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
      data: {
        labels: [],
        datasets: [
          { label: 'Total estudiantes', data: [], backgroundColor: '#1e40af', borderRadius: 6 },
          { label: 'Total apoyos', data: [], backgroundColor: '#38bdf8', borderRadius: 6 },
        ],
      },
      options: { scales: { y: { beginAtZero: true, grid: { color: '#e2e8f0' } }, x: { grid: { display: false } } } },
    }),
    supportType: buildChart('chartSupportType', {
      type: 'bar',
      data: {
        labels: ['Talleres', 'Mentorías', 'CIAC', 'Atenciones individuales', 'Tutoría par'],
        datasets: [{ label: 'Participaciones', data: [0, 0, 0, 0, 0], backgroundColor: ['#2563eb', '#14b8a6', '#1e3a8a', '#f59e0b', '#8b5cf6'], borderRadius: 6 }],
      },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#e2e8f0' } }, x: { grid: { display: false } } } },
    }),
    status: buildChart('chartSupportStatus', {
      type: 'doughnut',
      data: { labels: ['Con apoyo', 'Sin apoyo'], datasets: [{ data: [0, 0], backgroundColor: ['#16a34a', '#cbd5e1'], borderWidth: 0 }] },
    }),
    intensity: buildChart('chartIntensity', {
      type: 'bar',
      data: { labels: ['Bajo apoyo', 'Medio apoyo', 'Alto apoyo', 'Sin apoyo'], datasets: [{ label: 'Estudiantes', data: [0, 0, 0, 0], backgroundColor: ['#f59e0b', '#3b82f6', '#1d4ed8', '#cbd5e1'], borderRadius: 6 }] },
      options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: '#e2e8f0' } }, x: { grid: { display: false } } } },
    }),
    quality: buildChart('chartQuality', {
      type: 'bar',
      data: { labels: ['RUT duplicados', 'Inconsistencias', 'Mezcla marca/conteo'], datasets: [{ data: [0, 0, 0], backgroundColor: ['#ef4444', '#f97316', '#eab308'], borderRadius: 6 }] },
      options: { scales: { y: { beginAtZero: true, grid: { color: '#e2e8f0' } }, x: { grid: { display: false } } }, plugins: { legend: { display: false } } },
    }),
    missingCampusSource: buildChart('chartMissingCampusSource', {
      type: 'pie',
      data: { labels: [], datasets: [{ data: [], backgroundColor: ['#0ea5e9', '#22c55e', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'], borderWidth: 0 }] },
    }),
  };
}

export function updateCharts(charts, rows, missingCampusRows = [], qualityStats = {}) {
  const campusTotals = rows.reduce((acc, row) => {
    const campus = row.origen_base || row.campus || 'Sin campus';
    if (!acc[campus]) acc[campus] = { total: 0, totalSupport: 0 };
    acc[campus].total += 1;
    acc[campus].totalSupport += Number(row.total_sesiones || row.total_apoyos || 0);
    return acc;
  }, {});

  const campusEntries = Object.entries(campusTotals).sort((a, b) => b[1].total - a[1].total);
  charts.campus.data.labels = campusEntries.map(([label]) => label);
  charts.campus.data.datasets[0].data = campusEntries.map(([, value]) => value.total);
  charts.campus.data.datasets[1].data = campusEntries.map(([, value]) => value.totalSupport);

  charts.supportType.data.datasets[0].data = [
    rows.reduce((acc, row) => acc + Number(row.conteo_talleres || 0), 0),
    rows.reduce((acc, row) => acc + Number(row.conteo_mentorias || 0), 0),
    rows.reduce((acc, row) => acc + Number(row.conteo_ciac || 0), 0),
    rows.reduce((acc, row) => acc + Number(row.conteo_atenciones || 0), 0),
    rows.reduce((acc, row) => acc + Number(row.conteo_tutoria_par || 0), 0),
  ];

  const withSupport = rows.filter((row) => row.tiene_apoyo).length;
  charts.status.data.datasets[0].data = [withSupport, rows.length - withSupport];

  const intensityCounts = rows.reduce((acc, row) => {
    const key = row.intensidad_apoyo || 'Sin apoyo';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  charts.intensity.data.datasets[0].data = [
    intensityCounts['Bajo apoyo'] || 0,
    intensityCounts['Medio apoyo'] || 0,
    intensityCounts['Alto apoyo'] || 0,
    intensityCounts['Sin apoyo'] || 0,
  ];

  charts.quality.data.datasets[0].data = [
    qualityStats.duplicatedRuts || 0,
    qualityStats.inconsistentRecords || 0,
    qualityStats.mixedCountMarkRecords || 0,
  ];

  const sourceTotals = missingCampusRows.reduce((acc, row) => {
    const sources = row.fuentes_detectadas?.length ? row.fuentes_detectadas : ['Sin fuente'];
    sources.forEach((source) => {
      acc[source] = (acc[source] || 0) + 1;
    });
    return acc;
  }, {});
  const sourceEntries = Object.entries(sourceTotals).sort((a, b) => b[1] - a[1]).slice(0, 6);
  charts.missingCampusSource.data.labels = sourceEntries.map(([source]) => source);
  charts.missingCampusSource.data.datasets[0].data = sourceEntries.map(([, count]) => count);

  Object.values(charts).forEach((chart) => chart.update());
}
