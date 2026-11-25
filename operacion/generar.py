"""Propuestas asincrónicas del banco y escenarios de laboratorio por consola."""

import argparse
import logging
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5

from .planes import proponer
from .sqlserver import configuracion_aprobada

log = logging.getLogger('cysa.planificador')
VENTANA = 300


def generar(store, desde, hasta, *, identificador=None):
    if desde.tzinfo is None or hasta.tzinfo is None or not timedelta(0) < hasta - desde <= timedelta(hours=1):
        raise ValueError('Usa un intervalo con zona horaria de hasta una hora')
    id_plan = identificador or uuid4()
    if identificador and (guardado := store.obtener(id_plan)):
        return guardado
    filas = store.counts(desde, hasta, 'DEMO_INT_01', None, True, 1000, 0)
    cantidad = sum(x['cantidad'] for x in filas)
    if not cantidad:
        return None
    if len(filas) >= 1000 or cantidad > 3000:
        raise ValueError('Demanda demasiado grande para el banco; acorta el intervalo')
    candidato = proponer(filas, configuracion=configuracion_aprobada())
    candidato['plan_id'] = 'OP_' + id_plan.hex
    from .simular import evaluar
    validacion = evaluar(filas, candidato)
    origen = dict(desde=desde.isoformat(), hasta=hasta.isoformat(),
                  mensajes=[str(x['mensaje_id']) for x in filas])
    actor = 'servicio-planificador' if identificador else 'consola-banco'
    return store.guardar(id_plan, candidato, validacion, origen, actor)


def planificar(store, stop):
    procesada = None
    while not stop.wait(15):
        timestamp = int(datetime.now(timezone.utc).timestamp()) - 30
        ventana = timestamp // VENTANA * VENTANA
        if ventana == procesada:
            continue
        hasta = datetime.fromtimestamp(ventana, timezone.utc)
        desde = hasta - timedelta(seconds=VENTANA)
        identificador = uuid5(NAMESPACE_URL, f'cysa:DEMO_INT_01:webster:{ventana}')
        try:
            if generar(store, desde, hasta, identificador=identificador) is None:
                continue
        except ValueError as error:
            log.warning('Ventana de propuesta descartada: %s', error)
        except Exception:
            log.exception('No se pudo evaluar la ventana de conteos; se reintentará')
            continue
        procesada = ventana


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('desde', type=datetime.fromisoformat)
    parser.add_argument('hasta', type=datetime.fromisoformat)
    args = parser.parse_args()
    from .entorno import cargar
    from .almacen import Almacen
    cargar()
    store = Almacen()
    store.ready()
    try:
        plan = generar(store, args.desde, args.hasta)
    except ValueError as error:
        parser.error(str(error))
    if plan is None:
        parser.error('No hay conteos de prueba en el intervalo')
    print(plan['documento']['plan_id'], plan['estado'])


if __name__ == '__main__':
    main()
