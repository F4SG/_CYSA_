$ErrorActionPreference = 'Stop'
$solution = Split-Path $PSScriptRoot -Parent
$runDir = Join-Path $solution ('runtime/smoke/' + [guid]::NewGuid().ToString())
$dotnetExe = (Get-Command dotnet -ErrorAction Stop).Source
$processes = [Collections.Generic.List[Diagnostics.Process]]::new()
$variables = @('ASPNETCORE_ENVIRONMENT','Security__Mode','Storage__Directory','Evaluaciones__BaseUrl')
$previous = @{}
foreach ($name in $variables) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }

function Get-FreePort {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try { $listener.LocalEndpoint.Port } finally { $listener.Stop() }
}
function Start-Api([string]$Name, [int]$Port, [string]$LogSuffix) {
    $dll = Join-Path $solution "src/$Name/bin/Debug/net10.0/$Name.dll"
    if (-not (Test-Path -LiteralPath $dll)) { throw 'Compila CYSA.Web.sln antes de ejecutar esta prueba.' }
    $process = Start-Process -FilePath $dotnetExe -ArgumentList @(('"' + $dll + '"'), '--urls', "http://localhost:$Port") `
        -WorkingDirectory (Join-Path $solution "src/$Name") -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runDir "$Name-$LogSuffix.log") `
        -RedirectStandardError (Join-Path $runDir "$Name-$LogSuffix.err.log")
    $processes.Add($process)
    for ($i = 0; $i -lt 100; $i++) {
        if ($process.HasExited) { throw "$Name terminó antes de arrancar. Revisa $runDir" }
        try {
            $health = Invoke-RestMethod "http://localhost:$Port/health" -TimeoutSec 1
            if ($health.status -eq 'ok') { return $process }
        } catch { Start-Sleep -Milliseconds 100 }
    }
    throw "$Name no respondió a tiempo. Revisa $runDir"
}
function Assert-True([bool]$Value, [string]$Message) { if (-not $Value) { throw $Message } }
function Post-Json([string]$Url, [object]$Body, [string]$Token) {
    Invoke-RestMethod -Method Post -Uri $Url -Headers @{Authorization="Bearer $Token"} `
        -ContentType 'application/json; charset=utf-8' -Body ($Body | ConvertTo-Json -Depth 12)
}
function Assert-Status([scriptblock]$Action, [int]$Expected) {
    try { $null = & $Action } catch {
        if ([int]$_.Exception.Response.StatusCode -eq $Expected) { return }
        throw
    }
    throw "Se esperaba HTTP $Expected y la petición tuvo éxito."
}

try {
    & (Join-Path $PSScriptRoot 'Preparar-Demo.ps1') -Directorio $runDir
    $tokens = Get-Content (Join-Path $runDir 'tokens.json') -Raw | ConvertFrom-Json
    $env:ASPNETCORE_ENVIRONMENT = 'Development'
    $env:Security__Mode = 'Demo'
    $env:Storage__Directory = $runDir
    $portEval = Get-FreePort
    do { $portDecision = Get-FreePort } while ($portDecision -eq $portEval)
    $baseEval = "http://localhost:$portEval"
    $baseDecision = "http://localhost:$portDecision"
    $env:Evaluaciones__BaseUrl = $baseEval
    $null = Start-Api 'Cysa.Evaluaciones.Api' $portEval 'inicio'
    $decisionProcess = Start-Api 'Cysa.Decisiones.Api' $portDecision 'inicio'
    foreach ($base in @($baseEval, $baseDecision)) {
        $spec = Invoke-RestMethod "$base/swagger/v1/swagger.json"
        Assert-True ($null -ne $spec.paths) 'Swagger no expone operaciones.'
    }
    $plan = @{ planId='SMOKE'; version=1; interseccionId='DEMO_INT_01'; planBaseId='FIJO';
        escenario='Prueba HTTP real'; origen='demo';
        accesos=@(@{id='N'; demoraBaseSegundos=40; demoraCandidataSegundos=48; longitudCruceMetros=18});
        fases=@(@{id='P1'; accesos=@('N'); tiempoPeatonalSegundos=25}) }
    $rejected = Post-Json "$baseEval/api/evaluaciones" $plan $tokens.evaluador
    Assert-True (-not $rejected.aprobada) 'Debió rechazar un aumento del 20 %.'
    $plan.version=2
    $plan.accesos[0].demoraCandidataSegundos=42
    $approved = Post-Json "$baseEval/api/evaluaciones" $plan $tokens.evaluador
    Assert-True $approved.aprobada 'Debió aprobar el segundo escenario.'
    $decision = @{ solicitudId=[guid]::NewGuid().ToString(); evaluacionId=$approved.id; version=2;
        accion='autorizar'; motivo='Escenario comprobado durante prueba HTTP' }
    Assert-Status { Post-Json "$baseDecision/api/planes/SMOKE/decisiones" $decision $tokens.administrador } 403
    Assert-Status { Post-Json "$baseDecision/api/planes/SMOKE/decisiones" $decision $tokens.operadorSinMfa } 403
    $saved = Post-Json "$baseDecision/api/planes/SMOKE/decisiones" $decision $tokens.operador
    Assert-True ($saved.estadoPosterior -eq 'autorizado') 'La autorización no se guardó.'
    $retry = Post-Json "$baseDecision/api/planes/SMOKE/decisiones" $decision $tokens.operador
    Assert-True ($retry.id -eq $saved.id) 'El reintento duplicó la operación.'
    $decisionProcess.Kill()
    $decisionProcess.WaitForExit()
    $null = Start-Api 'Cysa.Decisiones.Api' $portDecision 'reinicio'
    $history = @(Invoke-RestMethod "$baseDecision/api/planes/SMOKE/historial" -Headers @{Authorization="Bearer $($tokens.operador)"})
    Assert-True ($history.Count -eq 1 -and $history[0].id -eq $saved.id) 'El historial no persistió tras reiniciar.'
    Write-Host 'CORRECTO: dos procesos HTTP, Swagger, rechazo/aprobación, permisos, MFA simulado, idempotencia y persistencia tras reiniciar.'
} finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
        $process.Dispose()
    }
    foreach ($name in $variables) { [Environment]::SetEnvironmentVariable($name, $previous[$name], 'Process') }
}
