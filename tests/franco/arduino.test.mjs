import {readFile} from 'node:fs/promises';
import {test} from 'node:test';
import assert from 'node:assert/strict';
const source = await readFile(new URL('../../panel/arduino-state.js', import.meta.url), 'utf8');
const {arduinoSessionFromReport, hasCurrentArduinoLights, integrationState} =
    await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const now = Date.now();
const session = {id:'sesion1',port:'COM3'};
const target = {id:'plan1',plan:'OP_123'};
const board = {activo:true,sesion:'sesion1',puerto:'COM3',timestamp:new Date(now).toISOString(),
    fase_actual:'NS_G',plan_activo:'OP_123',estado_controlador:'conectado'};
const applied = [{id:'plan1',estado_envio:'aplicado'}];

test('una visita directa descubre el Arduino solo con un reporte físico vigente', () => {
    const connected = {...board, sesion:'a'.repeat(32)};
    const detected = arduinoSessionFromReport(connected, now);
    assert.deepEqual(detected, {id:connected.sesion, port:'COM3', created:now});
    assert.equal(integrationState(null, null, [], null, now).kind, 'idle');
    assert.equal(hasCurrentArduinoLights(detected, connected, now), true);
    for (const patch of [{sesion:'otra'}, {puerto:'simulado'}, {detenido:true},
        {activo:false}, {timestamp:new Date(now-5000).toISOString()}])
        assert.equal(arduinoSessionFromReport({...connected,...patch}, now), null);
});

test('las luces físicas siguen disponibles aunque se rechace el plan', () => {
    const rejected = [{id:'plan1', estado_envio:'rechazado'}];
    assert.equal(integrationState(session, target, rejected, board, now).kind, 'error');
    assert.equal(hasCurrentArduinoLights(session, board, now), true);
    assert.equal(hasCurrentArduinoLights(session, board, now+4000), false);
    assert.equal(hasCurrentArduinoLights(session, {...board, detenido:true}, now), false);
});

test('detener conserva el resultado anterior pero no muestra el Arduino como activo', () => {
    assert.equal(integrationState(session,target,applied,{...board,detenido:true,activo:false},now).kind,'stopped');
    assert.equal(integrationState(session,target,applied,{...board,detenido:true,sesion:'otra'},now).kind,'offline');
});

test('autorizar o enviar no equivale a aplicar, aunque coincida el identificador', () => {
    for (const estado_envio of [null,'pendiente','enviado'])
        assert.equal(integrationState(session,target,[{id:'plan1',estado_envio}],board,now).kind,'waiting');
    assert.equal(integrationState(session,target,applied,board,now).kind,'applied');
});
test('otra sesión, otro puerto y reportes antiguos nunca confirman la placa', () => {
    for (const patch of [{sesion:'otra'},{puerto:'COM4'},{activo:false},{timestamp:new Date(now-5000).toISOString()}])
        assert.equal(integrationState(session,target,applied,{...board,...patch},now).kind,'offline');
});
test('el recibo histórico no confirma un plan distinto ni una falla actual', () => {
    assert.equal(integrationState(session,target,applied,{...board,plan_activo:'DEMO_FIJO'},now).kind,'changed');
    assert.equal(integrationState(session,target,applied,{...board,fase_actual:'INTERMITENTE'},now).kind,'error');
    assert.equal(integrationState(session,target,[{id:'plan1',estado_envio:'rechazado'}],board,now).kind,'error');
});
