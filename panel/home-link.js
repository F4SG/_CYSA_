export function panelReturnUrl(value){
 if(!value)throw new Error('No está configurado el panel general.');
 const url=new URL(value);
 if(!['http:','https:'].includes(url.protocol)||!['localhost','127.0.0.1','[::1]'].includes(url.hostname)||url.username||url.password)
  throw new Error('La dirección del panel general no es válida.');
 url.pathname='/';url.search='';url.hash='';url.searchParams.set('volver','1');return url.href;
}
