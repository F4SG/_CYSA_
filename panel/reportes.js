import {emptyRow, rowCells, setStatus} from './project-api.js';

const $ = id => document.getElementById(id);
const labels = {operacion: 'Operación', validacion: 'Validación'};
const number = new Intl.NumberFormat('es');
const metrics = row => [row.autos, row.motos, row.micros, row.total];
const columns = row => [labels[row.prueba ? 'validacion' : 'operacion'], row.interseccion, row.acceso, row.carril];
let read;
let current;
let loading = false;

function clearReport() {
    current = null;
    $('reportResults').hidden = true;
    $('reportCsv').disabled = true;
    setStatus($('reportStatus'));
}

function query() {
    const start = new Date($('reportDesde').value);
    const end = new Date($('reportHasta').value);
    if (!Number.isFinite(+start) || !Number.isFinite(+end) || start >= end || end - start > 31 * 86400000) {
        throw new Error('Elige un período válido de hasta 31 días.');
    }
    const params = new URLSearchParams({desde: start.toISOString(), hasta: end.toISOString()});
    if ($('reportIntersection').value) params.set('interseccion', $('reportIntersection').value);
    const context = $('reportContext').value;
    if (context !== 'todos') params.set('prueba', String(context === 'validacion'));
    return params;
}

function render(report, context, intersection) {
    const select = $('reportIntersection');
    const options = new Set(report.intersecciones);
    if (intersection) options.add(intersection);
    select.replaceChildren(new Option('Todas', ''), ...[...options].sort().map(id => new Option(id, id)));
    select.value = intersection;
    const contexts = context === 'todos' ? Object.keys(labels) : [context];
    $('reportSummary').replaceChildren(...contexts.map(key =>
        rowCells([labels[key], ...metrics(report.resumen[key]).map(value => number.format(value))])));
    const rows = report.items.map(row =>
        rowCells([...columns(row), ...metrics(row).map(value => number.format(value))]));
    $('reportBody').replaceChildren(...(rows.length ? rows : [emptyRow(8, 'Sin conteos para este período y estos filtros.')]));
    $('reportResults').hidden = false;
    $('reportCsv').disabled = rows.length === 0;
}

export async function loadReports() {
    if (loading) return false;
    clearReport();
    const status = $('reportStatus');
    const form = $('reportFilters');
    loading = true;
    form.disabled = true;
    try {
        const params = query();
        setStatus(status, 'Consultando conteos…');
        const report = await read('/reportes/conteos?' + params);
        render(report, $('reportContext').value, params.get('interseccion') || '');
        current = report;
        setStatus(status);
        return true;
    } catch (error) {
        setStatus(status, error.message, true);
        return false;
    } finally {
        form.disabled = false;
        loading = false;
    }
}

function csvCell(value) {
    const text = String(value);
    const safe = /^[=+@\-\t\r\n]/.test(text) ? "'" + text : text;
    return '"' + safe.replaceAll('"', '""') + '"';
}

function downloadReport() {
    if (!current?.items.length) return;
    const headings = ['Contexto', 'Intersección', 'Acceso', 'Carril', 'Autos', 'Motos', 'Micros', 'Total', 'Desde UTC', 'Hasta UTC (exclusivo)'];
    const rows = current.items.map(row => [...columns(row), ...metrics(row), current.desde, current.hasta]);
    const csv = [headings, ...rows].map(row => row.map(csvCell).join(';')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF', csv], {type: 'text/csv;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'CYSA_Reporte_Conteos.csv';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function initReports(api, localDate) {
    read = api;
    const now = Date.now();
    $('reportDesde').value = localDate(new Date(now - 86400000));
    $('reportHasta').value = localDate(new Date(now + 60000));
    $('reportForm').addEventListener('input', clearReport);
    $('reportForm').addEventListener('submit', event => {
        event.preventDefault();
        loadReports();
    });
    $('reportCsv').addEventListener('click', downloadReport);
}
