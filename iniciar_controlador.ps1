# Inicia el controlador semaforico emulado del banco de pruebas (Sprint 2).
# Doble clic en iniciar_controlador.bat, o desde PowerShell en la carpeta del repositorio:
#   .\iniciar_controlador.ps1                         elige el puerto de la placa o usa el MMU simulado
#   .\iniciar_controlador.ps1 -Puerto COM3            placa Arduino en COM3
#   .\iniciar_controlador.ps1 -SinPlaca               sin placa (MMU simulado)
#   .\iniciar_controlador.ps1 -Mqtt                   latidos y estado por el broker (stack Docker en marcha)
#   .\iniciar_controlador.ps1 -SimularCorte 30:120    centro simulado que se corta entre los 30 y 120 s (prueba RF-06)
#   .\iniciar_controlador.ps1 -ProbarPlaca -Puerto COM3   prueba automatica de la placa (LEDs y fallas del MMU)
param([string]$Puerto = '', [switch]$SinPlaca, [switch]$Mqtt, [switch]$RecibirPlanes, [string]$SimularCorte = '', [switch]$ProbarPlaca,
      [string]$Config = 'controlador/config/demo_int_01.yaml', [string]$Python = '', [string]$Instalacion = '')
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
Set-Location $repo
$py = if ($Python) { $Python } else { Join-Path $repo '.venv\Scripts\python.exe' }
if (-not (Test-Path $py)) { throw "No se encontro $py. Crear el entorno virtual como indica el README (seccion 2)." }
& $py -c "import serial" 2>$null
if ($LASTEXITCODE -ne 0) { & $py -m pip install -r controlador/requirements.txt }
$env:PYTHONPATH = (@('shared', 'controlador') | ForEach-Object { Join-Path $repo $_ }) -join ';'
$argumentos = @('-m', 'cysa_controlador.run', '--config', $Config)
if (-not $Puerto -and -not $SinPlaca) {
  Write-Host 'Puertos serie disponibles:' -ForegroundColor Cyan
  & $py -m serial.tools.list_ports -v
  $Puerto = Read-Host 'Puerto de la placa (ej. COM3). Enter para usar el MMU simulado'
}
if ($ProbarPlaca) {
  if (-not $Puerto) { throw 'La prueba de la placa necesita el puerto (ej. -Puerto COM3).' }
  & $py -m cysa_controlador.probar_placa --config $Config --puerto $Puerto
  exit $LASTEXITCODE
}
if ($Puerto) { $argumentos += @('--puerto', $Puerto) } else { $argumentos += '--sin-placa' }
if ($Mqtt) {
  if (-not $Instalacion) {
    $Instalacion=$repo
    if (-not (Test-Path (Join-Path $Instalacion 'infra/.env'))) {$Instalacion=Join-Path $env:LOCALAPPDATA 'CYSA/workspace'}
  }
  $Instalacion=(Resolve-Path -LiteralPath $Instalacion).Path
  $argumentos += @('--mqtt','--credenciales',(Join-Path $Instalacion 'infra/runtime/clientes/emulador.env'))
}
elseif ($SimularCorte) { $argumentos += @('--simular-corte', $SimularCorte) }
else { $argumentos += '--centro-simulado' }
if ($RecibirPlanes) {
  if (-not $Mqtt) { throw 'RecibirPlanes requiere Mqtt y la clave creada por preparar_control.py.' }
  $argumentos += @('--clave-planes', (Join-Path $Instalacion 'infra/runtime/control/clave.key'))
}
Write-Host 'Ctrl+C detiene el controlador; sin mensajes de la PC la placa pasa a rojo intermitente.' -ForegroundColor Cyan
& $py @argumentos
exit $LASTEXITCODE
