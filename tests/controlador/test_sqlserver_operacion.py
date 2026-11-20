"""Pruebas optativas con SQL Server real; nunca usan la base de Web III."""
import os,time
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from operacion.almacen import Almacen,EstadoInvalido
from operacion.planes import proponer,huella
from tests.controlador.test_planificacion import demanda

pytestmark=pytest.mark.skipif(os.environ.get('CYSA_SQL_TESTS')!='1',reason='Requiere SQL Server local de pruebas')
@pytest.fixture
def store():
    assert os.environ.get('CYSA_SQL_DATABASE')=='CYSA_Control_S2_Pruebas'
    a=Almacen();a.ready();a.pruebas_ids=[]
    yield a
    for id in a.pruebas_ids:
        row=a.obtener(id)
        if row and row.get('solicitud_id'):a.envio(row['solicitud_id'],'caducado','Fin de prueba transaccional sin actuadores')

def candidato(store,aprobada=True):
    p=proponer(demanda());id=uuid4();p['plan_id']='OP_'+id.hex
    store.guardar(id,p,dict(aprobada=aprobada,huella_plan=huella(p),sumo_real=True),{},'prueba')
    store.pruebas_ids.append(id)
    return id,p

def test_decision_concurrente_es_idempotente_y_solo_crea_un_envio(store):
    id,p=candidato(store);sid=uuid4();mfa=dict(auth_time=time.time(),amr=['otp'])
    def decidir(_):return store.decidir(id,sid,'autorizar','Prueba simultánea','operador-test',mfa)
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(decidir,range(4)))
    assert results.count(False)==1 and results.count(True)==3
    assert len([x for x in store.pendientes() if x['solicitud_id']==sid])==1
    with pytest.raises(EstadoInvalido):store.decidir(id,sid,'rechazar','Otro motivo','operador-test',mfa)

def test_plan_rechazado_o_sin_validacion_no_genera_despacho(store):
    id,p=candidato(store,False)
    with pytest.raises(EstadoInvalido):store.decidir(id,uuid4(),'autorizar','No permitido','operador-test',{})
    id,p=candidato(store);sid=uuid4();store.decidir(id,sid,'rechazar','No se aprueba','operador-test',{})
    assert store.obtener(id)['estado']=='rechazado'
    assert not any(x['solicitud_id']==sid for x in store.pendientes())

def test_confirmacion_de_version_exacta_se_conserva_al_reabrir(store):
    id,p=candidato(store);sid=uuid4();store.decidir(id,sid,'autorizar','Prueba de recibo','operador-test',{})
    with pytest.raises(ValueError):store.confirmar(dict(solicitud_id=str(sid),huella_plan='otra',estado='aplicado'))
    store.confirmar(dict(solicitud_id=str(sid),huella_plan=huella(p),estado='aplicado',detalle='Prueba'))
    assert Almacen().obtener(id)['estado_envio']=='aplicado'
    assert len(store.auditoria(id))==3
