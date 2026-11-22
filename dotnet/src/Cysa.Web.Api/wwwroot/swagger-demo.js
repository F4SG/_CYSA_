// Accesos de laboratorio únicamente: el endpoint está deshabilitado fuera de Development/local.
// Cargar la navegación también desde el script que Swagger ya utiliza.
import('/module-navigation.js').catch(()=>{});
window.addEventListener('load',()=>{
 const timer=setInterval(()=>{
  if(!window.ui?.preauthorizeApiKey || !window.ui.getSystem?.().specSelectors?.securityDefinitions?.()?.has('Bearer'))return;
  clearInterval(timer);
  const bar=document.createElement('div');bar.style.cssText='padding:16px;background:#edf4ef;display:flex;gap:12px;align-items:center;flex-wrap:wrap';
  const link=document.createElement('a');link.href='/demo';link.textContent='Panel de pruebas y migraciones';bar.append(link);
  const label=document.createElement('span');label.textContent='Preparando administrador de demostración…';bar.append(label);
  let activeRole=null,requestId=0;
  async function activate(role){
   const request=++requestId;
   try{
    const r=await fetch('/api/demo/acceso/'+role,{cache:'no-store'});
    if(!r.ok)throw new Error('Acceso no disponible');
    const data=await r.json();
    if(request!==requestId)return;
    window.ui.preauthorizeApiKey('Bearer',data.token);activeRole=role;
    label.textContent='Perfil activo: '+role+' · MFA simulada renovada';
   }catch{
    if(request!==requestId)return;
    label.textContent='No se pudo activar el perfil local. Pulsa un perfil para reintentar.';
   }
  }
  for(const role of ['administrador','operador','evaluador','operador-sin-mfa']){
   const b=document.createElement('button');b.textContent=role;b.type='button';
   b.onclick=()=>activate(role);bar.append(b);
  }
  document.querySelector('.swagger-ui')?.prepend(bar);
  activate('administrador');
  // Mantener vigente la sesión del docente sin reemplazar los perfiles de pruebas negativas.
  setInterval(()=>{if(activeRole==='administrador')activate('administrador');},4*60*1000);
 },200);
 setTimeout(()=>clearInterval(timer),15000);
});
