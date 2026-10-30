from types import SimpleNamespace
import pytest,numpy as np
from cysa_detector.counter import Lane,LineCounter
from cysa_detector.roi import crop_for_lanes,restore_box

def lane():return Lane('N','N_0',(.2,.5),(.8,.5),'both',((.2,.2),(.8,.2),(.8,.8),(.2,.8)))

def test_desactivado_conserva_imagen_original():
    frame=np.zeros((100,100,3),np.uint8)
    image,offset=crop_for_lanes(frame,[],{})
    assert image is frame and offset==(0,0)

def test_recorta_y_conserva_offset_sin_reescalar():
    frame=np.zeros((100,100,3),np.uint8)
    image,offset=crop_for_lanes(frame,[lane()],{'crop_to_lanes':True,'roi_padding':0})
    assert image.shape==(60,60,3) and offset==(20,20)
    assert np.shares_memory(frame,image)
    assert restore_box((20,20,40,40),offset)==(40,40,60,60)

def test_margen_y_limites_del_cuadro():
    frame=np.zeros((100,100,3),np.uint8)
    image,offset=crop_for_lanes(frame,[lane()],{'crop_to_lanes':True,'roi_padding':.5})
    assert image.shape==(100,100,3) and offset==(0,0)

@pytest.mark.parametrize('config',[{'crop_to_lanes':'true'},{'crop_to_lanes':True,'auto_carriles':True},{'crop_to_lanes':True,'roi_padding':-.1},{'crop_to_lanes':True,'roi_padding':float('nan')}])
def test_configuracion_no_valida(config):
    with pytest.raises(ValueError):crop_for_lanes(np.zeros((100,100,3),np.uint8),[lane()],config)

def test_lineas_sin_zona_no_inventan_recorte():
    with pytest.raises(ValueError):crop_for_lanes(np.zeros((100,100,3),np.uint8),[Lane('N','N_0',(.1,.5),(.8,.5))],{'crop_to_lanes':True})

def test_recuento_igual_al_restaurar_coordenadas():
    from datetime import datetime
    from cysa_detector.run import CameraSource
    class T(list):
        def cpu(self):return self
        def int(self):return self
        def tolist(self):return list(self)
    class Cap:
        def __init__(self):self.n=0
        def get(self,p):return 30
        def read(self):
            self.n+=1
            return (True,np.zeros((100,100,3),np.uint8)) if self.n<=2 else (False,None)
    class Model:
        def __init__(self,crop):self.n=0;self.crop=crop
        def track(self,frame,**kwargs):
            self.n+=1
            assert frame.shape[:2]==((60,60) if self.crop else (100,100))
            bottom=40 if self.n==1 else 60;delta=20 if self.crop else 0
            boxes=SimpleNamespace(xyxy=T([[40-delta,25-delta,60-delta,bottom-delta]]),id=T([1]),cls=T([3]),conf=T([.9]))
            return [SimpleNamespace(boxes=boxes)]
    counts=[]
    for crop in [False,True]:
        config=dict(interseccion='DEMO_INT_01',prueba=True,crop_to_lanes=crop,roi_padding=0)
        source=CameraSource(config,datetime.fromisoformat('2026-10-30T12:00:00-04:00'))
        events=list(source._loop(Cap(),Model(crop),LineCounter([lane()]),{3:'moto'},30,SimpleNamespace(CAP_PROP_FPS=5)))
        counts.append({e.clase:e.cantidad for e in events})
    assert counts[0]==counts[1] and counts[1]['moto']==1
