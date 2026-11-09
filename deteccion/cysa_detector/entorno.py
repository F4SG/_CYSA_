"""Composición de detección y controlador para laboratorio y modo sombra."""
import argparse
from contextlib import closing
from copy import deepcopy
import json
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import uuid4

from cysa.contracts import Conteo, Estado, PlanBorrador
from cysa.interfaces import Controlador, FuenteDeteccion
from .coordinacion import CoordinadorDetector
from .run import creador_detector, validar_calibracion


class FuentePrueba(FuenteDeteccion):
    def __init__(self, interseccion, conteos):
        self._conteos = tuple(conteo.model_copy() for conteo in conteos)
        if any(not conteo.prueba or conteo.interseccion != interseccion
               for conteo in self._conteos):
            raise ValueError('La fuente requiere conteos de prueba de su intersección')

    def eventos(self):
        for conteo in self._conteos:
            yield conteo.model_copy()


class ControladorEmulado(Controlador):
    """Registra en memoria la primera fase de un plan de prueba."""
    def __init__(self, interseccion):
        self.interseccion = interseccion
        self._plan = 'SIN_PLAN'
        self._fase = 'INICIAL'

    def estado(self):
        return Estado(mensaje_id=uuid4(), interseccion=self.interseccion,
                      fase_actual=self._fase, plan_activo=self._plan,
                      estado_controlador='conectado',
                      timestamp=datetime.now(timezone.utc), prueba=True)

    def enviar_plan(self, plan: PlanBorrador):
        if not plan.prueba or plan.interseccion != self.interseccion:
            raise ValueError('El emulador requiere un plan de prueba de su intersección')
        self._plan, self._fase = plan.plan_id, plan.fases[0].fase_id


class FabricaEntorno(ABC):
    @abstractmethod
    def crear_fuente(self) -> FuenteDeteccion:
        ...

    @abstractmethod
    def crear_controlador(self) -> Controlador:
        ...


class FabricaLaboratorio(FabricaEntorno):
    def __init__(self, interseccion, conteos: list[Conteo]):
        self.interseccion = interseccion
        self.conteos = tuple(conteo.model_copy() for conteo in conteos)

    def crear_fuente(self):
        return FuentePrueba(self.interseccion, self.conteos)

    def crear_controlador(self):
        return ControladorEmulado(self.interseccion)


class ControladorSombra(Controlador):
    """Expone un estado observado y conserva el bloqueo de envío de planes."""
    def __init__(self, estado):
        self._estado = estado.model_copy()

    def estado(self):
        return self._estado.model_copy()

    def enviar_plan(self, plan: PlanBorrador):
        super().enviar_plan(plan)


class FabricaSombra(FabricaEntorno):
    def __init__(self, config, estado: Estado, inicio_video=None):
        validar_calibracion(config)
        if estado.interseccion != config.get('interseccion') or estado.prueba is not config.get('prueba'):
            raise ValueError('El estado debe corresponder a la intersección y marca prueba del detector')
        self._creador = creador_detector(deepcopy(config), inicio_video)
        self._estado = estado.model_copy()

    def crear_fuente(self):
        return self._creador.crear_fuente()

    def crear_controlador(self):
        return ControladorSombra(self._estado)


def preparar_entorno(fabrica: FabricaEntorno):
    return fabrica.crear_fuente(), fabrica.crear_controlador()


def main():
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest='entorno', required=True)
    laboratorio = comandos.add_parser('laboratorio', help='Reproducir conteos y emular un plan de prueba')
    laboratorio.add_argument('--conteo', type=Path, required=True, action='append')
    laboratorio.add_argument('--plan', type=Path)
    laboratorio.add_argument('--salida', type=Path, required=True, help='Archivo JSONL nuevo')
    sombra = comandos.add_parser('sombra', help='Detectar y leer el estado recibido sin enviar planes')
    sombra.add_argument('--config', type=Path, required=True)
    sombra.add_argument('--estado', type=Path, required=True, help='Mensaje Estado guardado como JSON')
    sombra.add_argument('--inicio-video', type=datetime.fromisoformat)
    sombra.add_argument('--salida', type=Path, required=True, help='Archivo JSONL nuevo')
    args = parser.parse_args()

    try:
        if args.entorno == 'laboratorio':
            conteos = [Conteo.model_validate_json(p.read_bytes()) for p in args.conteo]
            fabrica = FabricaLaboratorio(conteos[0].interseccion, conteos)
        else:
            config = yaml.safe_load(args.config.read_text(encoding='utf-8'))
            if not isinstance(config, dict):
                raise ValueError('El perfil debe ser un mapa YAML')
            estado = Estado.model_validate_json(args.estado.read_bytes())
            fabrica = FabricaSombra(config, estado, args.inicio_video)
        fuente, controlador = preparar_entorno(fabrica)
        if args.entorno == 'laboratorio' and args.plan:
            controlador.enviar_plan(PlanBorrador.model_validate_json(args.plan.read_bytes()))
        with CoordinadorDetector().sesion(), args.salida.open('x', encoding='utf-8') as salida:
            def escribir(tipo, evento):
                registro = {'tipo': tipo, 'datos': evento.model_dump(mode='json')}
                salida.write(json.dumps(registro, ensure_ascii=False) + '\n')
                salida.flush()

            escribir('estado', controlador.estado())
            with closing(fuente.eventos()) as eventos:
                for evento in eventos:
                    escribir('conteo', evento)
    except (OSError, ValueError, RuntimeError, yaml.YAMLError) as error:
        parser.error(str(error))
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
