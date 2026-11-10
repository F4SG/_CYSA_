from dataclasses import FrozenInstanceError
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
import yaml

from simulacion import sumo_base as escenario_sumo
from simulacion.sumo_base import EscenarioSUMOBuilder
from cysa.contracts import Conteo, Estado, PlanBorrador
from cysa_detector import entorno, run
from cysa_detector.entorno import FabricaLaboratorio, FabricaSombra, preparar_entorno
from cysa_detector.run import CreadorCamara, CreadorVideo, FuenteCamara, FuenteVideo
from cysa_detector.counter import Lane, LineCounter
from tools.cristhian import detector


REPO = Path(__file__).resolve().parents[1]
FLUJOS = REPO / 'data/leonardo/ejemplos/flujos_DEMO.csv'


@pytest.fixture
def conteo():
    inicio = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    return Conteo(mensaje_id=uuid4(), interseccion='DEMO_INT_01', acceso='N',
                  carril='N_0', clase='auto', cantidad=1, inicio=inicio,
                  fin=inicio + timedelta(seconds=30), prueba=True)


def test_prototype_aisla_carriles_y_descarta_credenciales():
    base = {'source': 0, 'interseccion': 'BASE', 'auto_carriles': True,
            'configuracion_verificada': True, 'mqtt_password': 'prueba-ficticia',
            'lanes': [{'a': [.1, .2], 'polygon': [[.3, .4]]}]}
    fuente = detector.parse_source('1')
    a = detector.clonar_perfil(base, 'INT_A', fuente)
    b = detector.clonar_perfil(base, 'INT_B', fuente)
    a['lanes'][0]['polygon'][0][0] = .9
    assert b['lanes'] == base['lanes']
    assert base['lanes'][0]['polygon'] == [[.3, .4]]
    assert 'mqtt_password' not in a
    assert a['interseccion'] == 'INT_A' and a['source'] == 1
    assert a['configuracion_verificada'] is False and a['auto_carriles'] is False


def test_cli_clona_un_yaml_y_protege_el_destino(monkeypatch, tmp_path):
    base = REPO / 'deteccion/config/camara_usb.yaml'
    salida = tmp_path / 'nueva cámara.yaml'
    argv = ['detector.py', 'clonar-perfil', '--config', str(base),
            '--interseccion', 'INT_NUEVA', '--fuente', 'camara:USB',
            '--salida', str(salida)]
    monkeypatch.setattr(sys, 'argv', argv)
    assert detector.main() == 0
    original = salida.read_bytes()
    datos = yaml.safe_load(original)
    assert datos['camera_name'] == 'USB'
    assert datos['interseccion'] == 'INT_NUEVA'
    assert datos['configuracion_verificada'] is False
    with pytest.raises(SystemExit) as error:
        detector.main()
    assert error.value.code == 2
    assert salida.read_bytes() == original


def test_la_sesion_no_reusa_carriles_de_otra_interseccion(monkeypatch, tmp_path):
    monkeypatch.setattr(detector, 'RUNTIME', tmp_path / 'sesiones')
    perfiles = [tmp_path / nombre for nombre in ('base', 'nueva')]
    for ruta, nombre in zip(perfiles, ('BASE', 'NUEVA')):
        ruta.mkdir()
        (ruta / 'camara.yaml').write_text(
            yaml.safe_dump(dict(interseccion=nombre, source=0,
                                configuracion_verificada=nombre == 'BASE')),
            encoding='utf-8')
    fuente = detector.parse_source('0')
    detector.session_config(perfiles[0] / 'camara.yaml', fuente)
    sesion, marcar = detector.session_config(perfiles[1] / 'camara.yaml', fuente)
    assert marcar
    assert yaml.safe_load(sesion.read_text(encoding='utf-8'))['configuracion_verificada'] is False


@pytest.mark.parametrize(('creador', 'producto', 'source'),
                         [(CreadorCamara, FuenteCamara, 0),
                          (CreadorVideo, FuenteVideo, 'video.mp4')])
def test_factory_method_publica_contrato_y_cierra_al_fallar(
        monkeypatch, creador, producto, source, conteo):
    liberaciones = []
    cap = SimpleNamespace(release=lambda: liberaciones.append('liberada'))
    monkeypatch.setitem(sys.modules, 'ultralytics', SimpleNamespace(YOLO=lambda _: object()))
    monkeypatch.setattr(run, 'open_source', lambda *_: cap)

    def eventos(*_):
        yield conteo

    monkeypatch.setattr(run.CameraSource, '_loop', eventos)
    fabrica = creador(dict(source=source, interseccion=conteo.interseccion,
                           prueba=True, lanes=[dict(acceso='N', carril='N_0',
                           a=[.1, .5], b=[.9, .5], direction='both')],
                           class_map={2: 'auto'}))
    assert isinstance(fabrica.crear_fuente(), producto)
    publicados = []
    assert fabrica.ejecutar(publicados.append) is False
    assert publicados == [conteo]

    def falla(_):
        raise RuntimeError('publicación fallida')

    with pytest.raises(RuntimeError, match='publicación fallida'):
        fabrica.ejecutar(falla)
    assert liberaciones == ['liberada', 'liberada']


def test_builder_crea_escenarios_independientes(tmp_path):
    builder = EscenarioSUMOBuilder().con_red_demo().con_demanda(FLUJOS)
    primero = builder.con_salida(tmp_path / 'primero').construir()
    segundo = builder.con_semilla(12).con_salida(tmp_path / 'segundo').construir()
    assert primero.semilla == 42 and segundo.semilla == 12
    assert primero.red.parent != segundo.red.parent
    assert all(ruta.is_file() for ruta in (primero.red, primero.rutas, primero.config))
    assert not (primero.red.parent / 'tripinfo.xml').exists()
    with pytest.raises(FrozenInstanceError):
        primero.semilla = 5


def test_builder_valida_el_mapa_antes_de_escribir(tmp_path):
    accesos = tmp_path / 'accesos.csv'
    accesos.write_text('acceso,entrada,salida\nN,N_in,S_out\n', encoding='utf-8')
    salida = tmp_path / 'no-generar'
    builder = (EscenarioSUMOBuilder().con_red(escenario_sumo.DEMO / 'red.net.xml', accesos)
               .con_demanda(FLUJOS).con_salida(salida))
    with pytest.raises(ValueError, match='Acceso sin correspondencia'):
        builder.construir()
    assert not salida.exists()


def test_builder_limpia_archivos_parciales(monkeypatch, tmp_path):
    def falla(_rows, _mapping, carpeta):
        assert (carpeta / 'red.net.xml').exists()
        raise OSError('sin espacio')

    monkeypatch.setattr(escenario_sumo, 'build_routes', falla)
    builder = (EscenarioSUMOBuilder().con_red_demo().con_demanda(FLUJOS)
               .con_salida(tmp_path / 'no-generar'))
    with pytest.raises(OSError, match='sin espacio'):
        builder.construir()
    assert not list(tmp_path.iterdir())


def test_abstract_factory_limita_laboratorio_a_eventos_y_planes_de_prueba(conteo):
    fabrica = FabricaLaboratorio(conteo.interseccion, [conteo])
    fuente, controlador = preparar_entorno(fabrica)
    assert list(fuente.eventos()) == [conteo]
    assert controlador.estado().prueba is True
    plan = PlanBorrador(plan_id='P1', interseccion=conteo.interseccion,
                        fases=[dict(fase_id='N', duracion_s=10)], prueba=True)
    for cambios in ({'prueba': False}, {'interseccion': 'OTRA'}):
        with pytest.raises(ValueError):
            controlador.enviar_plan(plan.model_copy(update=cambios))
    assert controlador.estado().plan_activo == 'SIN_PLAN'
    controlador.enviar_plan(plan)
    assert controlador.estado().plan_activo == 'P1'
    assert controlador.estado().fase_actual == 'N'
    with pytest.raises(ValueError):
        preparar_entorno(FabricaLaboratorio(
            conteo.interseccion, [conteo.model_copy(update={'prueba': False})]))


def test_contadores_de_dos_camaras_mantienen_estado_independiente():
    carril = Lane('N', 'N_0', (.1, .5), (.9, .5))
    a = LineCounter([carril])
    b = LineCounter([carril])
    a.observe(7, 'auto', (.5, .3), 1)
    a.observe(7, 'auto', (.5, .7), 2)
    assert a.snapshot() == {('N', 'N_0', 'auto'): 1}
    assert b.snapshot() == {}
    b.observe(7, 'auto', (.5, .3), 1)
    b.observe(7, 'auto', (.5, .7), 2)
    assert b.snapshot() == {('N', 'N_0', 'auto'): 1}


def test_cli_detector_usa_creadores_y_anexa_sin_duplicar_cabecera(monkeypatch, tmp_path, conteo):
    fuentes = []
    publicados = []

    def emitir(self):
        fuentes.append((type(self), self.inicio_video))
        yield conteo.model_copy(update={'mensaje_id': uuid4()})

    class Publicador:
        def __init__(self, _):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def publish(self, evento):
            publicados.append(evento)

    monkeypatch.setattr(run.CameraSource, 'eventos', emitir)
    monkeypatch.setattr(run, 'Publisher', Publicador)
    perfil = tmp_path / 'perfil.yaml'
    salida = tmp_path / 'conteos.csv'
    inicio = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    for source, opciones in ((0, []), ('video.mp4', ['--inicio-video', inicio.isoformat()])):
        perfil.write_text(yaml.safe_dump(dict(source=source, configuracion_verificada=True)), encoding='utf-8')
        monkeypatch.setattr(sys, 'argv', ['run', '--config', str(perfil),
                            '--salida-conteos', str(salida), *opciones])
        assert run.main() == 0

    with salida.open(encoding='utf-8', newline='') as stream:
        filas = list(csv.DictReader(stream))
    assert fuentes == [(FuenteCamara, None), (FuenteVideo, inicio)]
    assert [fila['mensaje_id'] for fila in filas] == [str(evento.mensaje_id) for evento in publicados]

def test_cli_entornos_compone_familias_y_valida_la_marca(monkeypatch, tmp_path, conteo):
    salida = tmp_path / 'laboratorio.jsonl'
    datos = REPO / 'data/franco/ejemplos'
    monkeypatch.setattr(sys, 'argv', ['entorno', 'laboratorio', '--conteo', str(datos / 'conteo_DEMO.json'),
                        '--plan', str(datos / 'plan_borrador_DEMO.json'), '--salida', str(salida)])
    assert entorno.main() == 0
    estado_lab, conteo_lab = [json.loads(linea) for linea in salida.read_text(encoding='utf-8').splitlines()]
    assert estado_lab['datos']['plan_activo'] == 'DEMO_FIJO'
    assert conteo_lab['datos']['prueba'] is True

    def eventos(self):
        assert isinstance(self, FuenteVideo)
        yield conteo

    monkeypatch.setattr(run.CameraSource, 'eventos', eventos)
    estado = Estado.model_validate_json((datos / 'estado_DEMO.json').read_bytes())
    config = dict(source='video.mp4', interseccion=estado.interseccion,
                  configuracion_verificada=True, prueba=True)
    fabrica = FabricaSombra(config, estado)
    _, controlador = preparar_entorno(fabrica)
    with pytest.raises(NotImplementedError, match='Activación deshabilitada'):
        controlador.enviar_plan(PlanBorrador.model_validate_json((datos / 'plan_borrador_DEMO.json').read_bytes()))

    perfil = tmp_path / 'perfil.yaml'
    perfil.write_text(yaml.safe_dump(config), encoding='utf-8')
    salida = tmp_path / 'sombra.jsonl'
    argv = ['entorno', 'sombra', '--config', str(perfil), '--estado', str(datos / 'estado_DEMO.json'),
            '--salida', str(salida)]
    monkeypatch.setattr(sys, 'argv', argv)
    assert entorno.main() == 0
    estado_sombra, conteo_sombra = [json.loads(linea) for linea in salida.read_text(encoding='utf-8').splitlines()]
    assert estado_sombra['datos'] == estado.model_dump(mode='json')
    assert conteo_sombra['datos'] == conteo.model_dump(mode='json')

    perfil.write_text(yaml.safe_dump(dict(config, prueba=False)), encoding='utf-8')
    sin_crear = tmp_path / 'mezcla.jsonl'
    monkeypatch.setattr(sys, 'argv', [*argv[:-1], str(sin_crear)])
    with pytest.raises(SystemExit) as error:
        entorno.main()
    assert error.value.code == 2 and not sin_crear.exists()


def test_cli_sumo_prepara_red_suministrada_sin_ejecutar(monkeypatch, tmp_path):
    flujos = tmp_path / 'flujos.csv'
    flujos.write_text(FLUJOS.read_text(encoding='utf-8-sig').replace('true', 'false'), encoding='utf-8')
    accesos = tmp_path / 'accesos.csv'
    accesos.write_text('acceso,entrada,salida\nN,N_in,S_out\nS,S_in,N_out\n'
                      'E,E_in,W_out\nW,W_in,E_out\n', encoding='utf-8')
    salida = tmp_path / 'existente'
    salida.mkdir()
    monkeypatch.setattr(sys, 'argv', ['sumo_base', '--network', str(escenario_sumo.DEMO / 'red.net.xml'),
                        '--access-map', str(accesos), '--counts', str(flujos), '--out', str(salida),
                        '--seed', '14', '--prepare-only'])
    escenario_sumo.main()
    assert {archivo.name for archivo in salida.iterdir()} == {'red.net.xml', 'flujos.rou.xml', 'base.sumocfg'}
