let pending=false;
export function confirmAction({title,message,label='Confirmar'}){
 if(pending)return Promise.resolve(false);
 pending=true;const dialog=document.getElementById('confirmDialog');
 document.getElementById('confirmTitle').textContent=title;document.getElementById('confirmMessage').textContent=message;document.getElementById('confirmAccept').textContent=label;dialog.returnValue='cancel';
 return new Promise(resolve=>{dialog.addEventListener('close',()=>{pending=false;resolve(dialog.returnValue==='confirm');},{once:true});dialog.showModal();});
}
