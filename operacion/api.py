import os,time,threading
from datetime import datetime
from typing import Literal
from uuid import UUID,uuid4
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.auth import admin_access,read_access,require_roles
from .almacen import Almacen,EstadoInvalido
from .planes import huella,proponer

class SolicitudPlan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    desde:datetime
    hasta:datetime
    modo:Literal['webster','micros','emergencia']='webster'
    grupo:Literal['NS','EO']|None=None
    evento_utc:datetime|None=None
    @model_validator(mode='after')
    def periodo(self):
        if self.desde.tzinfo is None or self.hasta.tzinfo is None or not 0<(self.hasta-self.desde).total_seconds()<=3600:
            raise ValueError('Usar un intervalo con zona horaria de hasta una hora')
        if self.modo=='emergencia':
            if self.evento_utc is None or self.evento_utc.tzinfo is None or not -10<=self.evento_utc.timestamp()-time.time()<=240:
                raise ValueError('Define el evento de emergencia del banco con zona horaria, dentro de los próximos cuatro minutos')
        return self
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

def router(repo,store=None,simulator=None):
    store=store or Almacen();lock=threading.Lock()
    r=APIRouter(prefix='/api/operacion',tags=['Operación semafórica S2'])
    def habilitado():
        if os.environ.get('CYSA_CONTROL_ENABLED')!='true':raise HTTPException(503,'Habilita el banco S2 siguiendo controlador/INTEGRACION.md')
    @r.get('/planes',dependencies=[Depends(habilitado),Depends(read_access)])
    def listado():return {'items':store.listar()}
    @r.post('/planes',status_code=201,dependencies=[Depends(habilitado)])
    def generar(solicitud:SolicitudPlan,claims=Depends(admin_access)):
        if not lock.acquire(blocking=False):raise HTTPException(409,'Hay una simulación en curso')
        try:
            filas=repo.counts(solicitud.desde,solicitud.hasta,'DEMO_INT_01',None,True,1000,0)
            if len(filas)>=1000 or sum(x['cantidad'] for x in filas)>3000:raise ValueError('Demanda demasiado grande para el banco; acorta el intervalo')
            p=proponer(filas,solicitud.modo,solicitud.grupo);id=uuid4();p['plan_id']='OP_'+id.hex
            if solicitud.modo=='emergencia':p['evento_utc']=solicitud.evento_utc.timestamp()
            if simulator:v=simulator(filas,p)
            else:
                from .simular import buscar
                p,v=buscar(filas,p)
            return store.guardar(id,p,v,dict(desde=solicitud.desde.isoformat(),hasta=solicitud.hasta.isoformat(),
                mensajes=[str(x['mensaje_id']) for x in filas]),claims['sub'])
        except (ValueError,TimeoutError) as e:raise HTTPException(400,str(e)) from None
        finally:lock.release()
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
