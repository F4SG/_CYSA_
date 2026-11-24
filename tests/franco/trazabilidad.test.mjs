import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';

const panel = fileURLToPath(new URL('../../panel/', import.meta.url));
const codigo = await readFile(resolve(panel, 'configuraciones.js'), 'utf8');
const api = await readFile(resolve(panel, 'project-api.js'), 'utf8');
test('el panel conserva el motivo durante MFA y lo envía al confirmar', async () => {
    let listo = false, borrador, solicitud;
    const motivo = 'Ajuste de ámbar en el banco';
    const campos = new Map();
    const elemento = id => {
        if (!campos.has(id)) campos.set(id, {reset(){},showModal(){},close(){},
            elements:{aprobadaUtc:{},namedItem(){return null;}}, querySelectorAll(){return [];}});
        return campos.get(id);
    };
    const context = {document:{getElementById:elemento,querySelectorAll:()=>[]},
        oidc:{hasRole:()=>true,mfaReady:()=>listo,login:async()=>{}},
        setStatus(){}, rememberDraft:(vista, data)=>{borrador=data;},
        projectRequest:async (service, path, options)=>{
            solicitud={path,options};
            throw new Error('Fin de la captura de la solicitud');
        }};
    runInNewContext(codigo.replace(/^import .*;$/gm,'').replace(/^export /gm,''), context);
    context.initConfigurations();
    elemento('configNew').onclick();
    elemento('configMotivo').value=motivo;
    await elemento('configForm').onsubmit({preventDefault(){}});
    assert.equal(borrador.motivo,motivo);
    elemento('configMotivo').value='';
    listo=true;
    context.restoreConfiguration(borrador);
    assert.equal(elemento('configMotivo').value,motivo);
    await elemento('configForm').onsubmit({preventDefault(){}});
    assert.equal(solicitud.options.motivo,motivo);
    assert.equal(solicitud.path,'/api/proyecto/configuraciones');
});
test('la solicitud HTTP conserva motivos con tildes', async () => {
    let headers;
    const context = {AbortSignal,oidc:{accessToken:async()=>'prueba'},serviceUrl:()=>'/api/proyecto/configuraciones',
        fetch:async (url,options)=>{headers=options.headers; return {ok:true,json:async()=>({})};}};
    runInNewContext(api.replace(/^import .*;$/gm,'').replace(/^export /gm,''), context);
    await context.projectRequest('webApiBase','/api/proyecto/configuraciones',{method:'POST',body:{},motivo:'Ajuste de ámbar'});
    assert.equal(decodeURIComponent(headers['X-CYSA-Motivo']),'Ajuste de ámbar');
});
