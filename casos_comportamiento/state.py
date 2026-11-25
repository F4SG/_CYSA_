"""Caso de estudio 2 - State: controlador semafórico emulado (Sprint 2).

Prueba de concepto de RF-06 (modo local seguro) y RF-09 (emergencia simulada).
Cada estado decide qué eventos acepta y devuelve el contrato Estado real.

Supuestos de la prueba: ámbar 3 s y todo rojo 2 s (plan DEMO); en modo local
seguro no se atienden prioridades porque no hay coordinación con el centro.
"""
from datetime import datetime, timezone
from uuid import uuid4

from cysa.contracts import Estado

SIN_COMUNICACION_S = 60      # RF-06
AMBAR_S, TODO_ROJO_S = 3, 2  # plan DEMO


class EstadoControlador:
    nombre = 'BASE'
    def tick(self, c, ahora): ...
    def emergencia(self, c, acceso, ahora): ...
    def fin_emergencia(self, c, ahora): ...


class Normal(EstadoControlador):
    nombre = 'NORMAL'
    def tick(self, c, ahora):
        if ahora - c.ultimo_mensaje > SIN_COMUNICACION_S:
            c.cambiar(LocalSeguro(), ahora)
    def emergencia(self, c, acceso, ahora):
        c.cambiar(Emergencia(acceso, ahora), ahora)


class LocalSeguro(EstadoControlador):
    """Plan local fijo: sin prioridades hasta recuperar la comunicación."""
    nombre = 'LOCAL_SEGURO'
    def tick(self, c, ahora):
        if ahora - c.ultimo_mensaje <= SIN_COMUNICACION_S:
            c.cambiar(Normal(), ahora)


class Emergencia(EstadoControlador):
    """Despeje peatonal en curso -> ámbar -> todo rojo -> verde al acceso."""
    nombre = 'EMERGENCIA'
    def __init__(self, acceso, deteccion):
        self.acceso, self.deteccion = acceso, deteccion
        self.fase, self.desde = 'ESPERA_DESPEJE', deteccion
    def tick(self, c, ahora):
        if self.fase == 'ESPERA_DESPEJE' and ahora >= c.despeje_peatonal_hasta:
            self.fase, self.desde = 'AMBAR', ahora
        if self.fase == 'AMBAR' and ahora - self.desde >= AMBAR_S:
            self.fase, self.desde = 'TODO_ROJO', ahora
        if self.fase == 'TODO_ROJO' and ahora - self.desde >= TODO_ROJO_S:
            self.fase, self.desde = 'VERDE', ahora
            c.verde_emergencia_en = ahora
    def fin_emergencia(self, c, ahora):
        if self.fase == 'VERDE':
            c.cambiar(Normal(), ahora)


class ControladorConEstados:
    def __init__(self, interseccion, ahora=0.0):
        self.interseccion = interseccion
        self.ultimo_mensaje = ahora
        self.despeje_peatonal_hasta = ahora
        self.verde_emergencia_en = None
        self.historial = []
        self.estado_actual = Normal()

    def cambiar(self, nuevo, ahora):
        self.historial.append((ahora, self.estado_actual.nombre, nuevo.nombre))
        self.estado_actual = nuevo
        nuevo.tick(self, ahora)

    # Eventos: se delegan al estado actual, sin condiciones aquí.
    def mensaje_centro(self, ahora):
        self.ultimo_mensaje = ahora
        self.estado_actual.tick(self, ahora)
    def tick(self, ahora): self.estado_actual.tick(self, ahora)
    def emergencia_detectada(self, acceso, ahora): self.estado_actual.emergencia(self, acceso, ahora)
    def fin_emergencia(self, ahora): self.estado_actual.fin_emergencia(self, ahora)

    @property
    def fase(self):
        e = self.estado_actual
        return f'{e.nombre}_{e.fase}' if isinstance(e, Emergencia) else e.nombre

    def estado(self):
        return Estado(mensaje_id=uuid4(), interseccion=self.interseccion, fase_actual=self.fase,
                      plan_activo='LOCAL_SEGURO' if isinstance(self.estado_actual, LocalSeguro) else 'CENTRO',
                      estado_controlador='desconectado' if isinstance(self.estado_actual, LocalSeguro) else 'conectado',
                      timestamp=datetime.now(timezone.utc), prueba=True)
