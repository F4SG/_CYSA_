"""Builder para preparar archivos SUMO de prueba por separado."""
import csv
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree.ElementTree import parse

from simulacion.sumo_base import build_routes, load_counts, write_xml


DEMO = Path(__file__).resolve().parents[1] / 'simulacion' / 'escenarios' / 'DEMO'
DEMO_MAP = {'N': ('N_in', 'S_out'), 'S': ('S_in', 'N_out'),
            'E': ('E_in', 'W_out'), 'W': ('W_in', 'E_out')}


@dataclass(frozen=True)
class EscenarioSUMO:
    red: Path
    rutas: Path
    config: Path
    semilla: int


class EscenarioSUMOBuilder:
    def __init__(self):
        self.red = None
        self.accesos = None
        self.demanda = None
        self.salida = None
        self.semilla = 42

    def con_red_demo(self):
        self.red = DEMO / 'red.net.xml'
        self.accesos = None
        return self

    def con_red(self, red, accesos):
        self.red = Path(red)
        self.accesos = Path(accesos)
        return self

    def con_demanda(self, demanda):
        self.demanda = Path(demanda)
        return self

    def con_salida(self, salida):
        self.salida = Path(salida)
        return self

    def con_semilla(self, semilla):
        self.semilla = semilla
        return self

    def construir(self):
        if self.red is None or self.demanda is None or self.salida is None:
            raise ValueError('Completar red, demanda y salida')
        if not isinstance(self.semilla, int) or isinstance(self.semilla, bool):
            raise ValueError('La semilla debe ser un entero')
        salida = self.salida.absolute()
        if salida.exists():
            raise FileExistsError(salida)
        rows = load_counts(self.demanda)
        if any(row['prueba'].lower() != 'true' for row in rows):
            raise ValueError('El caso de estudio requiere conteos marcados prueba=true')
        if self.accesos is None:
            mapping = DEMO_MAP
        else:
            with self.accesos.open(encoding='utf-8-sig', newline='') as archivo:
                mapping = {}
                for row in csv.DictReader(archivo):
                    acceso = row['acceso']
                    if acceso in mapping:
                        raise ValueError(f'Acceso repetido: {acceso}')
                    mapping[acceso] = (row['entrada'], row['salida'])

        red = parse(self.red).getroot()
        if not any(plan.get('type') == 'static' and plan.find('phase') is not None
                   for plan in red.findall('tlLogic')):
            raise ValueError('La red debe incluir un plan fijo con fases')
        edges = {edge.get('id') for edge in red.findall('edge')}
        for acceso, par in mapping.items():
            if not set(par) <= edges:
                raise ValueError(f'El mapa usa aristas desconocidas para {acceso}')
        for row in rows:
            if row['acceso'] not in mapping:
                raise ValueError(f'Acceso sin correspondencia: {row["acceso"]}')

        # Reutilizar la configuración base y publicar los archivos juntos.
        config = parse(DEMO / 'base.sumocfg').getroot()
        with TemporaryDirectory(dir=salida.parent, prefix='.sumo-') as temporal:
            preparado = Path(temporal) / 'escenario'
            preparado.mkdir()
            shutil.copyfile(self.red, preparado / 'red.net.xml')
            duracion = build_routes(rows, mapping, preparado)
            config.find('time/end').set('value', str(duracion + 900))
            write_xml(preparado / 'base.sumocfg', config)
            preparado.rename(salida)

        return EscenarioSUMO(salida / 'red.net.xml', salida / 'flujos.rou.xml',
                             salida / 'base.sumocfg', self.semilla)
