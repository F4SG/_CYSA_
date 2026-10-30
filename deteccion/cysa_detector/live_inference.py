"""Un trabajo de IA y un único cuadro reciente pendiente, sin cola acumulativa."""
from threading import Condition,Thread
from time import monotonic

class LiveInference:
    def __init__(self,model,options):
        self.model=model;self.options=options
        self._condition=Condition();self._pending=None;self._completed=None
        self._stop=False;self._error=None;self.elapsed_ms=None
        self.replaced_frames=0
        self._thread=Thread(target=self._pump,name='cysa-inferencia',daemon=True)
        self._thread.start()

    def submit(self,image,offset,shape,captured_at):
        with self._condition:
            if self._stop:return False
            if self._pending is not None:self.replaced_frames+=1
            self._pending=(image,offset,shape,captured_at)
            self._condition.notify_all()
            return True

    def _pump(self):
        try:
            while True:
                with self._condition:
                    self._condition.wait_for(lambda:self._stop or self._pending is not None)
                    if self._stop:return
                    image,offset,shape,captured_at=self._pending;self._pending=None
                started=monotonic()
                results=self.model.track(image,**self.options)
                result=(results,offset,shape,captured_at,(monotonic()-started)*1000)
                with self._condition:
                    self._completed=result;self._condition.notify_all()
        except Exception as error:
            with self._condition:
                self._error=error;self._stop=True;self._condition.notify_all()

    def take(self):
        with self._condition:
            if self._error is not None:
                error=self._error;self._error=None;raise error
            result=self._completed;self._completed=None
            if result is not None:self.elapsed_ms=result[-1]
            return result

    def close(self):
        with self._condition:
            self._stop=True;self._pending=None;self._condition.notify_all()
        self._thread.join()
        with self._condition:
            if self._error is not None:
                error=self._error;self._error=None;raise error
