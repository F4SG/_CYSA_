"""Configuración local del banco; nunca devuelve ni imprime secretos al navegador."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def cargar():
    instalacion=Path(os.environ.get('CYSA_INSTALACION_DIR',ROOT))
    path=instalacion/'infra/.env'
    if not path.exists():raise RuntimeError('Primero configura la instalación IoT y Keycloak del README')
    values={line.split('=',1)[0]:line.split('=',1)[1] for line in path.read_text(encoding='utf-8-sig').splitlines() if '=' in line and not line.lstrip().startswith('#')}
    users=instalacion/'infra/runtime/clientes/usuarios-api.env'
    if not users.exists():raise RuntimeError('Ejecuta configurar_usuarios_local.py antes del banco S2')
    values.update({line.split('=',1)[0]:line.split('=',1)[1] for line in users.read_text().splitlines() if '=' in line})
    issuer=values.get('KEYCLOAK_PUBLIC_URL','http://localhost:8080').rstrip('/')
    broker_file=instalacion/'infra/runtime/clientes/emulador.env'
    broker={line.split('=',1)[0]:line.split('=',1)[1] for line in broker_file.read_text().splitlines() if '=' in line} if broker_file.exists() else {}
    defaults=dict(OIDC_ISSUER=issuer+'/realms/cysa',OIDC_JWKS_URL=issuer+'/realms/cysa/protocol/openid-connect/certs',
        OIDC_AUDIENCE='cysa-api',KC_INTERNAL_URL=issuer,KC_REALM='cysa',
        MQTT_HOST=broker.get('MQTT_HOST','localhost'),MQTT_PORT=broker.get('MQTT_PORT','8883'),MQTT_USER='plataforma',MQTT_PASSWORD=values['MQTT_PLATAFORMA_PASSWORD'],
        MQTT_CA=str(instalacion/'infra/runtime/mqtt/ca.crt'),CYSA_CONTROL_ENABLED='true',
        CYSA_PLAN_KEY_FILE=str(instalacion/'infra/runtime/control/clave.key'))
    for k in ('KC_USERS_CLIENT_ID','KC_USERS_CLIENT_SECRET'):defaults[k]=values[k]
    for k,v in defaults.items():os.environ.setdefault(k,v)
