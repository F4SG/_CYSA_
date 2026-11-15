"""Caso de estudio 3 - Command: cambios de configuración con trazabilidad.

Prueba de concepto para RF-02 (historial con usuario, fecha, motivo y valores
anterior/posterior) y RF-16 (aprobación del administrador y reversión
inmediata). Cada cambio es un objeto con ejecutar() y revertir().
"""
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Registro:
    fecha: datetime
    usuario: str
    accion: str
    clave: str
    anterior: object
    posterior: object
    motivo: str


@dataclass
class CambioConfiguracion:
    clave: str
    valor: object
    usuario: str
    rol: str
    motivo: str
    anterior: object = field(default=None, init=False)
    existia: bool = field(default=True, init=False)

    def ejecutar(self, config):
        if self.rol != 'administrador':
            raise PermissionError('Solo el administrador aprueba cambios (RF-16)')
        if not self.motivo.strip():
            raise ValueError('El motivo es obligatorio (RF-02)')
        self.existia = self.clave in config
        self.anterior = deepcopy(config.get(self.clave))
        config[self.clave] = deepcopy(self.valor)

    def revertir(self, config):
        if self.existia:
            config[self.clave] = deepcopy(self.anterior)
        else:
            config.pop(self.clave, None)   # la clave no existía antes del cambio


class HistorialCambios:
    """Invocador: aplica y revierte comandos y guarda el registro."""
    def __init__(self, config):
        self.config = config
        self._aplicados = []
        self._registros = []

    def aplicar(self, cambio):
        cambio.ejecutar(self.config)
        self._aplicados.append(cambio)
        self._anotar('aplicar', cambio, cambio.anterior, cambio.valor, cambio.motivo, cambio.usuario)

    def revertir_ultimo(self, usuario, motivo):
        if not self._aplicados:
            raise LookupError('No hay cambios que revertir')
        cambio = self._aplicados.pop()
        actual = deepcopy(self.config.get(cambio.clave))
        cambio.revertir(self.config)
        self._anotar('revertir', cambio, actual, cambio.anterior, motivo, usuario)

    def _anotar(self, accion, cambio, anterior, posterior, motivo, usuario):
        self._registros.append(Registro(datetime.now(timezone.utc), usuario, accion, cambio.clave,
                                        deepcopy(anterior), deepcopy(posterior), motivo))

    def registros(self):
        return tuple(self._registros)
