// Authorization Code + PKCE S256. Tokens únicamente en memoria; no usar localStorage.
let cfg,tokens=null,expires=0,refreshing=null,sessionVersion=0;
const encode=bytes=>btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
const random=()=>encode(crypto.getRandomValues(new Uint8Array(32)));
const decode=token=>JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(token.split('.')[1].replaceAll('-','+').replaceAll('_','/')),c=>c.charCodeAt(0))));
async function tokenRequest(body){
 const version=sessionVersion;
 const r=await fetch(cfg.issuer+'/protocol/openid-connect/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(body)});
 if(version!==sessionVersion)throw new Error('La sesión ha finalizado');
 if(!r.ok){tokens=null;expires=0;throw new Error('La sesión no pudo renovarse. Ingresa nuevamente.');}
 const next=await r.json();
 if(version!==sessionVersion)throw new Error('La sesión ha finalizado');
 if(typeof next.access_token!=='string'||!Number.isFinite(next.expires_in)||next.expires_in<=0){tokens=null;expires=0;throw new Error('Respuesta de sesión inválida');}
 tokens=next;expires=Date.now()+tokens.expires_in*1000;return tokens;
}
export async function init(config){
 cfg=config;
 const url=new URL(location.href);const code=url.searchParams.get('code');
 if(url.searchParams.has('error')){history.replaceState({},'',cfg.redirectUri);sessionStorage.removeItem('cysa.pkce');throw new Error('Ingreso cancelado o rechazado por Keycloak');}
 if(!code)return false;
 const saved=JSON.parse(sessionStorage.getItem('cysa.pkce')||'null');sessionStorage.removeItem('cysa.pkce');
 const state=url.searchParams.get('state');history.replaceState({},'',cfg.redirectUri);
 if(!saved||saved.state!==state||Date.now()-saved.created>300000)throw new Error('Respuesta OIDC inválida o expirada');
 await tokenRequest({grant_type:'authorization_code',client_id:cfg.clientId,redirect_uri:cfg.redirectUri,code,code_verifier:saved.verifier});
 const claims=decode(tokens.id_token);
 if(claims.nonce!==saved.nonce||claims.iss!==cfg.issuer||claims.aud!==cfg.clientId||claims.exp*1000<Date.now()){
   tokens=null;throw new Error('ID token no coincide con la solicitud de login');
 }
 return true;
}
export async function login(){
 const state=random(),nonce=random(),verifier=random();
 const challenge=encode(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier))));
 sessionStorage.setItem('cysa.pkce',JSON.stringify({state,nonce,verifier,created:Date.now()}));
 const q=new URLSearchParams({client_id:cfg.clientId,redirect_uri:cfg.redirectUri,response_type:'code',scope:'openid profile',state,nonce,code_challenge:challenge,code_challenge_method:'S256'});
 location.assign(cfg.issuer+'/protocol/openid-connect/auth?'+q);
}
export async function accessToken(){
 if(!tokens)throw new Error('Se requiere login');
 if(Date.now()>expires-30000){
  if(!refreshing){
   if(!tokens.refresh_token){tokens=null;throw new Error('Ingresa nuevamente para continuar');}
   refreshing=tokenRequest({grant_type:'refresh_token',client_id:cfg.clientId,refresh_token:tokens.refresh_token})
    .catch(error=>{tokens=null;expires=0;throw error;}).finally(()=>{refreshing=null;});
  }
  await refreshing;
 }
 if(!tokens)throw new Error('La sesión ha finalizado');
 return tokens.access_token;
}
export function identity(){const c=decode(tokens.access_token);return (c.preferred_username||c.sub)+' · '+(c.realm_access?.roles||[]).filter(r=>['operador','administrador'].includes(r)).join(', ');}
export function logout(){sessionVersion++;const hint=tokens?.id_token;tokens=null;expires=0;const q=new URLSearchParams({client_id:cfg.clientId,post_logout_redirect_uri:cfg.redirectUri});if(hint)q.set('id_token_hint',hint);location.assign(cfg.issuer+'/protocol/openid-connect/logout?'+q);}

export function hasRole(role){return Boolean(tokens&&(decode(tokens.access_token).realm_access?.roles||[]).includes(role));}
export function subject(){return tokens?decode(tokens.access_token).sub:null;}
