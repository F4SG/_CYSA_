import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
import {test} from 'node:test';
import assert from 'node:assert/strict';

const source=await readFile(new URL('../src/Cysa.Web.Api/wwwroot/swagger-demo.js',import.meta.url),'utf8');
const flush=()=>new Promise(setImmediate);
function setup(fetcher){
 const intervals=[],requests=[],authorized=[];
 let loaded,bar,ready=false;
 const window={addEventListener:(_,callback)=>{loaded=callback;},ui:{
  getSystem:()=>({specSelectors:{securityDefinitions:()=>({has:()=>ready})}}),
  preauthorizeApiKey:(scheme,token)=>authorized.push({scheme,token})
 }};
 const document={createElement:()=>({style:{},children:[],append(child){this.children.push(child);}}),
  querySelector:()=>({prepend:node=>{bar=node;}})};
 runInNewContext(source,{window,document,
  setInterval:(callback,ms)=>{const timer={callback,ms};intervals.push(timer);return timer;},
  clearInterval:timer=>{timer.cleared=true;},setTimeout:()=>{},
  fetch:async(url,options)=>{requests.push({url,options});return fetcher(url);}
 });
 loaded();
 return {intervals,requests,authorized,ready:()=>{ready=true;},
  get bar(){return bar;},get label(){return bar.children[1];},
  click:role=>bar.children.find(node=>node.textContent===role).onclick()};
}
const success=url=>({ok:true,json:async()=>({token:url.split('/').at(-1)+'-token'})});

test('espera el esquema y autoriza administrador automáticamente sin guardar el token',async()=>{
 const ui=setup(success);ui.intervals[0].callback();await flush();
 assert.equal(ui.requests.length,0);
 ui.ready();ui.intervals[0].callback();await flush();
 assert.equal(ui.requests[0].url,'/api/demo/acceso/administrador');
 assert.equal(ui.requests[0].options.cache,'no-store');
 assert.deepEqual(ui.authorized,[{scheme:'Bearer',token:'administrador-token'}]);
 assert.match(ui.label.textContent,/Perfil activo: administrador/);
 assert.equal(ui.intervals[0].cleared,true);
});

test('renueva administrador y respeta el cambio manual de perfil',async()=>{
 const ui=setup(success);ui.ready();ui.intervals[0].callback();await flush();
 const refresh=ui.intervals.find(timer=>timer.ms===240000);
 refresh.callback();await flush();assert.equal(ui.requests.length,2);
 await ui.click('operador');refresh.callback();await flush();
 assert.equal(ui.requests.length,3);
 assert.equal(ui.authorized.at(-1).token,'operador-token');
});

test('una respuesta automática tardía no reemplaza el perfil elegido',async()=>{
 let release;
 const ui=setup(url=>url.endsWith('administrador')?new Promise(resolve=>{release=()=>resolve(success(url));}):success(url));
 ui.ready();ui.intervals[0].callback();await flush();
 await ui.click('operador-sin-mfa');release();await flush();
 assert.equal(ui.authorized.length,1);
 assert.equal(ui.authorized[0].token,'operador-sin-mfa-token');
});

test('demo deshabilitada o fallo de red no conceden acceso y permiten reintentar',async()=>{
 let mode='blocked';
 const ui=setup(url=>{if(mode==='network')throw new Error('Sin conexión');return mode==='blocked'?{ok:false}:success(url);});
 ui.ready();ui.intervals[0].callback();await flush();
 assert.equal(ui.authorized.length,0);assert.match(ui.label.textContent,/reintentar/);
 mode='network';await ui.click('administrador');assert.equal(ui.authorized.length,0);
 mode='ok';await ui.click('administrador');assert.equal(ui.authorized.length,1);
});
