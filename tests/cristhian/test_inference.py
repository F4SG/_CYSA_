import pytest
from cysa_detector.inference import detection_settings

MAPPING={2:'auto',3:'moto',5:'micro'}

def test_predeterminados():
    options,thresholds=detection_settings({},MAPPING)
    assert options['imgsz']==640 and options['conf']==.3
    assert set(thresholds.values())=={.3}
    assert not options['save'] and not options['show']

def test_motos_no_baja_umbral_de_autos():
    options,thresholds=detection_settings(dict(confidence=.25,track_confidence=.1,class_confidence={3:.15},imgsz=960,end2end=False,agnostic_nms=True,iou=.5),MAPPING)
    assert thresholds=={2:.25,3:.15,5:.25}
    assert options['conf']==.1 and options['imgsz']==960
    assert options['end2end'] is False and options['agnostic_nms'] is True

@pytest.mark.parametrize('config',[{'confidence':0},{'confidence':True},{'confidence':float('nan')},{'track_confidence':.5},{'imgsz':961},{'imgsz':True},{'class_confidence':{7:.15}},{'class_confidence':[]},{'end2end':'false'}])
def test_rechaza_configuracion_invalida(config):
    with pytest.raises(ValueError):detection_settings(config,MAPPING)


def test_filtro_moto_debil_seguida_y_auto_debil():
    from datetime import datetime
    from types import SimpleNamespace
    import numpy as np
    from cysa_detector.run import CameraSource
    from cysa_detector.counter import Lane,LineCounter
    class T(list):
        def cpu(self):return self
        def int(self):return self
        def tolist(self):return list(self)
    class Cap:
        n=0
        def get(self,p):return 30
        def read(self):
            self.n+=1
            return (True,np.zeros((100,100,3),np.uint8)) if self.n<=2 else (False,None)
    class Model:
        n=0
        def track(self,frame,**kwargs):
            assert kwargs['imgsz']==960 and kwargs['conf']==.1
            self.n+=1;y=30 if self.n==1 else 70
            boxes=SimpleNamespace(xyxy=T([[15,10,25,y],[35,10,45,y]]),id=T([1,2]),cls=T([3,2]),conf=T([.2,.2]))
            return [SimpleNamespace(boxes=boxes)]
    source=CameraSource(dict(interseccion='DEMO_INT_01',prueba=True,confidence=.25,class_confidence={3:.15},track_confidence=.1,imgsz=960),datetime.fromisoformat('2026-10-30T12:00:00-04:00'))
    counter=LineCounter([Lane('N','N_0',(.1,.5),(.5,.5))])
    events=list(source._loop(Cap(),Model(),counter,MAPPING,30,SimpleNamespace(CAP_PROP_FPS=5)))
    counts={e.clase:e.cantidad for e in events}
    assert counts['moto']==1 and counts['auto']==0
