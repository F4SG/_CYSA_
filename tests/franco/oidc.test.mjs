import {readFile} from 'node:fs/promises';
import {test} from 'node:test';
import assert from 'node:assert/strict';
const source=await readFile(new URL('../../panel/oidc.js',import.meta.url),'utf8');
let sequence=0;
async function setup(handler){
 const saved={state:'estado',nonce:'nonce',verifier:'verificador',created:Date.now()};
 globalThis.location={href:'http://localhost:8088/?code=codigo&state=estado',assign:()=>{}};
 globalThis.history={replaceState:()=>{}};
 globalThis.sessionStorage={getItem:()=>JSON.stringify(saved),removeItem:()=>{},setItem:()=>{}};
 const jwt=claims=>'e30.'+Buffer.from(JSON.stringify(claims)).toString('base64url')+'.firma';
 const bundle=(seconds=10)=>({access_token:jwt({sub:'usuario',realm_access:{roles:['operador']}}),refresh_token:'renovable',id_token:jwt({nonce:'nonce',iss:'http://localhost:8080/realms/cysa',aud:'cysa-panel',exp:Date.now()/1000+300}),expires_in:seconds});
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
