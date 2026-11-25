"""La demo visual conserva corridas anteriores y aísla los datos por usuario."""
import csv
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import subprocess
from uuid import uuid4
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


def test_practice_counts_match_the_saved_sumo_scenario(tmp_path, monkeypatch, binaries):
    monkeypatch.syspath_prepend(str(ROOT / 'desktop'))
    import sumo_practica
    from sumo_vista_practica import VEHICULOS, preparar_vista

    batch = uuid4()
    folder = tmp_path / 'usuario con espacios' / str(batch)
    total = sumo_practica.generar(folder, datetime(2026, 11, 25, 20, 7, tzinfo=timezone.utc))
    with (folder / 'conteos.csv').open(encoding='utf-8') as file:
        rows = list(csv.DictReader(file))
    assert rows[0]['mensaje_id'] == str(batch)
    assert (rows[0]['carril'], rows[0]['clase']) == ('E_0', 'auto')
    assert rows[0]['inicio'] == '2026-11-24T20:05:00+00:00'
    assert rows[-1]['fin'] == '2026-11-25T20:05:00+00:00'
    assert len(rows) == 2880 * 6 * 3
    assert all((datetime.fromisoformat(r['fin']) - datetime.fromisoformat(r['inicio'])).total_seconds() == 30
               for r in rows)
    assert sum(int(r['cantidad']) for r in rows) == total > 0
    assert {(r['carril'], r['clase']) for r in rows if int(r['cantidad']) > 0} == {
        (c, t) for c in sumo_practica.CARRILES for t in sumo_practica.CLASES
    }

    routes_path = folder / 'flujos.rou.xml'
    original_routes = routes_path.read_bytes()
    visual = preparar_vista(folder / sumo_practica.CONFIG)
    assert routes_path.read_bytes() == original_routes
    visual_routes = parse(folder / 'flujos-visual.rou.xml')
    legend = parse(folder / 'entorno-practica.add.xml')
    for clase, etiqueta, figura, color, _ in VEHICULOS:
        tipo = visual_routes.find(f"vType[@id='{clase}']")
        assert (tipo.get('guiShape'), tipo.get('color')) == (figura, color)
        assert legend.find(f"poi[@id='etiqueta_{clase}']").get('type') == etiqueta
        assert legend.find(f"poly[@id='simbolo_{clase}']").get('color') == color

    subprocess.run([binaries / 'sumo.exe', '-c', visual.name, '--no-step-log', 'true'], cwd=folder, check=True)
    def measurements(name):
        return {(i.get('begin'), i.get('id')): i.get('nVehContrib')
                for i in parse(folder / name).getroot().iterfind('interval')}

    original = measurements(sumo_practica.SALIDA)
    assert original == measurements('reproduccion-' + sumo_practica.SALIDA)
    beginning = datetime.fromisoformat(rows[0]['inicio'])
    assert all(r['cantidad'] == original[f'{(datetime.fromisoformat(r["inicio"]) - beginning).total_seconds():.2f}',
                                              f'{r["carril"]}:{r["clase"]}'] for r in rows)
