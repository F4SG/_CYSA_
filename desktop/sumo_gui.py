"""Prepara una demostración visual independiente para el usuario del lanzador."""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4
from datetime import datetime

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
    from simulacion.corredor_demo import ESPERADOS, preparar_corredor

    executable = gui_binary()
    output = root / 'resultados' / 'sumo_gui' / (datetime.now().strftime('%Y%m%d-%H%M%S-') + uuid4().hex[:8])
    visual_config = preparar_corredor(output, executable.with_name('netconvert.exe'))
    manifest = {'Executable': str(executable), 'Config': str(visual_config),
                'Expected': ESPERADOS, 'prueba': True,
                'geometria': 'SINTETICA', 'validacion_piloto_real': False}
    (output / 'LEEME.txt').write_text(
        'CYSA - Simulación SUMO de demostración\n\n'
        'Corredor sintético A–B. Ambos cruces comienzan con plan fijo.\n'
        'Pulsa el triángulo de reproducir (Ctrl+A) para iniciar la simulación.\n'
        'La ambulancia naranja activa un evento predefinido en A. B recibe el aviso y espera el despeje peatonal.\n'
        'Cada cruce vuelve al plan fijo después del paso, con ámbar y todo rojo.\n'
        'Los marcadores señalan aviso (ámbar) o prioridad (verde).\n'
        'Consulta eventos_corredor.csv, semaforos.xml y tripinfo.xml en esta carpeta.\n'
        'Si cierras antes de finalizar, los resultados son parciales.\n'
        'La demostración se ejecuta exclusivamente dentro de SUMO.\n', encoding='utf-8')
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Corredor DEMO preparado: dos cruces y {ESPERADOS} vehículos. Archivos: {output}')
    return manifest


def drive(config, port):
    from simulacion.corredor_demo import conducir, traci_bundle

    traci = traci_bundle()
    con = traci.connect(port=port, host='127.0.0.1', numRetries=25, waitBetweenRetries=0.2)
    try:
        conducir(con, config.parent, visualizar=True)
    except traci.FatalTraCIError:
        print('SUMO cerró antes de completar el recorrido. La evidencia guardada es parcial.')
        raise
    finally:
        try:
            con.close()
        except (OSError, traci.FatalTraCIError):
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--report', type=Path)
    mode.add_argument('--drive', type=Path)
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    try:
        if args.report:
            prepare_demo(ROOT, args.report)
        elif args.port and 1 <= args.port <= 65535:
            drive(args.drive, args.port)
        else:
            parser.error('--drive requiere --port de la instancia SUMO lanzada en esta PC')
    except (RuntimeError, OSError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
