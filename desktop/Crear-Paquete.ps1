param([string]$Salida)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Salida) { $Salida = Join-Path $repo ('artifacts\desktop\' + (Get-Date -Format yyyyMMdd-HHmmss)) }
$null = New-Item -ItemType Directory -Force -Path $Salida
$salidaReal = (Resolve-Path -LiteralPath $Salida).Path
$package = Join-Path $salidaReal 'CYSA-Windows'
if (Test-Path -LiteralPath $package) { throw 'El directorio de paquete ya existe. Usa otra carpeta de salida.' }
$null = New-Item -ItemType Directory -Path $package
function Invoke-Dotnet([string[]]$Arguments) {
    & dotnet @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Falló la publicación .NET.' }
}
Invoke-Dotnet @('publish', "$PSScriptRoot\Cysa.Launcher\Cysa.Launcher.csproj", '-c', 'Release', '-o', $package, '--nologo')
foreach ($api in @('Cysa.Evaluaciones.Api','Cysa.Decisiones.Api')) {
    Invoke-Dotnet @('publish', "$repo\dotnet\src\$api\$api.csproj", '-c','Release','-r','win-x64','--self-contained','true','-p:PublishSingleFile=true','-p:IncludeNativeLibrariesForSelfExtract=true','-o',"$package\services\$api",'--nologo')
}
$app = Join-Path $package 'app'
$null = New-Item -ItemType Directory -Path $app
# Solo fuentes rastreadas y cambios de esta entrega. Nunca copiar el árbol de trabajo entero.
$tracked = @(& git -C $repo ls-files)
if ($LASTEXITCODE -ne 0) { throw 'No se pudo obtener la lista de archivos del repositorio.' }
$desktop = Get-ChildItem -LiteralPath $PSScriptRoot -Recurse -File | Where-Object { $_.FullName -notmatch '[\\/](bin|obj|__pycache__)[\\/]' -and $_.Extension -ne '.pyc' } | ForEach-Object { [IO.Path]::GetRelativePath($repo,$_.FullName).Replace('\','/') }
$files = @($tracked + $desktop + @('tests/test_launcher.py') | Sort-Object -Unique)
foreach ($relative in $files) {
    if ($relative -match '(^|/)(runtime|\.git|\.venv|resultados|respaldos|artifacts|bin|obj|__pycache__|\.launcher-setup)(/|$)' -or $relative -match '(^|/)\.env$' -or $relative -match '\.(key|pem|pt|mp4|avi|dump|tgz|pyc)$') {
        throw "Archivo privado o de ejecución en la lista de empaquetado: $relative"
    }
    $source = Join-Path $repo $relative
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { continue }
    $target = Join-Path $app $relative
    $null = New-Item -ItemType Directory -Force -Path (Split-Path $target)
    Copy-Item -LiteralPath $source -Destination $target
}
$dependencies = Join-Path $package 'dependencies'
$null = New-Item -ItemType Directory -Path $dependencies
$installer = Join-Path $dependencies 'python-3.12.10-amd64.exe'
Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $installer
$signature = Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') { throw 'La firma oficial del instalador Python no es válida.' }
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash
[IO.File]::WriteAllText($installer + '.sha256',$hash)
$commit = (& git -C $repo rev-parse HEAD).Trim()
$manifest = @{ repositorio='https://github.com/F4SG/_CYSA_.git'; rama='feature/integracion-completa'; baseCommit=$commit; construidoUtc=[DateTimeOffset]::UtcNow.ToString('O'); pythonSha256=$hash; plataforma='Windows x64'; cambiosLocales=(@(& git -C $repo status --porcelain).Count -gt 0) }
$manifest | ConvertTo-Json | Set-Content -LiteralPath "$package\version.json" -Encoding utf8
Copy-Item -LiteralPath "$PSScriptRoot\LEEME.txt" -Destination "$package\LEEME.txt"
Get-ChildItem -LiteralPath $package -Filter '*.pdb' -Recurse | Remove-Item
$zip = Join-Path $salidaReal 'CYSA-Windows.zip'
Compress-Archive -LiteralPath $package -DestinationPath $zip -CompressionLevel Optimal
Get-FileHash -LiteralPath $zip -Algorithm SHA256 | ForEach-Object { [IO.File]::WriteAllText($zip + '.sha256',$_.Hash) }
Write-Output "Paquete listo: $zip"
