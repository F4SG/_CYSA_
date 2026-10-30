// Preferencia visual compartida por cookie entre el panel y el acceso en localhost.
// No contiene ni almacena tokens o credenciales.
(()=>{
 const valid=value=>value==='light'||value==='dark';
 let theme='light';
 try{const cookie=document.cookie.split('; ').find(x=>x.startsWith('cysa-theme='))?.split('=')[1];const saved=localStorage.getItem('cysa.theme');theme=valid(cookie)?cookie:valid(saved)?saved:matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}catch{}
 function apply(value,persist=false){
  theme=valid(value)?value:'light';document.documentElement.dataset.theme=theme;
  for(const select of document.querySelectorAll('[data-theme-selector]'))select.value=theme;
  if(persist){try{localStorage.setItem('cysa.theme',theme);}catch{}document.cookie='cysa-theme='+theme+'; Path=/; Max-Age=31536000; SameSite=Lax'+(location.protocol==='https:'?'; Secure':'');}
 }
 apply(theme);
 function bind(){for(const select of document.querySelectorAll('[data-theme-selector]')){select.value=theme;select.addEventListener('change',event=>apply(event.target.value,true));}}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind);else bind();
 window.CYSATheme={bind};
})();
