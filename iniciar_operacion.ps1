# Banco S2 desde fuentes: SQL Server + SUMO + Keycloak/MQTT del entorno IoT.
param([int]$Puerto=5184,[string]$InstanciaSQL='localhost',[string]$BaseSQL='CYSA_Control_S2',
      [string]$Instalacion='',[string]$Python='')
$ErrorActionPreference='Stop'
$repo=$PSScriptRoot
Set-Location -LiteralPath $repo
if($Puerto -lt 1024 -or $Puerto -gt 65535){throw 'Puerto fuera de rango.'}
if(-not $Instalacion){
  $Instalacion=$repo
  if(-not (Test-Path (Join-Path $Instalacion 'infra/.env'))){$Instalacion=Join-Path $env:LOCALAPPDATA 'CYSA/workspace'}
}
if(-not (Test-Path (Join-Path $Instalacion 'infra/.env'))){throw 'Configura e inicia el entorno IoT según el README. No se regeneran sus cuentas ni secretos.'}
$Instalacion=(Resolve-Path -LiteralPath $Instalacion).Path
if(-not $Python){$Python=Join-Path $repo '.venv/Scripts/python.exe'}
if(-not (Test-Path -LiteralPath $Python)){
  & py -3.12 -m venv (Join-Path $repo '.venv')
  if($LASTEXITCODE -ne 0){throw 'Se necesita Python 3.12 para crear el entorno del banco.'}
  $Python=Join-Path $repo '.venv/Scripts/python.exe'
}
$requisitos=@('backend/requirements.txt','simulacion/requirements.txt','controlador/requirements.txt','operacion/requirements.txt')
$contenido=($requisitos | ForEach-Object {Get-Content -LiteralPath $_ -Raw}) -join "`n"
$sha=[Security.Cryptography.SHA256]::Create()
try{$hash=[BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($contenido))).Replace('-','')}
finally{$sha.Dispose()}
$marca=Join-Path (Split-Path -Parent $Python) 'cysa-s2-requisitos.txt'
if(-not (Test-Path $marca) -or (Get-Content $marca -Raw).Trim() -ne $hash){
  & $Python -m pip install --disable-pip-version-check -r backend/requirements.txt -r simulacion/requirements.txt -r controlador/requirements.txt -r operacion/requirements.txt
  if($LASTEXITCODE -ne 0){throw 'No se completó la instalación de dependencias.'}
  Set-Content -LiteralPath $marca -Value $hash
}
$env:PYTHONPATH=(@('','shared','backend','inventario','simulacion','controlador') | ForEach-Object {Join-Path $repo $_}) -join ';'
$env:CYSA_INSTALACION_DIR=$Instalacion
$env:CYSA_SQL_SERVER=$InstanciaSQL;$env:CYSA_SQL_DATABASE=$BaseSQL
$env:CYSA_OPERACION_PORT="$Puerto";$env:CYSA_OPERACION_URL="http://localhost:$Puerto"
& $Python tools/franco/preparar_control.py --repo $Instalacion
if($LASTEXITCODE -ne 0){throw 'No se preparó la clave del banco.'}
& $Python tools/franco/configurar_mfa_control.py --repo $Instalacion
if($LASTEXITCODE -ne 0){throw 'No se pudo configurar MFA. Comprueba que Keycloak esté iniciado.'}
Write-Host "Abrir http://localhost:$Puerto · SQL Server: $InstanciaSQL / $BaseSQL. Ctrl+C detiene el banco." -ForegroundColor Green
& $Python -m operacion.servidor
exit $LASTEXITCODE
