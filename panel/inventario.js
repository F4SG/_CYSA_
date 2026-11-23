import * as oidc from './oidc.js';
import {confirmAction} from './confirm.js';
const $=id=>document.getElementById(id);
let config,reload,busy=false,editing=null,editingAccess=null;
const form=()=>$('assetForm');
function status(message,error=false){$('inventoryStatus').textContent=message;$('inventoryStatus').classList.toggle('error',error);}
async function request(path,method,body){
 const token=await oidc.accessToken();
 const response=await fetch(config.apiBase+'/inventario'+path,{method,headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,cache:'no-store'});
 const result=await response.json();
 if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:response.status===422?'Revisa los campos: los identificadores solo admiten letras, números, guion y guion bajo.':response.status===403?'Solo un administrador puede modificar el inventario.':'No se pudo completar la operación.');
 return result;
}
function setBusy(value){busy=value;$('assetFields').disabled=value;$('assetSave').disabled=value;$('assetCancel').disabled=value;$('assetExample').disabled=value;$('assetNew').disabled=value;$('inventoryBody').inert=value;}
function openAsset(asset=null){
 if(busy||!oidc.hasRole('administrador'))return;
 editing=asset?.activo_id??null;editingAccess=asset?.acceso??null;form().reset();$('assetError').textContent='';
 $('assetTitle').textContent=editing?'Editar activo':'Registrar activo';
 $('assetSave').textContent=editing?'Guardar cambios':'Registrar activo';
 if(asset)for(const [key,value] of Object.entries(asset)){const field=form().elements.namedItem(key);if(!field)continue;if(field.type==='checkbox')field.checked=value;else field.value=value??'';}
 if(asset?.tipo==='acceso')$('assetError').textContent='Selecciona un tipo vigente para este registro: Controlador, Cámara o Intersección.';
 form().elements.activo_id.readOnly=!!editing;$('assetExample').hidden=!!editing;
 $('assetDialog').showModal();
}
export function inventoryActions(row,asset){
 const cell=document.createElement('td');cell.className='module-actions';row.append(cell);
 if(!oidc.hasRole('administrador')){cell.textContent='Solo consulta';return;}
 const edit=document.createElement('button');edit.type='button';edit.textContent='Editar';edit.setAttribute('aria-label','Editar '+asset.activo_id);edit.addEventListener('click',()=>openAsset(asset));
 const remove=document.createElement('button');remove.type='button';remove.textContent='Eliminar';remove.setAttribute('aria-label','Eliminar '+asset.activo_id);
 remove.addEventListener('click',async()=>{
  if(busy)return;
  if(!await confirmAction({title:'Eliminar activo',message:'Se eliminará el registro '+asset.activo_id+' del inventario. No desconecta el equipo ni borra sus conteos o estados. Esta acción no se puede deshacer desde el panel.',label:'Eliminar activo'}))return;
  if(busy)return;setBusy(true);
  try{await request('/'+encodeURIComponent(asset.activo_id),'DELETE');status('Activo eliminado del inventario.');try{await reload();}catch{status('Activo eliminado. Pulsa Actualizar para renovar la lista.',true);}}
  catch(error){status(error.message,true);}finally{setBusy(false);}
 });cell.append(edit,remove);
}
export function initInventory(value,onChange){
 config=value;reload=onChange;
 $('assetNew').hidden=!oidc.hasRole('administrador');
 $('assetNew').addEventListener('click',()=>openAsset());
 $('assetCancel').addEventListener('click',()=>{if(!busy)$('assetDialog').close();});
 $('assetDialog').addEventListener('cancel',event=>{if(busy)event.preventDefault();});
 $('assetExample').addEventListener('click',()=>{
  const fields=form().elements;fields.activo_id.value='DEMO_ARDUINO_'+Date.now().toString(36).toUpperCase();
  fields.interseccion.value='DEMO_INT_01';fields.tipo.value='controlador';
  fields.ubicacion.value='Banco de LEDs de laboratorio';fields.protocolo.value='USB_SERIAL';fields.prueba.checked=true;
  $('assetError').textContent='Ejemplo preparado. Revisa los datos y pulsa Registrar activo para guardarlo.';
 });
 form().addEventListener('submit',async event=>{
  event.preventDefault();if(busy||!form().reportValidity())return;
  const values=Object.fromEntries(new FormData(form()));
  const body={activo_id:values.activo_id.trim(),interseccion:values.interseccion.trim(),acceso:editingAccess,tipo:values.tipo,ubicacion:values.ubicacion.trim(),protocolo:values.protocolo.trim(),prueba:form().elements.prueba.checked};
  if(!body.ubicacion||!body.protocolo){$('assetError').textContent='Completa ubicación y protocolo; no pueden contener solo espacios.';return;}
  setBusy(true);$('assetError').textContent='Guardando…';
  try{
   await request(editing?'/'+encodeURIComponent(editing):'',editing?'PUT':'POST',body);
   $('assetDialog').close();status((editing?'Cambios guardados':'Activo registrado')+(body.prueba?' · Datos de prueba.':'.'));
   try{await reload();}catch{status('El activo se guardó. Pulsa Actualizar para renovar la lista.',true);}
  }catch(error){$('assetError').textContent=error.message;}finally{setBusy(false);}
 });
}
