import * as oidc from './oidc.js';
import {projectRequest, rememberDraft, rowCells, emptyRow, setStatus} from './project-api.js';

const $ = id => document.getElementById(id);
const resource = (path, options) => projectRequest('webApiBase', '/api/proyecto/' + path, options);
const pageSize = 15;
const date = value => value ? new Date(value).toLocaleString('es') : '—';
const localInput = value => {
    const time = new Date(value);
    return new Date(+time - time.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const views = {
    configuraciones: {
        headings: ['Intersección', 'Versión', 'Verde (s)', 'Ámbar / todo rojo (s)', 'Aprobación', 'Estado'],
        cells: item => [
            intersections.get(item.interseccionId) || item.interseccionId, item.version,
            `${item.verdeMinSegundos}–${item.verdeMaxSegundos}`, `${item.ambarSegundos} / ${item.todoRojoSegundos}`,
            `${item.responsableTecnico} · ${date(item.aprobadaUtc)}`, item.estado,
        ],
    },
    bitacoras: {
        headings: ['Fecha', 'Usuario (ID)', 'Operación', 'Objeto', 'Motivo', 'Valor anterior', 'Valor nuevo', 'MFA'],
        cells: item => [date(item.fechaUtc), item.usuarioId, item.operacion, `${item.objetoTipo} · ${item.objetoId}`,
            item.motivo, item.valorAnterior, item.valorPosterior, item.mfaVerificado ? 'Verificada' : '—'],
    },
    'versiones-modelo': {
        headings: ['Tipo', 'Identificador', 'Descripción', 'Estado', 'Activación'],
        cells: item => [item.tipo, item.identificador, item.descripcion, item.estado, date(item.activadaUtc)],
    },
};
let intersections = new Map();
let selected = 'configuraciones';
let page = 1;
let generation = 0;
let loaded = false;
let action;

export async function loadConfigurations({reloadIntersections = false} = {}) {
    if (reloadIntersections) loaded = false;
    const current = ++generation;
    const view = selected;
    const requestedPage = page;
    const status = $('configStatus');
    const admin = oidc.hasRole('administrador');
    const editable = view === 'configuraciones' && admin;
    const table = views[view];
    const columns = [...table.headings, ...(editable ? ['Acciones'] : [])];
    $('configNew').hidden = !editable;
    $('configNew').disabled = true;
    $('configPrevious').disabled = $('configNext').disabled = true;
    $('configHelp').hidden = view !== 'versiones-modelo';
    $('configHead').replaceChildren(...columns.map(title => {
        const cell = document.createElement('th');
        cell.scope = 'col';
        cell.textContent = title;
        return cell;
    }));
    $('configBody').replaceChildren(emptyRow(columns.length, 'Cargando registros…'));
    setStatus(status);
    try {
        const [items, available] = await Promise.all([
            resource(`${view}?pagina=${requestedPage}&tamano=${pageSize}`),
            view === 'configuraciones' && !loaded ? resource('intersecciones?tamano=100') : null,
        ]);
        if (current !== generation) return;
        if (available) {
            intersections = new Map(available.map(item => [item.id, item.nombre]));
            $('configForm').elements.interseccionId.replaceChildren(...available.map(item => new Option(item.nombre, item.id)));
            loaded = true;
        }
        $('configNew').disabled = intersections.size === 0;
        const rows = items.map(item => {
            const row = rowCells(table.cells(item));
            if (editable) {
                const cell = row.insertCell();
                cell.className = 'module-actions';
                for (const [label, method] of [['Editar', 'PUT'], ['Eliminar', 'DELETE']]) {
                    const button = document.createElement('button');
                    button.textContent = label;
                    button.onclick = () => openEditor({method, id: item.id, values: item});
                    cell.append(button);
                }
            }
            return row;
        });
        $('configBody').replaceChildren(...(rows.length ? rows : [emptyRow(columns.length, 'No hay registros.')]));
        $('configPage').textContent = 'Página ' + page;
        $('configPrevious').disabled = page === 1;
        $('configNext').disabled = items.length < pageSize;
    } catch (error) {
        if (current !== generation) return;
        $('configBody').replaceChildren(emptyRow(columns.length, 'No se pudo cargar esta consulta.'));
        setStatus(status, error.message, true);
    }
}

function openEditor(draft, restored = false) {
    action = draft;
    const form = $('configForm');
    const removing = draft.method === 'DELETE';
    $('configEditorTitle').textContent = removing ? 'Eliminar configuración'
        : draft.id ? 'Editar configuración' : 'Nueva configuración';
    $('configEditorFields').disabled = removing;
    $('configEditorFields').hidden = removing;
    $('configSave').textContent = removing ? 'Eliminar' : 'Guardar configuración';
    $('configEditorMessage').textContent = removing
        ? `Se eliminará la configuración ${draft.id} si no tiene referencias.`
        : 'La versión aprobada se usa al generar nuevas propuestas del banco.';
    form.reset();
    document.getElementById('configMotivo').value = draft.motivo || '';
    form.elements.aprobadaUtc.value = localInput(Date.now());
    for (const [name, value] of Object.entries(draft.values || {})) {
        const input = form.elements.namedItem(name);
        if (!input) continue;
        if (input.type === 'checkbox') input.checked = Boolean(value);
        else input.value = input.type === 'datetime-local' ? localInput(value) : value;
    }
    setStatus($('configEditorStatus'), restored ? 'Revisa los datos y confirma la operación.' : '');
    $('configEditor').showModal();
}

export function restoreConfiguration(draft) {
    if (oidc.hasRole('administrador')) openEditor(draft, true);
}

export function initConfigurations() {
    $('configNew').onclick = () => openEditor({method: 'POST'});
    $('configCancel').onclick = () => $('configEditor').close();
    $('configRefresh').onclick = loadConfigurations;
    $('configPrevious').onclick = () => { if (page > 1) { page--; loadConfigurations(); } };
    $('configNext').onclick = () => { page++; loadConfigurations(); };
    document.querySelectorAll('[data-config-view]').forEach(button => {
        button.onclick = () => {
            selected = button.dataset.configView;
            page = 1;
            document.querySelectorAll('[data-config-view]').forEach(tab => tab.setAttribute('aria-pressed', String(tab === button)));
            loadConfigurations();
        };
    });
    $('configForm').onsubmit = async event => {
        event.preventDefault();
        const status = $('configEditorStatus');
        const save = $('configSave');
        const {method, id} = action;
        const motivo = document.getElementById('configMotivo').value.trim();
        if (!motivo) { setStatus(status, 'Escribe el motivo del cambio.', true); return; }
        const values = {};
        if (method !== 'DELETE') {
            for (const input of $('configEditorFields').querySelectorAll('[name]')) {
                values[input.name] = input.type === 'checkbox' ? input.checked
                    : input.type === 'number' || input.name === 'interseccionId' ? Number(input.value)
                    : input.type === 'datetime-local' ? new Date(input.value).toISOString() : input.value.trim();
            }
        }
        save.disabled = true;
        try {
            if (!oidc.mfaReady()) {
                rememberDraft('configuraciones', {method, id, values, motivo});
                await oidc.login({mfa: true});
                return;
            }
            await resource('configuraciones' + (id ? '/' + id : ''), {
                method, motivo, body: method === 'DELETE' ? undefined : values,
            });
            $('configEditor').close();
            await loadConfigurations();
            if (!$('configStatus').classList.contains('error')) {
                setStatus($('configStatus'), method === 'DELETE' ? 'Configuración eliminada.' : 'Configuración guardada.');
            }
        } catch (error) { setStatus(status, error.message, true); }
        finally { save.disabled = false; }
    };
}
