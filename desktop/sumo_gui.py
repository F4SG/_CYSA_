"""Prepara una demostración visual independiente para el usuario del lanzador."""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree, parse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def gui_binary():
    # Usar la distribución instalada en esta venv, nunca otra del PATH del equipo.
    try:
        import sumo
        executable = Path(sumo.__file__).resolve().parent / 'bin' / 'sumo-gui.exe'
    except ImportError as error:
        raise RuntimeError('Falta SUMO. Pulsa Configurar esta PC para instalar sus dependencias.') from error
    if not executable.is_file():
        raise RuntimeError('Falta SUMO-GUI en esta instalación. Pulsa Configurar esta PC para repararla.')
    return executable


def prepare_demo(root, report):
    from simulacion.sumo_base import EscenarioSUMOBuilder

    executable = gui_binary()
    output = root / 'resultados' / 'sumo_gui' / (datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid4().hex[:8])
    counts = root / 'data/leonardo/ejemplos/flujos_DEMO.csv'
    scenario = (EscenarioSUMOBuilder().con_red_demo().con_demanda(counts)
                .con_salida(output).con_semilla(42).construir())
    # Centrar la intersección para distinguir los vehículos y las luces al abrir.
    view = Element('viewsettings')
    SubElement(view, 'scheme', name='real world')
    SubElement(view, 'viewport', zoom='300', x='300', y='300', angle='0')
    ElementTree(view).write(output / 'vista.xml', encoding='utf-8', xml_declaration=True)
    config = parse(scenario.config)
    visual = SubElement(config.getroot(), 'gui_only')
    SubElement(visual, 'gui-settings-file', value='vista.xml')
    visual_config = output / 'CYSA_DEMO.sumocfg'
    config.write(visual_config, encoding='utf-8', xml_declaration=True)
    manifest = {'Executable': str(executable), 'Config': str(visual_config),
                'Expected': scenario.esperados, 'prueba': True,
                'geometria': 'SINTETICA', 'validacion_piloto_real': False}
    (output / 'LEEME.txt').write_text(
        'CYSA - Simulación SUMO de demostración\n\n'
        'Red sintética y plan fijo. No representa una medición de tráfico real.\n'
        'Pulsa el triángulo de reproducir (Ctrl+A) para iniciar la simulación.\n'
        'Puedes pausar y ajustar Delay (ms) para observar vehículos y semáforos.\n'
        'Al terminar, cierra SUMO para guardar tripinfo.xml en esta carpeta.\n'
        'Si cierras antes de finalizar, los resultados son parciales.\n'
        'Esta prueba no calcula Webster ni envía planes a semáforos.\n', encoding='utf-8')
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Escenario DEMO preparado: {scenario.esperados} vehículos. Archivos: {output}')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare_demo(ROOT, args.report)
    except (RuntimeError, OSError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
