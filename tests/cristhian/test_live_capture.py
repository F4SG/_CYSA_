from threading import Event,Thread
import pytest
from cysa_detector.live_capture import LatestCapture

class Cap:
    def __init__(self,frames):self.frames=iter(frames);self.releases=0
    def read(self):
        try:return True,next(self.frames)
        except StopIteration:return False,None
    def release(self):self.releases+=1
    def get(self,p):return 30

def test_conserva_solo_el_cuadro_mas_reciente():
    cap=Cap([1,2,3]);stream=LatestCapture(cap,timeout=.05)
    stream._thread.join(1)
    assert stream.read()==(True,3)
    assert stream.dropped_frames==2
    assert stream.read()==(False,None)
    stream.release();assert cap.releases==1

def test_no_repite_ni_acumula_cuadros():
    gate=Event();ready=Event()
    class Controlled(Cap):
        def __init__(self):super().__init__([]);self.n=0
        def read(self):
            self.n+=1
            if self.n==1:return True,1
            if self.n==2:ready.set();gate.wait(1);return True,2
            if self.n==3:return True,3
            return False,None
    cap=Controlled();stream=LatestCapture(cap,timeout=.1)
    assert ready.wait(1)
    assert stream.read()==(True,1)
    gate.set();stream._thread.join(1)
    assert stream.read()==(True,3) and stream.dropped_frames==1
    assert stream.read()==(False,None)
    stream.release();assert cap.releases==1

def test_error_libera_camara():
    class Broken(Cap):
        def read(self):raise OSError('fuente interrumpida')
    cap=Broken([]);stream=LatestCapture(cap,timeout=.1);stream._thread.join(1)
    with pytest.raises(RuntimeError):stream.read()
    stream.release();assert cap.releases==1

def test_release_no_compite_con_read_bloqueado():
    gate=Event();reading=Event()
    class Blocking(Cap):
        def read(self):reading.set();gate.wait(1);return False,None
    cap=Blocking([]);stream=LatestCapture(cap,timeout=.1);assert reading.wait(1)
    close=Thread(target=stream.release);close.start()
    assert cap.releases==0
    gate.set();close.join(1)
    assert not close.is_alive() and cap.releases==1


def test_poll_no_bloquea_interfaz_si_no_hay_cuadro_nuevo():
    gate=Event();reading=Event()
    class Blocking(Cap):
        def read(self):reading.set();gate.wait(1);return False,None
    cap=Blocking([]);stream=LatestCapture(cap,timeout=.1)
    try:
        assert reading.wait(1)
        assert stream.poll(0)==(False,None)
        assert not stream._stop.is_set()
    finally:gate.set();stream.release()
    assert cap.releases==1
