import {arduinoSessionFromReport, hasCurrentArduinoLights, integrationState, isArduinoSession} from './arduino-state.js';

const $ = id => document.getElementById(id);
const key = 'cysa.arduino-integration';
let session = null;
try {
    const saved = JSON.parse(sessionStorage.getItem(key) || 'null');
    if (isArduinoSession(saved?.port, saved?.id) && Date.now() - saved.created <= 4 * 3600000) session = saved;
} catch { /* El seguimiento en memoria funciona aunque el navegador bloquee el almacenamiento. */ }
const params = new URLSearchParams(location.search);
const port = params.get('arduino'), id = params.get('sesion');
if (isArduinoSession(port, id) && (session?.port !== port || session?.id !== id))
    saveSession({port, id, created: Date.now()});

function saveSession(value) {
    session = value;
    try { sessionStorage.setItem(key, JSON.stringify(session)); } catch { /* Seguir en memoria. */ }
}

function observeArduino(board) {
    const detected = arduinoSessionFromReport(board);
    if (!detected || (session?.id === detected.id && session?.port === detected.port)) return;
    saveSession(detected);
}
let lastProof;
export const arduinoGuided = () => Boolean(session);
export const arduinoTargetId = () => session?.target?.id;

function renderVisualConfirmation() {
    const complete = session?.visual === true && lastProof === 'applied';
    $('arduinoTitle').textContent = complete ? 'Prueba completada correctamente' : 'Luces del Arduino';
    $('arduinoConfirmation').hidden = !session || complete;
    $('arduinoVisual').hidden = !session;
    $('arduinoProposals').hidden = complete;
    $('arduinoFinished').hidden = !complete;
    if (complete) {
        $('arduinoVisual').textContent = 'Conexión, autorización MFA, aplicación del plan y LEDs verificados. No quedan pasos pendientes en esta prueba.';
        if (lastProof === 'applied') $('arduinoProgress').textContent = 'Prueba finalizada. El plan autorizado sigue activo en el Arduino.';
    } else if (session?.visual === false) {
        $('arduinoVisual').textContent = 'Los LEDs no coinciden. La demostración queda pendiente: revisa pines, cableado y orientación NS / EO.';
    } else {
        $('arduinoVisual').textContent = 'La confirmación visual se habilita al coincidir el recibo y el plan activo.';
    }
}

export function initArduinoGuide() {
    $('arduinoProposals').onclick = () => $('plansBody').closest('article').scrollIntoView({behavior: 'smooth'});
    $('arduinoReturn').onclick = () => { location.hash = 'conteos'; };
    for (const [id, answer] of [['arduinoMatch', true], ['arduinoMismatch', false]]) {
        $(id).onclick = () => {
            if (!session || lastProof !== 'applied') return;
            saveSession({...session, visual: answer});
            renderVisualConfirmation();
        };
    }
    renderArduinoGuide([], null);
}

export function followArduinoPlan(plan) {
    if (!session) return;
    saveSession({...session, target: {id: plan.id, plan: plan.documento.plan_id}, visual: undefined});
    lastProof = 'waiting';
    renderVisualConfirmation();
    $('arduinoIntegration').scrollIntoView({behavior: 'smooth', block: 'start'});
}

export function renderArduinoGuide(plans, board) {
    observeArduino(board);
    const proof = integrationState(session, session?.target, plans, board);
    lastProof = proof.kind;
    $('arduinoProgress').textContent = proof.text;
    $('arduinoProgress').classList.toggle('error', ['offline','error'].includes(proof.kind));
    $('arduinoPort').textContent = session?.port || 'Sin conexión';
    $('arduinoTarget').textContent = session?.target?.plan || 'Todavía no seleccionado';
    const current = hasCurrentArduinoLights(session, board);
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
