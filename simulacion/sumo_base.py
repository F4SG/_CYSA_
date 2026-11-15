"""Genera red DEMO o reutiliza una red real con su plan fijo. Solo CLI."""
import argparse,csv,json,shutil,subprocess
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from pathlib import Path
from datetime import datetime
from xml.etree.ElementTree import Element,SubElement,ElementTree,ParseError,parse

def binary(name):
    found=shutil.which(name)
    if found:return found
    import sumolib
    return sumolib.checkBinary(name)
def write_xml(path,root):ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
def load_counts(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    if not rows:raise ValueError('No hay flujos: completar la plantilla')
    seen=set();ints=set()
    for r in rows:
        if r['clase'] not in ['auto','micro','moto'] or r['prueba'].lower() not in ['true','false']:raise ValueError('Clase o marca prueba inválida')
        r['cantidad']=int(r['cantidad']);r['inicio_dt']=datetime.fromisoformat(r['inicio'].replace('Z','+00:00'));r['fin_dt']=datetime.fromisoformat(r['fin'].replace('Z','+00:00'))
        if r['cantidad']<0 or r['inicio_dt'].tzinfo is None or r['fin_dt'].tzinfo is None or r['fin_dt']<=r['inicio_dt']:raise ValueError('Cantidad, zona o intervalo inválido')
        key=tuple(r[k] for k in ['interseccion','acceso','carril','clase','inicio','fin'])
        if key in seen:raise ValueError('Intervalo/carril/clase duplicado')
        seen.add(key);ints.add(r['interseccion'])
    if len(ints)!=1:raise ValueError('Ejecutar una intersección por escenario')
    if sum(r['cantidad'] for r in rows)==0:raise ValueError('Sin vehículos no existe una demora base medible')
    # Rechazar intervalos que se superpongan para el mismo carril y clase.
    groups={}
    for r in rows:groups.setdefault((r['acceso'],r['carril'],r['clase']),[]).append(r)
    for group in groups.values():
        ordered=sorted(group,key=lambda r:r['inicio_dt'])
        if any(a['fin_dt']>b['inicio_dt'] for a,b in zip(ordered,ordered[1:])):raise ValueError('Intervalos superpuestos')
    return rows

def demo_network(out):
    nodes=Element('nodes')
    for name,x,y,kind in [('C',0,0,'traffic_light'),('N',0,300,'priority'),('S',0,-300,'priority'),('E',300,0,'priority'),('W',-300,0,'priority')]:
        SubElement(nodes,'node',id=name,x=str(x),y=str(y),type=kind)
    edges=Element('edges');connections=Element('connections');mapping={}
    for idx,(acc,target) in enumerate([('N','S'),('S','N'),('E','W'),('W','E')]):
        SubElement(edges,'edge',id=acc+'_in',**{'from':acc,'to':'C','numLanes':'1','speed':'13.89'})
        SubElement(edges,'edge',id=acc+'_out',**{'from':'C','to':acc,'numLanes':'1','speed':'13.89'})
        SubElement(connections,'connection',**{'from':acc+'_in','to':target+'_out','fromLane':'0','toLane':'0','tl':'C','linkIndex':str(idx)})
        mapping[acc]=(acc+'_in',target+'_out')
    tls=Element('additional');logic=SubElement(tls,'tlLogic',id='C',type='static',programID='DEMO_FIJO',offset='0')
    for duration,state in [(30,'GGrr'),(3,'yyrr'),(2,'rrrr'),(30,'rrGG'),(3,'rryy'),(2,'rrrr')]:SubElement(logic,'phase',duration=str(duration),state=state)
    for name,root in [('demo.nod.xml',nodes),('demo.edg.xml',edges),('demo.con.xml',connections),('demo.tll.xml',tls)]:write_xml(out/name,root)
    subprocess.run([binary('netconvert'),'--node-files',str(out/'demo.nod.xml'),'--edge-files',str(out/'demo.edg.xml'),
      '--connection-files',str(out/'demo.con.xml'),'--tllogic-files',str(out/'demo.tll.xml'),'--output-file',str(out/'red.net.xml')],check=True)
    # netconvert puede reordenar linkIndex. Derivar los verdes de las conexiones finales,
    # no de los índices solicitados en PlainXML (evita verdes en conflicto).
    from xml.etree.ElementTree import parse
    tree=parse(out/'red.net.xml');net=tree.getroot()
    connections=[x for x in net.findall('connection') if x.get('tl')=='C']
    size=max(int(x.attrib['linkIndex']) for x in connections)+1
    logic=net.find("tlLogic[@id='C']")
    for child in list(logic):logic.remove(child)
    logic.set('programID','DEMO_FIJO')
    def state_for(accesses,color):
        state=['r']*size
        for x in connections:
            if x.attrib['from'].split('_')[0] in accesses:state[int(x.attrib['linkIndex'])]=color
        return ''.join(state)
    for duration,state in [(30,state_for(['N','S'],'G')),(3,state_for(['N','S'],'y')),(2,'r'*size),
                           (30,state_for(['E','W'],'G')),(3,state_for(['E','W'],'y')),(2,'r'*size)]:
        SubElement(logic,'phase',duration=str(duration),state=state)
    tree.write(out/'red.net.xml',encoding='utf-8',xml_declaration=True)
    actual=Element('additional')
    import copy
    actual.append(copy.deepcopy(logic));write_xml(out/'demo.tll.xml',actual)
    return out/'red.net.xml',mapping

def build_routes(rows,mapping,out):
    routes=Element('routes');base=min(r['inicio_dt'] for r in rows)
    for clase,vclass,length in [('auto','passenger','5'),('micro','bus','10'),('moto','motorcycle','2')]:
        SubElement(routes,'vType',id=clase,vClass=vclass,length=length,accel='2.0',decel='4.5',sigma='0',speedFactor='1')
    for access,(source,target) in mapping.items():SubElement(routes,'route',id='ruta_'+access,edges=source+' '+target)
    for i,r in enumerate(sorted(rows,key=lambda r:r['inicio_dt'])):
        if r['acceso'] not in mapping:raise ValueError('Acceso sin correspondencia en la red: '+r['acceso'])
        if r['cantidad']:
            SubElement(routes,'flow',id=f'{r["acceso"]}__{i}',type=r['clase'],route='ruta_'+r['acceso'],
              begin=str((r['inicio_dt']-base).total_seconds()),end=str((r['fin_dt']-base).total_seconds()),number=str(r['cantidad']),departLane='best')
    write_xml(out/'flujos.rou.xml',routes)
    return max((r['fin_dt']-base).total_seconds() for r in rows)

def summarize(tripinfo,path,prueba):
    from xml.etree.ElementTree import parse
    groups={};unfinished=0
    for t in parse(tripinfo).getroot().findall('tripinfo'):
        if float(t.get('arrival','-1'))<0:unfinished+=1;continue
        access=t.attrib['id'].split('__')[0];delay=float(t.attrib['timeLoss'])
        group=groups.setdefault(access,[]);group.append(delay)
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['acceso','vehiculos_completados','demora_media_timeLoss_s','prueba']);w.writeheader()
        for access,values in sorted(groups.items()):w.writerow({'acceso':access,'vehiculos_completados':len(values),'demora_media_timeLoss_s':f'{sum(values)/len(values):.6f}','prueba':str(prueba).lower()})
    return sum(map(len,groups.values())),unfinished


DEMO = Path(__file__).resolve().parent / 'escenarios' / 'DEMO'
DEMO_MAP = {'N': ('N_in', 'S_out'), 'S': ('S_in', 'N_out'),
            'E': ('E_in', 'W_out'), 'W': ('W_in', 'E_out')}


@dataclass(frozen=True)
class EscenarioSUMO:
    red: Path
    rutas: Path
    config: Path
    semilla: int
    demanda: Path
    esperados: int
    prueba: bool
    demo: bool


class EscenarioSUMOBuilder:
    def __init__(self):
        self.red = None
        self.accesos = None
        self.demanda = None
        self.salida = None
        self.semilla = 42
        self.generar_demo = False

    def con_red_demo(self, *, generar=False):
        self.generar_demo = generar
        self.red = DEMO / 'red.net.xml'
        self.accesos = None
        return self

    def con_red(self, red, accesos):
        self.generar_demo = False
        self.red = Path(red)
        self.accesos = Path(accesos)
        return self

    def con_demanda(self, demanda):
        self.demanda = Path(demanda)
        return self

    def con_salida(self, salida):
        self.salida = Path(salida)
        return self

    def con_semilla(self, semilla):
        self.semilla = semilla
        return self

    def construir(self):
        if self.red is None or self.demanda is None or self.salida is None:
            raise ValueError('Completar red, demanda y salida')
        if not isinstance(self.semilla, int) or isinstance(self.semilla, bool):
            raise ValueError('La semilla debe ser un entero')
        salida = self.salida.resolve()
        if salida.exists() and (not salida.is_dir() or any(salida.iterdir())):
            raise FileExistsError('Usar una carpeta de salida nueva/vacía para no mezclar resultados')
        rows = load_counts(self.demanda)
        marcas = [row['prueba'].lower() == 'true' for row in rows]
        demo = self.accesos is None
        if demo and not all(marcas):
            raise ValueError('La red DEMO requiere todos los conteos marcados prueba=true')
        if demo:
            mapping = DEMO_MAP
        else:
            with self.accesos.open(encoding='utf-8-sig', newline='') as archivo:
                mapping = {}
                reader = csv.DictReader(archivo)
                if not {'acceso', 'entrada', 'salida'} <= set(reader.fieldnames or []):
                    raise ValueError('El mapa requiere las columnas acceso, entrada y salida')
                for row in reader:
                    acceso = row['acceso']
                    if not acceso:
                        raise ValueError('El mapa contiene un acceso vacío')
                    if acceso in mapping:
                        raise ValueError(f'Acceso repetido: {acceso}')
                    mapping[acceso] = (row['entrada'], row['salida'])

        red = parse(self.red).getroot()
        if not any(plan.get('type') == 'static' and plan.find('phase') is not None
                   for plan in red.findall('tlLogic')):
            raise ValueError('La red debe incluir un plan fijo con fases')
        edges = {edge.get('id') for edge in red.findall('edge')}
        conexiones = {(item.get('from'), item.get('to')) for item in red.findall('connection')}
        for acceso, par in mapping.items():
            if not set(par) <= edges:
                raise ValueError(f'El mapa usa aristas desconocidas para {acceso}')
            if par not in conexiones:
                raise ValueError(f'Las aristas del acceso {acceso} no están conectadas')
        for row in rows:
            if row['acceso'] not in mapping:
                raise ValueError(f'Acceso sin correspondencia: {row["acceso"]}')

        # Reutilizar la configuración base y publicar los archivos juntos.
        config = parse(DEMO / 'base.sumocfg').getroot()
        salida.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=salida.parent, prefix='.sumo-') as temporal:
            preparado = Path(temporal) / 'escenario'
            preparado.mkdir()
            if demo and self.generar_demo:
                _, mapping = demo_network(preparado)
            else:
                shutil.copyfile(self.red, preparado / 'red.net.xml')
            duracion = build_routes(rows, mapping, preparado)
            config.find('time/end').set('value', str(duracion + 900))
            write_xml(preparado / 'base.sumocfg', config)
            if salida.exists():
                salida.rmdir()  # Solo se reemplaza una carpeta vacía.
            preparado.rename(salida)

        return EscenarioSUMO(salida / 'red.net.xml', salida / 'flujos.rou.xml',
                             salida / 'base.sumocfg', self.semilla, self.demanda,
                             sum(row['cantidad'] for row in rows), any(marcas), demo)


def ejecutar_escenario(escenario):
    out = escenario.config.parent
    command = [binary('sumo'), '-c', str(escenario.config), '--seed', str(escenario.semilla),
               '--no-step-log', 'true', '--duration-log.disable', 'true']
    subprocess.run(command, cwd=out, check=True)
    completed, unfinished = summarize(out / 'tripinfo.xml', out / 'demora_base.csv', escenario.prueba)
    status = {
        'prueba': escenario.prueba,
        'geometria': 'SINTETICA' if escenario.demo else 'SUMINISTRADA_NO_VALIDADA',
        'semilla': escenario.semilla, 'esperados': escenario.esperados,
        'completados': completed, 'incompletos': unfinished,
        'criterio': 'timeLoss promedio por acceso, sin incluir departDelay',
        'version_sumo': subprocess.check_output([binary('sumo'), '--version'], text=True).splitlines()[0],
        'fuente_conteos': str(escenario.demanda), 'comando': command, 'validacion_piloto_real': False,
    }
    (out / 'ejecucion.json').write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding='utf-8')
    if unfinished or completed != escenario.esperados:
        raise SystemExit('CORRIDA INCOMPLETA: revisar vehículos no completados antes de interpretar demora')
    print('Corrida terminada. Ver demora_base.csv y ejecucion.json. Esto no valida el piloto real.')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--counts', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--demo', action='store_true')
    p.add_argument('--network', type=Path)
    p.add_argument('--access-map', type=Path)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--prepare-only', action='store_true', help='Preparar los archivos sin ejecutar SUMO')
    a = p.parse_args()

    builder = EscenarioSUMOBuilder().con_demanda(a.counts).con_salida(a.out).con_semilla(a.seed)
    if a.demo:
        builder.con_red_demo(generar=not a.prepare_only)
    elif a.network and a.access_map:
        builder.con_red(a.network, a.access_map)
    else:
        p.error('Para red real proporcionar --network y --access-map; el plan fijo debe estar en la red')
    try:
        escenario = builder.construir()
    except (OSError, ValueError, KeyError, ParseError) as error:
        p.error(str(error))
    if a.prepare_only:
        print(f'Escenario preparado en {escenario.config}. Semilla: {escenario.semilla}.')
        return
    ejecutar_escenario(escenario)


if __name__ == '__main__':
    main()
