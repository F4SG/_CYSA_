param([string]$Directorio)
$ErrorActionPreference = 'Stop'
if (-not $Directorio) { $Directorio = Join-Path (Split-Path $PSScriptRoot -Parent) 'runtime' }
$null = New-Item -ItemType Directory -Force -Path $Directorio
$keyPath = Join-Path $Directorio 'demo.key'
if (-not (Test-Path -LiteralPath $keyPath)) {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    [IO.File]::WriteAllText($keyPath, [Convert]::ToBase64String($bytes))
}
$key = [Convert]::FromBase64String([IO.File]::ReadAllText($keyPath).Trim())
function ConvertTo-Base64Url([byte[]]$Bytes) {
    [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
}
function New-DemoToken([string]$Subject, [string]$Role, [bool]$Mfa, [string]$Scope = '') {
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $payload = @{ iss='cysa-demo-local'; aud='cysa-dotnet'; sub=$Subject; role=$Role;
        iat=$now; nbf=$now; exp=($now+1800); auth_time=$now; scope=$Scope }
    if ($Mfa) { $payload.amr = @('pwd','otp') }
    $header = ConvertTo-Base64Url ([Text.Encoding]::UTF8.GetBytes('{"alg":"HS256","typ":"JWT"}'))
    $body = ConvertTo-Base64Url ([Text.Encoding]::UTF8.GetBytes(($payload | ConvertTo-Json -Compress)))
    $unsigned = "$header.$body"
    $hmac = New-Object Security.Cryptography.HMACSHA256
    try {
        $hmac.Key = $key
        $signature = ConvertTo-Base64Url ($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($unsigned)))
    } finally { $hmac.Dispose() }
    "$unsigned.$signature"
}
$tokens = @{
    evaluador = New-DemoToken 'servicio-evaluador-demo' 'servicio' $false 'evaluaciones:importar'
    operador = New-DemoToken 'operador-demo' 'operador' $true
    operadorSinMfa = New-DemoToken 'operador-demo' 'operador' $false
    administrador = New-DemoToken 'administrador-demo' 'administrador' $true
}
[IO.File]::WriteAllText((Join-Path $Directorio 'tokens.json'), ($tokens | ConvertTo-Json))
$http = @"
@evaluaciones = http://localhost:5181
@decisiones = http://localhost:5182
@evaluador = $($tokens.evaluador)
@operador = $($tokens.operador)

### Crear una evaluación; cambia planId o version si ya existe
POST {{evaluaciones}}/api/evaluaciones
Authorization: Bearer {{evaluador}}
Content-Type: application/json

{"planId":"PLAN_DEMO","version":1,"interseccionId":"DEMO_INT_01","planBaseId":"FIJO_DEMO","escenario":"Demostración local","origen":"demo","accesos":[{"id":"N","demoraBaseSegundos":40,"demoraCandidataSegundos":42,"longitudCruceMetros":18}],"fases":[{"id":"PEATONAL_N","accesos":["N"],"tiempoPeatonalSegundos":25}]}

### Copia el id de la evaluación devuelta aquí
POST {{decisiones}}/api/planes/PLAN_DEMO/decisiones
Authorization: Bearer {{operador}}
Content-Type: application/json

{"solicitudId":"$([guid]::NewGuid())","evaluacionId":"REEMPLAZAR_UUID","version":1,"accion":"autorizar","motivo":"Cumple los criterios de la prueba local"}

### Consultar la bitácora
GET {{decisiones}}/api/planes/PLAN_DEMO/historial
Authorization: Bearer {{operador}}
"@
[IO.File]::WriteAllText((Join-Path $Directorio 'Demo.http'), $http)
Write-Host 'Demo preparada. Abre runtime/Demo.http en Visual Studio, o usa los tokens en Authorize de Swagger.'
Write-Host 'MFA es simulado solo en esta demo. Repite este script cada 5 minutos para renovar la autenticación de decisiones.'
Write-Host 'Los tokens, claves y bases locales quedan excluidos de Git.'
