import os,time
from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.auth import read_access,require_roles
from .almacen import Almacen,EstadoInvalido
class Decision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    solicitud_id:UUID
    accion:Literal['autorizar','rechazar']
    motivo:str=Field(min_length=5,max_length=1000)

def mfa_operador(claims=Depends(require_roles('operador'))):
    now=time.time();auth=claims.get('auth_time');amr=claims.get('amr',[])
    if not isinstance(auth,(int,float)) or isinstance(auth,bool) or not -5<=now-auth<=300:
        raise HTTPException(403,'Vuelve a autenticarte con MFA; evidencia de cinco minutos requerida')
    if not (isinstance(amr,list) and all(isinstance(x,str) for x in amr) and set(amr)&{'otp','mfa','hwk'} or claims.get('acr')=='2'):
        raise HTTPException(403,'Se requiere MFA de Keycloak; una sesión solo con contraseña no autoriza')
    return claims

def router(store=None):
    store=store or Almacen()
    r=APIRouter(prefix='/api/operacion',tags=['Operación semafórica S2'])
    def habilitado():
        if os.environ.get('CYSA_CONTROL_ENABLED')!='true':raise HTTPException(503,'Habilita el banco S2 siguiendo controlador/INTEGRACION.md')
    @r.get('/planes',dependencies=[Depends(habilitado),Depends(read_access)])
    def listado():return {'items':store.listar()}
    @r.get('/planes/{id}',dependencies=[Depends(habilitado),Depends(read_access)])
    def obtener(id:UUID):
        p=store.obtener(id)
        if not p:raise HTTPException(404,'Plan inexistente')
        return p
    @r.get('/planes/{id}/auditoria',dependencies=[Depends(habilitado),Depends(read_access)])
    def auditoria(id:UUID):return store.auditoria(id)
    @r.post('/planes/{id}/decisiones',dependencies=[Depends(habilitado)])
    def decidir(id:UUID,d:Decision,claims=Depends(mfa_operador)):
        if d.solicitud_id.int==0 or len(d.motivo.strip())<5:raise HTTPException(400,'Solicitud o motivo inválido')
        try:
            store.decidir(id,d.solicitud_id,d.accion,d.motivo.strip(),claims['sub'],
                dict(auth_time=claims['auth_time'],amr=claims.get('amr',[]),acr=claims.get('acr')))
            return store.obtener(id)
        except KeyError:raise HTTPException(404,'Plan inexistente') from None
        except EstadoInvalido as e:raise HTTPException(409,str(e)) from None
    return r
