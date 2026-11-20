"""MFA real para el cliente del panel: OTP obligatorio y AMR firmado por Keycloak."""
import json,sys
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

def configurar(root):
    env=read_env(Path(root)/'infra/.env');base=env.get('KEYCLOAK_PUBLIC_URL','http://localhost:8080')
    kc=KeycloakUsers(base=base,realm='cysa')
    result,_=kc.transport('POST',base+'/realms/master/protocol/openid-connect/token',
        dict(grant_type='password',client_id='admin-cli',username='bootstrap',password=env['KC_ADMIN_PASSWORD']),form=True)
    kc.token=lambda:result['access_token']
    flows,_=kc.api('GET','/authentication/flows');alias='cysa-control-mfa'
    if not any(f['alias']==alias for f in flows):kc.api('POST','/authentication/flows/browser/copy',{'newName':alias})
    executions,_=kc.api('GET',f'/authentication/flows/{alias}/executions')
    # Forzar la rama OTP, sin la condición que permite omitirla cuando aún no hay credencial.
    for e in executions:
        if e.get('displayName','').endswith('Conditional OTP'):
            kc.api('PUT',f'/authentication/flows/{alias}/executions',{'id':e['id'],'requirement':'REQUIRED'})
        if e.get('providerId')=='conditional-user-configured':
            kc.api('PUT',f'/authentication/flows/{alias}/executions',{'id':e['id'],'requirement':'DISABLED'})
        if e.get('providerId')=='auth-otp-form':
            kc.api('PUT',f'/authentication/flows/{alias}/executions',{'id':e['id'],'requirement':'REQUIRED'})
            referencia_otp(kc,e)
    flows,_=kc.api('GET','/authentication/flows');flow=next(f for f in flows if f['alias']==alias)
    clients,_=kc.api('GET','/clients?clientId=cysa-panel');client=clients[0]
    client.setdefault('authenticationFlowBindingOverrides',{})['browser']=flow['id']
    import os
    panel=os.environ.get('CYSA_OPERACION_URL','http://localhost:5184').rstrip('/')
    if panel+'/' not in client['redirectUris']:client['redirectUris'].append(panel+'/')
    if panel not in client['webOrigins']:client['webOrigins'].append(panel)
    kc.api('PUT','/clients/'+client['id'],client)
    mappers,_=kc.api('GET',f'/clients/{client["id"]}/protocol-mappers/models')
    if not any(m['protocolMapper']=='oidc-amr-mapper' for m in mappers):
        kc.api('POST',f'/clients/{client["id"]}/protocol-mappers/models',dict(name='cysa-amr',protocol='openid-connect',
            protocolMapper='oidc-amr-mapper',config={'access.token.claim':'true','id.token.claim':'true'}))
    if not any(m['name']=='cysa-auth-time' for m in mappers):
        kc.api('POST',f'/clients/{client["id"]}/protocol-mappers/models',dict(name='cysa-auth-time',protocol='openid-connect',
            protocolMapper='oidc-usersessionmodel-note-mapper',config={'user.session.note':'AUTH_TIME','claim.name':'auth_time',
                'jsonType.label':'long','access.token.claim':'true','id.token.claim':'true'}))
    users,_=kc.api('GET','/users?max=1000')
    for user in users:
        creds,_=kc.api('GET',f'/users/{user["id"]}/credentials')
        if not any(c['type']=='otp' for c in creds):
            actions=user.get('requiredActions',[])
            if 'CONFIGURE_TOTP' not in actions:
                user['requiredActions']=[*actions,'CONFIGURE_TOTP'];kc.api('PUT',f'/users/{user["id"]}',user)
    print('MFA OTP obligatorio configurado para el panel. Cada usuario enrola su autenticador en su siguiente ingreso; no se imprimen secretos.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=ROOT);a=p.parse_args();configurar(a.repo)
