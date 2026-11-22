// Leer la configuración al pulsar: una pestaña abierta antes del arranque puede tener datos antiguos.
export function moduleUrl(name,config){
 const operation=name==='Gestionar planes semafóricos'||name==='Operación semafórica (S2)';
 if(!operation&&!['Gestionar configuraciones del corredor','Swagger (Web III)'].includes(name))
  throw new Error('Este módulo se consulta dentro del panel general.');
 const value=operation?config.operacionBase:config.webApiBase;
 if(!value)throw new Error('El acceso al módulo todavía no está preparado. Espera a que CYSA indique Sistema listo.');
 const url=new URL(value);
 if(!['http:','https:'].includes(url.protocol)||!['localhost','127.0.0.1','[::1]'].includes(url.hostname)||url.username||url.password||url.search||url.hash)
  throw new Error('La dirección local del módulo no es válida. Revisa la configuración de CYSA.');
 if(operation)return url.origin+'/';
 if(name==='Swagger (Web III)')return url.origin+'/swagger';
 return url.origin+(name==='Gestionar configuraciones del corredor'?'/proyecto':'/demo')+'#'+encodeURIComponent(name);
}
export async function destination(name,fetchConfig=fetch){
 const response=await fetchConfig('/config.json',{cache:'no-store'});
 if(!response.ok)throw new Error('No se pudo consultar la configuración actual de los módulos.');
 return moduleUrl(name,await response.json());
}
