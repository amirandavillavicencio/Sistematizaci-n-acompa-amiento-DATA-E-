export function createMainTable(selector, onRowSelected) {
  return new Tabulator(selector, {
    layout: 'fitColumns',
    height: 500,
    pagination: true,
    paginationSize: 20,
    paginationSizeSelector: [20, 50, 100],
    movableColumns: true,
    placeholder: 'Sin registros para los filtros aplicados.',
    initialSort: [{ column: 'total_apoyos', dir: 'desc' }],
    columns: [
      { title: 'RUT', field: 'rut', minWidth: 130 },
      { title: 'Nombre', field: 'nombre', minWidth: 240 },
      { title: 'Campus', field: 'campus', minWidth: 140 },
      { title: 'CIAC', field: 'ciac', hozAlign: 'right', width: 95 },
      { title: 'Talleres', field: 'talleres', hozAlign: 'right', width: 100 },
      { title: 'Mentorías', field: 'mentorias', hozAlign: 'right', width: 105 },
      { title: 'Atenciones', field: 'atenciones', hozAlign: 'right', width: 105 },
      { title: 'Total apoyos', field: 'total_apoyos', hozAlign: 'right', width: 120 },
      { title: 'Estado', field: 'estado', width: 110 },
      { title: 'Calidad de datos', field: 'calidad', minWidth: 170 },
    ],
    rowClick: (_, row) => onRowSelected(row.getData()),
  });
}

export function updateMainTable(table, rows) {
  table.replaceData(rows);
}
