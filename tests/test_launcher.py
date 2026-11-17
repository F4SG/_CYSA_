"""Pruebas de aislamiento y recuperación del configurador de escritorio."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location('desktop_runtime', Path(__file__).resolve().parents[1] / 'desktop/runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def root_at(tmp_path, name):
    root = tmp_path / name
    (root / 'identidad').mkdir(parents=True)
    (root / 'panel').mkdir()
    (root / 'infra').mkdir()
    (root / 'identidad/realm.template.json').write_text('{}')
    (root / 'identidad/nginx.conf').write_text('connect-src http://localhost:8080; form-action http://localhost:8080')
    return root


def generator(command, **kwargs):
    stage = Path(command[command.index('--repo') + 1])
    clients = stage / 'infra/runtime/clientes'
    clients.mkdir(parents=True)
    for name in ('deteccion', 'prueba', 'emulador'):
        (clients / (name + '.env')).write_text(f'MQTT_PASSWORD=secreto-{stage.parent.name}\nMQTT_CA=staging\n')
    (stage / 'infra/.env').write_text('SECRET=' + stage.parent.name)
    (stage / 'panel/config.json').write_text(json.dumps({'issuer': command[command.index('--public-keycloak') + 1]}))


def test_new_users_keep_separate_configuration_and_secrets(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, 'run', generator)
    one = root_at(tmp_path, 'usuario con espacios')
    two = root_at(tmp_path, 'otro usuario')
    for root, port in ((one, 18883), (two, 18983)):
        runtime.prepare(root, 'http://localhost:18080', 'http://localhost:18088', port)
        client = (root / 'infra/runtime/clientes/deteccion.env').read_text()
        assert f'MQTT_PORT={port}' in client
        assert str(root / 'infra/runtime/mqtt/ca.crt') in client
        assert 'staging' not in client
        assert 'http://localhost:18080' in (root / 'infra/runtime/launcher/nginx.conf').read_text()
        assert 'http://localhost:8080' not in (root / 'infra/runtime/launcher/nginx.conf').read_text()
    first = (one / 'infra/.env').read_bytes()
    runtime.prepare(one, 'http://localhost:18080', 'http://localhost:18088', 18883)
    assert first == (one / 'infra/.env').read_bytes()
    assert first != (two / 'infra/.env').read_bytes()


def test_resume_after_runtime_promoted_before_env(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, 'run', generator)
    root = root_at(tmp_path, 'recuperacion')
    stage = root / '.launcher-setup'
    (stage / 'infra').mkdir(parents=True)
    (stage / 'panel').mkdir()
    generator(['--repo', str(stage), '--public-keycloak', 'http://localhost:19080'])
    (stage / 'generado').write_text('ok')
    (stage / 'infra/runtime').rename(root / 'infra/runtime')
    runtime.prepare(root, 'http://localhost:19080', 'http://localhost:19088', 19883)
    assert (root / 'infra/.env').read_text() == 'SECRET=recuperacion'
    assert json.loads((root / 'panel/config.json').read_text())['issuer'] == 'http://localhost:19080'
    assert not stage.exists()


def test_unknown_partial_config_is_preserved(tmp_path, monkeypatch):
    root = root_at(tmp_path, 'parcial')
    (root / 'infra/.env').write_text('NO_BORRAR=secreto')
    with pytest.raises(RuntimeError, match='incompleta'):
        runtime.prepare(root, 'http://localhost:18080', 'http://localhost:18088', 18883)
    assert (root / 'infra/.env').read_text() == 'NO_BORRAR=secreto'
