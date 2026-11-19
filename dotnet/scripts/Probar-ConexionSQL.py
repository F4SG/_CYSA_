"""Prueba el diagnóstico SQL sin migraciones ni cambios de datos (base demo ya preparada)."""
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
project = root / 'src/Cysa.Web.Api'
dll = project / 'bin/Debug/net10.0/Cysa.Web.Api.dll'
runtime = root / 'runtime/prueba-conexion-sql'
runtime.mkdir(parents=True, exist_ok=True)
environment = dict(os.environ, ASPNETCORE_ENVIRONMENT='Development', Logging__LogLevel__Default='Warning',
                   Storage__Directory=str(runtime))

def run(flag, env, success=True):
    result = subprocess.run(['dotnet', str(dll), flag], cwd=project, env=env,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert (result.returncode == 0) == success, (flag, result.returncode, result.stdout, result.stderr)
    return json.loads(result.stdout.strip().splitlines()[-1])

before = run('--verificar-demo', environment)
connected = run('--probar-conexion', environment)
assert connected['Conectada'] and connected['BaseDatos'] == 'CYSA_WebIII_Demo' and connected['BaseExiste']
for connection in [
    'Server=servidor-remoto;Database=CYSA_WebIII_Demo;Integrated Security=True',
    'Server=localhost;Database=otra_base;Integrated Security=True',
    'cadena sin formato',
    'Server=localhost;Database=CYSA_WebIII_Demo;User ID=usuario_sintetico_inexistente;Password=valor_sintetico_no_valido;TrustServerCertificate=True;Connect Timeout=2',
]:
    blocked = run('--probar-conexion', dict(environment, ConnectionStrings__Cysa=connection), False)
    assert blocked['Conectada'] is False
    assert 'valor_sintetico_no_valido' not in json.dumps(blocked)
blocked = run('--probar-conexion', dict(environment, ASPNETCORE_ENVIRONMENT='Production'), False)
assert blocked['Conectada'] is False
after = run('--verificar-demo', environment)
assert before['Tablas'] == after['Tablas'] and before['Comprobaciones'] == after['Comprobaciones']
report = {'resultado': 'PASS', 'conexionLocal': True, 'baseExiste': connected['BaseExiste'],
          'sinMigracionesNiCambiosDeDatos': True, 'conexionRemotaBloqueada': True,
          'otraBaseBloqueada': True, 'erroresSinCredenciales': True, 'produccionBloqueada': True}
(runtime / 'resultado.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
