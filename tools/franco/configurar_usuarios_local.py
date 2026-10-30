"""Habilita gestión de usuarios en el Keycloak local existente, sin recrear datos."""
import argparse,os,secrets,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'shared'))
from app.users import KeycloakUsers


def read_env(path):
    return {line.split('=',1)[0]:line.split('=',1)[1] for line in path.read_text(encoding='utf-8-sig').splitlines()
            if line.strip() and not line.lstrip().startswith('#') and '=' in line}


def prepare_identity_files(root):
    path=root/'infra/runtime/clientes/usuarios-api.env'
    if path.exists():return read_env(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    values=dict(KC_INTERNAL_URL='http://keycloak:8080',KC_REALM='cysa',KC_USERS_CLIENT_ID='cysa-user-admin',
        KC_USERS_CLIENT_SECRET=secrets.token_urlsafe(48))
    # Creación exclusiva: nunca sobrescribir un secreto existente.
    with path.open('x',encoding='utf-8') as stream:
        stream.write(''.join(f'{key}={value}\n' for key,value in values.items()))
    os.chmod(path,0o600)
    return values


def configure(root):
    settings=read_env(root/'infra/.env');values=prepare_identity_files(root)
    base=settings.get('KEYCLOAK_PUBLIC_URL','http://localhost:8080').rstrip('/')
    kc=KeycloakUsers(base=base,realm='cysa')
    result,_=kc.transport('POST',base+'/realms/master/protocol/openid-connect/token',
        dict(grant_type='password',client_id='admin-cli',username='bootstrap',password=settings['KC_ADMIN_PASSWORD']),form=True)
    kc.token=lambda:result['access_token']
    client_id=values['KC_USERS_CLIENT_ID']
    clients,_=kc.api('GET','/clients?clientId='+client_id)
    payload=dict(clientId=client_id,name='CYSA gestion de usuarios (solo backend)',enabled=True,
        protocol='openid-connect',publicClient=False,clientAuthenticatorType='client-secret',
        secret=values['KC_USERS_CLIENT_SECRET'],serviceAccountsEnabled=True,standardFlowEnabled=False,
        directAccessGrantsEnabled=False,implicitFlowEnabled=False,fullScopeAllowed=True,
        defaultClientScopes=['roles','basic'])
    if clients:kc.api('PUT','/clients/'+clients[0]['id'],payload)
    else:kc.api('POST','/clients',payload)
    clients,_=kc.api('GET','/clients?clientId='+client_id);client=clients[0]['id']
    account,_=kc.api('GET',f'/clients/{client}/service-account-user')
    management,_=kc.api('GET','/clients?clientId=realm-management');manager=management[0]['id']
    roles=[]
    for name in ['query-users','view-users','manage-users','view-realm']:
        role,_=kc.api('GET',f'/clients/{manager}/roles/{name}');roles.append(role)
    kc.api('POST',f'/users/{account["id"]}/role-mappings/clients/{manager}',roles)
    events,_=kc.api('GET','/events/config')
    events.update(adminEventsEnabled=True,adminEventsDetailsEnabled=False)
    kc.api('PUT','/events/config',events)
    print('Gestion de usuarios configurada. Reiniciar/recrear solo api para cargar su secreto local.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=ROOT)
    p.add_argument('--solo-archivos',action='store_true',help='Preparar el entorno sin conectar con Keycloak ni rotar secretos')
    args=p.parse_args();root=args.repo.resolve()
    if args.solo_archivos:
        prepare_identity_files(root);print('Entorno local de gestion preparado; no se modifico Keycloak.')
    else:configure(root)
if __name__=='__main__':main()
