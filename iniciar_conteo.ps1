# Inicia el conteo vehicular del Sprint 1 paso a paso: elegir fuente -> marcar carriles -> contar.
# Doble clic en iniciar_conteo.bat, o desde PowerShell en la carpeta del repositorio:
#   .\iniciar_conteo.ps1                      perfil de video/GPU (deteccion/config/video_santa_cruz.yaml)
#   .\iniciar_conteo.ps1 -Perfil deteccion/config/carriles_cristhian.yaml   perfil del celular (CPU)
#   .\iniciar_conteo.ps1 -Linea               marcar solo 2 puntos por carril en vez de 4 esquinas
#   .\iniciar_conteo.ps1 -Python C:\ruta\python.exe   usar otro entorno de Python
# Los conteos llegan al panel (Flujo vehicular) cada 30 s si el stack Docker esta en marcha.
param([string]$Perfil = 'deteccion/config/video_santa_cruz.yaml', [switch]$Linea, [string]$Salida = '', [string]$Python = '')
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
Set-Location $repo
$py = if ($Python) { $Python } else { Join-Path $repo '.venv\Scripts\python.exe' }
if (-not (Test-Path $py)) { throw "No se encontro $py. Crear el entorno virtual como indica el README (seccion 6)." }
if (-not (Test-Path (Join-Path $repo 'infra\runtime\clientes\deteccion.env'))) {
  throw 'Faltan las credenciales locales (infra\runtime\clientes\deteccion.env). Ejecutar primero la instalacion del README.'
}
try { Invoke-RestMethod -TimeoutSec 3 http://localhost:8088/health | Out-Null }
catch { Write-Host 'Aviso: el panel no responde en http://localhost:8088. Iniciar Docker (README seccion 7) para ver los conteos.' -ForegroundColor Yellow }
if (-not $Salida) { $Salida = 'resultados/conteos_' + (Get-Date -Format 'yyyyMMdd_HHmm') + '.csv' }
$modo = if ($Linea) { 'linea' } else { 'zona' }
Write-Host '1) Elegir la fuente  2) Marcar los carriles (flecha roja = sentido, D invierte, S guarda)  3) Contar (Q termina)' -ForegroundColor Cyan
& $py tools/cristhian/detector.py iniciar --config $Perfil --fuente --marcar $modo --salida $Salida
$codigo = $LASTEXITCODE
Write-Host "Conteos guardados en $Salida" -ForegroundColor Green
exit $codigo
