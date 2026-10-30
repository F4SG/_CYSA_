from copy import deepcopy
from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.auth import principal
from app.main import create_app
from app.users import KeycloakUsers

ADMIN='11111111-1111-4111-8111-111111111111'
OPERATOR='22222222-2222-4222-8222-222222222222'
TECH='33333333-3333-4333-8333-333333333333'
PASSWORD='Solo-prueba-no-real-42!'

class Directory(KeycloakUsers):
    def __init__(self):
        super().__init__(secret='solo-prueba')
        self.rows={ADMIN:dict(id=ADMIN,username='admin',enabled=True),OPERATOR:dict(id=OPERATOR,username='operador',enabled=True),
            TECH:dict(id=TECH,username='service-account-prueba',enabled=True,serviceAccountClientId='prueba')}
        self.assignments={ADMIN:['administrador'],OPERATOR:['operador'],TECH:[]}
        self.calls=[];self.fail_assign=False
    def api(self,method,path,data=None):
        self.calls.append((method,path))
        if path.startswith('/roles/') and method=='GET':return dict(id=path[7:],name=path[7:]),{}
        if path.startswith('/users?'):return deepcopy(list(self.rows.values())),{}
        if path=='/users' and method=='POST':
            if any(x['username']==data['username'] for x in self.rows.values()):raise HTTPException(409,'El usuario o correo ya existe')
            uid=str(uuid4());self.rows[uid]={**deepcopy(data),'id':uid};self.assignments[uid]=[]
            return None,{'Location':'http://keycloak/admin/realms/cysa/users/'+uid}
        pieces=path.strip('/').split('/');uid=pieces[1]
        if uid not in self.rows:raise HTTPException(404,'No existe')
        if len(pieces)==2:
            if method=='GET':return deepcopy(self.rows[uid]),{}
            if method=='PUT':self.rows[uid].update(data);return None,{}
            if method=='DELETE':del self.rows[uid];del self.assignments[uid];return None,{}
        if pieces[-1]=='logout':return None,{}
        if 'role-mappings' in path:
            if method=='GET':return [dict(id=x,name=x) for x in self.assignments[uid]],{}
            if method=='POST':
                if self.fail_assign:raise HTTPException(503,'Fallo simulado')
                self.assignments[uid]=list(set(self.assignments[uid])|{x['name'] for x in data});return None,{}
            if method=='DELETE':self.assignments[uid]=[x for x in self.assignments[uid] if x not in {r['name'] for r in data}];return None,{}
        raise AssertionError((method,path))

@pytest.fixture
def setup(repository):
    directory=Directory();app=create_app(repository,directory)
    claims={'sub':ADMIN,'realm_access':{'roles':['administrador']}}
    app.dependency_overrides[principal]=lambda:claims
    with TestClient(app) as client:yield client,directory,claims


def payload(role='operador'):
    return dict(username='nuevo.usuario',first_name='Usuario',last_name='Prueba',email='prueba@example.invalid',role=role,password=PASSWORD)

@pytest.mark.parametrize('role',['administrador','operador'])
def test_admin_crea_ambos_roles_con_clave_temporal_sin_exponerla(setup,role):
    client,directory,_=setup
    response=client.post('/api/usuarios',json=payload(role));assert response.status_code==201,response.text
    user=response.json();assert user['roles']==[role] and user['enabled'] and user['temporary_password']
    assert PASSWORD not in response.text and 'credentials' not in response.text
    assert response.headers['cache-control']=='no-store'
    raw=directory.rows[user['id']];assert raw['credentials'][0]['temporary'] and not raw['emailVerified']
    assert client.post('/api/usuarios',json=payload(role)).status_code==409


def test_lista_excluye_cuentas_tecnicas_y_no_incluye_claves(setup):
    client,_,_=setup;response=client.get('/api/usuarios')
    assert response.status_code==200 and len(response.json()['items'])==2
    assert 'service-account' not in response.text and 'credentials' not in response.text

@pytest.mark.parametrize('method,path,body',[('get','/api/usuarios',None),('post','/api/usuarios',payload()),('patch','/api/usuarios/'+ADMIN,{'role':'operador','enabled':False})])
def test_operador_no_gestiona_usuarios_ni_consulta_keycloak(setup,method,path,body):
    client,directory,claims=setup;claims.update(sub=OPERATOR,realm_access={'roles':['operador']})
    response=getattr(client,method)(path,**({'json':body} if body else {}))
    assert response.status_code==403 and directory.calls==[]


def test_sin_token_no_hay_acceso(repository):
    directory=Directory()
    with TestClient(create_app(repository,directory)) as client:
        assert client.get('/api/usuarios').status_code==401
        assert client.post('/api/usuarios',json=payload()).status_code==401
    assert directory.calls==[]

@pytest.mark.parametrize('changes',[{'role':'realm-admin'},{'password':'corta'},{'email':'no-es-correo'},{'username':'../admin'},{'enabled':True}])
def test_validacion_de_alta_rechaza_privilegios_y_datos_invalidos(setup,changes):
    client,directory,_=setup
    assert client.post('/api/usuarios',json={**payload(),**changes}).status_code==422
    assert not any(method=='POST' for method,path in directory.calls)


def test_cambio_de_rol_estado_y_cierre_de_sesiones(setup):
    client,directory,_=setup
    response=client.patch('/api/usuarios/'+OPERATOR,json={'role':'administrador','enabled':False})
    assert response.status_code==200 and response.json()['roles']==['administrador'] and not response.json()['enabled']
    assert ('POST',f'/users/{OPERATOR}/logout') in directory.calls
    assert client.patch('/api/usuarios/'+OPERATOR,json={'role':'operador','enabled':True}).json()['enabled']


def test_autoproteccion_y_token_de_admin_con_rol_revocado(setup):
    client,directory,_=setup
    assert client.patch('/api/usuarios/'+ADMIN,json={'role':'operador','enabled':False}).status_code==409
    assert directory.rows[ADMIN]['enabled']
    directory.assignments[ADMIN]=['operador']
    assert client.post('/api/usuarios',json=payload()).status_code==403
    directory.assignments[ADMIN]=['administrador'];directory.rows[ADMIN]['enabled']=False
    assert client.get('/api/usuarios').status_code==403


def test_cuentas_tecnicas_y_id_invalido_no_modificables(setup):
    client,_,_=setup
    assert client.patch('/api/usuarios/'+TECH,json={'role':'operador','enabled':True}).status_code==403
    assert client.patch('/api/usuarios/no-es-uuid',json={'role':'operador','enabled':True}).status_code==422
    assert client.patch('/api/usuarios/'+OPERATOR,json={'role':'operador','enabled':'false'}).status_code==422


def test_fallo_de_asignacion_no_deja_cuenta_nueva_activa(setup):
    client,directory,_=setup;directory.fail_assign=True
    assert client.post('/api/usuarios',json=payload()).status_code==503
    assert not any(x['username']=='nuevo.usuario' for x in directory.rows.values())


def test_fallo_de_cambio_mantiene_cuenta_desactivada(setup):
    client,directory,_=setup;directory.fail_assign=True
    assert client.patch('/api/usuarios/'+OPERATOR,json={'role':'administrador','enabled':True}).status_code==503
    assert not directory.rows[OPERATOR]['enabled']


def test_errores_de_validacion_no_devuelven_claves(setup):
    client,_,_=setup
    response=client.post('/api/usuarios',json={**payload(),'role':'rol-invalido'})
    assert response.status_code==422 and PASSWORD not in response.text
    assert all('input' not in error and 'ctx' not in error for error in response.json()['detail'])


def test_configuracion_local_genera_un_solo_secreto_no_lo_rota(tmp_path):
    from configurar_usuarios_local import prepare_identity_files
    values=prepare_identity_files(tmp_path)
    assert len(values['KC_USERS_CLIENT_SECRET'])>=48
    assert prepare_identity_files(tmp_path)==values
    assert (tmp_path/'infra/runtime/clientes/usuarios-api.env').is_file()


def test_quitar_rol_tambien_bloquea_escrituras_de_inventario_con_jwt_anterior(setup,monkeypatch):
    client,directory,_=setup
    directory.assignments[ADMIN]=['operador']
    response=client.post('/api/inventario/carga',json={'items':[]})
    assert response.status_code==403


def test_cuenta_desactivada_pierde_tambien_lectura_de_monitoreo(setup):
    client,directory,_=setup;directory.rows[ADMIN]['enabled']=False
    assert client.get('/api/estados').status_code==403


def test_falta_de_configuracion_no_omite_control_de_permisos(repository,monkeypatch):
    from app.users import KeycloakUsers
    monkeypatch.delenv('KC_USERS_CLIENT_SECRET',raising=False)
    directory=KeycloakUsers()
    directory.user=lambda uid:directory.token()
    app=create_app(repository,directory)
    app.dependency_overrides[principal]=lambda:{'sub':ADMIN,'realm_access':{'roles':['administrador']}}
    with TestClient(app) as client:
        assert client.post('/api/inventario/carga',json={'items':[]}).status_code==503


def test_rol_malformado_no_provoca_error_interno(setup):
    client,_,claims=setup;claims['realm_access']['roles']=[{'rol':'administrador'}]
    assert client.get('/api/estados').status_code==403


def test_bloquea_redirecciones_de_identidad_sin_reenviar_credenciales():
    from app.users import NoRedirect
    from urllib.request import Request
    from urllib.error import HTTPError
    request=Request('http://keycloak/realms/cysa',headers={'Authorization':'Bearer secreto-de-prueba'})
    with pytest.raises(HTTPError):NoRedirect().redirect_request(request,None,302,'Found',{},'https://ajeno.invalid/')


def test_respuesta_de_identidad_excesiva_no_se_procesa():
    directory=KeycloakUsers(secret='solo-prueba')
    class Response:
        headers={}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):return b'x'*limit
    class Opener:
        def open(self,*args,**kw):return Response()
    directory._opener=Opener()
    with pytest.raises(HTTPException) as result:directory.transport('GET','http://keycloak/')
    assert result.value.status_code==503


def test_realm_access_malformado_no_provoca_error_interno(setup):
    client,_,claims=setup;claims['realm_access']=['administrador']
    assert client.get('/api/estados').status_code==403


def test_password_llega_a_keycloak_sin_recortar_espacios(setup):
    client,directory,_=setup
    password='  Una clave exacta 42!  '
    response=client.post('/api/usuarios',json={**payload(),'first_name':'  Persona  ','password':password})
    assert response.status_code==201
    stored=directory.rows[response.json()['id']]
    assert stored['credentials'][0]['value']==password
    assert stored['firstName']=='Persona'


def test_preparacion_previa_a_compose_no_conecta_identidad(tmp_path,monkeypatch):
    import sys
    import configurar_usuarios_local as local
    monkeypatch.setattr(sys,'argv',['configurar_usuarios_local.py','--repo',str(tmp_path),'--solo-archivos'])
    def forbidden(*args):raise AssertionError('No debe conectar con Keycloak')
    monkeypatch.setattr(local,'configure',forbidden)
    local.main()
    before=(tmp_path/'infra/runtime/clientes/usuarios-api.env').read_bytes()
    local.main()
    assert (tmp_path/'infra/runtime/clientes/usuarios-api.env').read_bytes()==before
