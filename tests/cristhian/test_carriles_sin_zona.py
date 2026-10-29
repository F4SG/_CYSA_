"""Regresión: con varias líneas sin zona (marcar_lineas.py), cada carril cuenta lo suyo."""
from datetime import datetime
from types import SimpleNamespace
import numpy as np
from cysa_detector.run import CameraSource
from cysa_detector.counter import Lane, LineCounter

# Dos vehículos bajan: el 1 por el carril izquierdo (x=0.2) y el 2 por el derecho (x=0.4).
TRAYECTORIAS = [[(1, 0.2, 0.3), (2, 0.4, 0.3)], [(1, 0.2, 0.7), (2, 0.4, 0.7)]]


class Cap:
    def __init__(self): self.n = 0
    def get(self, p): return 30
    def read(self):
        self.n += 1
        return (True, np.zeros((100, 100, 3), np.uint8)) if self.n <= len(TRAYECTORIAS) else (False, None)


class T(list):
    def cpu(self): return self
    def int(self): return self
    def tolist(self): return list(self)


class Model:
    def __init__(self): self.n = 0
    def track(self, frame, **k):
        objs = TRAYECTORIAS[self.n]; self.n += 1
        boxes = SimpleNamespace(xyxy=T([[x * 100 - 5, y * 100 - 10, x * 100 + 5, y * 100] for _, x, y in objs]),
                                id=T([i for i, _, _ in objs]), cls=T([2 for _ in objs]))
        return [SimpleNamespace(boxes=boxes)]


def test_cada_carril_sin_zona_cuenta_lo_suyo():
    lanes = [Lane('N', 'N_0', (0.1, 0.5), (0.3, 0.5)), Lane('N', 'N_1', (0.3, 0.5), (0.5, 0.5))]
    source = CameraSource({'interseccion': 'DEMO_INT_01', 'prueba': True},
                          datetime.fromisoformat('2026-10-27T12:00:00-04:00'))
    eventos = list(source._loop(Cap(), Model(), LineCounter(lanes), {2: 'auto'}, 30, SimpleNamespace(CAP_PROP_FPS=5)))
    autos = {e.carril: e.cantidad for e in eventos if e.clase == 'auto'}
    assert autos == {'N_0': 1, 'N_1': 1}
