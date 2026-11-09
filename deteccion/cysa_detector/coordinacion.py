"""Una sesión de detector por proceso, sin compartir recursos de captura."""
from contextlib import contextmanager
from threading import Lock


class CoordinadorDetector:
    _instancia = None
    _creacion = Lock()

    def __new__(cls):
        with cls._creacion:
            if cls._instancia is None:
                instancia = super().__new__(cls)
                instancia._activa = Lock()
                cls._instancia = instancia
            return cls._instancia

    @contextmanager
    def sesion(self):
        if not self._activa.acquire(blocking=False):
            raise RuntimeError('Ya hay una sesión de detector activa en este proceso')
        try:
            yield
        finally:
            self._activa.release()
