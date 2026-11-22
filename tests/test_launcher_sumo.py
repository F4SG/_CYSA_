"""La demo visual conserva corridas anteriores y aísla los datos por usuario."""
import csv
import importlib.util
from pathlib import Path
from xml.etree.ElementTree import parse

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('launcher_sumo', ROOT / 'desktop/sumo_gui.py')
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)
from simulacion.corredor_demo import AMBULANCIA, ESPERADOS, conducir, traci_bundle


@pytest.fixture
def binaries():
    pytest.importorskip('sumo')
    return gui.gui_binary().parent


def test_visual_demo_isolated_repeatable_and_keeps_previous_results(tmp_path, binaries):
    scenarios = []
    for name in ('usuario con espacios', 'otro usuario', 'usuario con espacios'):
        root = tmp_path / name
        manifest = gui.prepare_demo(root, root / 'sumo-scenario.json')
        config = Path(manifest['Config'])
        assert config.is_relative_to(root)
        assert manifest['Expected'] == ESPERADOS
        assert manifest['prueba'] and not manifest['validacion_piloto_real']
        xml = parse(config).getroot()
        for tag in ('net-file', 'route-files', 'additional-files'):
            assert (config.parent / xml.find('input/' + tag).get('value')).is_file()
        scenarios.append(config)
    assert len(set(scenarios)) == 3
    assert all(config.is_file() for config in scenarios)


def test_real_sumo_prioritizes_ambulance_and_restores_both_crossings(tmp_path, binaries):
    manifest = gui.prepare_demo(tmp_path, tmp_path / 'escenario.json')
    config = Path(manifest['Config'])
    traci = traci_bundle()
    traci.start([str(binaries / 'sumo.exe'), '-c', str(config), '--seed', '42'], numRetries=2)
    try:
        conducir(traci, config.parent)
    finally:
        traci.close()
    with (config.parent / 'eventos_corredor.csv').open(encoding='utf-8') as file:
        log = {(row['cruce'], row['evento']): float(row['segundo_sumo']) for row in csv.DictReader(file)}
    assert log['B', 'aviso_recibido'] - log['A', 'aviso_enviado'] == 1
    assert log['B', 'aviso_recibido'] < log['A', 'ambulancia_paso']
    assert log['B', 'despeje_peatonal_en_curso'] < log['B', 'despeje_peatonal_completado']
    assert log['B', 'despeje_peatonal_completado'] <= log['B', 'verde_prioridad']
    states = parse(config.parent / 'semaforos.xml').getroot()
    for cross, alert in [('A', 'evento_emergencia'), ('B', 'aviso_recibido')]:
        time = lambda event: log[cross, event]
        green, passage = time('verde_prioridad'), time('ambulancia_paso')
        assert 0 < green - time(alert) <= 10
        assert green < passage < time('plan_fijo_restaurado')
        assert time('todo_rojo') - time('ambar') >= 3
        assert green - time('todo_rojo') >= 2
        assert time('todo_rojo_retorno') - time('ambar_retorno') >= 3
        assert time('plan_fijo_restaurado') - time('todo_rojo_retorno') >= 2
        history = {float(s.get('time')): s for s in states.findall(f"tlsState[@id='{cross}']")}
        assert {s.get('state') for t, s in history.items() if time('todo_rojo') <= t < green} == {'rrrrr'}
        assert history[time('plan_fijo_restaurado')].get('programID') == 'DEMO_FIJO'
    trips = parse(config.parent / 'tripinfo.xml').getroot().findall('tripinfo')
    assert any(t.get('id') == AMBULANCIA for t in trips)
    assert len(trips) == ESPERADOS and all(float(t.get('arrival')) >= 0 for t in trips)


def test_missing_gui_explains_how_to_repair(monkeypatch, tmp_path):
    import types
    import sys
    monkeypatch.setitem(sys.modules, 'sumo', types.SimpleNamespace(__file__=str(tmp_path / '__init__.py')))
    with pytest.raises(RuntimeError, match='Configurar esta PC'):
        gui.gui_binary()
