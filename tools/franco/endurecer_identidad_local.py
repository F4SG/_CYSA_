"""Aplica protecciones de identidad y normaliza SOLO cuentas locales conocidas."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend'),str(ROOT/'shared')]
from app.users import KeycloakUsers
from configurar_usuarios_local import read_env

SECURITY=dict(bruteForceProtected=True,permanentLockout=False,failureFactor=5,
    waitIncrementSeconds=30,maxFailureWaitSeconds=300,maxDeltaTimeSeconds=600,
    minimumQuickLoginWaitSeconds=2,quickLoginCheckMilliSeconds=1000,
    passwordPolicy='length(12) and maxLength(128)')


def apply(root):
    values=read_env(root/'infra/.env');base=values.get('KEYCLOAK_PUBLIC_URL','http://localhost:8080').rstrip('/')
    kc=KeycloakUsers(base=base,realm='cysa')
    token,_=kc.transport('POST',base+'/realms/master/protocol/openid-connect/token',
        dict(grant_type='password',client_id='admin-cli',username='bootstrap',password=values['KC_ADMIN_PASSWORD']),form=True)
    kc.token=lambda:token['access_token']
    realm,_=kc.api('GET','');users,_=kc.api('GET','/users?max=1000')
    by_id={u['id']:u for u in users};by_name={u['username']:u for u in users}
    initial=root/'infra/runtime/clientes/usuarios-locales.json'
    sample=root/'infra/runtime/clientes/prueba-usuarios.json'
    local=json.loads(initial.read_text(encoding='utf-8')) if initial.exists() else {}
    samples=json.loads(sample.read_text(encoding='utf-8')) if sample.exists() else {'users':[]}
    changes=[];accounts=[]
    for username,role,first,last,email in [
        ('administrador','administrador','Administración','CYSA','administracion@cysa.example'),
        ('operador','operador','Operación','Central','operacion@cysa.example')]:
        if username in local and username in by_name:
            row=by_name[username];changes.append((row,dict(username=username,firstName=first,lastName=last,email=email,emailVerified=False)))
            accounts.append(dict(username=username,role=role,password=local[username],id=row['id']))
    for entry in samples['users']:
        row=by_id.get(entry.get('id'))
        if not row:continue
        role=entry['role'];username='admin.accesos' if role=='administrador' else 'operador.transito'
        if row['username'] not in [entry['username'],username]:raise RuntimeError('Una cuenta fue modificada fuera de esta herramienta; revisar antes de normalizar')
        if username in by_name and by_name[username]['id']!=row['id']:raise RuntimeError('El nombre de destino ya existe; no se sobrescribe')
        changes.append((row,dict(username=username,firstName='Gestión' if role=='administrador' else 'Operación',lastName='de accesos' if role=='administrador' else 'de tránsito',email=username+'@cysa.example',emailVerified=False)))
        entry['username']=username;accounts.append(dict(entry))
    backup=root/'respaldos/seguridad-2026-10-30';backup.mkdir(parents=True,exist_ok=True)
    path=backup/'perfiles-anteriores.json'
    if not path.exists():path.write_text(json.dumps([row for row,_ in changes],indent=2,ensure_ascii=False),encoding='utf-8')
    # Se habilita temporalmente el cambio de nombre para esta migración local y se restaura siempre.
    original=realm.get('editUsernameAllowed',False)
    kc.api('PUT','',{**SECURITY,'editUsernameAllowed':True})
    try:
        for row,profile in changes:kc.api('PUT','/users/'+row['id'],profile)
    finally:kc.api('PUT','',{'editUsernameAllowed':original})
    master=KeycloakUsers(base=base,realm='master');master.token=kc.token;master.api('PUT','',SECURITY)
    if sample.exists():sample.write_text(json.dumps(samples,indent=2,ensure_ascii=False),encoding='utf-8')
    (root/'infra/runtime/clientes/cuentas-locales.json').write_text(json.dumps({'url':'http://localhost:8088/','users':accounts},indent=2,ensure_ascii=False),encoding='utf-8')
    print('Perfiles actualizados; identificadores, roles y contrasenas conservados. Protecciones activadas.')
    for account in accounts:print(account['username']+' / '+account['role'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=ROOT);args=parser.parse_args();apply(args.repo.resolve())
if __name__=='__main__':main()
