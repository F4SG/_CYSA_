"""La demo visual conserva corridas anteriores y aísla los datos por usuario."""
import importlib.util
from pathlib import Path
import shutil
from xml.etree.ElementTree import parse

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('launcher_sumo', ROOT / 'desktop/sumo_gui.py')
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)


def test_visual_demo_isolated_repeatable_and_keeps_previous_results(tmp_path, monkeypatch):
    monkeypatch.setattr(gui, 'gui_binary', lambda: Path('sumo-gui.exe'))
    scenarios = []
    for name in ('usuario con espacios', 'otro usuario', 'usuario con espacios'):
        root = tmp_path / name
        counts = root / 'data/leonardo/ejemplos/flujos_DEMO.csv'
        counts.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'data/leonardo/ejemplos/flujos_DEMO.csv', counts)
        manifest = gui.prepare_demo(root, root / 'sumo-scenario.json')
        config = Path(manifest['Config'])
        assert config.is_relative_to(root)
        assert manifest['Expected'] == 13
        assert manifest['prueba'] and not manifest['validacion_piloto_real']
        xml = parse(config).getroot()
        for tag in ('net-file', 'route-files'):
            assert (config.parent / xml.find('input/' + tag).get('value')).is_file()
        scenarios.append(config)
    assert len(set(scenarios)) == 3
    assert all(config.is_file() for config in scenarios)


def test_missing_gui_explains_how_to_repair(monkeypatch, tmp_path):
    import types
    import sys
    monkeypatch.setitem(sys.modules, 'sumo', types.SimpleNamespace(__file__=str(tmp_path / '__init__.py')))
    with pytest.raises(RuntimeError, match='Configurar esta PC'):
        gui.gui_binary()
