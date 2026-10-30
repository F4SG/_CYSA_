(()=>{
 function init(){
  document.documentElement.lang='es';document.body.classList.add('cysa-auth');
  const page=document.querySelector('.login-pf-page');if(!page)return;
  const toolbar=document.createElement('div');toolbar.className='auth-toolbar';
  const label=document.createElement('label');label.textContent='Apariencia';
  const selector=document.createElement('select');selector.setAttribute('data-theme-selector','');selector.setAttribute('aria-label','Tema de la interfaz');selector.add(new Option('Claro','light'));selector.add(new Option('Oscuro','dark'));label.append(selector);toolbar.append(label);
  const shell=document.createElement('main');shell.className='auth-shell';
  const intro=document.createElement('aside');intro.className='auth-intro';
  const brand=document.createElement('div');brand.className='auth-brand';
  const mark=document.createElement('span');mark.className='brand-mark';mark.setAttribute('aria-hidden','true');for(let i=0;i<3;i++)mark.append(document.createElement('i'));
  const brandName=document.createElement('span');brandName.textContent='CYSA';const tagline=document.createElement('small');tagline.textContent='Gestión de tránsito';brandName.append(tagline);brand.append(mark,brandName);
  const copy=document.createElement('div');copy.className='auth-copy';
  const eyebrow=document.createElement('p');eyebrow.className='auth-eyebrow';eyebrow.textContent='INFORMACIÓN DEL CORREDOR';
  const title=document.createElement('h2');title.append(document.createTextNode('Gestión del'),document.createElement('br'),document.createTextNode('tránsito urbano.'));
  const description=document.createElement('p');description.textContent='Conteos vehiculares, infraestructura y comunicación en una sola plataforma.';
  const features=document.createElement('ul');for(const text of ['Monitoreo por carril','Inventario del corredor','Accesos por rol']){const li=document.createElement('li');li.textContent=text;features.append(li);}copy.append(eyebrow,title,description,features);
  const note=document.createElement('p');note.className='auth-note';note.textContent='Plataforma de gestión semafórica';intro.append(brand,copy,note);
  const panel=document.createElement('section');panel.className='auth-panel';panel.append(page);
  const help=document.createElement('p');help.className='auth-help';help.textContent='¿Necesitas acceso? Contacta al administrador de tu organización.';panel.append(help);
  shell.append(intro,panel);document.body.append(toolbar,shell);window.CYSATheme?.bind();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
