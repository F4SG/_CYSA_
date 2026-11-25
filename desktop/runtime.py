"""Acciones del lanzador. No usa cuentas, rutas ni tokens de otra instalación."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / p) for p in ('shared', 'backend', 'inventario', 'deteccion', 'tools/franco', 'tools/cristhian')]


def prepare(root, identity, panel, mqtt_port):
    """Genera en staging y reanuda una promoción interrumpida sin rotar secretos."""
    stage = root / '.launcher-setup'
    runtime = root / 'infra/runtime'
    env = root / 'infra/.env'
    complete = stage / 'generado'
    if not (runtime.exists() and env.exists()):
        if not complete.exists():
            if runtime.exists() or env.exists():
                raise RuntimeError('Configuración incompleta ajena al lanzador. Conserva infra/.env y runtime; revisa los registros antes de continuar.')
            if stage.exists():
                shutil.rmtree(stage)
            (stage / 'identidad').mkdir(parents=True)
            (stage / 'panel').mkdir()
            (stage / 'infra').mkdir()
            shutil.copy2(root / 'identidad/realm.template.json', stage / 'identidad/realm.template.json')
            subprocess.run([sys.executable, str(root / 'tools/franco/preparar_local.py'), '--repo', str(stage),
                            '--public-keycloak', identity, '--public-panel', panel], check=True)
            complete.write_text('ok', encoding='utf-8')
        # Si se corta el proceso entre estos pasos, el marcador conserva la copia
        # completa para terminar la promoción en el siguiente intento.
        if not runtime.exists():
            shutil.move(str(stage / 'infra/runtime'), runtime)
        if not env.exists():
            shutil.copy2(stage / 'infra/.env', env)
    if complete.exists():
        shutil.copy2(stage / 'panel/config.json', root / 'panel/config.json')
    for name in ('deteccion', 'prueba', 'emulador'):
        path = runtime / 'clientes' / f'{name}.env'
        values = dict(line.split('=', 1) for line in path.read_text(encoding='utf-8-sig').splitlines() if '=' in line)
        values.update(MQTT_HOST='localhost', MQTT_PORT=str(mqtt_port), MQTT_CA=str(runtime / 'mqtt/ca.crt'))
        path.write_text(''.join(f'{k}={v}\n' for k, v in values.items()), encoding='utf-8')
    from configurar_usuarios_local import prepare_identity_files
    prepare_identity_files(root)
    panel_port = urlparse(panel).port
    identity_port = urlparse(identity).port
    if not all(isinstance(p, int) and 1024 <= p <= 65535 for p in (panel_port, identity_port, mqtt_port)):
        raise ValueError('Puertos locales inválidos')
    launcher = runtime / 'launcher'
    launcher.mkdir(exist_ok=True)
    nginx = (root / 'identidad/nginx.conf').read_text(encoding='utf-8')
    (launcher / 'nginx.conf').write_text(nginx.replace('http://localhost:8080', identity), encoding='utf-8')
    (root / 'infra/launcher.override.yaml').write_text(
        'services:\n'
        f'  panel:\n    ports: !override ["127.0.0.1:{panel_port}:80"]\n'
        '    volumes: ["./runtime/launcher/nginx.conf:/etc/nginx/conf.d/default.conf:ro"]\n'
        f'  keycloak:\n    ports: !override ["127.0.0.1:{identity_port}:8080"]\n'
        f'  mosquitto:\n    ports: !override ["127.0.0.1:{mqtt_port}:8883"]\n', encoding='utf-8')
    if complete.exists():
        shutil.rmtree(stage)
    print('Configuración de esta PC preparada; secretos existentes conservados.')


class LoginForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form' and attrs.get('id') == 'kc-form-login':
            self.action = attrs.get('action')
        if tag == 'input' and attrs.get('type') == 'hidden' and attrs.get('name'):
            self.fields[attrs['name']] = attrs.get('value', '')


def login(panel, username, password):
    import httpx
    config = httpx.get(panel + '/config.json', trust_env=False).json()
    issuer = config['issuer']
    if urlparse(issuer).hostname not in ('localhost', '127.0.0.1'):
        raise RuntimeError('Esta prueba solo admite el proveedor local de esta instalación')
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    state = secrets.token_urlsafe(24)
    with httpx.Client(follow_redirects=True, timeout=20, trust_env=False) as client:
        response = client.get(issuer + '/protocol/openid-connect/auth', params={
            'client_id': config['clientId'], 'redirect_uri': config['redirectUri'], 'response_type': 'code',
            'scope': 'openid profile', 'state': state, 'nonce': secrets.token_urlsafe(24),
            'code_challenge': challenge, 'code_challenge_method': 'S256'})
        response.raise_for_status()
        form = LoginForm()
        form.feed(response.text)
        if not form.action or urlparse(form.action).netloc != urlparse(issuer).netloc:
            raise RuntimeError('No se encontró el formulario del proveedor local')
        # Excepción Secure de localhost que los navegadores aplican automáticamente.
        for cookie in client.cookies.jar:
            if cookie.domain in ('localhost', 'localhost.local', '127.0.0.1'):
                cookie.secure = False
        response = client.post(form.action, data={**form.fields, 'username': username, 'password': password, 'credentialId': ''})
        response.raise_for_status()
        query = parse_qs(response.url.query.decode())
        if query.get('state') != [state] or 'code' not in query:
            raise RuntimeError('El ingreso local no se completó')
        response = client.post(issuer + '/protocol/openid-connect/token', data={
            'grant_type': 'authorization_code', 'client_id': config['clientId'], 'redirect_uri': config['redirectUri'],
            'code': query['code'][0], 'code_verifier': verifier})
        response.raise_for_status()
        return response.json()['access_token']


def verify(args):
    import httpx
    from cysa.contracts import Conteo
    from cysa.mqtt import Publisher
    passwords = json.loads((ROOT / 'infra/runtime/clientes/usuarios-locales.json').read_text(encoding='utf-8-sig'))
    with httpx.Client(timeout=20, trust_env=False) as client:
        panel_response = client.get(args.panel + '/')
        assert panel_response.status_code == 200, 'Panel inaccesible'
        config = client.get(args.panel + '/config.json').json()
        origin = config['issuer'].removesuffix('/realms/cysa')
        assert origin in panel_response.headers.get('content-security-policy', ''), 'La política del navegador no permite el proveedor local'
        assert client.get(args.panel + '/api/conteos').status_code == 401, 'Falta protección de consultas'
        print('PASS: panel y consultas protegidas')
        headers = None
        for role in ('operador', 'administrador'):
            headers = {'Authorization': 'Bearer ' + login(args.panel, role, passwords[role])}
            for path in ('conteos', 'estados', 'inventario'):
                assert client.get(args.panel + '/api/' + path, headers=headers).status_code == 200, f'Consulta {path} con {role}'
            assert client.get(args.panel + '/api/usuarios', headers=headers).status_code == (200 if role == 'administrador' else 403), f'Permisos de {role}'
            print('PASS: ingreso OIDC/PKCE y permisos de ' + role)
        for line in (ROOT / 'infra/runtime/clientes/prueba.env').read_text(encoding='utf-8-sig').splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
        now = datetime.now(timezone.utc)
        uid = uuid4()
        count = Conteo(mensaje_id=uid, interseccion='DEMO_INT_01', acceso='N', carril='QA_LAUNCHER',
                       clase='auto', cantidad=1, inicio=now-timedelta(seconds=30), fin=now, prueba=True)
        with Publisher('cysa-launcher-' + uid.hex[:8]) as publisher:
            publisher.publish(count)
        for _ in range(25):
            response = client.get(args.panel + '/api/conteos', headers=headers, params={'carril': 'QA_LAUNCHER', 'limit': 1000})
            response.raise_for_status()
            if any(row['mensaje_id'] == str(uid) for row in response.json()['items']):
                break
            time.sleep(1)
        else:
            raise RuntimeError('El conteo de prueba no llegó desde MQTT a la API')
        print('PASS: MQTT/TLS → consumidor → PostgreSQL → API (conteo sintético)')
        for base in (args.evaluation, args.decision):
            response = client.get(base + '/health')
            assert response.json()['status'] == 'ok' and response.json()['soloPrueba'] is True
            assert client.get(base + '/swagger/v1/swagger.json').status_code == 200
        print('PASS: ambas APIs .NET y Swagger. No se valida precisión en tráfico real.')


def demo_test(args):
    import httpx
    tokens = json.loads((ROOT / 'dotnet/runtime/tokens.json').read_text())
    with httpx.Client(timeout=20, trust_env=False) as client:
        plan = 'LAUNCHER_' + uuid4().hex[:12]
        body = dict(planId=plan, version=1, interseccionId='DEMO_INT_01', planBaseId='FIJO', escenario='Prueba del lanzador', origen='demo',
                    accesos=[dict(id='N', demoraBaseSegundos=40, demoraCandidataSegundos=48, longitudCruceMetros=18)],
                    fases=[dict(id='P1', accesos=['N'], tiempoPeatonalSegundos=25)])
        headers = {'Authorization': 'Bearer ' + tokens['evaluador']}
        response = client.post(args.evaluation + '/api/evaluaciones', json=body, headers=headers)
        assert response.status_code == 201 and response.json()['aprobada'] is False, 'Rechazo del aumento del 20 %'
        body['version'] = 2
        body['accesos'][0]['demoraCandidataSegundos'] = 42
        response = client.post(args.evaluation + '/api/evaluaciones', json=body, headers=headers)
        assert response.status_code == 201 and response.json()['aprobada'] is True, 'Aprobación del escenario'
        decision = dict(solicitudId=str(uuid4()), evaluacionId=response.json()['id'], version=2, accion='autorizar', motivo='Prueba local del lanzador')
        url = args.decision + f'/api/planes/{plan}/decisiones'
        for role in ('administrador', 'operadorSinMfa'):
            assert client.post(url, json=decision, headers={'Authorization': 'Bearer ' + tokens[role]}).status_code == 403, 'Permisos de decisión'
        headers = {'Authorization': 'Bearer ' + tokens['operador']}
        response = client.post(url, json=decision, headers=headers)
        assert response.status_code == 201, 'Autorizar con operador de demo: renueva Tokens de demo si venció la ventana de 5 minutos'
        retry = client.post(url, json=decision, headers=headers)
        assert retry.is_success and retry.json()['id'] == response.json()['id'], 'Idempotencia'
        history = client.get(args.decision + f'/api/planes/{plan}/historial', headers=headers)
        assert history.is_success and len(history.json()) == 1, 'Historial'
    print('PASS: dos APIs HTTP, evaluación, rechazo/aprobación, permisos, MFA simulado e idempotencia.')


def detector(source, device='cpu', csv_video=None):
    import yaml
    from detector import FachadaConteo, parse_source
    from hardware import validate_device
    os.chdir(ROOT)
    source_type = parse_source(source)['tipo']
    if csv_video and source_type != 'video':
        raise ValueError('La carga de datos requiere un archivo de video.')
    profile_name = 'video_santa_cruz.yaml' if source_type == 'video' else 'carriles_cristhian.yaml'
    profile = yaml.safe_load((ROOT / 'deteccion/config' / profile_name).read_text(encoding='utf-8'))
    selected = validate_device(device)
    if profile_name == 'carriles_cristhian.yaml':
        profile['imgsz'] = 640
    profile.update(device=selected, configuracion_verificada=False)
    if source_type == 'video':
        profile.update(interseccion='DEMO_VIDEO', prueba=True)
    if csv_video:
        profile['ritmo_real'] = False
    destination = ROOT / f'resultados/launcher-{"video-importacion" if csv_video else device}.yaml'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(yaml.safe_dump(profile, allow_unicode=True), encoding='utf-8')
    print('Modo del detector: ' + ('CPU' if device == 'cpu' else 'GPU CUDA ' + device), flush=True)
    salida = csv_video or ROOT / ('resultados/conteos_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv')
    facade = FachadaConteo()
    if csv_video:
        return facade.iniciar(destination, salida, fuente=source, marcar='zona', solo_csv=True)
    return facade.iniciar(destination, salida, fuente=source, marcar='zona')


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='action', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('--identity', required=True)
    prep.add_argument('--panel', required=True)
    prep.add_argument('--mqtt-port', type=int, required=True)
    for name in ('verify', 'demo-test'):
        command = commands.add_parser(name)
        command.add_argument('--panel', default='http://localhost:18088')
        command.add_argument('--evaluation', required=True)
        command.add_argument('--decision', required=True)
    command = commands.add_parser('detector')
    command.add_argument('--source', required=True)
    command.add_argument('--device', default='cpu')
    command.add_argument('--csv-video', type=Path)
    command = commands.add_parser('hardware')
    command.add_argument('--out', type=Path, required=True)
    commands.add_parser('prepare-gpu')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(ROOT, args.identity, args.panel, args.mqtt_port)
    elif args.action == 'verify':
        verify(args)
    elif args.action == 'demo-test':
        demo_test(args)
    elif args.action == 'hardware':
        from hardware import detect
        result = detect(ROOT)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Recomendado: ' + ('CPU' if result['Recommended'] == 'cpu' else 'GPU'))
    elif args.action == 'prepare-gpu':
        from hardware import prepare_gpu
        prepare_gpu()
    else:
        return detector(args.source, args.device, args.csv_video)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        # Los errores HTTP pueden incluir códigos OIDC en sus URLs. No volcarlos.
        print('ERROR:', type(error).__name__, str(error) if isinstance(error, (AssertionError, RuntimeError, ValueError)) else 'Revisa Docker, los servicios y la configuración de esta PC.')
        raise SystemExit(1)
