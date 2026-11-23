"""Consulta de telemetría local; los archivos antiguos nunca acreditan una conexión."""
import json
from datetime import datetime, timezone


def estado_arduino(path, ahora=None):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        timestamp = datetime.fromisoformat(data['timestamp'])
        age = ((ahora or datetime.now(timezone.utc)) - timestamp).total_seconds()
        return {**data, 'activo': 0 <= age <= 3}
    except (OSError, ValueError, KeyError, TypeError):
        return {'activo': False}
