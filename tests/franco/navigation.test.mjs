import {readFile} from 'node:fs/promises';
import {test} from 'node:test';
import assert from 'node:assert/strict';
const source=await readFile(new URL('../../panel/navigation.js',import.meta.url),'utf8');
const {moduleUrl,destination}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const homeSource=await readFile(new URL('../../panel/home-link.js',import.meta.url),'utf8');
const {panelReturnUrl}=await import('data:text/javascript;base64,'+Buffer.from(homeSource).toString('base64'));

test('una pestaña antigua lee el puerto vigente al pulsar y no utiliza 5184',async()=>{
 let read=0;
 const fetchConfig=async(path,options)=>{assert.equal(path,'/config.json');assert.equal(options.cache,'no-store');return {ok:true,json:async()=>({operacionBase:read++?'http://localhost:25184':'http://localhost:15184'})};};
 assert.equal(await destination('Gestionar planes semafóricos',fetchConfig),'http://localhost:15184/');
 assert.equal(await destination('Operación semafórica (S2)',fetchConfig),'http://localhost:25184/');
});
test('cada módulo conserva la dirección de la instalación y su destino correcto',()=>{
 const config={operacionBase:'http://localhost:25184',webApiBase:'http://localhost:25183/'};
 assert.equal(moduleUrl('Gestionar configuraciones del corredor',config),'http://localhost:25183/proyecto#Gestionar%20configuraciones%20del%20corredor');
 assert.equal(moduleUrl('Consultar reportes de desempeño',config),'http://localhost:25183/demo#Consultar%20reportes%20de%20desempe%C3%B1o');
 assert.equal(moduleUrl('Swagger (Web III)',config),'http://localhost:25183/swagger');
});
test('una configuración incompleta o una lectura fallida no abre un puerto supuesto',async()=>{
 assert.throws(()=>moduleUrl('Gestionar planes semafóricos',{}),/no está preparado/);
 await assert.rejects(destination('Gestionar planes semafóricos',async()=>({ok:false})),/No se pudo consultar/);
 for(const value of ['https://example.com','javascript:alert(1)','http://usuario:clave@localhost:15184'])
  assert.throws(()=>moduleUrl('Gestionar planes semafóricos',{operacionBase:value}),/no es válida/);
});
test('volver reutiliza el panel general configurado y solicita recuperar la sesión',()=>{
 assert.equal(panelReturnUrl('http://localhost:28088/'),'http://localhost:28088/?volver=1');
 assert.equal(panelReturnUrl('http://127.0.0.1:28088/otra?ruta=1#seccion'),'http://127.0.0.1:28088/?volver=1');
 assert.throws(()=>panelReturnUrl('https://example.com'),/no es válida/);
 assert.throws(()=>panelReturnUrl(null),/No está configurado/);
});
