import * as oidc from './oidc.js';
import {projectRequest, rememberDraft, rowCells, emptyRow, setStatus} from './project-api.js';

const $ = id => document.getElementById(id);
const operation = (path, options) => projectRequest('operacionBase', '/api/' + path, options);
const requests = new Map();
let loading = false;
let decision;
const modes = {webster: 'Webster', micros: 'Prioridad para micros', emergencia: 'Emergencia'};
const states = {validado: 'Validado', no_aprobado: 'No aprobado', autorizado: 'Autorizado', rechazado: 'Rechazado'};

export async function loadPlans() {
    if (loading) return;
    loading = true;
    const status = $('plansStatus');
    $('plansRefresh').disabled = true;
    try {
        const [plans, controller] = await Promise.all([
            operation('operacion/planes'), operation('estados'),
        ]);
        const rows = plans.items.map(plan => {
            const doc = plan.documento;
            const gain = plan.validacion.mejora_porcentaje;
            const row = rowCells([
                doc.plan_id, modes[doc.modo] || doc.modo, `${doc.verdes.NS} / ${doc.verdes.EO}`,
                Number.isFinite(gain) ? gain.toFixed(2) + ' %' : null,
                states[plan.estado] || plan.estado, [plan.estado_envio || 'Sin envío', plan.detalle_envio].filter(Boolean).join(' · '),
            ]);
            const buttons = row.insertCell();
            buttons.className = 'module-actions';
            const operations = [['Evidencia', () => openEvidence(plan)]];
            if (plan.estado === 'validado' && oidc.hasRole('operador')) {
                operations.push(['Autorizar', () => openDecision({id: plan.id, label: doc.plan_id, accion: 'autorizar'})]);
                operations.push(['Rechazar', () => openDecision({id: plan.id, label: doc.plan_id, accion: 'rechazar'})]);
            }
            for (const [label, click] of operations) {
                const button = document.createElement('button');
                button.textContent = label;
                button.onclick = click;
                buttons.append(button);
            }
            return row;
        });
        $('plansBody').replaceChildren(...(rows.length ? rows : [emptyRow(7, 'Todavía no hay propuestas evaluadas.')]));
        const reports = controller.items.map(item => {
            const time = Date.parse(item.timestamp);
            const fresh = Number.isFinite(time) && Date.now() - time <= 30000;
            return rowCells([
                item.interseccion, item.fase_actual, item.plan_activo,
                fresh ? item.estado_controlador : 'Sin reporte reciente',
                Number.isFinite(time) ? new Date(time).toLocaleString('es') : '—',
            ]);
        });
        $('controllerBody').replaceChildren(...(reports.length ? reports : [emptyRow(5, 'El emulador aún no ha reportado su estado.')]));
        if (status.classList.contains('error')) setStatus(status);
    } catch (error) { setStatus(status, error.message, true); }
    finally { loading = false; $('plansRefresh').disabled = false; }
}

function openDecision(draft, restored = false) {
    decision = draft;
    const title = draft.accion === 'autorizar' ? 'Autorizar plan' : 'Rechazar plan';
    $('planDecisionTitle').textContent = title;
    $('planDecisionSubmit').textContent = title;
    $('planDecisionName').textContent = draft.label;
    $('planReason').value = draft.motivo || '';
    setStatus($('planDecisionStatus'), restored ? 'Revisa el motivo y confirma tu decisión.' : '');
    $('planDecision').showModal();
}

export function restoreDecision(draft) {
    if (oidc.hasRole('operador')) openDecision(draft, true);
}

async function openEvidence(plan) {
    $('planEvidenceTitle').textContent = plan.documento.plan_id;
    $('planEvidenceData').textContent = '';
    setStatus($('planEvidenceStatus'), 'Cargando evidencia…');
    const dialog = $('planEvidence');
    dialog.showModal();
    try {
        const auditoria = await operation(`operacion/planes/${plan.id}/auditoria`);
        if ($('planEvidenceTitle').textContent !== plan.documento.plan_id) return;
        $('planEvidenceData').textContent = JSON.stringify({
            plan: plan.documento, validacion: plan.validacion, origen: plan.origen, auditoria,
        }, null, 2);
        setStatus($('planEvidenceStatus'));
    } catch (error) { setStatus($('planEvidenceStatus'), error.message, true); }
}

export function initPlans() {
    $('plansRefresh').onclick = loadPlans;
    $('planDecisionCancel').onclick = () => $('planDecision').close();
    $('planEvidenceClose').onclick = () => $('planEvidence').close();
    $('planDecisionForm').onsubmit = async event => {
        event.preventDefault();
        const motivo = $('planReason').value.trim();
        const status = $('planDecisionStatus');
        if (motivo.length < 5) { setStatus(status, 'Escribe un motivo de al menos cinco caracteres.', true); return; }
        const button = $('planDecisionSubmit');
        button.disabled = true;
        try {
            if (!oidc.mfaReady()) {
                rememberDraft('planes', {...decision, motivo});
                await oidc.login({mfa: true});
                return;
            }
            const {id, accion} = decision;
            const key = JSON.stringify([id, accion, motivo]);
            if (!requests.has(key)) requests.set(key, crypto.randomUUID());
            await operation(`operacion/planes/${id}/decisiones`, {
                method: 'POST', body: {solicitud_id: requests.get(key), accion, motivo},
            });
            requests.delete(key);
            $('planDecision').close();
            setStatus($('plansStatus'), 'Decisión registrada.');
            await loadPlans();
        } catch (error) { setStatus(status, error.message, true); }
        finally { button.disabled = false; }
    };
}
