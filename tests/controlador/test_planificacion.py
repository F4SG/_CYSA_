from datetime import datetime,timedelta,timezone
from copy import deepcopy
import importlib.util
import pytest
from operacion.planes import proponer,validar,minimo_peatonal,huella

def demanda(n=60,e=60,micros=False):
    t=datetime(2026,11,20,tzinfo=timezone.utc)
    return [dict(interseccion='DEMO_INT_01',acceso=a,carril=a+'_0',clase='micro' if micros and a in ('N','S') else 'auto',
                 cantidad=q,inicio=t,fin=t+timedelta(seconds=600),prueba=True)
            for a,q in [('N',n),('S',n),('E',e),('W',e)]]

def test_webster_genera_plan_ejecutable_y_no_acorta_peatones():
    p=proponer(demanda());cruce,plan=validar(p)
    assert len(plan.fases)==6 and all(t>=minimo_peatonal(g) for g,t in p['verdes'].items())
    original=huella(p);p['verdes']['NS']+=1;assert huella(p)!=original

@pytest.mark.parametrize('bad',[float('nan'),float('inf'),0,-1,True,1000])
def test_tiempos_inseguros_no_se_convierten_en_plan(bad):
    p=proponer(demanda());p['verdes']['NS']=bad
    with pytest.raises(ValueError):validar(p)

def test_no_acepta_conteos_fuera_del_banco_ni_inventa_micros():
    r=demanda();r[0]['prueba']=False
    with pytest.raises(ValueError):proponer(r)
    with pytest.raises(ValueError):proponer(demanda(),'micros','NS')
    p=proponer(demanda(20,20,True),'micros','NS')
    assert p['extension_micro_s']<=10

@pytest.mark.skipif(importlib.util.find_spec('sumolib') is None,reason='SUMO no instalado')
def test_sumo_real_completa_demanda_y_mide_reduccion_sin_perjudicar_accesos():
    from operacion.simular import evaluar
    r=demanda();p=proponer(r);v=evaluar(r,p)
    assert v['sumo_real'] and v['aprobada'] and v['mejora_porcentaje']>=10
    assert v['vehiculos']==240 and v['huella_plan']==huella(p)
    assert all(v['candidato'][a]<=v['referencia'][a]*1.15+.001 for a in ('N','S','E','W'))

@pytest.mark.skipif(importlib.util.find_spec('sumolib') is None,reason='SUMO no instalado')
def test_prioridad_micros_elige_extension_condicional_sin_perjudicar_resto():
    from operacion.simular import buscar
    r=demanda(40,40,True);p,v=buscar(r,proponer(r,'micros','NS'))
    assert v['aprobada'] and 0<p['extension_micro_s']<=10
    assert v['candidato']['micro']<=v['referencia']['micro']*.9
    assert v['candidato']['resto']<=v['referencia']['resto']*1.1+.001
