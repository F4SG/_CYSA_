(async()=>{
 try{
  const [config,helpers]=await Promise.all([fetch('/navigation/config',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('Navegación no disponible');return r.json();}),import('/home-link.js')]);
  let link=document.getElementById('panelHome');
  if(!link){link=document.createElement('a');link.id='panelHome';link.className='button';link.style.cssText='display:inline-block;margin:16px;padding:10px 16px;border:1px solid #175f48;border-radius:6px;color:#175f48;background:white';document.body.prepend(link);}
  link.href=helpers.panelReturnUrl(config.panelUrl);link.textContent='Volver al panel general';link.hidden=false;
  const brand=document.querySelector('.brand');if(brand)brand.href=link.href;
 }catch(error){console.error('No se pudo preparar el regreso al panel general:',error.message);}
})();
