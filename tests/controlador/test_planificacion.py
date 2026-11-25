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
    assert sum(f.duracion_s for f in plan.fases if f.peatonal)>=minimo_peatonal('NS')
    original=huella(p);p['verdes']['NS']+=1;assert huella(p)!=original

@pytest.mark.parametrize('bad',[float('nan'),float('inf'),0,-1,True,1000])
def test_tiempos_inseguros_no_se_convierten_en_plan(bad):
    p=proponer(demanda());p['verdes']['NS']=bad
    with pytest.raises(ValueError):validar(p)

def test_no_acepta_conteos_fuera_del_banco():
    filas = demanda()
    filas[0]['prueba'] = False
    with pytest.raises(ValueError):proponer(filas)


def test_micros_integran_la_demanda_sin_modo_de_prioridad():
    filas = demanda(20,20,True)
    plan = proponer(filas)
    assert plan['modo'] == 'webster' and plan['grupo_prioridad'] is None
    assert 'extension_micro_s' not in plan
    with pytest.raises(ValueError, match='Modo inválido'):
        proponer(filas, 'micros', 'NS')
    with pytest.raises(ValueError, match='fuera del alcance'):
        validar({**plan, 'modo': 'micros'})


@pytest.mark.parametrize('demora_acceso, aprobada', [(115, True), (115.0005, False)])
def test_webster_no_exige_mejora_global_y_limita_empeoramiento_por_acceso(monkeypatch, demora_acceso, aprobada):
    from operacion import simular

    resultados = iter([({'total': 100, 'N': 100}, 240, None),
                       ({'total': 95, 'N': demora_acceso}, 240, None)])
    monkeypatch.setattr(simular, '_ejecutar', lambda *args: next(resultados))
    filas = demanda()
    evaluacion = simular.evaluar(filas, proponer(filas))
    assert evaluacion['mejora_porcentaje'] == 5
    assert evaluacion['aprobada'] is aprobada


@pytest.mark.skipif(importlib.util.find_spec('sumolib') is None,reason='SUMO no instalado')
def test_sumo_real_completa_demanda_y_mide_reduccion_sin_perjudicar_accesos():
    from operacion.simular import evaluar
    r=demanda();p=proponer(r);v=evaluar(r,p)
    assert v['sumo_real'] and v['aprobada'] and v['mejora_porcentaje']>=10
    assert v['vehiculos']==240 and v['huella_plan']==huella(p)
    assert all(v['candidato'][a]<=v['referencia'][a]*1.15+.001 for a in ('N','S','E','W'))

def test_configuracion_aprobada_viaja_en_el_documento_ejecutable():
    from operacion.planes import TIEMPOS
    config = dict(id=7, version=2, tiempos={**TIEMPOS,'verde_min_s':18,'ambar_s':4})
    p = proponer(demanda(), configuracion=config)
    _, plan = validar(p)
    assert p['configuracion_id'] == 7 and p['configuracion_version'] == 2
    assert plan.verde_min_s == 18
    assert all(f.duracion_s == 4 for f in plan.fases if 'Y' in f.luces)

@pytest.mark.skipif(importlib.util.find_spec('sumolib') is None,reason='SUMO no instalado')
def test_sumo_emergencia_incluye_retorno_y_despeje():
    from operacion.simular import evaluar
    r = demanda()
    v = evaluar(r, proponer(r,'emergencia','EO'))
    assert v['cruce_peatonal_sumo']
    sin = v['prioridad_emergencia']['sin_despeje']
    con = v['prioridad_emergencia']['con_despeje']
    assert sin['demora_s'] <= 10 and sin['retorno_s'] > sin['verde_s']
    assert con['verde_s'] >= 81.667 and con['retorno_s'] > con['verde_s']
