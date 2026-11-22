"""Carga cinco demandas sintéticas en el banco local para practicar autorización."""

import argparse
import csv
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
ACCESOS = ('N', 'S', 'E', 'W')
DATOS = ROOT / 'data/franco/ejemplos/planes_autorizacion_demo.csv'
sys.path[:0] = [str(ROOT / part) for part in ('', 'shared', 'backend', 'inventario', 'simulacion', 'controlador')]

from cysa.contracts import Conteo
from cysa.mqtt import Publisher
from operacion.almacen import Almacen
from operacion.entorno import cargar
from operacion.generar import generar
from operacion.planes import proponer
from operacion.simular import buscar
from operacion.sqlserver import configuracion_aprobada


def configurar(install):
    workspace = install / 'workspace'
    settings = install / 'webiii-sql.json'
    server = json.loads(settings.read_text(encoding='utf-8-sig'))['Instancia'] if settings.exists() else 'localhost'
    os.environ.update(CYSA_INSTALACION_DIR=str(workspace), CYSA_SQL_DATABASE='CYSA_Control_S2',
                      CYSA_SQL_SERVER=server)
    cargar()
    credentials = workspace / 'infra/runtime/clientes/prueba.env'
    if not credentials.is_file():
        raise ValueError('Primero configura e inicia CYSA desde el lanzador.')
    for line in credentials.read_text(encoding='utf-8-sig').splitlines():
        key, separator, value = line.partition('=')
        if separator and key.strip() in {'MQTT_CA', 'MQTT_HOST', 'MQTT_PORT', 'MQTT_USER', 'MQTT_PASSWORD'}:
            os.environ[key.strip()] = value.strip()
    if os.environ.get('MQTT_HOST') not in ('localhost', '127.0.0.1'):
        raise ValueError('Los ejemplos requieren el broker de esta PC.')


def ventanas_libres(store, count):
    corte = (int(datetime.now(timezone.utc).timestamp()) // 300) * 300
    result = []
    for offset in range(2, 26):
        end = datetime.fromtimestamp(corte - 300 * offset, timezone.utc)
        start = end - timedelta(minutes=5)
        if not store.counts(start, end, 'DEMO_INT_01', None, True):
            result.append((start, end))
            if len(result) == count:
                return result
    raise ValueError('No hay suficientes ventanas vacías en las últimas dos horas.')


def conteos(profile, start):
    tag = uuid4().hex[:8]
    return [Conteo(mensaje_id=uuid4(), interseccion='DEMO_INT_01', acceso=access,
                   carril=f'DEMO_PLAN_{tag}_{access}', clase='auto', cantidad=int(profile[access]),
                   inicio=start+timedelta(seconds=30*interval), fin=start+timedelta(seconds=30*(interval+1)),
                   prueba=True) for interval in range(10) for access in ACCESOS]


def publicar(publisher, store, events, start, end):
    for event in events:
        publisher.publish(event)
    expected = {str(event.mensaje_id) for event in events}
    for _ in range(30):
        persisted = store.counts(start, end, 'DEMO_INT_01', None, True)
        if expected <= {str(row['mensaje_id']) for row in persisted}:
            break
        time.sleep(1)
    else:
        raise ValueError('El banco no recibió todos los conteos. Comprueba que el sistema esté iniciado.')
    plan = generar(store, start, end)
    if not plan or plan['estado'] != 'validado' or not expected <= set(plan['origen']['mensajes']):
        raise ValueError('La propuesta guardada del caso no quedó validada con los datos esperados.')
    return plan['documento']['plan_id']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_install = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'CYSA'
    parser.add_argument('--instalacion', type=Path, default=default_install,
                        help='Carpeta de datos del lanzador que contiene workspace')
    parser.add_argument('--solo-validar', action='store_true', help='Evalúa en SUMO sin cargar conteos ni guardar planes')
    options = parser.parse_args()
    try:
        configurar(options.instalacion.resolve())
        with DATOS.open(encoding='utf-8', newline='') as file:
            profiles = list(csv.DictReader(file))
        store = Almacen()
        settings = configuracion_aprobada()
        windows = ventanas_libres(store, len(profiles))
        prepared = []
        for profile, (start, end) in zip(profiles, windows, strict=True):
            events = conteos(profile, start)
            rows = [event.model_dump() for event in events]
            _, validation = buscar(rows, proponer(rows, configuracion=settings))
            if not validation['aprobada']:
                raise ValueError(f"{profile['caso']} quedó fuera de los umbrales de SUMO: {validation['motivos']}")
            print(f"{profile['caso']}: mejora simulada {validation['mejora_porcentaje']:.2f} %", flush=True)
            prepared.append((profile['caso'], events, start, end))
        if options.solo_validar:
            return
        with Publisher('cysa-planes-demo-' + uuid4().hex[:8]) as publisher:
            for case, events, start, end in prepared:
                plan_id = publicar(publisher, store, events, start, end)
                print(f'{case}: {plan_id} validado', flush=True)
    except (KeyError, OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f'No se pudieron preparar los casos: {error}\n')


if __name__ == '__main__':
    main()
