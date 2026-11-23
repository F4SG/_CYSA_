"""Estado local del controlador físico para la demostración; no es una lectura óptica."""
import json
import time
from pathlib import Path


class TelemetriaArduino:
    def __init__(self, path, puerto, sesion, reloj=time.monotonic):
        self.path, self.puerto, self.sesion = Path(path), puerto, sesion
        self.reloj, self.ultimo, self.previo = reloj, float('-inf'), None

    def __call__(self, ctrl):
        ahora = self.reloj()
        actual = (ctrl.plan_id, ctrl.fase_id, ctrl.modo.nombre)
        if actual == self.previo and ahora - self.ultimo < 1:
            return
        snapshot = ctrl.estado().model_dump(mode='json')
        snapshot.update(puerto=self.puerto, sesion=self.sesion,
                        luces=dict(zip(ctrl.cruce.grupos, ctrl.luces)) if ctrl.luces else None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(snapshot), encoding='utf-8')
        tmp.replace(self.path)
        self.ultimo, self.previo = ahora, actual
