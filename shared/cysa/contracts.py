from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')]
class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')
class Timed(StrictModel):
    @staticmethod
    def utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Se requiere fecha ISO8601 con zona horaria')
        return value.astimezone(timezone.utc)
class Conteo(Timed):
    version: Literal['1.0'] = '1.0'
    mensaje_id: UUID
    interseccion: Identifier
    acceso: Identifier
    carril: Identifier
    clase: Literal['auto','micro','moto']
    cantidad: Annotated[int, Field(strict=True, ge=0, le=100000)]
    inicio: datetime
    fin: datetime
    prueba: StrictBool
    _dates = field_validator('inicio','fin')(Timed.utc)
    @model_validator(mode='after')
    def interval(self):
        seconds=(self.fin-self.inicio).total_seconds()
        if not 0 < seconds <= 30.5:
            raise ValueError('Intervalo válido: mayor a 0 y hasta 30.5 segundos')
        return self
class Estado(Timed):
    version: Literal['1.0'] = '1.0'
    mensaje_id: UUID
    interseccion: Identifier
    fase_actual: Identifier
    plan_activo: Identifier
    estado_controlador: Literal['conectado','desconectado','desconocido']
    timestamp: datetime
    prueba: StrictBool
    _date = field_validator('timestamp')(Timed.utc)
class Latido(Timed):
    """Señal periódica del centro de control (tópico centro/latido). Sin latidos por más de
    60 s, cada controlador pasa a su plan local seguro (RF-06)."""
    version: Literal['1.0'] = '1.0'
    timestamp: datetime
    _date = field_validator('timestamp')(Timed.utc)
TOPICO_LATIDO = 'centro/latido'
class Activo(StrictModel):
    activo_id: Identifier
    interseccion: Identifier
    acceso: Identifier | None = None
    tipo: Literal['interseccion','acceso','camara','controlador']
    ubicacion: Annotated[str,Field(min_length=1,max_length=200)]
    protocolo: Annotated[str,Field(min_length=1,max_length=80)]
    prueba: StrictBool
class Fase(StrictModel):
    fase_id: Identifier
    duracion_s: Annotated[int,Field(strict=True,gt=0,le=600)]
class PlanBorrador(StrictModel):
    """Contrato reservado para S2; sin envío, autorización ni ejecución en S1."""
    version: Literal['1.0'] = '1.0'
    plan_id: Identifier
    interseccion: Identifier
    fases: Annotated[list[Fase],Field(min_length=1)]
    prueba: StrictBool

def decode_message(topic: str, payload: bytes):
    if len(payload)>16384: raise ValueError('Mensaje demasiado grande')
    parts=topic.split('/')
    if len(parts)==4 and parts[0]=='corredor' and parts[3]=='conteos':
        event=Conteo.model_validate_json(payload)
        if [event.interseccion,event.acceso]!=parts[1:3]: raise ValueError('Tópico y cuerpo no coinciden')
        return event
    if len(parts)==3 and parts[0]=='corredor' and parts[2]=='estado':
        event=Estado.model_validate_json(payload)
        if event.interseccion!=parts[1]: raise ValueError('Tópico y cuerpo no coinciden')
        return event
    raise ValueError('Tópico no admitido en S1')
