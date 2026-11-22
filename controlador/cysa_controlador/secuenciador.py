"""Recorre las fases de un plan y cambia de plan solo al terminar un todo rojo."""


class Secuenciador:
    def __init__(self, plan, ahora):
        self.plan = plan
        self.indice = 0
        self.inicio = ahora
        self.pendiente = None
        self.temporal_pendiente = False
        self.retorno = None
        self.fin_verde = None
        self.cruce_solicitado = False
        self.reanudar_indice = None

    @property
    def fase(self):
        return self.plan.fases[self.indice]

    @property
    def luces(self):
        return self.fase.luces

    def solicitar(self, plan, *, temporal=False, fin_verde=None):
        """Pide cambiar de plan; se aplica al terminar la próxima fase de todo rojo."""
        self.pendiente = None if plan is self.plan else plan
        self.temporal_pendiente = temporal and self.pendiente is not None
        self.fin_verde = fin_verde

    def solicitar_cruce(self):
        if not self.fase.peatonal:
            self.cruce_solicitado = True

    def corte_verde(self, ahora, verde_min_s):
        if 'G' in self.fase.luces:
            return max(ahora, self.inicio + verde_min_s)
        return None

    def hasta_cambio(self, ahora, *, fin_verde=None):
        fin = self.inicio + self.fase.duracion_s
        espera = max(0, min(fin, fin_verde) - ahora) if fin_verde is not None else max(0, fin - ahora)
        for paso in range(len(self.plan.fases)):
            fase = self.plan.fases[(self.indice + paso) % len(self.plan.fases)]
            if paso:
                espera += fase.duracion_s
            if fase.todo_rojo:
                return espera
        raise ValueError('No existe transición segura')

    def tick(self, ahora):
        """Avanza las fases vencidas. Devuelve True si cambiaron las luces."""
        cambio = False
        while True:
            fin = self.inicio + self.fase.duracion_s
            if self.fin_verde is not None:
                fin = min(fin, self.fin_verde)
            if ahora < fin:
                break
            self.inicio = fin
            self.fin_verde = None
            solicitud_atendida = False
            if self.fase.todo_rojo and self.pendiente is not None:
                siguiente = (self.indice + 1) % len(self.plan.fases)
                if self.fase.fase_id == 'PEATON_TODO_ROJO' and self.reanudar_indice is not None:
                    siguiente = self.reanudar_indice
                self.retorno = (self.plan, siguiente) if self.temporal_pendiente else None
                self.plan, self.pendiente, self.indice = self.pendiente, None, 0
                self.temporal_pendiente = False
                self.reanudar_indice = None
            elif self.fase.todo_rojo and self.retorno is not None:
                self.plan, self.indice = self.retorno
                self.retorno = None
            elif self.fase.fase_id == 'PEATON_TODO_ROJO' and self.reanudar_indice is not None:
                self.indice, self.reanudar_indice = self.reanudar_indice, None
            elif self.fase.todo_rojo and self.cruce_solicitado:
                siguiente = (self.indice + 1) % len(self.plan.fases)
                cruce = next((i for i, fase in enumerate(self.plan.fases) if fase.peatonal == 'cruce'), None)
                if cruce is None:
                    self.indice = siguiente
                else:
                    self.reanudar_indice = siguiente if siguiente != cruce else None
                    self.indice = cruce
                    self.cruce_solicitado = False
                    solicitud_atendida = True
            else:
                self.indice = (self.indice + 1) % len(self.plan.fases)
            if self.fase.a_demanda and not solicitud_atendida:
                if self.cruce_solicitado:
                    self.cruce_solicitado = False
                else:
                    self.indice = (self.indice + 3) % len(self.plan.fases)
            cambio = True
        return cambio
