import numpy as np
from cysa_detector.auto_lanes import AutoLanes
from cysa_detector.counter import LineCounter

def populate(horizontal=False):
    auto=AutoLanes()
    tid=0
    for center,direction in [(.25,1),(.65,-1)]:
        for offset in [-.008,0,.008]:
            tid+=1
            depths=np.linspace(.25,.85,32)
            if direction<0:depths=depths[::-1]
            for i,depth in enumerate(depths):
                point=(center+offset,float(depth))
                if horizontal:point=point[::-1]
                auto.observe(tid,point,.06,.06,i*.1)
    return auto

def test_separa_dos_carriles_y_sentidos():
    auto=populate();lanes=auto.infer()
    assert len(lanes)==2
    assert {l.direction for l in lanes}=={'negative_to_positive','positive_to_negative'}
    auto.lanes=lanes
    assert auto.assign(99,(.25,.55)).carril!=auto.assign(100,(.65,.55)).carril
    assert auto.assign(101,(.45,.55)) is None
    assert auto.assign(102,(.95,.55)) is None

def test_horizontal():
    auto=populate(True);auto.lanes=auto.infer()
    assert len(auto.lanes)==2
    assert auto.assign(1,(.55,.25)) is not None

def test_sin_evidencia_no_inventa():
    auto=AutoLanes()
    for i in range(30):auto.observe(1,(.2,.2+i*.01),.06,.06,i)
    assert not auto.infer()
    for i in range(30):auto.observe(2,(.7,.7),.06,.06,i)
    assert not auto.infer()

def test_doble_cruce_cambio_carril_no_duplica():
    lanes=populate().infer();c=LineCounter(lanes)
    left,right=lanes
    y=left.a[1]
    c.observe(1,'auto',(.25,y-.1),0,('N',left.carril))
    c.observe(1,'auto',(.25,y+.1),1,('N',left.carril))
    y=right.a[1]
    c.observe(1,'auto',(.65,y+.1),2,('N',right.carril))
    c.observe(1,'auto',(.65,y-.1),3,('N',right.carril))
    assert sum(c.snapshot().values())==1

def test_no_asignado_no_cuenta():
    lanes=populate().infer();c=LineCounter(lanes);y=lanes[0].a[1]
    c.observe(1,'auto',(.25,y-.1),0,('',''))
    c.observe(1,'auto',(.25,y+.1),1,('',''))
    assert not c.snapshot()

def test_historial_caduca():
    auto=populate();auto.observe(999,(.1,.1),.06,.06,1000)
    assert len(auto.tracks)==1
