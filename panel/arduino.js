import {integrationState} from './arduino-state.js';

const $ = id => document.getElementById(id);
const key = 'cysa.arduino-integration';
let session;
try {
    const params = new URLSearchParams(location.search);
    const port = params.get('arduino'), id = params.get('sesion');
    if (/^COM\d+$/i.test(port || '') && /^[a-f0-9]{32}$/.test(id || '')) {
        session = {port, id, created: Date.now()};
        sessionStorage.setItem(key, JSON.stringify(session));
    } else {
        session = JSON.parse(sessionStorage.getItem(key) || 'null');
        if (!session || Date.now() - session.created > 4 * 3600000) session = null;
    }
} catch { session = null; }
let lastProof;
export const arduinoGuided = () => Boolean(session);
export const arduinoTargetId = () => session?.target?.id;

function renderVisualConfirmation() {
    const complete = session.visual === true;
    $('arduinoTitle').textContent = complete ? 'Prueba completada correctamente' : 'Arduino → MFA → Plan aplicado';
    $('arduinoConfirmation').hidden = complete;
    $('arduinoProposals').hidden = complete;
    $('arduinoFinished').hidden = !complete;
    if (complete) {
        $('arduinoVisual').textContent = 'Conexión, autorización MFA, aplicación del plan y LEDs verificados. No quedan pasos pendientes en esta prueba.';
        if (lastProof === 'applied') $('arduinoProgress').textContent = 'Prueba finalizada. El plan autorizado sigue activo en el Arduino.';
    } else if (session.visual === false) {
        $('arduinoVisual').textContent = 'Los LEDs no coinciden. La demostración queda pendiente: revisa pines, cableado y orientación NS / EO.';
    } else {
        $('arduinoVisual').textContent = 'La confirmación visual se habilita al coincidir el recibo y el plan activo.';
    }
}

export function initArduinoGuide() {
    if (!session) return;
    $('arduinoIntegration').hidden = false;
    $('arduinoPort').textContent = session.port;
    $('arduinoProposals').onclick = () => $('plansBody').closest('article').scrollIntoView({behavior: 'smooth'});
    $('arduinoReturn').onclick = () => { location.hash = 'conteos'; };
    for (const [id, answer] of [['arduinoMatch', true], ['arduinoMismatch', false]]) {
        $(id).onclick = () => {
            if (lastProof !== 'applied') return;
            session.visual = answer;
            sessionStorage.setItem(key, JSON.stringify(session));
            renderVisualConfirmation();
        };
    }
    renderVisualConfirmation();
}

export function followArduinoPlan(plan) {
    if (!session) return;
    session.target = {id: plan.id, plan: plan.documento.plan_id};
    delete session.visual;
    sessionStorage.setItem(key, JSON.stringify(session));
    lastProof = 'waiting';
    renderVisualConfirmation();
    $('arduinoIntegration').scrollIntoView({behavior: 'smooth', block: 'start'});
}

export function renderArduinoGuide(plans, board) {
    if (!session) return;
    const proof = integrationState(session, session.target, plans, board);
    lastProof = proof.kind;
    $('arduinoProgress').textContent = proof.text;
    $('arduinoProgress').classList.toggle('error', ['offline','error'].includes(proof.kind));
    $('arduinoTarget').textContent = session.target?.plan || 'Todavía no seleccionado';
    const current = !['offline','error','stopped'].includes(proof.kind);
    $('arduinoActive').textContent = current ? board.plan_activo : 'Sin confirmar';
    $('arduinoPhase').textContent = current ? board.fase_actual : 'Sin confirmar';
    $('arduinoTimestamp').textContent = board?.timestamp ? new Date(board.timestamp).toLocaleTimeString('es') : 'Sin reporte';
    for (const group of ['NS','EO']) {
        const color = current ? board.luces?.[group] : null;
        const container = $('arduinoLights' + group);
        for (const light of container.querySelectorAll('[data-light]'))
            light.classList.toggle('lit', light.dataset.light === color);
        $('arduinoColor' + group).textContent = ({G:'VERDE',Y:'ÁMBAR',R:'ROJO'})[color] || 'Sin confirmar';
    }
    $('arduinoMatch').disabled = $('arduinoMismatch').disabled = proof.kind !== 'applied';
    renderVisualConfirmation();
}
