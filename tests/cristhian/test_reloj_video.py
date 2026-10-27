"""Reloj de video: los intervalos siguen cuadro/fps y no la velocidad de la PC."""
from datetime import datetime, timedelta
from types import SimpleNamespace
import numpy as np
import pytest
from cysa_detector.counter import Lane, LineCounter
from cysa_detector.run import CameraSource

CONFIG = {'interseccion': 'DEMO_INT_01', 'prueba': True}


class FakeCap:
    def __init__(self, frames, fps):
        self.left, self.fps = frames, fps
    def get(self, prop):
        return self.fps
    def read(self):
        if self.left == 0:
            return False, None
        self.left -= 1
        return True, np.zeros((4, 4, 3), np.uint8)


class FakeModel:
    def track(self, frame, **k):
        assert k['save'] is False
        return [SimpleNamespace(boxes=None)]


def eventos(frames, fps, inicio):
    src = CameraSource(CONFIG, inicio)
    counter = LineCounter([Lane('N', 'N_0', (0.1, 0.5), (0.4, 0.5))])
    cv2 = SimpleNamespace(CAP_PROP_FPS=5)
    return list(src._loop(FakeCap(frames, fps), FakeModel(), counter, {2: 'auto'}, 30, cv2))


def test_intervalos_con_tiempo_del_video():
    inicio = datetime.fromisoformat('2026-10-31T07:00:00-04:00')
    ev = eventos(30 * 75, 30, inicio)                      # 75 s de video a 30 fps
    tramos = sorted({(e.inicio, e.fin) for e in ev})
    assert [(a - inicio, b - inicio) for a, b in tramos] == [
        (timedelta(0), timedelta(seconds=30)),
        (timedelta(seconds=30), timedelta(seconds=60)),
        (timedelta(seconds=60), timedelta(seconds=75))]
    assert len(ev) == 3 * 3                                # 3 tramos x 3 clases x 1 carril


def test_inicio_video_requiere_zona():
    with pytest.raises(ValueError):
        CameraSource(CONFIG, datetime(2026, 10, 31, 7, 0))
