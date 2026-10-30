from threading import Event
import pytest
from cysa_detector.live_inference import LiveInference


def test_pendiente_siempre_es_el_mas_reciente_y_solo_un_modelo_a_la_vez():
    first=Event();second=Event();release_first=Event();release_second=Event();calls=[]
    class Model:
        def track(self,image,**options):
            calls.append(image)
            if image=='cuadro1':first.set();assert release_first.wait(2)
            else:second.set();assert release_second.wait(2)
            return [image]
    worker=LiveInference(Model(),{'imgsz':512})
    try:
        worker.submit('cuadro1',(10,20),(720,1280),123)
        assert first.wait(1) and worker.take() is None
        worker.submit('cuadro2',(0,0),(720,1280),124)
        worker.submit('cuadro3',(1,2),(720,1280),125)
        assert worker.replaced_frames==1 and calls==['cuadro1']
        release_first.set();assert second.wait(1)
        result=worker.take()
        assert result[:4]==(['cuadro1'],(10,20),(720,1280),123)
        assert calls==['cuadro1','cuadro3'] and worker.elapsed_ms>=0
    finally:release_first.set();release_second.set();worker.close()


def test_error_de_ia_se_propaga_sin_bloquear_poll():
    class Model:
        def track(self,image,**options):raise ValueError('modelo fallido')
    worker=LiveInference(Model(),{})
    worker.submit('frame',(0,0),(1,1),0)
    try:
        worker._thread.join(1)
        with pytest.raises(ValueError,match='modelo fallido'):worker.take()
    finally:worker.close()


def test_conteo_asincrono_usa_cada_resultado_una_sola_vez():
    import numpy as np
    from types import SimpleNamespace
    from cysa_detector.run import CameraSource
    from cysa_detector.counter import Lane,LineCounter
    class T(list):
        def cpu(self):return self
        def int(self):return self
        def tolist(self):return list(self)
    class Model:
        n=0
        def track(self,image,**kw):
            self.n+=1;bottom=40 if self.n==1 else 60
            boxes=SimpleNamespace(xyxy=T([[40,20,60,bottom]]),id=T([1]),cls=T([3]),conf=T([.9]))
            return [SimpleNamespace(boxes=boxes)]
    worker=LiveInference(Model(),{})
    class Cap:
        n=0;delivered_at=None
        def poll(self,timeout):
            if self.n>=3:return False,None
            if self.n:
                with worker._condition:
                    assert worker._condition.wait_for(lambda:worker._completed is not None,1)
            self.n+=1;return True,np.zeros((100,100,3),np.uint8)
        @property
        def finished(self):return self.n>=3
    lane=Lane('N','N_0',(.1,.5),(.9,.5),'both',((.1,.1),(.9,.1),(.9,.9),(.1,.9)))
    source=CameraSource(dict(interseccion='DEMO_INT_01',prueba=True))
    counter=LineCounter([lane])
    try:
        events=list(source._loop(Cap(),None,counter,{3:'moto'},30,SimpleNamespace(),worker))
    finally:worker.close()
    assert counter.snapshot().get(('N','N_0','moto'))==1
    if events:assert sum(e.cantidad for e in events if e.clase=='moto')==1
