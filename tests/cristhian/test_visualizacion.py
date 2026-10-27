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
    def imshow(self,*args):self.shown+=1
    def waitKey(self,*args):return self.key
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
    list(source._loop(Cap(),Model(),counter,{2:'auto'},30,cv));return cv

def test_una_ventana_persistente_para_todos_los_cuadros():
    cv=run(-1)
    assert cv.created==1 and cv.shown==3

def test_q_cierra_tras_el_primer_cuadro():
    cv=run(ord('q'))
    assert cv.created==1 and cv.shown==1
