"""Controlador emulado del banco de pruebas: contexto del patrón State."""
from datetime import datetime, timezone
from uuid import uuid4

from cysa.contracts import Estado, PlanBorrador
from cysa.interfaces import Controlador

from .estados import Intermitente, LocalSeguro, SIN_COMUNICACION_S
from .secuenciador import Secuenciador


class ControladorEmulado(Controlador):
    def __init__(self, cruce, plan_centro, plan_local, prueba, ahora, sin_comunicacion_s=SIN_COMUNICACION_S):
        if not isinstance(prueba, bool):
            raise ValueError('prueba debe ser booleano')
        self.cruce = cruce
        self.plan_centro = plan_centro
        self.plan_local = plan_local
        self.prueba = prueba
        self.sin_comunicacion_s = sin_comunicacion_s
        self.ultimo_latido = float('-inf')
        self.historial = []
        # Al arrancar no hay comunicación confirmada: empieza en el plan local seguro.
        self.secuenciador = Secuenciador(plan_local, ahora)
        self.modo = LocalSeguro()

    # --- eventos (se delegan al modo actual) ---
    def latido(self, ahora):
        self.ultimo_latido = ahora
        self.modo.latido(self, ahora)

    def tick(self, ahora):
        self.modo.tick(self, ahora)
        if self.intermitente:
            return False
        return self.secuenciador.tick(ahora)

    def falla_mmu(self, motivo, ahora):
        self.modo.falla_mmu(self, motivo, ahora)

    def cambiar(self, nuevo, ahora):
        self.historial.append((ahora, self.modo.nombre, nuevo.nombre))
        self.modo = nuevo
        nuevo.al_entrar(self, ahora)

    # --- consultas ---
    @property
    def intermitente(self):
        return isinstance(self.modo, Intermitente)

    @property
    def luces(self):
        return None if self.intermitente else self.secuenciador.luces

    @property
    def fase_id(self):
        return 'INTERMITENTE' if self.intermitente else self.secuenciador.fase.fase_id

    @property
    def plan_id(self):
        return 'INTERMITENTE' if self.intermitente else self.secuenciador.plan.plan_id

    def estado(self):
        return Estado(mensaje_id=uuid4(), interseccion=self.cruce.interseccion, fase_actual=self.fase_id,
                      plan_activo=self.plan_id,
                      estado_controlador='conectado' if self.modo.conectado else 'desconectado',
                      timestamp=datetime.now(timezone.utc), prueba=self.prueba)

    def enviar_plan(self, plan: PlanBorrador):
        raise PermissionError('El envío de planes requiere autorización y MFA (RF-12); no está habilitado.')
