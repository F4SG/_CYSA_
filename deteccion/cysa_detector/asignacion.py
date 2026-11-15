"""Strategy: formas de asignar un vehículo detectado a un carril.

El detector elige una estrategia al iniciar (o al recalibrar) y la usa en cada
cuadro sin condiciones sobre el modo. La clave devuelta es la que recibe
LineCounter.observe(lane_key=...):
  (acceso, carril)  el vehículo pertenece a ese carril;
  FUERA_DE_ZONA     está fuera de toda zona y no se cuenta;
  None              no hay zonas: decide el cruce de cada línea.
"""
from abc import ABC, abstractmethod

FUERA_DE_ZONA = ('', '')


class AsignadorCarril(ABC):
    @abstractmethod
    def asignar(self, track_id, punto):
        """Devuelve (carril o None, clave para LineCounter)."""

    @abstractmethod
    def muestra_fuera_de_zona(self):
        """True si los vehículos sin carril se dibujan igual en el visor."""


class AsignacionPorZonas(AsignadorCarril):
    """El carril es la zona dibujada (polígono) que contiene el punto."""
    def __init__(self, lanes):
        self.lanes = [lane for lane in lanes if lane.polygon]

    def asignar(self, track_id, punto):
        lane = next((l for l in self.lanes if l.contains(punto)), None)
        return lane, ((lane.acceso, lane.carril) if lane else FUERA_DE_ZONA)

    def muestra_fuera_de_zona(self):
        return False


class AsignacionPorLineas(AsignadorCarril):
    """Solo segmentos sin zona: un segmento "contiene" cualquier punto, así que no
    sirve para asignar; cada línea decide su propio cruce (ver commit 32ed535)."""
    def asignar(self, track_id, punto):
        return None, None

    def muestra_fuera_de_zona(self):
        return True


class AsignacionAutomatica(AsignadorCarril):
    """Carriles aprendidos de las trayectorias con AutoLanes."""
    def __init__(self, auto_lanes):
        self.auto = auto_lanes

    def asignar(self, track_id, punto):
        lane = self.auto.assign(track_id, punto)
        return lane, ((lane.acceso, lane.carril) if lane else FUERA_DE_ZONA)

    def muestra_fuera_de_zona(self):
        return not any(lane.polygon for lane in self.auto.lanes)


def crear_asignador(config, lanes, auto_lanes=None):
    """Elige la estrategia según el perfil."""
    if config.get('auto_carriles'):
        if auto_lanes is None:
            raise ValueError('El modo automático requiere AutoLanes')
        return AsignacionAutomatica(auto_lanes)
    if any(lane.polygon for lane in lanes):
        return AsignacionPorZonas(lanes)
    return AsignacionPorLineas()
