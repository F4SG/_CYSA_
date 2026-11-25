"""Genera conteos de práctica a partir de detectores virtuales en SUMO."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random
import subprocess
import sys
from uuid import UUID, uuid5
from xml.etree.ElementTree import Element, SubElement, parse

from sumo_gui import gui_binary
from simulacion.sumo_base import demo_network, write_xml


PERIODO = 30
PERIODO_DEMANDA = 300
DURACION = 24 * 3600
BOLIVIA = timezone(timedelta(hours=-4))
SEMILLA = 42
CARRILES = ('E_0', 'N_0', 'N_1', 'N_2', 'S_0', 'W_0')
CLASES = ('auto', 'micro', 'moto')
CONFIG = 'practica.sumocfg'
SALIDA = 'detectores.xml'


def preparar_escenario(carpeta, inicio, netconvert):
    red, accesos = demo_network(carpeta, carriles_norte=3, netconvert=netconvert)
    rutas = Element('routes')
    for clase, tipo, longitud in [('auto', 'passenger', '5'), ('micro', 'bus', '10'),
                                  ('moto', 'motorcycle', '2')]:
        SubElement(rutas, 'vType', id=clase, vClass=tipo, length=longitud, color={
            'auto': '0,180,255', 'micro': '255,170,0', 'moto': '80,220,100',
        }[clase])
    for acceso, aristas in accesos.items():
        SubElement(rutas, 'route', id=acceso, edges=' '.join(aristas))

    azar = Random(SEMILLA)
    for segundo in range(0, DURACION, PERIODO_DEMANDA):
        hora = (inicio + timedelta(seconds=segundo)).astimezone(BOLIVIA).hour
        demanda = 1.6 if hora in (7, 8, 12, 13, 17, 18, 19) else 0.45 if hora < 6 or hora >= 22 else 1
        for carril in CARRILES:
            acceso, numero = carril.split('_')
            for clase, base in [('auto', 12), ('micro', 2), ('moto', 6)]:
                cantidad = max(0, round(base * demanda) + azar.randint(-1, 1))
                if cantidad:
                    SubElement(rutas, 'flow', id=f'{segundo}_{carril}_{clase}', type=clase,
                               route=acceso, departLane=numero, begin=str(segundo),
                               end=str(segundo + PERIODO_DEMANDA), number=str(cantidad))
    write_xml(carpeta / 'flujos.rou.xml', rutas)

    detectores = Element('additional')
    for carril in CARRILES:
        acceso, numero = carril.split('_')
        for clase in CLASES:
            SubElement(detectores, 'inductionLoop', id=f'{carril}:{clase}',
                       lane=f'{acceso}_in_{numero}', pos='-12', period=str(PERIODO),
                       vTypes=clase, file=SALIDA)
    write_xml(carpeta / 'detectores.add.xml', detectores)

    config = Element('configuration')
    entrada = SubElement(config, 'input')
    SubElement(entrada, 'net-file', value=red.name)
    SubElement(entrada, 'route-files', value='flujos.rou.xml')
    SubElement(entrada, 'additional-files', value='detectores.add.xml')
    SubElement(SubElement(config, 'time'), 'end', value=str(DURACION))
    SubElement(SubElement(config, 'random_number'), 'seed', value=str(SEMILLA))
    SubElement(SubElement(config, 'processing'), 'time-to-teleport', value='-1')
    write_xml(carpeta / CONFIG, config)


def exportar_conteos(carpeta, lote, inicio):
    datos = {}
    for intervalo in parse(carpeta / SALIDA).getroot().iterfind('interval'):
        segundo = int(float(intervalo.attrib['begin']))
        clave = (segundo, intervalo.attrib['id'])
        if clave in datos or float(intervalo.attrib['end']) != segundo + PERIODO:
            raise ValueError('SUMO devolvió intervalos duplicados o incompletos.')
        datos[clave] = int(intervalo.attrib['nVehContrib'])

    esperados = [(segundo, carril, clase) for segundo in range(0, DURACION, PERIODO)
                 for carril in CARRILES for clase in CLASES]
    if set(datos) != {(s, f'{c}:{t}') for s, c, t in esperados} or not any(datos.values()):
        raise ValueError('La medición de SUMO está vacía o le faltan intervalos.')

    with (carpeta / 'conteos.csv').open('w', encoding='utf-8', newline='') as archivo:
        writer = csv.writer(archivo, lineterminator='\n')
        writer.writerow(('mensaje_id', 'interseccion', 'acceso', 'carril', 'clase',
                         'cantidad', 'inicio', 'fin'))
        for indice, (segundo, carril, clase) in enumerate(esperados):
            detector = f'{carril}:{clase}'
            desde = inicio + timedelta(seconds=segundo)
            hasta = desde + timedelta(seconds=PERIODO)
            # El primer intervalo de E_0/auto identifica el escenario en PostgreSQL.
            mensaje = lote if indice == 0 else uuid5(lote, f'{segundo}:{detector}')
            writer.writerow((mensaje, 'DEMO_INT_01', carril[0], carril, clase,
                             datos[segundo, detector], desde.isoformat(), hasta.isoformat()))
    return sum(datos.values())


def generar(carpeta, ahora=None):
    ejecutable = gui_binary()
    lote = UUID(carpeta.name)
    ahora = ahora or datetime.now(timezone.utc)
    fin = datetime.fromtimestamp(int(ahora.timestamp()) // PERIODO_DEMANDA * PERIODO_DEMANDA, timezone.utc)
    inicio = fin - timedelta(seconds=DURACION)
    carpeta.mkdir(parents=True, exist_ok=False)
    preparar_escenario(carpeta, inicio, ejecutable.with_name('netconvert.exe'))
    subprocess.run([ejecutable.with_name('sumo.exe'), '-c', CONFIG, '--no-step-log', 'true'],
                   cwd=carpeta, check=True)
    total = exportar_conteos(carpeta, lote, inicio)
    print(f'SUMO midió {total} vehículos en DEMO_INT_01, del {inicio.astimezone(BOLIVIA):%d/%m %H:%M} '
          f'al {fin.astimezone(BOLIVIA):%d/%m %H:%M} (Bolivia).')
    return total


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('carpeta', type=Path)
    args = parser.parse_args()
    try:
        generar(args.carpeta)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
