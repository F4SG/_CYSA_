import importlib.util,sys
from pathlib import Path
import pytest
import cv2,numpy as np
from cysa_detector.counter import Lane,LineCounter

def module():
    path=Path(__file__).resolve().parents[2]/'tools/cristhian/calibrar_via.py'
    spec=importlib.util.spec_from_file_location('calibrar_via',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

POINTS=[(.1,.55),(.55,.55),(.95,.98),(.05,.98)]

def as_lanes(rows):return [Lane(x['acceso'],x['carril'],tuple(x['a']),tuple(x['b']),x['direction'],tuple(tuple(p) for p in x['polygon'])) for x in rows]

def test_puente_queda_fuera_de_todas_las_zonas():
    lanes=as_lanes(module().create_lanes(POINTS,3))
    assert len(lanes)==3
    assert all(not lane.contains((.5,.3)) for lane in lanes)
    assert all(lane.contains(tuple((np.array(lane.a)+np.array(lane.b))/2)) for lane in lanes)

def test_cada_carril_cuenta_un_cruce_y_no_puente():
    lanes=as_lanes(module().create_lanes(POINTS,3));counter=LineCounter(lanes)
    matrix=cv2.getPerspectiveTransform(np.array([[0,0],[1,0],[1,1],[0,1]],np.float32),np.array(POINTS,np.float32))
    def project(x,y):
        point=matrix@np.array([x,y,1.]);return tuple(point[:2]/point[2])
    for i,lane in enumerate(lanes):
        key=(lane.acceso,lane.carril)
        counter.observe(i,'auto',project((i+.5)/3,.4),0,key)
        counter.observe(i,'auto',project((i+.5)/3,.8),1,key)
    counter.observe(99,'moto',(.3,.2),0,('',''));counter.observe(99,'moto',(.7,.4),1,('',''))
    assert counter.snapshot()=={('N',f'N_{i}','auto'):1 for i in range(3)}

@pytest.mark.parametrize('count',[0,9,True])
def test_cantidad_invalida(count):
    with pytest.raises(ValueError):module().create_lanes(POINTS,count)

def test_esquinas_cruzadas_no_se_guardan():
    with pytest.raises(ValueError):module().create_lanes([POINTS[0],POINTS[2],POINTS[1],POINTS[3]],3)

def test_se_puede_mover_linea_dentro_de_la_via():
    rows=module().create_lanes(POINTS,3,line_at=.8)
    lanes=as_lanes(rows)
    assert all(l.contains(l.a) and l.contains(l.b) for l in lanes)
