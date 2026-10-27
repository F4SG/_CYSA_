import importlib.util
from pathlib import Path
import pytest
from cysa_detector.counter import Lane,LineCounter

POLY=((.1,.1),(.45,.1),(.45,.9),(.1,.9))
def lane(name='N_0',polygon=POLY,a=(.1,.5),b=(.45,.5),direction='both'):
    return Lane('N',name,a,b,direction,polygon)

def test_cuenta_solo_cruce_y_una_vez():
    c=LineCounter([lane()])
    c.observe(1,'auto',(.3,.2),0)
    assert not c.snapshot()
    c.observe(1,'auto',(.3,.8),1)
    assert c.snapshot()=={('N','N_0','auto'):1}
    c.observe(1,'auto',(.3,.2),2)
    assert c.snapshot()=={('N','N_0','auto'):1}

def test_fuera_del_segmento_no_cuenta():
    c=LineCounter([lane()])
    c.observe(1,'auto',(.8,.2),0);c.observe(1,'auto',(.8,.8),1)
    assert not c.snapshot()

def test_carriles_separados():
    second=lane('N_1',((.55,.1),(.9,.1),(.9,.9),(.55,.9)),(.55,.5),(.9,.5))
    c=LineCounter([lane(),second])
    for i,x in enumerate([.3,.7,.5]):
        c.observe(i,'auto',(x,.2),0);c.observe(i,'auto',(x,.8),1)
    assert c.snapshot()=={('N','N_0','auto'):1,('N','N_1','auto'):1}

def test_direccion():
    c=LineCounter([lane(direction='negative_to_positive')])
    c.observe(1,'auto',(.3,.8),0);c.observe(1,'auto',(.3,.2),1)
    assert not c.snapshot()

def test_borde_e_interior():
    l=lane()
    assert l.contains((.1,.5)) and l.contains((.3,.5))
    assert not l.contains((.8,.5))

def test_linea_fuera_rechazada():
    with pytest.raises(ValueError):lane(b=(.8,.5))

def test_editor_valida():
    spec=importlib.util.spec_from_file_location('editor',Path(__file__).resolve().parents[2]/'tools/cristhian/delimitar_carriles.py')
    editor=importlib.util.module_from_spec(spec);spec.loader.exec_module(editor)
    result=editor.make_lane(list(POLY)+[(.1,.5),(.45,.5)],0,'N','both')
    assert result['carril']=='N_0'
    with pytest.raises(ValueError):editor.make_lane(list(POLY),0,'N','both')
    with pytest.raises(ValueError):editor.make_lane([POLY[0],POLY[2],POLY[1],POLY[3],(.1,.5),(.45,.5)],0,'N','both')
