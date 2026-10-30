"""Captura en vivo con un único cuadro pendiente; archivos de video no usan este modo."""
from threading import Condition,Event,Thread
import time

class LatestCapture:
    def __init__(self,cap,timeout=10):
        self._cap=cap;self._condition=Condition();self._stop=Event();self._done=False
        self._frame=None;self._sequence=0;self._consumed=0;self._captured_at=0
        self.delivered_at=None;self.dropped_frames=0;self.timeout=timeout;self._error=None
        self._thread=Thread(target=self._pump,name='cysa-captura-reciente',daemon=True)
        self._thread.start()
    def _pump(self):
        try:
            deadline=time.monotonic()+self.timeout
            while not self._stop.is_set():
                ok,frame=self._cap.read()
                if not ok:
                    if time.monotonic()>=deadline:break
                    self._stop.wait(.03);continue
                deadline=time.monotonic()+min(1.,self.timeout)
                with self._condition:
                    self._frame=frame;self._sequence+=1;self._captured_at=time.monotonic()
                    self._condition.notify_all()
        except Exception as error:
            self._error=error
        finally:
            self._cap.release()
            with self._condition:self._done=True;self._condition.notify_all()
    def read(self,timeout=None):
        if timeout is None:timeout=self.timeout
        with self._condition:
            self._condition.wait_for(lambda:self._sequence>self._consumed or self._done or self._stop.is_set(),timeout)
            if self._stop.is_set():return False,None
            if self._sequence>self._consumed:
                self.dropped_frames+=max(0,self._sequence-self._consumed-1)
                self._consumed=self._sequence;self.delivered_at=self._captured_at
                return True,self._frame
            if self._error:raise RuntimeError('Error durante la captura en vivo') from self._error
            return False,None
    def poll(self,timeout=0):
        return self.read(timeout=timeout)
    @property
    def finished(self):
        with self._condition:
            if self._error:raise RuntimeError('Error durante la captura en vivo') from self._error
            return self._done or self._stop.is_set()
    def get(self,prop):return self._cap.get(prop)
    def release(self):
        self._stop.set()
        with self._condition:self._condition.notify_all()
        self._thread.join(timeout=2)
        # El hilo que lee es el único que libera la cámara; no competir con un read bloqueado.
        if self._thread.is_alive():print('Captura pendiente de cierre del controlador; no se fuerza release concurrente.',flush=True)
