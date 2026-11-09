"""Abstract Factory de laboratorio, aislada del detector, API y MQTT."""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import uuid4

from cysa.contracts import Conteo, Estado, PlanBorrador
from cysa.interfaces import Controlador, FuenteDeteccion


class FuentePrueba(FuenteDeteccion):
    def __init__(self, interseccion, conteos):
        self._conteos = tuple(conteo.model_copy() for conteo in conteos)
        if any(not conteo.prueba or conteo.interseccion != interseccion
               for conteo in self._conteos):
            raise ValueError('La fuente requiere conteos de prueba de su intersección')

    def eventos(self):
        for conteo in self._conteos:
            yield conteo.model_copy()


class ControladorEmulado(Controlador):
    """Registra en memoria la primera fase de un plan de prueba."""
    def __init__(self, interseccion):
        self.interseccion = interseccion
        self._plan = 'SIN_PLAN'
        self._fase = 'INICIAL'

    def estado(self):
        return Estado(mensaje_id=uuid4(), interseccion=self.interseccion,
                      fase_actual=self._fase, plan_activo=self._plan,
                      estado_controlador='conectado',
                      timestamp=datetime.now(timezone.utc), prueba=True)

    def enviar_plan(self, plan: PlanBorrador):
        if not plan.prueba or plan.interseccion != self.interseccion:
            raise ValueError('El emulador requiere un plan de prueba de su intersección')
        self._plan, self._fase = plan.plan_id, plan.fases[0].fase_id


class FabricaEntorno(ABC):
    @abstractmethod
    def crear_fuente(self) -> FuenteDeteccion:
        ...

    @abstractmethod
    def crear_controlador(self) -> Controlador:
        ...


class FabricaLaboratorio(FabricaEntorno):
    def __init__(self, interseccion, conteos: list[Conteo]):
        self.interseccion = interseccion
        self.conteos = tuple(conteo.model_copy() for conteo in conteos)

    def crear_fuente(self):
        return FuentePrueba(self.interseccion, self.conteos)

    def crear_controlador(self):
        return ControladorEmulado(self.interseccion)


def preparar_entorno(fabrica: FabricaEntorno):
    return fabrica.crear_fuente(), fabrica.crear_controlador()
