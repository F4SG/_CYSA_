"""Corredor sintético de dos cruces para la demostración interactiva de SUMO."""

import csv
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from xml.etree.ElementTree import Element, SubElement, parse

from .sumo_base import write_xml


CRUCES = ('A', 'B')
CORREDOR = ('W_A', 'A_B', 'B_E')
AMBULANCIA = 'AMBULANCIA_DEMO'
PLAN_FIJO = 'DEMO_FIJO'
AMBAR_S = 3
TODO_ROJO_S = 2
FIN_S = 160
ESPERADOS = 19


def preparar_red(output, netconvert):
    nodes = Element('nodes')
    edges = Element('edges')
    links = Element('connections')
    coords = {'W': (-180, 0), 'A': (0, 0), 'B': (250, 0), 'E': (430, 0)}
    axes = {}
    for cross, west, east in [('A', 'W', 'B'), ('B', 'A', 'E')]:
        x, _ = coords[cross]
        north, south = cross + 'N', cross + 'S'
        coords.update({north: (x, 100), south: (x, -100)})
        axes[cross] = ((north, south), (west, east))
    for node, (x, y) in coords.items():
        SubElement(nodes, 'node', id=node, x=str(x), y=str(y),
                   type='traffic_light' if node in CRUCES else 'priority')
    roads = {tuple(sorted((cross, arm))) for cross, axes_at_cross in axes.items()
             for pair in axes_at_cross for arm in pair}
    for a, b in sorted(roads):
        for source, target in ((a, b), (b, a)):
            SubElement(edges, 'edge', id=f'{source}_{target}',
                       attrib={'from': source, 'to': target, 'speed': '13.89',
                               'numLanes': '1', 'sidewalkWidth': '2'})
    for cross, ((north, south), (west, east)) in axes.items():
        for source, target in ((north, south), (south, north), (west, east), (east, west)):
            SubElement(links, 'connection', attrib={'from': f'{source}_{cross}', 'to': f'{cross}_{target}',
                                                  'fromLane': '1', 'toLane': '1'})
        SubElement(links, 'crossing', node=cross, edges=f'{west}_{cross} {cross}_{west}',
                   width='3', priority='true')
    for name, data in [('red.nod.xml', nodes), ('red.edg.xml', edges), ('red.con.xml', links)]:
        write_xml(output / name, data)
    result = subprocess.run([str(netconvert), '--node-files', 'red.nod.xml',
                             '--edge-files', 'red.edg.xml', '--connection-files', 'red.con.xml',
                             '--output-file', 'red.net.xml'], cwd=output,
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise RuntimeError('SUMO no pudo construir el corredor: ' + result.stderr.strip())
    network = parse(output / 'red.net.xml').getroot()
    for cross, ((north, south), (west, east)) in axes.items():
        connections = network.findall(f"connection[@tl='{cross}']")
        walking = {e.get('id') for e in network.findall("edge[@function='crossing']")
                   if e.get('id').startswith(f':{cross}_')}
        indices = {c.get('from'): int(c.get('linkIndex')) for c in connections}
        count = max(int(c.get('linkIndex')) for c in connections) + 1
        pedestrian = {int(c.get('linkIndex')) for c in connections if c.get('to') in walking}
        if not pedestrian:
            raise ValueError(f'Falta el semáforo peatonal del cruce {cross}')
        ns = {indices[f'{north}_{cross}'], indices[f'{south}_{cross}']}
        ew = {indices[f'{west}_{cross}'], indices[f'{east}_{cross}']}
        logic = network.find(f"tlLogic[@id='{cross}']")
        logic.clear()
        logic.attrib.update(id=cross, type='static', programID=PLAN_FIJO, offset='0')
        phases = [
            ('N-S y paso peatonal', 30, ns | pedestrian, 'G'),
            ('Ámbar N-S', AMBAR_S, ns, 'y'),
            ('Todo rojo', TODO_ROJO_S, set(), 'r'),
            ('E-O', 30, ew, 'G'),
            ('Ámbar E-O', AMBAR_S, ew, 'y'),
            ('Todo rojo', TODO_ROJO_S, set(), 'r'),
        ]
        for name, seconds, indexes, color in phases:
            state = ''.join(color if index in indexes else 'r' for index in range(count))
            SubElement(logic, 'phase', duration=str(seconds), state=state, name=name)
    write_xml(output / 'red.net.xml', network)


def preparar_rutas(output):
    routes = Element('routes')
    SubElement(routes, 'vType', id='auto', vClass='passenger', sigma='0', speedFactor='1')
    SubElement(routes, 'vType', id='ambulancia', vClass='emergency', guiShape='emergency',
               color='1,0.22,0.04', sigma='0', speedFactor='1')
    SubElement(routes, 'route', id='oeste_este', edges=' '.join(CORREDOR))
    SubElement(routes, 'route', id='este_oeste', edges='E_B B_A A_W')
    for cross in CRUCES:
        SubElement(routes, 'route', id=cross+'_ns', edges=f'{cross}N_{cross} {cross}_{cross}S')
        SubElement(routes, 'route', id=cross+'_sn', edges=f'{cross}S_{cross} {cross}_{cross}N')
    for index, name in enumerate(('A_ns', 'B_sn', 'este_oeste', 'B_ns', 'A_sn', 'oeste_este')):
        SubElement(routes, 'flow', id='trafico_'+name, type='auto', route=name, number='3',
                   begin=str(index * 2), end=str(index * 2 + 64))
    # Esta persona cruza calzada en B mientras llega el aviso anticipado.
    person = SubElement(routes, 'person', id='PEATON_B', depart='16', departPos='-0.5')
    SubElement(person, 'walk', edges='A_B B_A', arrivalPos='0.5', speed='0.9')
    SubElement(routes, 'vehicle', id=AMBULANCIA, type='ambulancia', route='oeste_este',
               depart='18', departPos='92', departSpeed='max')
    write_xml(output / 'rutas.rou.xml', routes)


def preparar_corredor(output, netconvert):
    output.mkdir(parents=True)
    preparar_red(output, netconvert)
    preparar_rutas(output)
    config = Element('configuration')
    inputs = SubElement(config, 'input')
    for name, value in [('net-file', 'red.net.xml'), ('route-files', 'rutas.rou.xml'),
                        ('additional-files', 'resultados.add.xml')]:
        SubElement(inputs, name, value=value)
    time = SubElement(config, 'time')
    SubElement(time, 'step-length', value='0.5')
    SubElement(time, 'end', value=str(FIN_S))
    results = SubElement(config, 'output')
    SubElement(results, 'tripinfo-output', value='tripinfo.xml')
    SubElement(results, 'tripinfo-output.write-unfinished', value='true')
    events = Element('additional')
    SubElement(events, 'timedEvent', type='SaveTLSStates', dest='semaforos.xml')
    write_xml(output / 'resultados.add.xml', events)
    report = SubElement(config, 'report')
    SubElement(report, 'no-step-log', value='true')
    visual = SubElement(config, 'gui_only')
    SubElement(visual, 'gui-settings-file', value='vista.xml')
    view = Element('viewsettings')
    SubElement(view, 'scheme', name='real world')
    SubElement(view, 'viewport', zoom='185', x='305', y='100', angle='0')
    write_xml(output / 'vista.xml', view)
    path = output / 'CYSA_DEMO.sumocfg'
    write_xml(path, config)
    return path


@dataclass
class Cruce:
    id: str
    fases: tuple
    etapa: str = 'fijo'
    hasta: float = 0
    alerta: float = 0
    esperando_peaton: bool = False

    @property
    def rojo(self):
        return self.fases[2].state


def conducir(con, output, *, visualizar=False):
    """Lee la posición del vehículo y aplica el mismo ciclo seguro a cada cruce."""
    tls = con.trafficlight
    crossings = {name: Cruce(name, tls.getAllProgramLogics(name)[0].phases) for name in CRUCES}
    aviso = None
    with (output / 'eventos_corredor.csv').open('w', encoding='utf-8', newline='', buffering=1) as stream:
        log = csv.writer(stream)
        log.writerow(('segundo_sumo', 'cruce', 'evento', 'detalle'))

        def emit(t, cross, event, detail=''):
            log.writerow((f'{t:.1f}', cross, event, detail))
            if visualizar:
                print(f'{t:5.1f} s | {cross} | {event.replace("_", " ")} {detail}', flush=True)

        def mark(cross, color):
            if visualizar:
                con.poi.setColor(cross.id, color)

        def start(cross, t):
            cross.alerta = t
            phase = tls.getPhase(cross.id)
            if phase in (0, 3):
                tls.setRedYellowGreenState(cross.id, cross.fases[phase + 1].state)
                cross.etapa, cross.hasta = 'ambar', t + AMBAR_S
                emit(t, cross.id, 'ambar')
            elif phase in (1, 4):
                cross.etapa, cross.hasta = 'ambar', tls.getNextSwitch(cross.id)
                tls.setRedYellowGreenState(cross.id, cross.fases[phase].state)
                emit(t, cross.id, 'ambar_en_curso')
            else:
                remaining = tls.getNextSwitch(cross.id) - t
                tls.setRedYellowGreenState(cross.id, cross.rojo)
                cross.etapa, cross.hasta = 'rojo', t + remaining
                emit(t, cross.id, 'todo_rojo_en_curso')
            mark(cross, (255, 155, 20, 255))

        for name, x in [('A', 180), ('B', 430)]:
            if visualizar:
                con.poi.add(name, x, 117, (95, 120, 138, 255), 'Cruce ' + name,
                            layer=20, width=10, height=10)
            emit(0, name, 'plan_fijo', PLAN_FIJO)
        while con.simulation.getTime() < FIN_S:
            con.simulationStep()
            t = con.simulation.getTime()
            moving = AMBULANCIA in con.vehicle.getIDList()
            road = con.vehicle.getRoadID(AMBULANCIA) if moving else ''
            pos = con.vehicle.getLanePosition(AMBULANCIA) if moving else 0
            if aviso is None and road == CORREDOR[0] and pos >= 95:
                emit(t, 'A', 'evento_emergencia', AMBULANCIA)
                start(crossings['A'], t)
                emit(t, 'A', 'aviso_enviado', 'destino B')
                aviso = t + 1
            if aviso is not None and crossings['B'].etapa == 'fijo' and t >= aviso:
                emit(t, 'B', 'aviso_recibido', 'origen A')
                start(crossings['B'], t)
            for index, cross in enumerate(crossings.values()):
                if cross.etapa == 'ambar' and t >= cross.hasta:
                    tls.setRedYellowGreenState(cross.id, cross.rojo)
                    cross.etapa, cross.hasta = 'rojo', t + TODO_ROJO_S
                    emit(t, cross.id, 'todo_rojo')
                if cross.etapa == 'rojo' and t >= cross.hasta:
                    walking = any(con.person.getRoadID(p).startswith(f':{cross.id}_c')
                                  for p in con.person.getIDList())
                    if walking:
                        if not cross.esperando_peaton:
                            emit(t, cross.id, 'despeje_peatonal_en_curso')
                            cross.esperando_peaton = True
                        continue
                    if cross.esperando_peaton:
                        emit(t, cross.id, 'despeje_peatonal_completado')
                    tls.setRedYellowGreenState(cross.id, cross.fases[3].state)
                    cross.etapa = 'prioridad'
                    mark(cross, (43, 222, 145, 255))
                    emit(t, cross.id, 'verde_prioridad', f'{t - cross.alerta:.1f} s desde el aviso local')
                if cross.etapa == 'prioridad' and road == CORREDOR[index + 1] and pos >= 6:
                    emit(t, cross.id, 'ambulancia_paso')
                    tls.setRedYellowGreenState(cross.id, cross.fases[4].state)
                    cross.etapa, cross.hasta = 'retorno_ambar', t + AMBAR_S
                    emit(t, cross.id, 'ambar_retorno')
                if cross.etapa == 'retorno_ambar' and t >= cross.hasta:
                    tls.setRedYellowGreenState(cross.id, cross.rojo)
                    cross.etapa, cross.hasta = 'retorno_rojo', t + TODO_ROJO_S
                    emit(t, cross.id, 'todo_rojo_retorno')
                if cross.etapa == 'retorno_rojo' and t >= cross.hasta:
                    tls.setProgram(cross.id, PLAN_FIJO)
                    tls.setPhase(cross.id, 0)
                    cross.etapa = 'restaurado'
                    mark(cross, (95, 120, 138, 255))
                    emit(t, cross.id, 'plan_fijo_restaurado', PLAN_FIJO)
            if all(c.etapa == 'restaurado' for c in crossings.values()) and not con.simulation.getMinExpectedNumber():
                emit(t, 'A-B', 'corrida_completada')
                return
        raise RuntimeError('La corrida terminó sin completar el recorrido o el retorno a plan fijo.')


def traci_bundle():
    import sumo

    tools = Path(sumo.__file__).resolve().parent / 'tools'
    sys.path.insert(0, str(tools))
    try:
        import traci
        return traci
    finally:
        sys.path.remove(str(tools))
