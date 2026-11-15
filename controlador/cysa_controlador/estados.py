"""State: modos de operación del controlador emulado.

CENTRO        sigue el plan del centro de control mientras llegan latidos.
LOCAL_SEGURO  sin latidos por más de 60 s (RF-06): corre el plan local seguro.
INTERMITENTE  el monitor de conflictos (MMU) detectó una falla: luces en
              intermitente hasta reiniciar el banco. No se sale por software.
"""
SIN_COMUNICACION_S = 60.0


class Modo:
    nombre = 'BASE'
    conectado = False
    def al_entrar(self, c, ahora): ...
    def tick(self, c, ahora): ...
    def latido(self, c, ahora): ...
    def falla_mmu(self, c, motivo, ahora):
        c.cambiar(Intermitente(motivo), ahora)


class Centro(Modo):
    nombre = 'CENTRO'
    conectado = True
    def al_entrar(self, c, ahora):
        c.secuenciador.solicitar(c.plan_centro)
    def tick(self, c, ahora):
        if ahora - c.ultimo_latido > c.sin_comunicacion_s:
            c.cambiar(LocalSeguro(), ahora)


class LocalSeguro(Modo):
    nombre = 'LOCAL_SEGURO'
    def al_entrar(self, c, ahora):
        c.secuenciador.solicitar(c.plan_local)
    def latido(self, c, ahora):
        c.cambiar(Centro(), ahora)     # el cambio de plan espera el próximo todo rojo


class Intermitente(Modo):
    nombre = 'INTERMITENTE'
    def __init__(self, motivo):
        self.motivo = motivo
    def falla_mmu(self, c, motivo, ahora):
        pass                           # ya está en falla; no se repite la transición
