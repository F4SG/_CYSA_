"""Verifica diagnóstico, ausencia de mutaciones y detección de datos ajenos a la semilla.

Recrea únicamente CYSA_WebIII_Demo. Requiere la Web API compilada y SQL Server local.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, default=5186)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
project = root / 'src/Cysa.Web.Api'
dll = project / 'bin/Debug/net10.0/Cysa.Web.Api.dll'
runtime = root / 'runtime/verificacion-semilla'
runtime.mkdir(parents=True, exist_ok=True)
base = f'http://localhost:{args.port}'
environment = dict(os.environ, ASPNETCORE_ENVIRONMENT='Development', Security__Mode='Demo',
                   Demo__Enabled='true', Storage__Directory=str(runtime), Logging__LogLevel__Default='Warning')

def cli(flag, env=None, expected=0):
    result = subprocess.run(['dotnet', str(dll), flag], cwd=project, env=env or environment,
                            capture_output=True, text=True, encoding='utf-8', timeout=90)
    assert (result.returncode == 0) == (expected == 0), (flag, result.returncode, result.stderr)
    return json.loads(result.stdout.strip().splitlines()[-1]) if expected == 0 else None

def request(path, method='GET', body=None, token=None, expected=200):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if path == '/api/demo/base' and method == 'POST':
        headers['X-CYSA-Confirmar'] = 'CYSA_WebIII_Demo'
    req = urllib.request.Request(base + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        response = urllib.request.urlopen(req, timeout=90)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        data = json.loads(response.read())
        assert response.status == expected, (path, response.status, data)
        return data

cli('--recrear-demo')
before = cli('--verificar-demo')
assert before['Cumple'] and len(before['Tablas']) == 26
after = cli('--verificar-demo')
assert before['Tablas'] == after['Tablas'] and before['Comprobaciones'] == after['Comprobaciones']
cli('--verificar-demo', dict(environment, ASPNETCORE_ENVIRONMENT='Production'), expected=1)
assert cli('--verificar-demo')['Tablas'] == before['Tablas']

with (runtime / 'server.log').open('w', encoding='utf-8') as log:
    process = subprocess.Popen(['dotnet', str(dll), '--urls', base], cwd=project,
                               env=environment, stdout=log, stderr=log)
    try:
        for _ in range(100):
            assert process.poll() is None, 'No inició la API de prueba; revisar server.log'
            try:
                urllib.request.urlopen(base + '/health', timeout=1).close()
                break
            except OSError:
                time.sleep(.2)
        else:
            raise AssertionError('La API no respondió')
        admin = request('/api/demo/acceso/administrador')['token']
        operator = request('/api/demo/acceso/operador')['token']
        request('/api/demo/verificacion', expected=401)
        report = request('/api/demo/verificacion', token=operator)
        assert report['cumple'] and report['tablas'] == before['Tablas']
        # Una marca no sintética debe detectarse, aunque las cantidades sean suficientes.
        request('/api/corredores', 'POST', {'nombre': 'Prueba negativa de semilla',
                'descripcion': 'Registro temporal que debe detectar el diagnóstico', 'prueba': False}, admin, 201)
        bad = request('/api/demo/verificacion', token=operator)
        assert not bad['cumple']
        failed = [c['codigo'] for c in bad['comprobaciones'] if c['incumplimientos']]
        assert 'sinteticos-Corredor' in failed and 'sinteticos-Bitacora' in failed
        # La consulta no corrige ni borra el dato observado.
        repeated = request('/api/demo/verificacion', token=operator)
        assert repeated['tablas'] == bad['tablas'] and repeated['comprobaciones'] == bad['comprobaciones']
        request('/api/demo/base', 'POST', {}, admin)
        restored = request('/api/demo/verificacion', token=operator)
        assert restored['cumple'] and restored['tablas'] == before['Tablas']
        result = {'resultado': 'PASS', 'comprobacionesCoherencia': len(report['comprobaciones']),
                  'sinMutaciones': True, 'inconsistenciaDetectada': failed, 'semillaRestaurada': True,
                  'produccionBloqueada': True, 'accesoAnonimo': 401}
        (runtime / 'resultado.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False))
    finally:
        process.terminate()
        try:
            process.wait(10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(10)
