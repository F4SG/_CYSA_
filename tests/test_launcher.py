"""Pruebas de aislamiento y recuperación del configurador de escritorio."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

spec = importlib.util.spec_from_file_location('desktop_runtime', Path(__file__).resolve().parents[1] / 'desktop/runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
hardware_spec = importlib.util.spec_from_file_location('launcher_hardware', Path(__file__).resolve().parents[1] / 'desktop/hardware.py')
hardware = importlib.util.module_from_spec(hardware_spec)
hardware_spec.loader.exec_module(hardware)


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


@pytest.mark.parametrize('cpu,gpus,expected', [
    (100, [], 'cpu'),
    (100, [dict(Device='0', Ms=110)], 'cpu'),
    (100, [dict(Device='0', Ms=95)], 'cpu'),
    (100, [dict(Device='0', Ms=40)], '0'),
    (100, [dict(Device='0', Ms=40), dict(Device='1', Ms=20)], '1'),
    (100, [dict(Device='0', Ms=None)], 'cpu'),
])
def test_recommendation_uses_measured_speed_and_avoids_noise(cpu, gpus, expected):
    assert hardware.choose(cpu, gpus)[0] == expected


@pytest.mark.parametrize('version,index', [((13, 5), 'cu130'), ((12, 8), 'cu126'), ((11, 8), 'cu118'), ((11, 7), None), (None, None)])
def test_gpu_packages_match_supported_driver_version(version, index):
    result = hardware.cuda_packages(version)
    assert (result[2] if result else None) == index


def test_unavailable_gpu_does_not_silently_run_as_cpu(monkeypatch):
    monkeypatch.setitem(sys.modules, 'torch', types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)))
    assert hardware.validate_device('cpu') == 'cpu'
    with pytest.raises(RuntimeError, match='ya no está disponible'):
        hardware.validate_device('0')
    with pytest.raises(ValueError):
        hardware.validate_device('gpu;cmd')


def test_detect_compares_cpu_and_gpu_and_recovers_from_gpu_failure(tmp_path, monkeypatch):
    cuda = types.SimpleNamespace(is_available=lambda: True, device_count=lambda: 2, get_device_name=lambda index: f'GPU {index}')
    monkeypatch.setitem(sys.modules, 'torch', types.SimpleNamespace(cuda=cuda))
    monkeypatch.setattr(hardware, 'nvidia_info', lambda: (True, (13, 0)))
    seen = []
    def measure(weights, device):
        seen.append(device)
        if device == '1':
            raise RuntimeError('GPU no compatible')
        return 100 if device == 'cpu' else 20
    monkeypatch.setattr(hardware, 'benchmark', measure)
    result = hardware.detect(tmp_path)
    assert seen == ['cpu', '0', '1']
    assert result['Recommended'] == '0'
    assert result['GpuReady'] is True
    assert result['CpuMs'] == 100 and result['GpuMs'] == 20


@pytest.mark.parametrize('device,expected', [('cpu', 'cpu'), ('1', 1)])
@pytest.mark.parametrize('video', [True, False])
def test_selected_mode_reaches_detector_profile(tmp_path, monkeypatch, device, expected, video):
    import detector
    import yaml
    root = tmp_path / 'usuario'
    (root / 'deteccion/config').mkdir(parents=True)
    for name in ('carriles_cristhian.yaml', 'video_santa_cruz.yaml'):
        profile = Path(__file__).resolve().parents[1] / 'deteccion/config' / name
        (root / 'deteccion/config' / name).write_bytes(profile.read_bytes())
    source = str(tmp_path / 'video con espacios.mp4') if video else '0'
    if video:
        Path(source).touch()
    captured = {}
    class Facade:
        def iniciar(self, profile, output, **kwargs):
            captured.update(yaml.safe_load(profile.read_text()))
            captured['source'] = kwargs['fuente']
            return 0
    monkeypatch.setattr(runtime, 'ROOT', root)
    monkeypatch.setattr(detector, 'FachadaConteo', Facade)
    monkeypatch.setitem(sys.modules, 'hardware', types.SimpleNamespace(validate_device=lambda _: expected))
    monkeypatch.chdir(tmp_path)
    assert runtime.detector(source, device) == 0
    assert captured['device'] == expected
    assert captured['imgsz'] == (960 if video else 640)
    assert captured['model'].endswith('yolo26n.pt' if video else 'yolo26s.pt')
    assert len(captured['lanes']) == 3
    assert captured['source'] == source
