import * as oidc from './oidc.js';
import {confirmAction} from './confirm.js';
const $=id=>document.getElementById(id);
let config,offset=0,busy=false,creating=false;
const limit=25;
function status(message,error=false){$('usersStatus').textContent=message;$('usersStatus').classList.toggle('error',error);}
async function request(path='',method='GET',body){
 const token=await oidc.accessToken();
 const response=await fetch(config.apiBase+'/usuarios'+path,{method,headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,cache:'no-store'});
 const result=await response.json();
 if(!response.ok){const detail=typeof result.detail==='string'?result.detail:response.status===422?'Revisa los datos y usa una contraseña de al menos 12 caracteres.':'No se pudo completar la operación.';throw new Error(detail);}
 return result;
}
function cell(row,value){const td=document.createElement('td');if(value instanceof Node)td.append(value);else td.textContent=String(value??'');row.append(td);return td;}
export async function loadUsers(){
 if(busy||!oidc.hasRole('administrador'))return;busy=true;$('reloadUsers').disabled=true;$('usersBody').inert=true;
 try{
  const query=new URLSearchParams({offset:String(offset),limit:String(limit),search:$('usersSearch').value.trim()});
  const result=await request('?'+query);$('usersBody').replaceChildren();
  for(const user of result.items){
   const row=document.createElement('tr'),own=user.id===oidc.subject();
   const account=document.createElement('div'),username=document.createElement('div');username.textContent=user.username;username.className='user-name';account.append(username);
   if(own){const badge=document.createElement('span');badge.textContent='Tu cuenta';badge.className='own-label';account.append(badge);}cell(row,account);
   const profile=document.createElement('div'),name=document.createElement('div'),email=document.createElement('span');name.textContent=[user.first_name,user.last_name].filter(Boolean).join(' ');email.textContent=user.email;email.className='user-email';profile.append(name,email);cell(row,profile);
   const role=document.createElement('select');role.setAttribute('aria-label','Rol de '+user.username);
   for(const [name,label] of [['operador','Operador'],['administrador','Administrador']])role.add(new Option(label,name));role.value=user.roles[0]||'operador';
   const label=document.createElement('label'),enabled=document.createElement('input');enabled.type='checkbox';enabled.checked=user.enabled;enabled.setAttribute('aria-label','Cuenta activa de '+user.username);label.append(enabled,document.createTextNode('Activo'));
   const save=document.createElement('button');save.type='button';save.textContent='Guardar';save.disabled=true;
   role.disabled=own;enabled.disabled=own;
   const changed=()=>save.disabled=own||(role.value===(user.roles[0]||'operador')&&enabled.checked===user.enabled);role.addEventListener('change',changed);enabled.addEventListener('change',changed);
   save.addEventListener('click',async()=>{
    if(!await confirmAction({title:'Actualizar acceso',message:'Se guardarán el rol y el estado de '+user.username+'. Sus sesiones se cerrarán para aplicar el cambio.',label:'Guardar cambios'}))return;
    save.disabled=true;role.disabled=true;enabled.disabled=true;
    try{await request('/'+encodeURIComponent(user.id),'PATCH',{role:role.value,enabled:enabled.checked});status('Cuenta actualizada.');await loadUsers();}
    catch(error){status(error.message+' Actualiza la lista para verificar el estado.',true);}
    finally{role.disabled=own;enabled.disabled=own;changed();}
   });
   cell(row,role);cell(row,label);cell(row,save);$('usersBody').append(row);
  }
  if(!result.items.length){const row=document.createElement('tr');cell(row,'No se encontraron usuarios. Prueba con otro nombre o correo.').colSpan=5;$('usersBody').append(row);}
  $('usersCount').textContent=result.items.length+' '+(result.items.length===1?'usuario en esta página':'usuarios en esta página');
  $('usersPrev').disabled=offset===0;$('usersNext').disabled=!result.has_more;
 }catch(error){status(error.message,true);}
 finally{busy=false;$('reloadUsers').disabled=false;$('usersBody').inert=false;}
}
export function initUsers(value){
 config=value;if(!oidc.hasRole('administrador'))return;$('usersTab').hidden=false;
 const dialog=$('newUserDialog'),form=$('newUserForm');
 const roleHelp=()=>{$('roleHelp').textContent=form.elements.role.value==='administrador'?'El administrador puede gestionar usuarios y las configuraciones permitidas.':'El operador puede consultar la información del corredor.';};
 const close=()=>{if(!creating)dialog.close();};
 $('openUserDialog').addEventListener('click',()=>{form.reset();$('newUserError').textContent='';roleHelp();dialog.showModal();});
 $('closeUserDialog').addEventListener('click',close);$('cancelUserDialog').addEventListener('click',close);
 dialog.addEventListener('cancel',event=>{if(creating)event.preventDefault();});dialog.addEventListener('close',()=>{form.reset();$('newUserError').textContent='';});form.elements.role.addEventListener('change',roleHelp);
 $('reloadUsers').addEventListener('click',()=>{offset=0;loadUsers();});$('usersSearch').addEventListener('change',()=>{offset=0;loadUsers();});
 $('usersPrev').addEventListener('click',()=>{offset=Math.max(0,offset-limit);loadUsers();});$('usersNext').addEventListener('click',()=>{offset+=limit;loadUsers();});
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(creating)return;const body=Object.fromEntries(new FormData(form));
  if(body.role==='administrador'&&!await confirmAction({title:'Crear administrador',message:'Esta cuenta podrá gestionar otros usuarios y las configuraciones permitidas de CYSA.',label:'Crear administrador'})){body.password='';return;}
  creating=true;$('newUserError').textContent='';for(const id of ['createUser','closeUserDialog','cancelUserDialog'])$(id).disabled=true;$('createUser').textContent='Creando cuenta…';
  try{const created=await request('','POST',body);offset=0;creating=false;dialog.close();status('Cuenta '+created.username+' creada. Debe cambiar su contraseña al ingresar.');await loadUsers();}
  catch(error){$('newUserError').textContent=error.message;}
  finally{body.password='';form.elements.password.value='';creating=false;for(const id of ['createUser','closeUserDialog','cancelUserDialog'])$(id).disabled=false;$('createUser').textContent='Crear usuario';}
 });
}
