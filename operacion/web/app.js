import * as oidc from '/oidc.js';
const $=id=>document.getElementById(id),requests=new Map();
let refreshing=false;
async function api(path,options={}){
 const token=await oidc.accessToken();
 const r=await fetch(path,{...options,headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},cache:'no-store',signal:AbortSignal.timeout(options.method==='POST'?300000:15000)});
 const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data;
}
function cell(row,value){const td=document.createElement('td');td.textContent=value;row.append(td);return td;}
function empty(id,columns,message){const tr=document.createElement('tr');cell(tr,message).colSpan=columns;$(id).append(tr);}
async function action(work){$('status').textContent='Procesando…';try{await work();$('status').textContent='';}catch(e){$('status').textContent=e.message;}}
async function decidir(plan,accion,button){
 const motivo=$('reason').value.trim();if(motivo.length<5)throw new Error('Escribe un motivo de al menos cinco caracteres.');
 const key=[plan.id,accion,motivo].join('|');if(!requests.has(key))requests.set(key,crypto.randomUUID());
 button.disabled=true;
 try{await api('/api/operacion/planes/'+plan.id+'/decisiones',{method:'POST',body:JSON.stringify({solicitud_id:requests.get(key),accion,motivo})});await refresh();}
 finally{button.disabled=false;}
}
async function refresh(){
 if(refreshing)return;refreshing=true;
 try{
  const [plans,states]=await Promise.all([api('/api/operacion/planes'),api('/api/estados')]);$('plans').replaceChildren();
  for(const p of plans.items){const tr=document.createElement('tr');
   cell(tr,p.documento.plan_id);cell(tr,p.documento.modo);cell(tr,p.documento.verdes.NS+' / '+p.documento.verdes.EO);
   cell(tr,p.validacion.mejora_porcentaje.toFixed(2)+' %');cell(tr,p.estado);
   cell(tr,(p.estado_envio||'Sin envío')+(p.detalle_envio?' · '+p.detalle_envio:''));const actions=cell(tr,'');
   if(p.estado==='validado'&&oidc.hasRole('operador'))for(const [label,accion] of [['Autorizar','autorizar'],['Rechazar','rechazar']]){
    const b=document.createElement('button');b.textContent=label;b.onclick=()=>action(()=>decidir(p,accion,b));actions.append(b);
   }
   const e=cell(tr,'');const b=document.createElement('button');b.textContent='Evidencia';b.onclick=()=>action(async()=>{$('evidence').textContent=JSON.stringify({plan:p,auditoria:await api('/api/operacion/planes/'+p.id+'/auditoria')},null,2);});e.append(b);$('plans').append(tr);
  }
  if(!plans.items.length)empty('plans',8,'Todavía no hay planes. Selecciona un intervalo con conteos de prueba y pulsa Calcular y validar en SUMO.');
  $('states').replaceChildren();for(const s of states.items){const tr=document.createElement('tr');const age=Date.now()-Date.parse(s.timestamp);const state=Number.isFinite(age)&&age<=30000?s.estado_controlador:'Sin reporte reciente';[s.interseccion,s.fase_actual,s.plan_activo,state,s.timestamp].forEach(v=>cell(tr,v));$('states').append(tr);}
  if(!states.items.length)empty('states',5,'No hay reportes del controlador. Inícialo con -Puerto COM3 -Mqtt -RecibirPlanes para ver el Arduino aquí.');
 }finally{refreshing=false;}
}
$('generate').onsubmit=e=>{e.preventDefault();action(async()=>{
 $('simulate').disabled=true;try{
  const modo=$('mode').value;await api('/api/operacion/planes',{method:'POST',body:JSON.stringify({desde:new Date($('desde').value).toISOString(),hasta:new Date($('hasta').value).toISOString(),modo,grupo:modo==='webster'?null:$('group').value,evento_utc:modo==='emergencia'?new Date($('eventTime').value).toISOString():null})});await refresh();
 }finally{$('simulate').disabled=false;}
});};
$('login').onclick=()=>oidc.login();$('renew').onclick=()=>oidc.login({fresh:true});$('logout').onclick=()=>oidc.logout();
function localDate(d){return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
action(async()=>{
 const config=await(await fetch('/config.json')).json();if(!await oidc.init(config))return;
 $('identity').textContent=oidc.identity();$('login').hidden=true;$('renew').hidden=$('logout').hidden=false;$('workspace').hidden=false;
 $('simulate').disabled=!oidc.hasRole('administrador');$('desde').value=localDate(new Date(Date.now()-15*60000));$('hasta').value=localDate(new Date());
 $('eventTime').value=localDate(new Date(Date.now()+120000));
 await refresh();setInterval(()=>{if(!document.hidden)refresh().catch(e=>{$('status').textContent=e.message;});},5000);
});
