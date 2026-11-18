// Accesos de laboratorio únicamente: el endpoint está deshabilitado fuera de Development/local.
window.addEventListener('load',()=>{
 const timer=setInterval(()=>{
  if(!window.ui?.preauthorizeApiKey)return;
  clearInterval(timer);
  const bar=document.createElement('div');bar.style.cssText='padding:16px;background:#edf4ef;display:flex;gap:12px;align-items:center;flex-wrap:wrap';
  const link=document.createElement('a');link.href='/demo';link.textContent='Panel de pruebas y migraciones';bar.append(link);
  const label=document.createElement('span');label.textContent='Acceso local · MFA simulada (5 min):';bar.append(label);
  for(const role of ['administrador','operador','evaluador','operador-sin-mfa']){
   const b=document.createElement('button');b.textContent=role;b.type='button';
   b.onclick=async()=>{const r=await fetch('/api/demo/acceso/'+role,{cache:'no-store'});if(!r.ok){label.textContent='Acceso de demostración no disponible.';return;}
    const data=await r.json();window.ui.preauthorizeApiKey('Bearer',data.token);label.textContent='Perfil activo: '+role+' · MFA simulada renovada';};bar.append(b);
  }
  document.querySelector('.swagger-ui')?.prepend(bar);
 },200);
 setTimeout(()=>clearInterval(timer),15000);
});
