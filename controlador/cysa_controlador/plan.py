"""Planes de fases y reglas de seguridad que el controlador nunca deja romper."""
from dataclasses import dataclass
from math import isfinite

VERDE, AMBAR, ROJO = 'G', 'Y', 'R'
LUCES = (VERDE, AMBAR, ROJO)


@dataclass(frozen=True)
class Fase:
    fase_id: str
    duracion_s: float
    luces: tuple            # una letra por grupo, en el orden de Interseccion.grupos
    peatonal: str | None = None
    a_demanda: bool = False

    @property
    def todo_rojo(self):
        return self.peatonal is None and all(luz == ROJO for luz in self.luces)


@dataclass(frozen=True)
class Plan:
    plan_id: str
    fases: tuple
    verde_min_s: float = 10


@dataclass(frozen=True)
class Interseccion:
    interseccion: str
    grupos: tuple                 # p. ej. ('NS', 'EO')
    conflictos: frozenset         # pares de índices de grupos que no pueden tener paso a la vez
    ambar_min_s: float
    todo_rojo_min_s: float
    verde_min_s: float

    def en_conflicto(self, luces):
        """Devuelve el primer par de grupos en conflicto con paso (verde o ámbar), o None."""
        for a, b in self.conflictos:
            if luces[a] != ROJO and luces[b] != ROJO:
                return self.grupos[a], self.grupos[b]
        return None


def validar_plan(plan, cruce):
    """Lanza ValueError si el plan puede producir una situación insegura."""
    n = len(cruce.grupos)
    if not plan.fases:
        raise ValueError(f'{plan.plan_id}: el plan no tiene fases')
    if AMBAR in plan.fases[0].luces:
        raise ValueError(f'{plan.plan_id}: la primera fase no puede tener ámbar (el plan empieza tras un todo rojo)')
    if not any(f.todo_rojo for f in plan.fases):
        raise ValueError(f'{plan.plan_id}: falta una fase de todo rojo para cambiar de plan con seguridad')
    for fase in plan.fases:
        if len(fase.luces) != n or any(luz not in LUCES for luz in fase.luces):
            raise ValueError(f'{plan.plan_id}/{fase.fase_id}: luces inválidas {fase.luces}')
        if not isfinite(fase.duracion_s) or fase.duracion_s <= 0:
            raise ValueError(f'{plan.plan_id}/{fase.fase_id}: duración debe ser positiva')
        par = cruce.en_conflicto(fase.luces)
        if par:
            raise ValueError(f'{plan.plan_id}/{fase.fase_id}: verdes en conflicto {par[0]} y {par[1]}')
        if AMBAR in fase.luces and fase.duracion_s < cruce.ambar_min_s:
            raise ValueError(f'{plan.plan_id}/{fase.fase_id}: ámbar menor a {cruce.ambar_min_s} s')
        if fase.todo_rojo and fase.duracion_s < cruce.todo_rojo_min_s:
            raise ValueError(f'{plan.plan_id}/{fase.fase_id}: todo rojo menor a {cruce.todo_rojo_min_s} s')
        if VERDE in fase.luces and fase.duracion_s < cruce.verde_min_s:
            raise ValueError(f'{plan.plan_id}/{fase.fase_id}: verde menor a {cruce.verde_min_s} s')
        if fase.peatonal is not None and (fase.peatonal not in ('cruce', 'despeje') or any(luz != ROJO for luz in fase.luces)):
            raise ValueError(f'{plan.plan_id}/{fase.fase_id}: fase peatonal incompatible con tráfico vehicular')
    # Transiciones, incluida la vuelta de la última fase a la primera.
    fases = list(plan.fases)
    for i,fase in enumerate(fases):
        if fase.a_demanda and (fase.peatonal!='cruce' or not fases[(i+2)%len(fases)].todo_rojo):
            raise ValueError(f'{plan.plan_id}: el cruce a demanda requiere despeje y todo rojo final')
    for actual, siguiente in zip(fases, fases[1:] + fases[:1]):
        if actual.peatonal == 'cruce' and siguiente.peatonal != 'despeje':
            raise ValueError(f'{plan.plan_id}: el cruce requiere despeje peatonal')
        if siguiente.peatonal == 'despeje' and (actual.peatonal != 'cruce' or siguiente.duracion_s <= 0):
            raise ValueError(f'{plan.plan_id}: despeje sin fase peatonal previa')
        for g in range(n):
            antes, despues = actual.luces[g], siguiente.luces[g]
            if antes == VERDE and despues == ROJO:
                raise ValueError(f'{plan.plan_id}: {cruce.grupos[g]} pasa de verde a rojo sin ámbar '
                                 f'({actual.fase_id} -> {siguiente.fase_id})')
            if antes == AMBAR and despues == VERDE:
                raise ValueError(f'{plan.plan_id}: {cruce.grupos[g]} pasa de ámbar a verde '
                                 f'({actual.fase_id} -> {siguiente.fase_id})')
            if antes == ROJO and despues == AMBAR:
                raise ValueError(f'{plan.plan_id}: {cruce.grupos[g]} pasa de rojo a ámbar '
                                 f'({actual.fase_id} -> {siguiente.fase_id})')
    return plan


def cargar_interseccion(datos):
    grupos = tuple(datos['grupos'])
    if len(grupos) < 2 or len(set(grupos)) != len(grupos):
        raise ValueError('Se requieren al menos dos grupos con nombres distintos')
    indice = {g: i for i, g in enumerate(grupos)}
    conflictos = set()
    for a, b in datos.get('conflictos', []):
        if a not in indice or b not in indice or a == b:
            raise ValueError(f'Conflicto inválido: {a}-{b}')
        conflictos.add(tuple(sorted((indice[a], indice[b]))))
    if not conflictos:
        raise ValueError('Declarar al menos un par de grupos en conflicto')
    tiempos = datos.get('tiempos_min', {})
    return Interseccion(interseccion=datos['interseccion'], grupos=grupos, conflictos=frozenset(conflictos),
                        ambar_min_s=float(tiempos.get('ambar_s', 3)), todo_rojo_min_s=float(tiempos.get('todo_rojo_s', 1)),
                        verde_min_s=float(tiempos.get('verde_s', 5)))


def cargar_plan(plan_id, fases, cruce):
    convertidas = []
    for f in fases:
        luces = f['luces']
        if set(luces) != set(cruce.grupos):
            raise ValueError(f'{plan_id}/{f.get("fase_id")}: indicar la luz de cada grupo {cruce.grupos}')
        convertidas.append(Fase(str(f['fase_id']), float(f['duracion_s']),
                                tuple(str(luces[g]).upper() for g in cruce.grupos),
                                f.get('peatonal'), f.get('a_demanda',False)))
    return validar_plan(Plan(plan_id, tuple(convertidas), cruce.verde_min_s), cruce)

