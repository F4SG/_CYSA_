using System.Text.Json;

namespace Cysa.Launcher;

internal sealed partial class Instance
{
    string? arduinoControllerPort;
    string? arduinoSession;
    string? controllerStopFile;
    string? arduinoResumePlan;
    bool arduinoPaused;
    public bool ArduinoRunning => arduinoControllerPort is not null && apis.TryGetValue("Controlador S2", out var controller) && !controller.HasExited;
    public bool ArduinoCanResume => arduinoControllerPort is not null && !ArduinoRunning;

    void SaveArduinoControl() => File.WriteAllText(Path.Combine(Root, "arduino-control.json"),
        JsonSerializer.Serialize(new { Port = arduinoControllerPort, Session = arduinoSession, Plan = arduinoResumePlan }));

    void RestoreArduinoControl()
    {
        var path = Path.Combine(Root, "arduino-control.json");
        if (!File.Exists(path)) return;
        try {
            using var saved = JsonDocument.Parse(File.ReadAllText(path));
            var data = saved.RootElement;
            var port = data.GetProperty("Port").GetString();
            if (port is null || !System.Text.RegularExpressions.Regex.IsMatch(port, @"^COM\d+$")) return;
            arduinoControllerPort = port;
            arduinoSession = data.GetProperty("Session").GetString() ?? Guid.NewGuid().ToString("N");
            arduinoResumePlan = data.GetProperty("Plan").GetString();
            arduinoPaused = true; // Reiniciar el lanzador nunca arranca la placa sin pulsar Reanudar.
        }
        catch (Exception error) when (error is IOException or JsonException or KeyNotFoundException or InvalidOperationException) {
            Write("No se pudo recuperar la selección Arduino; repite Probar Arduino.");
        }
    }

    public async Task StopArduino()
    {
        if (!ArduinoRunning) throw new InvalidOperationException("No hay un controlador Arduino ejecutándose.");
        var path = Path.Combine(Repo,"infra/runtime/control/arduino-estado.json");
        var stopped = new Dictionary<string,JsonElement>();
        try {
            using var snapshot = JsonDocument.Parse(await File.ReadAllTextAsync(path));
            var data = snapshot.RootElement;
            if (data.GetProperty("sesion").GetString() != arduinoSession) throw new InvalidOperationException("Sesión distinta");
            var active = data.GetProperty("plan_activo").GetString();
            if (active is not null && active is not ("INTERMITENTE" or "LOCAL_SEGURO")) arduinoResumePlan = active == "DEMO_FIJO" ? null : active;
            stopped = JsonSerializer.Deserialize<Dictionary<string,JsonElement>>(data.GetRawText())!;
        }
        catch (Exception error) when (error is IOException or JsonException or KeyNotFoundException or InvalidOperationException) {
            arduinoResumePlan ??= "NO_CONFIRMADO";
            Write("No se pudo identificar el plan para reanudar. Se detiene igualmente el Arduino; revisa el registro antes de reanudar.");
        }
        arduinoPaused = true;
        SaveArduinoControl();
        await StopController();
        await Task.Delay(1200);
        stopped["sesion"] = JsonSerializer.SerializeToElement(arduinoSession);
        stopped["puerto"] = JsonSerializer.SerializeToElement(arduinoControllerPort);
        stopped["timestamp"] = JsonSerializer.SerializeToElement(DateTimeOffset.UtcNow);
        stopped["detenido"] = JsonSerializer.SerializeToElement(true);
        stopped["fase_actual"] = JsonSerializer.SerializeToElement("ARDUINO_DETENIDO");
        stopped["estado_controlador"] = JsonSerializer.SerializeToElement("desconectado");
        stopped["luces"] = JsonSerializer.SerializeToElement<object?>(null);
        await File.WriteAllTextAsync(path, JsonSerializer.Serialize(stopped));
        Write("Arduino DETENIDO. Sin órdenes por USB, el MMU queda en rojo intermitente. Pulsa Reanudar Arduino para continuar.");
    }

    public async Task ResumeArduino()
    {
        if (!ArduinoCanResume) throw new InvalidOperationException("Primero prueba y selecciona el Arduino; no debe haber otro controlador ejecutándose.");
        arduinoPaused = true;
        await StartAll();
        arduinoPaused = false;
        try {
            StartController(OperationEnvironment());
            var path = Path.Combine(Repo,"infra/runtime/control/arduino-estado.json");
            var started = DateTimeOffset.UtcNow;
            for (var attempt = 0; attempt < 600; attempt++) {
                if (apis["Controlador S2"].HasExited) throw new InvalidOperationException("El Arduino no pudo reanudarse. Revisa puerto, firmware y el plan autorizado en el registro.");
                if (File.Exists(path)) {
                    using var snapshot = JsonDocument.Parse(await File.ReadAllTextAsync(path));
                    var data = snapshot.RootElement;
                    if (data.GetProperty("sesion").GetString() == arduinoSession && data.GetProperty("timestamp").GetDateTimeOffset() >= started) {
                        if (data.GetProperty("fase_actual").GetString() == "INTERMITENTE") throw new InvalidOperationException("El MMU reportó una falla al reanudar.");
                        if (data.GetProperty("estado_controlador").GetString() == "conectado" &&
                            data.GetProperty("plan_activo").GetString() == (arduinoResumePlan ?? "DEMO_FIJO")) {
                            SaveArduinoControl();
                            Write($"Arduino REANUDADO en {arduinoControllerPort}. Plan {arduinoResumePlan ?? "DEMO_FIJO"} activo tras transición segura.");
                            return;
                        }
                    }
                }
                await Task.Delay(100);
            }
            throw new InvalidOperationException("No se confirmó la recuperación del plan autorizado en el Arduino.");
        }
        catch { await StopController(); arduinoPaused = true; SaveArduinoControl(); throw; }
    }
    public string OperationUrl=>$"http://localhost:{Ports.Operation}";

    Dictionary<string,string> OperationEnvironment()=>new()
    {
        ["PYTHONPATH"]=string.Join(Path.PathSeparator,new[]{"","shared","backend","inventario","simulacion","controlador"}.Select(p=>Path.Combine(Repo,p))),
        ["CYSA_INSTALACION_DIR"]=Repo,
        ["CYSA_SQL_SERVER"]=SqlServerActual(),
        ["CYSA_SQL_DATABASE"]="CYSA_Control_S2",
        ["CYSA_OPERACION_PORT"]=Ports.Operation.ToString(),
        ["CYSA_OPERACION_URL"]=OperationUrl,
        ["CYSA_WEB_URL"]=WebUrl,
        ["CYSA_PANEL_URL"]=PanelUrl+"/"
    };

    async Task<bool> PrepararEjemplos()
    {
        Write("Validando cinco propuestas de práctica en SUMO…");
        try
        {
            var code = await Run(Venv, ["tools/franco/preparar_planes_demo.py", "--instalacion", Root],
                environment: OperationEnvironment(), check: false, timeoutMinutes: 3);
            if (code == 0) return true;
        }
        catch (InvalidOperationException error)
        {
            Write(error.Message);
        }
        Write("No se pudo renovar el lote de práctica. Se conserva el lote anterior.");
        return false;
    }

    async Task StartOperation()
    {
        var environment=OperationEnvironment();
        if(!apis.TryGetValue("Operacion S2",out var server) || server.HasExited)
        {
            if(!IsFree(Ports.Operation))throw new InvalidOperationException($"El puerto del banco S2 ({Ports.Operation}) está ocupado por otro proceso.");
            var requirements=new[]{"backend/requirements.txt","simulacion/requirements.txt","controlador/requirements.txt","operacion/requirements.txt"};
            var fingerprint=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(string.Join("\n",requirements.Select(p=>File.ReadAllText(Path.Combine(Repo,p)))))));
            var marker=Path.Combine(Root,"s2-requisitos.sha256");
            if(!File.Exists(marker) || File.ReadAllText(marker)!=fingerprint)
            {
                Write("Preparando dependencias del banco S2; se reutiliza el entorno Python de esta PC.");
                await Run(Venv,new[]{"-m","pip","install","--disable-pip-version-check"}.Concat(requirements.SelectMany(p=>new[]{"-r",p})),environment:environment,timeoutMinutes:15);
                await File.WriteAllTextAsync(marker,fingerprint);
            }
            await Run(Venv,["tools/franco/preparar_control.py","--repo",Repo],environment:environment);
            await Run(Venv,["tools/franco/configurar_mfa_control.py","--repo",Repo],environment:environment);
            apis["Operacion S2"]=Start(Venv,["-m","operacion.servidor"],environment:environment);
        }
        await WaitOperationReady();
        if(!arduinoPaused && (!apis.TryGetValue("Controlador S2",out var controller) || controller.HasExited))
        {
            // El arranque general usa software. Nunca elige ni abre un puerto serial.
            StartController(environment);
            await Task.Delay(1000);
            if(apis["Controlador S2"].HasExited)throw new InvalidOperationException("El controlador S2 no pudo iniciar. Revisa el registro.");
        }
        var path=Path.Combine(Repo,"panel/config.json");
        var config=JsonSerializer.Deserialize<Dictionary<string,JsonElement>>(await File.ReadAllTextAsync(path))!;
        config["operacionBase"]=JsonSerializer.SerializeToElement(OperationUrl);
        await File.WriteAllTextAsync(path,JsonSerializer.Serialize(config));
        Write(arduinoPaused ? "Arduino detenido. Pulsa Reanudar Arduino para continuar; los servicios del panel siguen disponibles." : arduinoControllerPort is null
            ? "Banco S2 listo con SQL Server, MQTT y MMU simulado. La placa física y la fuente de cámara se seleccionan aparte."
            : $"Banco S2 listo con Arduino físico en {arduinoControllerPort}; recibe planes autorizados con MFA.");
    }

    void StartController(Dictionary<string,string> environment)
    {
        controllerStopFile = Path.Combine(Root, "controlador-" + Guid.NewGuid().ToString("N") + ".stop");
        var args = new List<string> { "-m", "cysa_controlador.run", "--config", "controlador/config/demo_int_01.yaml",
            "--mqtt", "--credenciales", Path.Combine(Repo,"infra/runtime/clientes/emulador.env"),
            "--clave-planes", Path.Combine(Repo,"infra/runtime/control/clave.key"), "--stop-file", controllerStopFile };
        if (arduinoControllerPort is null) args.Add("--sin-placa");
        else args.AddRange(["--puerto", arduinoControllerPort, "--telemetria", Path.Combine(Repo,"infra/runtime/control/arduino-estado.json"),
            "--sesion", arduinoSession!]);
        if (arduinoControllerPort is not null && arduinoResumePlan is not null) args.AddRange(["--reanudar-plan", arduinoResumePlan]);
        apis["Controlador S2"] = Start(Venv, args, environment: environment);
    }

    async Task StopController()
    {
        if (!apis.Remove("Controlador S2", out var controller)) return;
        try {
            if (!controller.HasExited) {
                if (controllerStopFile is not null) await File.WriteAllTextAsync(controllerStopFile, "stop");
                using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(8));
                try { await controller.WaitForExitAsync(timeout.Token); }
                catch (OperationCanceledException) { controller.Kill(true); await controller.WaitForExitAsync(); }
            }
        }
        finally {
            controller.Dispose();
            if (controllerStopFile is not null && File.Exists(controllerStopFile)) File.Delete(controllerStopFile);
            controllerStopFile = null;
        }
    }

    public async Task StartArduinoIntegration(string port)
    {
        RequireConfigured();
        // Preparar los servicios antes de sustituir el controlador que ya estaba funcionando.
        await StartAll(true);
        await StopController();
        arduinoControllerPort = port;
        arduinoSession = Guid.NewGuid().ToString("N");
        arduinoPaused = false;
        arduinoResumePlan = null;
        SaveArduinoControl();
        StartController(OperationEnvironment());
        try {
            var path = Path.Combine(Repo,"infra/runtime/control/arduino-estado.json");
            for (var attempt = 0; attempt < 150; attempt++) {
                if (apis["Controlador S2"].HasExited) throw new InvalidOperationException("El controlador Arduino terminó. Revisa puerto, firmware y registro.");
                if (File.Exists(path)) {
                    using var snapshot = JsonDocument.Parse(await File.ReadAllTextAsync(path));
                    var data = snapshot.RootElement;
                    if (data.GetProperty("sesion").GetString() == arduinoSession) {
                        if (data.GetProperty("fase_actual").GetString() == "INTERMITENTE")
                            throw new InvalidOperationException("El Arduino reportó una falla del MMU. Revisa el registro y repite la prueba.");
                        if (data.GetProperty("estado_controlador").GetString() == "conectado") {
                            Write($"Integración física lista en {port}. Autoriza con MFA; el panel esperará el recibo de aplicación y mostrará las luces ordenadas.");
                            Open(PanelUrl + "/?modulo=planes&volver=1&arduino=" + Uri.EscapeDataString(port) + "&sesion=" + arduinoSession);
                            return;
                        }
                    }
                }
                await Task.Delay(100);
            }
            throw new InvalidOperationException("El Arduino no confirmó conexión con el centro. Revisa MQTT y el registro.");
        }
        catch { await StopController(); arduinoControllerPort = arduinoSession = null; throw; }
    }

    async Task WaitOperationReady()
    {
        for(var attempt=0;attempt<60;attempt++)
        {
            if(apis.TryGetValue("Operacion S2",out var process) && process.HasExited)
                throw new InvalidOperationException("El banco S2 terminó durante el arranque. Revisa SQL Server y el registro.");
            try
            {
                using var response=await http.GetAsync(OperationUrl+"/health");
                if(response.IsSuccessStatusCode)
                {
                    using var data=JsonDocument.Parse(await response.Content.ReadAsStringAsync());
                    if(data.RootElement.TryGetProperty("mqtt_conectado",out var mqtt) && mqtt.GetBoolean())return;
                }
            }
            catch(HttpRequestException){} catch(TaskCanceledException){}
            await Task.Delay(1000);
        }
        throw new InvalidOperationException("El banco S2 no está listo: SQL Server y MQTT deben estar disponibles. Revisa el registro.");
    }
}
