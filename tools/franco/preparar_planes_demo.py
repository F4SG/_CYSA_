"""Reemplaza las cinco propuestas sintéticas del banco local para practicar autorización."""

import argparse
import csv
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
ACCESOS = ('N', 'S', 'E', 'W')
DATOS = ROOT / 'data/franco/ejemplos/planes_autorizacion_demo.csv'
sys.path[:0] = [str(ROOT / part) for part in ('', 'shared', 'backend', 'inventario', 'simulacion', 'controlador')]

from operacion.almacen import Almacen
from operacion.planes import proponer
from operacion.simular import buscar
from operacion.sqlserver import configuracion_aprobada


def configurar(install):
    settings = install / 'webiii-sql.json'
    server = json.loads(settings.read_text(encoding='utf-8-sig'))['Instancia'] if settings.exists() else 'localhost'
    os.environ.update(CYSA_SQL_DATABASE='CYSA_Control_S2', CYSA_SQL_SERVER=server)


def conteos(profile, start):
    return [dict(interseccion='DEMO_INT_01', acceso=access, carril=access+'_0', clase='auto',
                 cantidad=int(profile[access]), inicio=start+timedelta(seconds=30*interval),
                 fin=start+timedelta(seconds=30*(interval+1)), prueba=True)
            for interval in range(10) for access in ACCESOS]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_install = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'CYSA'
    parser.add_argument('--instalacion', type=Path, default=default_install,
                        help='Carpeta de datos del lanzador que contiene workspace')
    parser.add_argument('--solo-validar', action='store_true', help='Evalúa en SUMO sin guardar planes')
    parser.add_argument('--conservar-vigentes', action='store_true',
                        help='Conserva un lote idéntico, pendiente y con tiempo para decidir')
    options = parser.parse_args()
    try:
        configurar(options.instalacion.resolve())
        with DATOS.open(encoding='utf-8', newline='') as file:
            profiles = list(csv.DictReader(file))
        store = Almacen()
        settings = configuracion_aprobada()
        if len(profiles) != 5:
            raise ValueError('El CSV debe definir cinco casos de ejemplo.')
        start = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=5)
        end = start + timedelta(minutes=5)
        prepared = []
        for number, profile in enumerate(profiles, 1):
            ident = uuid4()
            rows = conteos(profile, start)
            plan = proponer(rows, configuracion=settings)
            plan['plan_id'] = f'EJEMPLO_{number}_{ident.hex}'
            plan, validation = buscar(rows, plan)
            if not validation['aprobada']:
                raise ValueError(f"{profile['caso']} quedó fuera de los umbrales de SUMO: {validation['motivos']}")
            print(f"{profile['caso']}: mejora simulada {validation['mejora_porcentaje']:.2f} %", flush=True)
            origin = dict(caso=profile['caso'], desde=start.isoformat(), hasta=end.isoformat(),
                          autos_por_acceso={access: int(profile[access]) for access in ACCESOS},
                          intervalo_s=30, prueba=True)
            prepared.append((ident, plan, validation, origin))
        if options.solo_validar:
            return
        changed = store.reemplazar_ejemplos(prepared, conservar_vigentes=options.conservar_vigentes)
        print('Se cargaron cinco propuestas de práctica validadas.' if changed else
              'Se conservaron las cinco propuestas vigentes, con sus identificadores.', flush=True)
    except (KeyError, OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f'No se pudieron preparar los casos: {error}\n')


if __name__ == '__main__':
    main()
