import {readFile} from 'node:fs/promises';
import {test} from 'node:test';
import assert from 'node:assert/strict';
const source=await readFile(new URL('../../panel/oidc.js',import.meta.url),'utf8');
let sequence=0;
async function setup(handler,accessClaims={},mfa=false){
 const saved={state:'estado',nonce:'nonce',verifier:'verificador',created:Date.now(),mfa};
 globalThis.location={href:'http://localhost:8088/?code=codigo&state=estado',assign:()=>{}};
 globalThis.history={replaceState:()=>{}};
 globalThis.sessionStorage={getItem:()=>JSON.stringify(saved),removeItem:()=>{},setItem:()=>{}};
 const jwt=claims=>'e30.'+Buffer.from(JSON.stringify(claims)).toString('base64url')+'.firma';
 const bundle=(seconds=10)=>({access_token:jwt({sub:'usuario',realm_access:{roles:['operador']},...accessClaims}),refresh_token:'renovable',id_token:jwt({nonce:'nonce',iss:'http://localhost:8080/realms/cysa',aud:'cysa-panel',exp:Date.now()/1000+300}),expires_in:seconds});
 globalThis.fetch=async(url,options)=>new URLSearchParams(options.body).get('grant_type')==='authorization_code'?{ok:true,json:async()=>bundle()}:handler(bundle);
 const oidc=await import('data:text/javascript;base64,'+Buffer.from(source+'\n// caso '+sequence++).toString('base64'));
 await oidc.init({issuer:'http://localhost:8080/realms/cysa',clientId:'cysa-panel',redirectUri:'http://localhost:8088/'});
 return oidc;
}

test('tres consultas concurrentes renuevan una sola vez',async()=>{
 let count=0,release;const gate=new Promise(resolve=>release=resolve);
 const oidc=await setup(async bundle=>{count++;await gate;return {ok:true,json:async()=>bundle(300)};});
 const pending=[oidc.accessToken(),oidc.accessToken(),oidc.accessToken()];
 await new Promise(setImmediate);assert.equal(count,1);release();
 const values=await Promise.all(pending);assert.equal(new Set(values).size,1);
});

test('renovacion fallida no conserva una sesion utilizable',async()=>{
 const oidc=await setup(async()=>({ok:false}));
 await assert.rejects(oidc.accessToken(),/Ingresa nuevamente/);
 await assert.rejects(oidc.accessToken(),/Se requiere login/);
});

test('cerrar sesion mientras renueva no restaura tokens',async()=>{
 let release;const gate=new Promise(resolve=>release=resolve);
 const oidc=await setup(async bundle=>{await gate;return {ok:true,json:async()=>bundle(300)};});
 const pending=oidc.accessToken();const rejected=assert.rejects(pending,/sesión ha finalizado/);
 oidc.logout();release();await rejected;
 await assert.rejects(oidc.accessToken(),/Se requiere login/);
});

test('consulta normal solicita nivel uno y no fuerza OTP',async()=>{
 const oidc=await setup(async bundle=>({ok:true,json:async()=>bundle(300)}));let destination;
 location.assign=url=>destination=new URL(url);await oidc.login();
 assert.equal(destination.searchParams.get('acr_values'),'1');
 assert.equal(destination.searchParams.has('claims'),false);assert.equal(oidc.mfaReady(),false);
});

test('acción crítica solicita nivel dos esencial y autentica de nuevo',async()=>{
 const oidc=await setup(async bundle=>({ok:true,json:async()=>bundle(300)}));let destination,saved;
 location.assign=url=>destination=new URL(url);sessionStorage.setItem=(_,value)=>saved=JSON.parse(value);
 await oidc.login({mfa:true});assert.equal(destination.searchParams.get('acr_values'),'2');
 assert.equal(JSON.parse(destination.searchParams.get('claims')).id_token.acr.essential,true);
 assert.equal(destination.searchParams.get('max_age'),'0');assert.equal(saved.mfa,true);
});

test('MFA vencida o sin segundo factor no habilita cambios',async()=>{
 for(const claims of [{auth_time:Date.now()/1000,acr:'1'},{auth_time:Date.now()/1000-301,acr:'2'},{auth_time:Date.now()/1000+60,acr:'2'}]){
  const oidc=await setup(async bundle=>({ok:true,json:async()=>bundle(300)}),claims);assert.equal(oidc.mfaReady(),false);
 }
 const oidc=await setup(async bundle=>({ok:true,json:async()=>bundle(300)}),{auth_time:Date.now()/1000-1,acr:'2'});assert.equal(oidc.mfaReady(),true);
});

test('el retorno de una solicitud MFA rechaza una sesión degradada',async()=>{
 await assert.rejects(setup(async bundle=>({ok:true,json:async()=>bundle(300)}),{auth_time:Date.now()/1000,acr:'1'},true),/no confirmó el segundo factor/);
});

test('un módulo reutiliza SSO sin solicitar otro botón ni forzar contraseña u OTP',async()=>{
 const oidc=await setup(async bundle=>({ok:true,json:async()=>bundle(300)}));
 location.href='http://localhost:15184/';let target;location.assign=url=>target=new URL(url);
 const active=await oidc.ensureSession({issuer:'http://localhost:8080/realms/cysa',clientId:'cysa-panel',redirectUri:'http://localhost:15184/'});
 assert.equal(active,false);assert.equal(target.searchParams.get('redirect_uri'),'http://localhost:15184/');
 assert.equal(target.searchParams.get('acr_values'),'1');assert.equal(target.searchParams.has('prompt'),false);assert.equal(target.searchParams.has('max_age'),false);
});

test('un retorno OIDC válido entra al módulo sin iniciar otra autorización',async()=>{
 const oidc=await setup(async bundle=>({ok:true,json:async()=>bundle(300)}));let redirects=0;location.assign=()=>redirects++;
 const active=await oidc.ensureSession({issuer:'http://localhost:8080/realms/cysa',clientId:'cysa-panel',redirectUri:'http://localhost:8088/'});
 assert.equal(active,true);assert.equal(redirects,0);
});
