"""Ejecuta el controlador emulado.

Ejemplos (desde la raíz del repositorio, con PYTHONPATH=shared;controlador):
  python -m cysa_controlador.run --config controlador/config/demo_int_01.yaml --sin-placa --simular-corte 30:120
  python -m cysa_controlador.run --config controlador/config/demo_int_01.yaml --puerto COM3 --mqtt
"""
import argparse
import os
import time
from datetime import datetime
from pathlib import Path

from .centro import CentroMQTT, CentroSimulado, SinCentro
from .controlador import ControladorEmulado
from .mmu import INTERVALO_ENVIO_S, MMUSerial, MMUSimulada
from .plan import cargar_interseccion, cargar_plan

PERIODO_S = 0.1
PUBLICAR_CADA_S = 10.0          # RF-04: estado cada 30 s como máximo
NOMBRES = {'G': 'VERDE', 'Y': 'AMBAR', 'R': 'ROJO'}


def cargar_config(ruta):
    import yaml
    datos = yaml.safe_load(Path(ruta).read_text(encoding='utf-8'))
    if not isinstance(datos, dict):
        raise ValueError('La configuración debe ser un mapa YAML')
    cruce = cargar_interseccion(datos)
    centro = cargar_plan(datos['plan_centro']['plan_id'], datos['plan_centro']['fases'], cruce)
    local = cargar_plan(datos['plan_local']['plan_id'], datos['plan_local']['fases'], cruce)
    return datos, cruce, centro, local


REPO = Path(__file__).resolve().parents[2]
CREDENCIALES = REPO / 'infra/runtime/clientes/emulador.env'


def cargar_credenciales(ruta):
    """Carga MQTT_HOST, MQTT_USER, etc. del archivo generado en la instalación (no versionado)."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f'No existe {ruta}. Ejecutar la instalación del README para generar las credenciales.')
    for linea in ruta.read_text(encoding='utf-8-sig').splitlines():
        if linea.strip() and not linea.lstrip().startswith('#') and '=' in linea:
            clave, valor = linea.split('=', 1)
            os.environ[clave.strip()] = valor.strip()


def parse_corte(texto):
    desde, _, hasta = texto.partition(':')
    desde = float(desde)
    hasta = float(hasta) if hasta else None
    if desde < 0 or (hasta is not None and hasta <= desde):
        raise argparse.ArgumentTypeError('Usar INICIO:FIN en segundos, con FIN mayor que INICIO (FIN opcional)')
    return desde, hasta


def describir(ctrl):
    if ctrl.intermitente:
        return f'INTERMITENTE | {ctrl.modo.motivo}'
    luces = ' '.join(f'{g}={NOMBRES[l]}' for g, l in zip(ctrl.cruce.grupos, ctrl.luces))
    texto = f'{ctrl.modo.nombre} | plan {ctrl.plan_id} | fase {ctrl.fase_id} | {luces}'
    pendiente = ctrl.secuenciador.pendiente
    if pendiente is not None:
        texto += f' (pasa a {pendiente.plan_id} al terminar el próximo todo rojo)'
    return texto


def ejecutar(ctrl, mmu, centro, *, reloj=time.monotonic, dormir=time.sleep, duracion_s=None, stop_file=None, imprimir=print,receptor=None):
    inicio = reloj()
    visto = None
    ultimo_envio = ultimo_estado = float('-inf')
    anterior = previo = None
    while duracion_s is None or reloj() - inicio < duracion_s:
        if stop_file and Path(stop_file).exists():
            break
        ahora = reloj()
        latido = centro.ultimo_latido(ahora)
        if latido is not None and latido != visto:
            visto = latido
            ctrl.latido(latido)
        ctrl.tick(ahora)
        for mensaje in mmu.mensajes(ahora):
            if mensaje.startswith('FALLA:'):
                ctrl.falla_mmu(mensaje, ahora)
        if receptor:
            for raw in centro.recibir_planes():
                try:receptor.recibir(raw)
                except (ValueError,KeyError,TypeError):imprimir('Plan descartado: firma, contrato o vigencia no válidos')
            receptor.tick()
        if not ctrl.intermitente and (ctrl.luces != anterior or ahora - ultimo_envio >= INTERVALO_ENVIO_S):
            mmu.enviar(ctrl.luces, ahora)
            ultimo_envio = ahora
        actual = (ctrl.modo.nombre, ctrl.plan_id, ctrl.fase_id)
        if actual != previo or ahora - ultimo_estado >= PUBLICAR_CADA_S:
            if actual != previo:
                imprimir(f'[{datetime.now():%H:%M:%S}] {describir(ctrl)}')
            centro.publicar_estado(ctrl.estado())
            previo, ultimo_estado = actual, ahora
        anterior = ctrl.luces
        dormir(PERIODO_S)


def main(argv=None):
    p = argparse.ArgumentParser(description='Controlador semafórico emulado (banco de pruebas, Sprint 2)')
    p.add_argument('--config', type=Path, required=True)
    placa = p.add_mutually_exclusive_group(required=True)
    placa.add_argument('--puerto', help='Puerto serial de la placa Arduino (COM3, /dev/ttyUSB0...)')
    placa.add_argument('--sin-placa', action='store_true', help='Usar el MMU simulado en software')
    centro = p.add_mutually_exclusive_group()
    centro.add_argument('--mqtt', action='store_true', help='Recibir latidos y publicar el estado por MQTT')
    centro.add_argument('--simular-corte', type=parse_corte, metavar='INICIO:FIN',
                        help='Centro simulado que deja de latir entre INICIO y FIN segundos (FIN opcional)')
    centro.add_argument('--centro-simulado', action='store_true', help='Centro simulado que late siempre (sin broker)')
    p.add_argument('--credenciales', type=Path, default=CREDENCIALES, help='Archivo .env del usuario MQTT emulador')
    p.add_argument('--duracion', type=float, help='Detener después de N segundos')
    p.add_argument('--stop-file', type=Path, help='Detener cuando exista este archivo')
    p.add_argument('--clave-planes',type=Path,help='Clave del banco para recibir planes firmados por MQTT')
    p.add_argument('--recibos',type=Path,default=REPO/'resultados/controlador/recibos.json')
    a = p.parse_args(argv)
    try:
        datos, cruce, plan_centro, plan_local = cargar_config(a.config)
    except (KeyError, ValueError) as error:
        p.error(f'Configuración inválida: {error}')
    ahora = time.monotonic()
    ctrl = ControladorEmulado(cruce, plan_centro, plan_local, datos.get('prueba'), ahora)
    if a.mqtt:
        try:
            cargar_credenciales(a.credenciales)
        except FileNotFoundError as error:
            p.error(str(error))
        enlace = CentroMQTT()
    elif a.simular_corte is not None or a.centro_simulado:
        enlace = CentroSimulado(ahora, a.simular_corte)
    else:
        enlace = SinCentro()
    try:
        mmu = MMUSimulada(cruce) if a.sin_placa else MMUSerial(a.puerto, cruce)
    except (OSError, RuntimeError, TimeoutError) as error:
        enlace.cerrar()
        p.error(f'No se pudo usar la placa: {error}')
    print(f'Controlador {cruce.interseccion}: grupos {", ".join(cruce.grupos)}. Ctrl+C para detener.')
    try:
        receptor=None
        if a.clave_planes:
            if not a.mqtt:raise ValueError('La recepción de planes requiere --mqtt')
            from .recepcion import ReceptorPlanes
            from operacion.mensajes import clave
            receptor=ReceptorPlanes(ctrl,clave(a.clave_planes),a.recibos,enlace.confirmar_plan)
        ejecutar(ctrl, mmu, enlace, duracion_s=a.duracion, stop_file=a.stop_file,receptor=receptor)
    except KeyboardInterrupt:
        pass
    finally:
        mmu.cerrar()
        enlace.cerrar()
    print('Controlador detenido. Sin mensajes de la PC, la placa pasa a intermitente en 1 s.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
