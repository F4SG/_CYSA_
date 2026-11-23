import * as oidc from './oidc.js';
import {projectRequest, rememberDraft, rowCells, emptyRow, setStatus} from './project-api.js';
import {arduinoGuided, arduinoTargetId, initArduinoGuide, renderArduinoGuide, followArduinoPlan} from './arduino.js';

const $ = id => document.getElementById(id);
const operation = (path, options) => projectRequest('operacionBase', '/api/' + path, options);
const requests = new Map();
const resolved = new Map();
let loading;
let plansShown = [];
let renderedPlans = '';
let decision;
let sending = false;
let redirecting = false;
const modes = {webster: 'Webster', micros: 'Prioridad para micros', emergencia: 'Emergencia'};
const states = {validado: 'Validado', no_aprobado: 'No aprobado', autorizado: 'Autorizado',
    rechazado: 'Rechazado', vencido: 'Vencido'};
const evaluationLifetime = 15 * 60 * 1000;
const expiredMessage = 'La evaluación venció; repetir la simulación';
const unavailableMessage = 'Este plan ya no admite una decisión.';
const expired = (plan, now = Date.now()) => plan.estado === 'validado'
    && now - Date.parse(plan.creado) > evaluationLifetime;

function drawPlans() {
    const now = Date.now();
    let available = false;
    const rows = plansShown.map(snapshot => {
        const plan = snapshot.estado === 'validado' ? resolved.get(snapshot.id) || snapshot : snapshot;
        const doc = plan.documento;
        const gain = plan.validacion.mejora_porcentaje;
        const evaluationExpired = expired(plan, now);
        const canDecide = plan.estado === 'validado' && !evaluationExpired && !resolved.has(plan.id);
        available ||= canDecide;
        const row = rowCells([
            doc.plan_id, modes[doc.modo] || doc.modo, `${doc.verdes.NS} / ${doc.verdes.EO}`,
            Number.isFinite(gain) ? gain.toFixed(2) + ' %' : null,
            evaluationExpired ? 'Vencido' : states[plan.estado] || plan.estado,
            [plan.estado_envio || 'Sin envío', plan.detalle_envio].filter(Boolean).join(' · '),
        ]);
        const buttons = row.insertCell();
        buttons.className = 'module-actions';
        const operations = [['Evidencia', () => openEvidence(plan)]];
        if (canDecide && oidc.hasRole('operador')) {
            for (const [label, accion] of [['Autorizar', 'autorizar'], ['Rechazar', 'rechazar']]) {
                operations.push([label, () => openDecision({id: plan.id, label: doc.plan_id, accion}),
                    sending && decision?.id === plan.id]);
            }
        }
        for (const [label, click, disabled = false] of operations) {
            const button = document.createElement('button');
            button.textContent = label;
            button.disabled = disabled;
            button.onclick = click;
            buttons.append(button);
        }
        return row;
    });
    $('plansBody').replaceChildren(...(rows.length ? rows : [emptyRow(7, 'Todavía no hay propuestas evaluadas.')]));
    $('plansExamples').hidden = available;
}

export function loadPlans() {
    loading ??= refreshPlans().finally(() => { loading = null; });
    return loading;
}

async function refreshPlans() {
    const status = $('plansStatus');
    $('plansRefresh').disabled = true;
    try {
        const [plans, controller, arduino] = await Promise.all([
            operation('operacion/planes'), operation('estados'),
            arduinoGuided() ? operation('banco/arduino') : Promise.resolve(null),
        ]);
        plansShown = plans.items;
        // Conservar los botones y el foco mientras solo cambian las fases del Arduino.
        const signature = JSON.stringify(plans.items.map(plan => [plan, expired(plan)]));
        if (signature !== renderedPlans) {
            drawPlans();
            renderedPlans = signature;
        }
        const targetId = arduinoTargetId();
        const trackedPlans = targetId && !plans.items.some(plan => plan.id === targetId)
            ? [...plans.items, await operation(`operacion/planes/${encodeURIComponent(targetId)}`)] : plans.items;
        renderArduinoGuide(trackedPlans, arduino);
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
    } catch (error) { setStatus(status, error.message, true); renderArduinoGuide(plansShown, null); }
    finally { $('plansRefresh').disabled = false; }
}

function decisionIssue(id) {
    const snapshot = plansShown.find(plan => plan.id === id);
    if (snapshot && expired(snapshot)) return expiredMessage;
    if (resolved.has(id) || snapshot && snapshot.estado !== 'validado') return unavailableMessage;
    return '';
}

function openDecision(draft, restored = false) {
    if (sending || $('planDecision').open) return;
    const issue = decisionIssue(draft.id);
    if (issue) {
        drawPlans();
        setStatus($('plansStatus'), issue);
        return;
    }
    decision = draft;
    const title = draft.accion === 'autorizar' ? 'Autorizar plan' : 'Rechazar plan';
    $('planDecisionTitle').textContent = title;
    $('planDecisionSubmit').textContent = title;
    $('planDecisionName').textContent = draft.label;
    $('planReason').value = draft.motivo || '';
    setStatus($('planDecisionStatus'), restored ? 'Revisa el motivo y confirma tu decisión.' : '');
    $('planDecision').showModal();
}

function setSending(value) {
    sending = value;
    $('planDecisionSubmit').disabled = value;
    $('planDecisionCancel').disabled = value;
    $('planReason').readOnly = value;
    drawPlans();
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
    initArduinoGuide();
    $('plansRefresh').onclick = loadPlans;
    const dialog = $('planDecision');
    $('planDecisionCancel').onclick = () => { if (!sending) dialog.close(); };
    dialog.addEventListener('cancel', event => { if (sending) event.preventDefault(); });
    window.addEventListener('pageshow', event => {
        if (!event.persisted || !redirecting) return;
        redirecting = false;
        setSending(false);
        setStatus($('planDecisionStatus'));
    });
    $('planEvidenceClose').onclick = () => $('planEvidence').close();
    $('planDecisionForm').onsubmit = async event => {
        event.preventDefault();
        if (sending || !dialog.open || !decision) return;
        const issue = decisionIssue(decision.id);
        if (issue) {
            dialog.close();
            drawPlans();
            setStatus($('plansStatus'), issue);
            return;
        }
        const motivo = $('planReason').value.trim();
        const status = $('planDecisionStatus');
        if (motivo.length < 5) { setStatus(status, 'Escribe un motivo de al menos cinco caracteres.', true); return; }
        const {id, accion} = decision;
        const key = JSON.stringify([id, accion, motivo]);
        setSending(true);
        setStatus(status, 'Registrando decisión…');
        try {
            if (!oidc.mfaReady()) {
                rememberDraft('planes', {...decision, motivo});
                setStatus(status, 'Abriendo verificación de dos pasos…');
                await oidc.login({mfa: true});
                redirecting = true;
                return;
            }
            if (!requests.has(key)) requests.set(key, crypto.randomUUID());
            const saved = await operation(`operacion/planes/${id}/decisiones`, {
                method: 'POST', body: {solicitud_id: requests.get(key), accion, motivo},
            });
            resolved.set(id, saved);
            if (accion === 'autorizar') {
                const plan = plansShown.find(row => row.id === id);
                if (plan) followArduinoPlan(plan);
            }
            requests.delete(key);
            dialog.close();
            setStatus($('plansStatus'), 'Decisión registrada.');
        } catch (error) {
            if (error.status === 409 || error.status === 404) {
                const plan = plansShown.find(row => row.id === id);
                resolved.set(id, plan && error.message === expiredMessage ? {...plan, estado: 'vencido'} : null);
                requests.delete(key);
                dialog.close();
                setStatus($('plansStatus'), error.message || unavailableMessage);
            } else {
                setStatus(status, error.message, true);
            }
        } finally {
            if (!redirecting) setSending(false);
        }
        if (resolved.has(id)) {
            await loading;
            await loadPlans();
        }
    };
}
