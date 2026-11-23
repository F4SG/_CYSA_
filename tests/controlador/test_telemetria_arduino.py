import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cysa_controlador.controlador import ControladorEmulado
from cysa_controlador.run import cargar_config
from cysa_controlador.telemetria import TelemetriaArduino
from operacion.arduino import estado_arduino
from operacion.servidor import create_app
from operacion.entorno import identidad_interna


def test_identidad_interna_evitar_ipv6_sin_cambiar_issuer_o_https():
    assert identidad_interna('http://localhost:18080') == 'http://127.0.0.1:18080'
    for issuer in ('https://localhost:18080', 'http://keycloak:8080', 'https://identity.example.com'):
        assert identidad_interna(issuer) == issuer


def test_telemetria_registra_luces_y_sesion_y_falla(tmp_path):
    _, cruce, centro, local = cargar_config(Path(__file__).parents[2]/'controlador/config/demo_int_01.yaml')
    ctrl = ControladorEmulado(cruce, centro, local, True, 0)
    output = tmp_path/'estado.json'
    reporter = TelemetriaArduino(output, 'COM3', 'session', reloj=lambda: 0)
    reporter(ctrl)
    data = json.loads(output.read_text())
    assert data['luces'] == {'NS': 'G', 'EO': 'R'}
    assert data['sesion'] == 'session' and data['puerto'] == 'COM3'
    ctrl.falla_mmu('FALLA:CONFLICTO', 0)
    reporter(ctrl)
    data = json.loads(output.read_text())
    assert data['fase_actual'] == 'INTERMITENTE' and data['luces'] is None


@pytest.mark.parametrize('age,active', [(0, True), (2, True), (4, False), (-2, False)])
def test_estado_viejo_o_futuro_no_acredita_conexion(tmp_path, age, active):
    now = datetime.now(timezone.utc)
    path = tmp_path/'estado.json'
    path.write_text(json.dumps({'timestamp': (now-timedelta(seconds=age)).isoformat()}))
    assert estado_arduino(path, now)['activo'] is active


def test_archivo_ausente_o_incompleto_no_acredita_conexion(tmp_path):
    path = tmp_path/'estado.json'
    assert estado_arduino(path) == {'activo': False}
    path.write_text('{')
    assert estado_arduino(path) == {'activo': False}


def test_telemetria_no_es_publica():
    app = create_app(store=object(), directory=object(), worker=False)
    response = TestClient(app).get('/api/banco/arduino')
    assert response.status_code == 401
