export function createMainTable(selector, onRowSelected) {
  return new Tabulator(selector, {
    layout: 'fitColumns',
    height: 470,
    pagination: true,
    paginationSize: 15,
    paginationSizeSelector: [15, 30, 50, 100],
    movableColumns: true,
    placeholder: 'Sin registros para los filtros aplicados.',
    initialSort: [{ column: 'total_apoyos', dir: 'desc' }],
    columns: [
      { title: 'RUT', field: 'rut', minWidth: 130 },
      { title: 'Nombre', field: 'nombre', minWidth: 220, headerFilter: 'input' },
      { title: 'Campus', field: 'campus', minWidth: 130, headerFilter: 'list' },
      { title: 'CIAC', field: 'ciac', hozAlign: 'right', width: 90 },
      { title: 'Talleres', field: 'talleres', hozAlign: 'right', width: 100 },
      { title: 'Mentorías', field: 'mentorias', hozAlign: 'right', width: 100 },
      { title: 'Atenciones', field: 'atenciones', hozAlign: 'right', width: 105 },
      { title: 'Total apoyos', field: 'total_apoyos', hozAlign: 'right', width: 120 },
      { title: 'Estado', field: 'estado', width: 105 },
      { title: 'Observación/calidad', field: 'calidad', minWidth: 170 },
    ],
    rowClick: (_, row) => onRowSelected(row.getData()),
  });
}

export function updateMainTable(table, rows) {
  table.setData(rows);
}
