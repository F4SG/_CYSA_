"""Recorre las fases de un plan y cambia de plan solo al terminar un todo rojo."""


class Secuenciador:
    def __init__(self, plan, ahora):
        self.plan = plan
        self.indice = 0
        self.inicio = ahora
        self.pendiente = None

    @property
    def fase(self):
        return self.plan.fases[self.indice]

    @property
    def luces(self):
        return self.fase.luces

    def solicitar(self, plan):
        """Pide cambiar de plan; se aplica al terminar la próxima fase de todo rojo."""
        self.pendiente = None if plan is self.plan else plan

    def tick(self, ahora):
        """Avanza las fases vencidas. Devuelve True si cambiaron las luces."""
        cambio = False
        while ahora - self.inicio >= self.fase.duracion_s:
            self.inicio += self.fase.duracion_s
            if self.fase.todo_rojo and self.pendiente is not None:
                self.plan, self.pendiente, self.indice = self.pendiente, None, 0
            else:
                self.indice = (self.indice + 1) % len(self.plan.fases)
            cambio = True
        return cambio
