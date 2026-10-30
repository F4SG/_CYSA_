from datetime import datetime
from types import SimpleNamespace
import cv2
import numpy as np
from cysa_detector.run import CameraSource
from cysa_detector.counter import Lane,LineCounter

class Cap:
    def __init__(self):self.n=0
    def get(self,p):return 30
    def read(self):
        self.n+=1
        return (True,np.zeros((80,120,3),np.uint8)) if self.n<=3 else (False,None)

class CV:
    def __init__(self,key=-1):self.created=0;self.shown=0;self.key=key
    def __getattr__(self,name):return getattr(cv2,name)
    def namedWindow(self,*args):self.created+=1
    def resizeWindow(self,*args):self.initial_size=args[1:]
    def setMouseCallback(self,window,callback):self.callback=callback
    def imshow(self,window,image):
        self.shown+=1
        if self.key=='click':
            rect=dict(self.callback.__self__.buttons)['stop']
            self.callback(1,rect[0]+1,rect[1]+1,0,None)
    def waitKey(self,*args):return -1 if self.key=='click' else self.key
    def getWindowProperty(self,*args):return 1

class Model:
    def track(self,frame,**kwargs):
        assert kwargs['show'] is False
        assert not any(kwargs[k] for k in ['save','save_txt','save_crop','save_frames'])
        return [SimpleNamespace(boxes=None)]

def run(key):
    config={'interseccion':'DEMO_INT_01','prueba':True,'show':True}
    source=CameraSource(config,datetime.fromisoformat('2026-10-27T12:00:00-04:00'))
    cv=CV(key);counter=LineCounter([Lane('N','N_0',(.1,.5),(.4,.5))])
    list(source._loop(Cap(),Model(),counter,{2:'auto'},30,cv));cv.source=source;return cv

def test_una_ventana_persistente_para_todos_los_cuadros():
    cv=run(-1)
    assert cv.created==1 and cv.shown==3
    assert cv.initial_size[0]<=1280 and cv.initial_size[1]<=900

def test_q_cierra_tras_el_primer_cuadro():
    cv=run(ord('q'))
    assert cv.created==1 and cv.shown==1


def test_boton_detener_finaliza_tras_primer_cuadro():
    cv=run('click')
    assert cv.created==1 and cv.shown==1


def test_editar_finaliza_bucle_y_solicita_editor():
    cv=run(ord('e'))
    assert cv.shown==1 and cv.source.edit_requested


def test_ventana_sigue_actualizando_mientras_ia_esta_bloqueada():
    from threading import Event
    from cysa_detector.live_inference import LiveInference
    entered=Event();release=Event()
    class SlowModel:
        def track(self,*args,**kw):
            entered.set();assert release.wait(2)
            return [SimpleNamespace(boxes=None)]
    class LiveCap(Cap):
        delivered_at=None
        def poll(self,timeout):
            if self.n==1:assert entered.wait(1)
            return self.read()
        @property
        def finished(self):return self.n>3
    worker=LiveInference(SlowModel(),{})
    source=CameraSource({'interseccion':'DEMO_INT_01','prueba':True,'show':True})
    cv=CV(ord('e'));cap=LiveCap()
    try:
        list(source._loop(cap,None,LineCounter([Lane('N','N_0',(.1,.5),(.4,.5))]),{2:'auto'},30,cv,worker))
        assert cv.shown==1 and source.edit_requested
        assert not release.is_set()
    finally:release.set();worker.close()


def test_video_actualiza_varios_cuadros_sin_esperar_deteccion():
    from threading import Event
    from cysa_detector.live_inference import LiveInference
    entered=Event();release=Event()
    class SlowModel:
        def track(self,*args,**kw):
            entered.set();assert release.wait(2)
            return [SimpleNamespace(boxes=None)]
    class LiveCap(Cap):
        delivered_at=None
        def poll(self,timeout):
            if self.n==1:assert entered.wait(1)
            return self.read()
        @property
        def finished(self):return self.n>3
    worker=LiveInference(SlowModel(),{})
    cv=CV();source=CameraSource({'interseccion':'DEMO_INT_01','prueba':True,'show':True})
    try:
        list(source._loop(LiveCap(),None,LineCounter([]),{2:'auto'},30,cv,worker))
        assert cv.shown==3 and not release.is_set()
    finally:release.set();worker.close()


def test_resultado_recien_terminado_pero_viejo_cuenta_sin_pintar_recuadro():
    import time
    class T(list):
        def cpu(self):return self
        def int(self):return self
        def tolist(self):return list(self)
    boxes=SimpleNamespace(xyxy=T([[40,20,60,60]]),id=T([1]),cls=T([2]),conf=T([.9]))
    class Worker:
        elapsed_ms=500
        def take(self):return [SimpleNamespace(boxes=boxes)],(0,0),(80,120),time.monotonic()-2,500
        def submit(self,*args):pass
    class LiveCap(Cap):
        delivered_at=None
        def poll(self,timeout):return self.read()
        @property
        def finished(self):return self.n>3
    class CVNoOldBox(CV):
        def rectangle(self,image,a,b,*args):
            assert not (image.shape[:2]==(80,120) and a==(40,20) and b==(60,60))
            return cv2.rectangle(image,a,b,*args)
    counter=LineCounter([Lane('N','N_0',(.1,.5),(.9,.5),'both')])
    counter.observe(1,'auto',(50/120,.25),time.monotonic())
    source=CameraSource(dict(interseccion='DEMO_INT_01',prueba=True,show=True))
    cv=CVNoOldBox(ord('q'))
    list(source._loop(LiveCap(),None,counter,{2:'auto'},30,cv,Worker()))
    assert counter.snapshot()[('N','N_0','auto')]==1 and cv.shown==1
