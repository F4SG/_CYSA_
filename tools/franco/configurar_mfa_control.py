"""Ingreso con contraseña; OTP y enrolamiento solo al solicitar nivel 2."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'shared'),str(ROOT/'tools/franco')]
from app.users import KeycloakUsers
from configurar_usuarios_local import read_env

def referencia_otp(kc,execution):
    # Keycloak AmrUtils obtiene estas referencias de ejecuciones completadas, no de atributos del usuario.
    payload={'alias':'cysa-otp-'+execution['id'],'config':{'default.reference.value':'otp','default.reference.maxAge':'300'}}
    config_id=execution.get('authenticationConfig')
    if config_id:kc.api('PUT','/authentication/config/'+config_id,dict(payload,id=config_id))
    else:kc.api('POST',f'/authentication/executions/{execution["id"]}/config',payload)

def configurar_flujo(kc):
    alias='cysa-step-up-v1'
    flows,_=kc.api('GET','/authentication/flows')
    if not any(f['alias']==alias for f in flows):
        kc.api('POST','/authentication/flows',dict(alias=alias,providerId='basic-flow',topLevel=True,builtIn=False))
    def execution(parent,provider,requirement):
        entries,_=kc.api('GET',f'/authentication/flows/{parent}/executions')
        item=next((e for e in entries if e.get('providerId')==provider and e.get('level',0)==0),None)
        if item is None:
            kc.api('POST',f'/authentication/flows/{parent}/executions/execution',{'provider':provider})
            entries,_=kc.api('GET',f'/authentication/flows/{parent}/executions')
            item=next(e for e in entries if e.get('providerId')==provider and e.get('level',0)==0)
        kc.api('PUT',f'/authentication/flows/{parent}/executions',dict(item,requirement=requirement))
        return item
    def subflow(parent,name,requirement):
        entries,_=kc.api('GET',f'/authentication/flows/{parent}/executions')
        item=next((e for e in entries if e.get('displayName')==name),None)
        if item is None:
            kc.api('POST',f'/authentication/flows/{parent}/executions/flow',dict(alias=name,type='basic-flow',provider='basic-flow',description='CYSA: autenticación por nivel'))
            entries,_=kc.api('GET',f'/authentication/flows/{parent}/executions')
            item=next(e for e in entries if e.get('displayName')==name)
        kc.api('PUT',f'/authentication/flows/{parent}/executions',dict(item,requirement=requirement))
    execution(alias,'auth-cookie','ALTERNATIVE')
    forms=alias+'-forms';subflow(alias,forms,'ALTERNATIVE')
    for level,provider,age in [(1,'auth-username-password-form',36000),(2,'auth-otp-form',0)]:
        child=alias+'-level-'+str(level);subflow(forms,child,'CONDITIONAL')
        condition=execution(child,'conditional-level-of-authentication','REQUIRED')
        payload=dict(alias=child+'-condition',config={'loa-condition-level':str(level),'loa-max-age':str(age)})
        if condition.get('authenticationConfig'):
            kc.api('PUT','/authentication/config/'+condition['authenticationConfig'],dict(payload,id=condition['authenticationConfig']))
        else:kc.api('POST',f'/authentication/executions/{condition["id"]}/config',payload)
        factor=execution(child,provider,'REQUIRED')
        if level==2:referencia_otp(kc,factor)
    flows,_=kc.api('GET','/authentication/flows')
    return next(f for f in flows if f['alias']==alias)

def configurar(root):
    env=read_env(Path(root)/'infra/.env');base=env.get('KEYCLOAK_PUBLIC_URL','http://localhost:8080')
    # Administración local: evitar el reintento IPv6 de Windows en cada petición.
    base=base.replace('://localhost:', '://127.0.0.1:')
    kc=KeycloakUsers(base=base,realm='cysa')
    result,_=kc.transport('POST',base+'/realms/master/protocol/openid-connect/token',
        dict(grant_type='password',client_id='admin-cli',username='bootstrap',password=env['KC_ADMIN_PASSWORD']),form=True)
    expires=time.monotonic()+result.get('expires_in',60)-10
    def admin_token():
        nonlocal result,expires
        if time.monotonic()>=expires:
            result,_=kc.transport('POST',base+'/realms/master/protocol/openid-connect/token',
                dict(grant_type='password',client_id='admin-cli',username='bootstrap',password=env['KC_ADMIN_PASSWORD']),form=True)
            expires=time.monotonic()+result.get('expires_in',60)-10
        return result['access_token']
    kc.token=admin_token
    flow=configurar_flujo(kc)
    clients,_=kc.api('GET','/clients?clientId=cysa-panel');client=clients[0]
    client.setdefault('authenticationFlowBindingOverrides',{})['browser']=flow['id']
    client.setdefault('attributes',{}).update({'default.acr.values':'1','acr.loa.map':json.dumps({'1':1,'2':2})})
    import os
    panel=os.environ.get('CYSA_OPERACION_URL','http://localhost:5184').rstrip('/')
    web=os.environ.get('CYSA_WEB_URL','http://localhost:15183').rstrip('/')
    for redirect,origin in [(panel+'/',panel),(web+'/proyecto',web)]:
        if redirect not in client['redirectUris']:client['redirectUris'].append(redirect)
        if origin not in client['webOrigins']:client['webOrigins'].append(origin)
    logout=client['attributes'].get('post.logout.redirect.uris','').split('##')
    client['attributes']['post.logout.redirect.uris']='##'.join(dict.fromkeys([*filter(None,logout),panel+'/',web+'/proyecto']))
    kc.api('PUT','/clients/'+client['id'],client)
    mappers,_=kc.api('GET',f'/clients/{client["id"]}/protocol-mappers/models')
    if not any(m['protocolMapper']=='oidc-acr-mapper' for m in mappers):
        kc.api('POST',f'/clients/{client["id"]}/protocol-mappers/models',dict(name='cysa-acr',protocol='openid-connect',
            protocolMapper='oidc-acr-mapper',config={'access.token.claim':'true','id.token.claim':'true'}))
    if not any(m['protocolMapper']=='oidc-amr-mapper' for m in mappers):
        kc.api('POST',f'/clients/{client["id"]}/protocol-mappers/models',dict(name='cysa-amr',protocol='openid-connect',
            protocolMapper='oidc-amr-mapper',config={'access.token.claim':'true','id.token.claim':'true'}))
    if not any(m['name']=='cysa-auth-time' for m in mappers):
        kc.api('POST',f'/clients/{client["id"]}/protocol-mappers/models',dict(name='cysa-auth-time',protocol='openid-connect',
            protocolMapper='oidc-usersessionmodel-note-mapper',config={'user.session.note':'AUTH_TIME','claim.name':'auth_time',
                'jsonType.label':'long','access.token.claim':'true','id.token.claim':'true'}))
    users,_=kc.api('GET','/users?max=1000')
    for user in users:
        actions=user.get('requiredActions',[])
        if 'CONFIGURE_TOTP' in actions:
            user['requiredActions']=[a for a in actions if a!='CONFIGURE_TOTP'];kc.api('PUT',f'/users/{user["id"]}',user)
    print('Ingreso con contraseña configurado. Nivel 2 exige OTP: el QR aparece solo al realizar la primera acción crítica. Credenciales OTP existentes conservadas.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT);a=p.parse_args();configurar(a.repo)
