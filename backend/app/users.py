"""Gestión de cuentas de CYSA delegada en Keycloak; secretos solo en el servidor."""
import json,logging,os,re,time
from threading import RLock
from typing import Literal
from uuid import UUID
from urllib.parse import urlencode,quote,urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from fastapi import APIRouter,Depends,HTTPException,Query,Response
from pydantic import BaseModel,ConfigDict,Field,SecretStr,StrictBool,field_validator
from app.auth import admin_access

ROLES={'administrador','operador'}
log=logging.getLogger('uvicorn.error')

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        raise HTTPError(request.full_url,code,'Redireccion de identidad no permitida',headers,fp)


class NewUser(BaseModel):
    model_config=ConfigDict(extra='forbid')
    username:str=Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,63}$')
    first_name:str=Field(min_length=1,max_length=80)
    last_name:str=Field(min_length=1,max_length=80)
    email:str=Field(min_length=5,max_length=254)
    role:Literal['administrador','operador']
    password:SecretStr=Field(min_length=12,max_length=128)
    @field_validator('username','first_name','last_name','email',mode='before')
    @classmethod
    def trim_profile(cls,value):
        return value.strip() if isinstance(value,str) else value
    @field_validator('email')
    @classmethod
    def valid_email(cls,value):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):raise ValueError('Correo invalido')
        return value

class UserChange(BaseModel):
    model_config=ConfigDict(extra='forbid')
    role:Literal['administrador','operador']
    enabled:StrictBool

class KeycloakUsers:
    def __init__(self,base=None,realm=None,client=None,secret=None):
        self.base=(base or os.environ.get('KC_INTERNAL_URL','http://keycloak:8080')).rstrip('/')
        url=urlsplit(self.base)
        if url.scheme not in ('http','https') or not url.netloc or url.username or url.password or url.query or url.fragment:
            raise ValueError('KC_INTERNAL_URL debe ser una URL HTTP(S) sin credenciales ni parametros')
        self._opener=build_opener(NoRedirect())
        self.realm=realm or os.environ.get('KC_REALM','cysa')
        self.client=client or os.environ.get('KC_USERS_CLIENT_ID','cysa-user-admin')
        self.secret=secret or os.environ.get('KC_USERS_CLIENT_SECRET','')
        self._access_token=None;self._expires=0;self.lock=RLock()

    def transport(self,method,url,data=None,token=None,form=False):
        body=(urlencode(data).encode() if form else json.dumps(data).encode()) if data is not None else None
        headers={'Accept':'application/json'}
        if body is not None:headers['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
        if token:headers['Authorization']='Bearer '+token
        try:
            with self._opener.open(Request(url,data=body,headers=headers,method=method),timeout=5) as response:
                raw=response.read(2*1024*1024+1)
                if len(raw)>2*1024*1024:raise ValueError('Respuesta de identidad demasiado grande')
                return (json.loads(raw) if raw else None),response.headers
        except HTTPError as error:
            code=error.code;error.close()
            if code==409:raise HTTPException(409,'El usuario o correo ya existe') from None
            if code==404:raise HTTPException(404,'Cuenta o recurso de identidad no encontrado') from None
            if code==400:raise HTTPException(422,'Keycloak rechazo los datos o la politica de contrasena') from None
            self._access_token=None;self._expires=0
            raise HTTPException(503,'Gestion de identidad no disponible o sin permisos') from None
        except (URLError,TimeoutError,OSError,ValueError):
            raise HTTPException(503,'Servicio de identidad no disponible') from None

    def token(self):
        if not self.secret:raise HTTPException(503,'Gestion de usuarios pendiente de configuracion local')
        if self._access_token is None or time.monotonic()>=self._expires:
            result,_=self.transport('POST',f'{self.base}/realms/{quote(self.realm,safe="")}/protocol/openid-connect/token',
                dict(grant_type='client_credentials',client_id=self.client,client_secret=self.secret),form=True)
            if not isinstance(result,dict) or not isinstance(result.get('access_token'),str) or not isinstance(result.get('expires_in'),(int,float)) or result['expires_in']<=0:
                raise HTTPException(503,'Respuesta de identidad invalida')
            self._access_token=result['access_token'];self._expires=time.monotonic()+max(1,result['expires_in']-20)
        return self._access_token

    def api(self,method,path,data=None):
        return self.transport(method,f'{self.base}/admin/realms/{quote(self.realm,safe="")}{path}',data,self.token())

    def roles(self,user_id):
        rows,_=self.api('GET',f'/users/{user_id}/role-mappings/realm/composite')
        return sorted({x['name'] for x in rows}&ROLES)

    def user(self,user_id):
        user_id=quote(str(user_id),safe='')
        row,_=self.api('GET',f'/users/{user_id}')
        if row.get('serviceAccountClientId') or row.get('username','').startswith('service-account-'):
            raise HTTPException(403,'Las cuentas tecnicas no se gestionan desde el panel')
        return self.public(row,self.roles(user_id))

    @staticmethod
    def public(row,roles):
        return dict(id=row['id'],username=row.get('username',''),first_name=row.get('firstName',''),
            last_name=row.get('lastName',''),email=row.get('email',''),enabled=bool(row.get('enabled')),
            roles=roles,temporary_password='UPDATE_PASSWORD' in row.get('requiredActions',[]))

    def verify(self,claims,allowed):
        with self.lock:
            try:user=self.user(claims['sub'])
            except HTTPException as error:
                if error.status_code==404:raise HTTPException(403,'Cuenta no disponible') from None
                raise
            if not user['enabled'] or not set(user['roles']).intersection(allowed):
                raise HTTPException(403,'La cuenta no tiene permiso vigente para esta accion')

    def actor(self,claims):self.verify(claims,{'administrador'})

    def list(self,claims,first=0,limit=25,search=''):
        with self.lock:
            self.actor(claims)
            rows,_=self.api('GET','/users?'+urlencode(dict(first=first,max=limit,search=search,briefRepresentation=False)))
            items=[]
            for row in rows:
                if row.get('serviceAccountClientId') or row.get('username','').startswith('service-account-'):continue
                roles=self.roles(row['id'])
                if roles:items.append(self.public(row,roles))
            return dict(items=items,offset=first,limit=limit,has_more=len(rows)==limit)

    def create(self,claims,new):
        with self.lock:
            self.actor(claims)
            role,_=self.api('GET','/roles/'+new.role)
            row=dict(username=new.username,firstName=new.first_name,lastName=new.last_name,email=new.email,
                enabled=False,emailVerified=False,requiredActions=['UPDATE_PASSWORD'],
                credentials=[dict(type='password',value=new.password.get_secret_value(),temporary=True)])
            _,headers=self.api('POST','/users',row)
            location=headers.get('Location','');user_id=location.rsplit('/',1)[-1]
            try:UUID(user_id)
            except (ValueError,TypeError):raise HTTPException(503,'Keycloak no devolvio el identificador de la cuenta') from None
            try:
                self.api('POST',f'/users/{user_id}/role-mappings/realm',[role])
                self.api('PUT',f'/users/{user_id}',dict(enabled=True))
            except HTTPException:
                # La cuenta nace desactivada y solo se habilita tras asignar el rol.
                try:
                    self.api('PUT',f'/users/{user_id}',dict(enabled=False))
                    self.api('DELETE',f'/users/{user_id}')
                except HTTPException:log.error('usuarios alta incompleta: cuenta=%s; verificar estado en Keycloak',user_id)
                raise
            log.info('usuarios crear actor=%s cuenta=%s rol=%s',claims['sub'],user_id,new.role)
            return self.user(user_id)

    def change(self,claims,user_id,change):
        with self.lock:
            self.actor(claims)
            if str(user_id)==claims['sub']:raise HTTPException(409,'No puedes cambiar tu propio rol o desactivar tu cuenta')
            old=self.user(user_id)
            if not old['roles']:raise HTTPException(403,'La cuenta no pertenece a los roles de CYSA')
            # Serializado en la API local: validar actor antes de cada operacion impide
            # que dos administradores se desactiven mutuamente en peticiones concurrentes.
            direct,_=self.api('GET',f'/users/{user_id}/role-mappings/realm')
            direct_names={x['name'] for x in direct}&ROLES
            if set(old['roles'])-direct_names:
                raise HTTPException(409,'La cuenta tiene roles heredados; revisar sus grupos en Keycloak')
            role,_=self.api('GET','/roles/'+change.role)
            self.api('PUT',f'/users/{user_id}',dict(enabled=False))
            try:
                self.api('POST',f'/users/{user_id}/logout')
                self.api('POST',f'/users/{user_id}/role-mappings/realm',[role])
                direct,_=self.api('GET',f'/users/{user_id}/role-mappings/realm')
                remove=[x for x in direct if x['name'] in ROLES and x['name']!=change.role]
                if remove:self.api('DELETE',f'/users/{user_id}/role-mappings/realm',remove)
                self.api('PUT',f'/users/{user_id}',dict(enabled=change.enabled))
            except HTTPException:
                try:self.api('PUT',f'/users/{user_id}',dict(enabled=False))
                except HTTPException:pass
                log.error('usuarios cambio incompleto actor=%s cuenta=%s; verificar estado en Keycloak',claims['sub'],user_id)
                raise
            log.info('usuarios cambiar actor=%s cuenta=%s rol=%s activo=%s',claims['sub'],user_id,change.role,change.enabled)
            return self.user(user_id)


def build_users_router(directory):
    router=APIRouter(prefix='/api/usuarios',tags=['Usuarios'])
    @router.get('')
    def users(response:Response,offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=50),
              search:str=Query('',max_length=80),claims=Depends(admin_access)):
        response.headers['Cache-Control']='no-store'
        return directory.list(claims,offset,limit,search)
    @router.post('',status_code=201)
    def create_user(new:NewUser,response:Response,claims=Depends(admin_access)):
        response.headers['Cache-Control']='no-store'
        return directory.create(claims,new)
    @router.patch('/{user_id}')
    def change_user(user_id:UUID,change:UserChange,response:Response,claims=Depends(admin_access)):
        response.headers['Cache-Control']='no-store'
        return directory.change(claims,str(user_id),change)
    return router
