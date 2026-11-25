import json,time
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from fastapi import HTTPException
from operacion.api import mfa_operador
from operacion.mensajes import firmar,verificar
from operacion.planes import proponer,huella
from cysa_controlador.recepcion import ReceptorPlanes
from cysa_controlador.run import cargar_config
from cysa_controlador.controlador import ControladorEmulado
from cysa_controlador.estados import LocalSeguro
from pathlib import Path

KEY=b'x'*32
def payload():
    t=datetime(2026,11,20,tzinfo=timezone.utc)
    rows=[dict(interseccion='DEMO_INT_01',acceso=a,carril=a+'_0',clase='auto',cantidad=60,inicio=t,fin=t+timedelta(seconds=600),prueba=True) for a in 'NSEW']
    p=proponer(rows)
    return dict(tipo='plan',solicitud_id=str(uuid4()),plan=p,huella_plan=huella(p),usuario='operador',mfa_verificado=True,emitido=1000,vence=1300)

@pytest.mark.parametrize('changes',[{'mfa_verificado':False},{'vence':999},{'huella_plan':'incorrecta'}])
def test_rechaza_ordenes_sin_prueba_mfa_caducadas_o_alteradas(changes):
    p=payload();p.update(changes)
    with pytest.raises(ValueError):verificar(firmar(p,KEY),KEY,1000)

def test_mqtt_no_puede_alterar_fases_sin_romper_firma():
    p=payload();raw=json.loads(firmar(p,KEY));raw['payload']=raw['payload'].replace('15.0','90.0')
    with pytest.raises(ValueError):verificar(json.dumps(raw),KEY,1000)


@pytest.mark.parametrize('raw',['[]','null','{"payload":123,"firma":"x"}'])
def test_sobres_malformados_se_descartan_sin_detener_el_receptor(raw):
    with pytest.raises(ValueError):verificar(raw,KEY,1000)

@pytest.mark.parametrize('desfase, evidencia', [
    (0, {'amr': ['pwd']}),
    (-301, {'amr': ['otp']}),
    (30, {'acr': '2'}),
])
def test_mfa_no_acepta_solo_clave_ni_evidencia_vencida_o_futura(desfase, evidencia):
    claims = dict(auth_time=time.time() + desfase, **evidencia)
    with pytest.raises(HTTPException) as ex:mfa_operador(claims)
    assert ex.value.status_code==403

def test_mfa_admite_amr_otp_o_acr_dos_firmados_por_proveedor():
    for extra in [dict(amr=['pwd','otp']),dict(acr='2')]:
        claims=dict(sub='operador',auth_time=time.time(),**extra);assert mfa_operador(claims)==claims

def contexto(tmp_path):
    _,cruce,central,local=cargar_config(Path(__file__).resolve().parents[2]/'controlador/config/demo_int_01.yaml')
    ctrl=ControladorEmulado(cruce,central,local,True,0);ctrl.latido(0)
    # Entrar a un todo rojo y mantener un centro confirmado.
    ctrl.tick(28);clock=[28.0];ctrl.ultimo_latido=28
    out=[];r=ReceptorPlanes(ctrl,KEY,tmp_path/'recibos.json',out.append,reloj=lambda:clock[0],utc=lambda:1000+clock[0])
    return ctrl,r,clock,out

def test_aplica_al_final_del_todo_rojo_y_no_reaplica_duplicados(tmp_path):
    c,r,clock,out=contexto(tmp_path);p=payload();raw=firmar(p,KEY)
    old=c.plan_id;r.recibir(raw);assert c.plan_id==old
    clock[0]=31;c.tick(31);r.tick();assert c.plan_id==p['plan']['plan_id']
    clock[0]=31.5;r.tick();assert verificar(out[-1],KEY,1031.5)['estado']=='aplicado'
    r.recibir(raw);assert c.secuenciador.pendiente is None
    restarted=ReceptorPlanes(c,KEY,tmp_path/'recibos.json',out.append,reloj=lambda:clock[0],utc=lambda:1032)
    restarted.recibir(raw);assert c.secuenciador.pendiente is None

def test_caida_de_centro_no_cancela_el_cambio_a_local_seguro(tmp_path):
    c,r,clock,out=contexto(tmp_path);p=payload();r.recibir(firmar(p,KEY))
    clock[0]=89;c.tick(89);r.tick()
    assert not c.modo.conectado
    assert c.plan_id==c.plan_local.plan_id or c.secuenciador.pendiente is c.plan_local
    assert verificar(out[-1],KEY,1089)['estado']=='rechazado'


def test_orden_al_arrancar_espera_latido_y_no_aplica_desconectado(tmp_path):
    c,r,clock,out=contexto(tmp_path);c.modo=LocalSeguro();p=payload()
    anterior=c.secuenciador.pendiente
    r.recibir(firmar(p,KEY));assert r.esperando_centro is not None
    assert c.secuenciador.pendiente is anterior and not out
    c.latido(clock[0]);r.tick()
    assert r.esperando_centro is None and r.pendiente is not None
    assert c.plan_id!=p['plan']['plan_id']


def test_orden_sin_latido_caduca_sin_programar_fases(tmp_path):
    c,r,clock,out=contexto(tmp_path);c.modo=LocalSeguro();p=payload()
    anterior=c.secuenciador.pendiente
    r.recibir(firmar(p,KEY));clock[0]=301;r.tick()
    assert r.esperando_centro is None and c.secuenciador.pendiente is anterior
    assert verificar(out[-1],KEY,1301)['estado']=='rechazado'


@pytest.mark.parametrize('modo', ['micros', 'emergencia'])
def test_controlador_rechaza_prioridades_fuera_del_banco(tmp_path, modo):
    controlador, receptor, _, recibos = contexto(tmp_path)
    anterior = controlador.secuenciador.pendiente
    orden = payload()
    orden['plan']['modo'] = modo
    orden['huella_plan'] = huella(orden['plan'])
    with pytest.raises(ValueError, match='Solo se despachan planes Webster'):
        receptor.recibir(firmar(orden, KEY))
    assert controlador.secuenciador.pendiente is anterior
    assert not recibos
