import * as oidc from './oidc.js';
import {initUsers,loadUsers} from './users.js';
const $=id=>document.getElementById(id);
let config,data={counts:[],inventory:[],states:[]},offset=0,hasMore=false,loading=false;
const fmt=s=>s?new Date(s).toLocaleString():'Pendiente';
function cell(tr,value){const td=document.createElement('td');td.textContent=String(value??'Pendiente');tr.append(td);return td;}
function source(tr,prueba){const td=cell(tr,''),badge=document.createElement('span');badge.textContent=prueba?'Validación':'Operación';badge.className='source-badge'+(prueba?' simulated':'');td.append(badge);}
function empty(body,columns){if(!body.children.length){const tr=document.createElement('tr'),td=cell(tr,'Sin datos para esta consulta');td.colSpan=columns;td.className='empty';body.append(tr);}}
function draw(){
 const q=$('search').value.trim().toLocaleLowerCase('es');
 const selected=$('intersectionFilter').value;
 const match=row=>(!selected||row.interseccion===selected)&&Object.values(row).some(v=>String(v??'').toLocaleLowerCase('es').includes(q));
 for(const id of ['countsBody','inventoryBody','statesBody'])$(id).replaceChildren();
 data.counts.filter(match).forEach(x=>{const tr=document.createElement('tr');[x.interseccion,x.acceso+' / '+x.carril,x.clase,x.cantidad,fmt(x.inicio)+' — '+fmt(x.fin)].forEach(v=>cell(tr,v));source(tr,x.prueba);$('countsBody').append(tr);});
 data.inventory.filter(match).forEach(x=>{const tr=document.createElement('tr');[x.activo_id,x.interseccion+' / '+(x.acceso||'—'),x.tipo,x.ubicacion,x.protocolo].forEach(v=>cell(tr,v));source(tr,x.prueba);$('inventoryBody').append(tr);});
 data.states.filter(match).forEach(x=>{const tr=document.createElement('tr');const age=Math.max(0,(Date.now()-new Date(x.timestamp).getTime())/1000);if(age>30)tr.className='stale';[x.interseccion,x.fase_actual,x.plan_activo,x.estado_controlador,fmt(x.timestamp),Math.round(age)+' s'+(age>30?' · Sin actualización':'')].forEach(v=>cell(tr,v));source(tr,x.prueba);$('statesBody').append(tr);});
 $('summaryVehicles').textContent=data.counts.filter(match).reduce((n,x)=>n+x.cantidad,0).toLocaleString('es');$('summaryIntersections').textContent=new Set([...data.inventory,...data.states,...data.counts].filter(match).map(x=>x.interseccion)).size;$('summaryAssets').textContent=data.inventory.filter(match).length;
 empty($('countsBody'),6);empty($('inventoryBody'),6);empty($('statesBody'),7);$('loadMore').hidden=!hasMore;
}
async function api(path){const token=await oidc.accessToken();const r=await fetch(config.apiBase+path,{headers:{Authorization:'Bearer '+token},cache:'no-store'});if(!r.ok)throw new Error('API '+r.status+': '+(r.status===401?'sesión inválida':r.status===403?'rol sin permiso':'no disponible'));return r.json();}
function range(){const start=new Date($('desde').value),end=new Date($('hasta').value);if(!Number.isFinite(+start)||!Number.isFinite(+end)||start>=end)throw new Error('Selecciona un rango de fechas válido');const params=new URLSearchParams({desde:start.toISOString(),hasta:end.toISOString(),limit:'200',offset:String(offset)});if($('intersectionFilter').value)params.set('interseccion',$('intersectionFilter').value);return params;}
async function refresh(more=false){
 if(loading)return;loading=true;$('reload').disabled=true;$('loadMore').disabled=true;
 try{if(!more){offset=0;if($('live').checked){$('hasta').value=localDate(new Date(Date.now()+60000));$('desde').value=localDate(new Date(Date.now()-3600000));}}const params=range();const result=await api('/conteos?'+params);const [inventory,states]=more?[null,null]:await Promise.all([api('/inventario'),api('/estados')]);
 data.counts=more?data.counts.concat(result.items):result.items;offset+=result.items.length;hasMore=result.items.length===200;if(inventory)data.inventory=inventory.items;if(states)data.states=states.items;const current=$('intersectionFilter').value;const ids=[...new Set([...data.inventory,...data.states,...data.counts].map(x=>x.interseccion))].sort();$('intersectionFilter').replaceChildren(new Option('Todas',''),...ids.map(id=>new Option(id,id)));if(ids.includes(current))$('intersectionFilter').value=current;draw();$('status').classList.remove('error');$('status').textContent='Última actualización: '+new Date().toLocaleTimeString()+' · Intervalos cargados: '+data.counts.length;
 }catch(error){$('status').classList.add('error');$('status').textContent=error.message+' · Los datos que queden visibles pertenecen a la última consulta correcta.';}finally{loading=false;$('reload').disabled=false;$('loadMore').disabled=false;}
}
function localDate(d){return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
$('intersectionFilter').addEventListener('change',()=>refresh());$('live').addEventListener('change',()=>{$('desde').disabled=$('live').checked;$('hasta').disabled=$('live').checked;if($('live').checked)refresh();});$('search').addEventListener('input',draw);$('reload').addEventListener('click',()=>refresh());$('loadMore').addEventListener('click',()=>refresh(true));
const login=()=>oidc.login().catch(e=>{$('status').classList.add('error');$('status').textContent=e.message;});$('login').addEventListener('click',login);$('welcomeLogin').addEventListener('click',login);$('logout').addEventListener('click',oidc.logout);
const views={conteos:['MONITOREO','Flujo vehicular','Conteos por intersección, acceso y carril.'],inventario:['INFRAESTRUCTURA','Inventario','Activos y conexiones de tu corredor.'],estados:['MONITOREO','Comunicación','Estado y última información de cada intersección.'],usuarios:['ADMINISTRACIÓN','Usuarios','Gestiona tu equipo y sus permisos de acceso.']};
document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{
 const selected=button.dataset.tab;document.querySelectorAll('[data-tab]').forEach(x=>x.setAttribute('aria-pressed',String(x===button)));
 for(const id of Object.keys(views))$(id).hidden=id!==selected;
 const [eyebrow,title,description]=views[selected];$('pageEyebrow').textContent=eyebrow;$('pageTitle').textContent=title;$('pageDescription').textContent=description;
 const users=selected==='usuarios';document.querySelector('.filters').hidden=users;$('summary').hidden=users;$('status').hidden=users;
 if(users)loadUsers();
}));
try{config=await (await fetch('config.json')).json();const active=await oidc.init(config);if(active){$('welcome').hidden=true;$('workspace').hidden=false;$('summary').after($('status'));$('login').hidden=true;$('logout').hidden=false;$('identity').textContent=oidc.identity();initUsers(config);$('hasta').value=localDate(new Date(Date.now()+60000));$('desde').value=localDate(new Date(Date.now()-3600000));$('desde').disabled=true;$('hasta').disabled=true;await refresh();setInterval(()=>{if(!document.hidden&&$('live').checked)refresh();},15000);}}catch(e){$('status').textContent=e.message;}
