import * as oidc from './oidc.js';
import {serviceUrl} from './navigation.js';

let readingConfig;

export async function projectRequest(service, path, {method = 'GET', body, motivo} = {}) {
    readingConfig ??= fetch('/config.json', {cache: 'no-store'})
        .then(response => {
            if (!response.ok) throw new Error('No se pudo leer la configuración de CYSA.');
            return response.json();
        }).finally(() => { readingConfig = null; });
    const url = serviceUrl(await readingConfig, service, path);
    const headers = {Authorization: 'Bearer ' + await oidc.accessToken()};
    if (motivo) headers['X-CYSA-Motivo'] = encodeURIComponent(motivo);
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    let response;
    try {
        response = await fetch(url, {
            method, headers, cache: 'no-store', redirect: 'error',
            body: body === undefined ? undefined : JSON.stringify(body),
            signal: AbortSignal.timeout(15000),
        });
    } catch {
        throw new Error('El servicio no respondió. Comprueba que CYSA esté iniciado.');
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
        const error = new Error(data?.title || (typeof data?.detail === 'string' ? data.detail : null)
            || (response.status === 403 ? 'Tu sesión no tiene permiso para esta acción.' : `El servicio respondió HTTP ${response.status}.`));
        error.status = response.status;
        throw error;
    }
    return data;
}

export function rememberDraft(view, data) {
    sessionStorage.setItem('cysa.project-draft', JSON.stringify({
        view, data, subject: oidc.subject(), created: Date.now(),
    }));
}

export function takeDraft() {
    const raw = sessionStorage.getItem('cysa.project-draft');
    sessionStorage.removeItem('cysa.project-draft');
    if (!raw) return null;
    try {
        const draft = JSON.parse(raw);
        const age = Date.now() - draft.created;
        return draft.subject === oidc.subject() && age >= 0 && age < 600000 ? draft : null;
    } catch { return null; }
}

export function rowCells(values) {
    const row = document.createElement('tr');
    for (const value of values) {
        const cell = row.insertCell();
        cell.textContent = value ?? '—';
    }
    return row;
}

export function emptyRow(columns, message) {
    const row = rowCells([message]);
    row.cells[0].colSpan = columns;
    row.cells[0].className = 'empty';
    return row;
}

export function setStatus(element, message = '', error = false) {
    element.textContent = message;
    element.classList.toggle('error', error);
}
