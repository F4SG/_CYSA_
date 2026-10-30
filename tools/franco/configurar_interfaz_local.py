"""Aplica el tema y el idioma de CYSA al realm existente, sin modificar cuentas."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'shared'))
from app.users import KeycloakUsers
from configurar_usuarios_local import read_env

def configure(root):
    values=read_env(root/'infra/.env');base=values.get('KEYCLOAK_PUBLIC_URL','http://localhost:8080').rstrip('/')
    kc=KeycloakUsers(base=base,realm='cysa')
    result,_=kc.transport('POST',base+'/realms/master/protocol/openid-connect/token',
        dict(grant_type='password',client_id='admin-cli',username='bootstrap',password=values['KC_ADMIN_PASSWORD']),form=True)
    kc.token=lambda:result['access_token']
    kc.api('PUT','',dict(displayName='CYSA',loginTheme='cysa',internationalizationEnabled=True,supportedLocales=['es'],defaultLocale='es'))
    print('Tema CYSA e idioma espanol aplicados. Cuentas y contrasenas conservadas.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=ROOT);args=p.parse_args()
    configure(args.repo.resolve())
if __name__=='__main__':main()
