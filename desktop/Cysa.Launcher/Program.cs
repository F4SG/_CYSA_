using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Cysa.Launcher;

internal static class Program
{
    [STAThread]
    static void Main(string[] args)
    {
        if (args.Contains("--self-test")) { SelfTest.Run(args.Last()); return; }
        if (args.Length == 3 && args[0] == "--integration-test") { IntegrationTest.Run(args[1], args[2]).GetAwaiter().GetResult(); return; }
        if (args.Length == 4 && args[0] == "--webiii-startup-test") { WebStartupTest.Run(args[1],args[2],args[3]).GetAwaiter().GetResult(); return; }
        if (args.Length == 4 && args[0] == "--system-startup-test") { SystemStartupTest.Run(args[1],args[2],args[3]).GetAwaiter().GetResult(); return; }
        ApplicationConfiguration.Initialize();
        var root = args.Length == 2 && args[0] == "--data-dir" ? Path.GetFullPath(args[1]) : Instance.Home;
        using var mutex = new Mutex(true, "Local\\CYSA-" + Instance.ProjectFor(root), out var first);
        if (!first) { MessageBox.Show("CYSA ya está abierto para este usuario."); return; }
        try { Application.Run(new MainForm(new Instance(root))); }
        catch (Exception error) { MessageBox.Show(error.Message, "CYSA", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }
}

internal sealed record HardwareReport(string Recommended, bool GpuReady, string GpuDevice, string GpuName, double CpuMs, double? GpuMs, bool NvidiaDetected, string Reason);
internal sealed record SumoScenario(string Executable, string Config, int Expected);

internal sealed record Ports(int Panel, int Identity, int Mqtt, int Evaluation, int Decision, int Web = 15183, int Operation = 15184)
{
    public int[] All => [Panel, Identity, Mqtt, Evaluation, Decision, Web, Operation];
    public static Ports Select(Func<int, bool> free)
    {
        for (var offset = 0; offset < 20000; offset += 100)
        {
            var ports = new Ports(18088 + offset, 18080 + offset, 18883 + offset, 15181 + offset, 15182 + offset, 15183 + offset, 15184 + offset);
            if (ports.All.All(free)) return ports;
        }
        throw new InvalidOperationException("No se encontró un grupo de puertos libres.");
    }
}

internal sealed partial class Instance
{
    public static string Home => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CYSA");
    public static string ProjectFor(string path) => "cysa-" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(path).ToUpperInvariant())))[..12].ToLowerInvariant();
    public string Root { get; }
    public string Package { get; }
    public string? SourceRoot { get; }
    public string Repo => Path.Combine(Root, "workspace");
    public string Python => FindPython() ?? Path.Combine(Root, "python", "python.exe");
    public string Venv => Path.Combine(Repo, ".venv", "Scripts", "python.exe");
    public string Project => ProjectFor(Root);
    public Ports Ports { get; }
    public string PanelUrl => $"http://localhost:{Ports.Panel}";
    public string IdentityUrl => $"http://localhost:{Ports.Identity}";
    public bool Configured => File.Exists(Path.Combine(Repo, "infra", ".env")) && File.Exists(Path.Combine(Repo, "infra", "runtime", "clientes", "usuarios-locales.json"));
    public string Docker { get; }
    public Action<string> Log { get; set; } = _ => { };
    public Process? Detector { get; private set; }
    public Process? SumoGui { get; private set; }
    Process? sumoDriver;
    readonly Dictionary<string, Process> apis = [];
    readonly DockerSession dockerSession = new();
    readonly HttpClient http = new() { Timeout = TimeSpan.FromSeconds(3) };
    readonly string logPath;

    public Instance(string? root = null, string? package = null)
    {
        Root = root ?? Home;
        Package = package ?? AppContext.BaseDirectory;
        SourceRoot=SourceLayout.FindRoot(Package);
        Directory.CreateDirectory(Root);
        Directory.CreateDirectory(Path.Combine(Root, "logs"));
        logPath = Path.Combine(Root, "logs", "lanzador.log");
        var settings = Path.Combine(Root, "puertos.json");
        Ports = File.Exists(settings) ? JsonSerializer.Deserialize<Ports>(File.ReadAllText(settings))! : Ports.Select(IsFree);
        if (!File.Exists(settings)) File.WriteAllText(settings, JsonSerializer.Serialize(Ports));
        Docker = FindDocker();
    }

    public static bool IsFree(int port)
    {
        try { var listener = new TcpListener(IPAddress.Loopback, port); listener.Start(); listener.Stop(); return true; }
        catch (SocketException) { return false; }
    }

    static string FindDocker()
    {
        var candidates = (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator)
            .Select(p => Path.Combine(p, "docker.exe")).Concat(new[] {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Docker", "Docker", "resources", "bin", "docker.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "DockerDesktop", "resources", "bin", "docker.exe") });
        return candidates.FirstOrDefault(File.Exists) ?? "docker.exe";
    }

    string? FindPython()
    {
        var own = Path.Combine(Root, "python", "python.exe");
        if (File.Exists(own)) return own;
        foreach (var hive in new[] { Microsoft.Win32.Registry.CurrentUser, Microsoft.Win32.Registry.LocalMachine })
        {
            using var key = hive.OpenSubKey(@"Software\Python\PythonCore\3.12\InstallPath");
            var path = key?.GetValue("ExecutablePath") as string;
            if (path != null && File.Exists(path)) return path;
        }
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        foreach (var path in new[] { Path.Combine(local,"Python","pythoncore-3.12-64","python.exe"), Path.Combine(local,"Programs","Python","Python312","python.exe") })
            if (File.Exists(path)) return path;
        return null;
    }

    public void Write(string text)
    {
        // Nunca registrar stdout de archivos de credenciales ni argumentos de tokens.
        lock (logPath) File.AppendAllText(logPath, $"{DateTimeOffset.Now:O} {text}{Environment.NewLine}");
        Log(text);
    }

    public async Task<int> Run(string file, IEnumerable<string> args, string? cwd = null, Dictionary<string, string>? environment = null, bool check = true, bool output = true, int timeoutMinutes = 30)
    {
        using var process = Start(file, args, cwd, environment, output);
        using var timeout = new CancellationTokenSource(TimeSpan.FromMinutes(timeoutMinutes));
        try { await process.WaitForExitAsync(timeout.Token); }
        catch (OperationCanceledException) { process.Kill(true); throw new InvalidOperationException("La operación excedió el tiempo de espera. Revisa los registros y vuelve a intentarlo."); }
        process.WaitForExit();
        if (check && process.ExitCode != 0) throw new InvalidOperationException($"{Path.GetFileName(file)} terminó con código {process.ExitCode}. Revisa el registro de la ventana.");
        return process.ExitCode;
    }

    Process Start(string file, IEnumerable<string> args, string? cwd = null, Dictionary<string, string>? environment = null, bool output = true)
    {
        var info = new ProcessStartInfo(file) { WorkingDirectory = cwd ?? Repo, UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true, StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8 };
        info.Environment["PYTHONIOENCODING"] = "utf-8";
        info.Environment["PYTHONUTF8"] = "1";
        info.Environment["PYTHONUNBUFFERED"] = "1";
        if (Path.IsPathRooted(Docker)) info.Environment["PATH"] = Path.GetDirectoryName(Docker) + Path.PathSeparator + Environment.GetEnvironmentVariable("PATH");
        foreach (var arg in args) info.ArgumentList.Add(arg);
        if (environment != null) foreach (var pair in environment) info.Environment[pair.Key] = pair.Value;
        var process = new Process { StartInfo = info };
        if (output)
        {
            process.OutputDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) Write(e.Data); };
            process.ErrorDataReceived += (_, e) => { if (!string.IsNullOrWhiteSpace(e.Data)) Write(e.Data); };
        }
        process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine();
        return process;
    }

    public void Seed()
    {
        var source = Path.Combine(Package, "app");
        var fromSources=!File.Exists(Path.Combine(source,"infra","compose.yaml"));
        if(fromSources)source=SourceRoot??throw new InvalidOperationException("Faltan las fuentes y la carpeta app. Extrae el ZIP Windows completo; el archivo CYSA.exe aislado no contiene el proyecto.");
        Directory.CreateDirectory(Repo);
        foreach (var file in fromSources?SourceLayout.Files(source):Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories))
        {
            var relative = Path.GetRelativePath(source, file);
            // El paquete no debe contener estado local. Defensa adicional frente a un ZIP mal armado.
            if (relative.Split(Path.DirectorySeparatorChar).Any(p => p is "runtime" or ".git" or ".venv" or "resultados" or "respaldos") || Path.GetFileName(file) == ".env")
                throw new InvalidOperationException("El paquete contiene estado privado y no se puede instalar.");
            var target = Path.Combine(Repo, relative);
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            if (relative == Path.Combine("panel", "config.json") && Configured) continue;
            File.Copy(file, target, true);
        }
        Write("Archivos preparados en la carpeta de este usuario.");
    }

    public async Task EnsureDocker()
    {
        try
        {
            if (await Run(Docker, ["info", "--format", "{{.ServerVersion}}"], Root, check: false, output: false, timeoutMinutes: 1) == 0) return;
        }
        catch (System.ComponentModel.Win32Exception) { throw new InvalidOperationException("Instala Docker Desktop con el botón correspondiente y vuelve a configurar. Docker debe usar contenedores Linux."); }
        var desktop = new[] {
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Docker", "Docker", "Docker Desktop.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "DockerDesktop", "Docker Desktop.exe") }.FirstOrDefault(File.Exists);
        if (desktop == null) throw new InvalidOperationException("Abre Docker Desktop y espera a que esté listo.");
        Write("Iniciando Docker Desktop…");
        Process.Start(new ProcessStartInfo(desktop) { UseShellExecute = false, WindowStyle = ProcessWindowStyle.Hidden });
        for (var i = 0; i < 60; i++)
        {
            await Task.Delay(3000);
            if (await Run(Docker, ["info", "--format", "{{.ServerVersion}}"], Root, check: false, output: false, timeoutMinutes: 1) == 0) return;
        }
        throw new InvalidOperationException("Docker no inició. Comprueba WSL 2 y el estado de Docker Desktop.");
    }

    public async Task Configure()
    {
        Seed();
        await EnsureDocker();
        if (!File.Exists(Python))
        {
            Write("Instalando Python 3.12 para este usuario (sin modificar PATH)…");
            var installer = Path.Combine(Package, "dependencies", "python-3.12.10-amd64.exe");
            var expected = File.ReadAllText(installer + ".sha256").Trim();
            using var stream = File.OpenRead(installer);
            if (!Convert.ToHexString(SHA256.HashData(stream)).Equals(expected, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("El instalador de Python no coincide con la huella del paquete.");
            await Run(installer, ["/quiet", "InstallAllUsers=0", "Include_launcher=0", "PrependPath=0", "Include_test=0", "Include_doc=0", "Include_pip=1", "Include_tcltk=1", "TargetDir=" + Path.GetDirectoryName(Python)], Root, timeoutMinutes: 10);
        }
        if (!File.Exists(Venv)) await Run(Python, ["-m", "venv", Path.Combine(Repo, ".venv")]);
        Write("Instalando dependencias. La primera descarga puede tardar varios minutos…");
        await Run(Venv, ["-m", "pip", "install", "--disable-pip-version-check", "-r", "backend/requirements.txt", "-r", "deteccion/requirements.txt", "-r", "simulacion/requirements.txt", "-r", "tests/requirements.txt"]);
        await Run(Venv, ["desktop/runtime.py", "prepare", "--identity", IdentityUrl, "--panel", PanelUrl, "--mqtt-port", Ports.Mqtt.ToString()]);
        await Compose("up", "-d", "--build");
        await WaitUrl($"http://127.0.0.1:{Ports.Identity}/realms/cysa", 180);
        foreach (var script in new[] { "configurar_usuarios_local.py", "configurar_interfaz_local.py", "endurecer_identidad_local.py" })
            await Run(Venv, ["tools/franco/" + script]);
        await Compose("up", "-d", "--force-recreate", "--no-deps", "api");
        File.WriteAllText(Path.Combine(Root, "configurado"), DateTimeOffset.UtcNow.ToString("O"));
        await StartAll();
        Write("Instalación terminada. Abre Credenciales para ver las cuentas creadas en esta PC.");
    }

    string[] ComposeArgs(params string[] args) => ["compose", "-p", Project, "--env-file", Path.Combine(Repo, "infra", ".env"), "-f", Path.Combine(Repo, "infra", "compose.yaml"), "-f", Path.Combine(Repo, "infra", "launcher.override.yaml"), .. args];
    Task<int> Compose(params string[] args)
    {
        // Registrar el intento antes de arrancar: un fallo puede dejar contenedores parciales.
        if (args.FirstOrDefault() == "up") dockerSession.MarkUsed();
        return Run(Docker, ComposeArgs(args));
    }

    async Task<bool> DockerAvailable()
    {
        try { return await Run(Docker, ["info", "--format", "{{.ServerVersion}}"], Root, check: false, output: false, timeoutMinutes: 1) == 0; }
        catch (Exception error) when (error is System.ComponentModel.Win32Exception or IOException or InvalidOperationException) { return false; }
    }
    void RequireConfigured()
    {
        if (!Configured || !File.Exists(Path.Combine(Root, "configurado"))) throw new InvalidOperationException("Pulsa Configurar esta PC para completar la instalación.");
    }

    bool ejemplosPreparados;
    public Task StartAll() => StartAll(false);

    async Task StartAll(bool renovarEjemplos)
    {
        RequireConfigured();
        await PreparePanelNavigation();
        await EnsureDocker();
        await Compose("up", "-d");
        await EnsureReportsApi();
        await WaitUrl($"http://127.0.0.1:{Ports.Identity}/realms/cysa", 180);
        await Run("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", Path.Combine(Repo, "dotnet", "scripts", "Preparar-Demo.ps1"), "-Directorio", Path.Combine(Repo, "dotnet", "runtime")]);
        foreach (var (name, port) in new[] { ("Cysa.Evaluaciones.Api", Ports.Evaluation), ("Cysa.Decisiones.Api", Ports.Decision) })
        {
            if (apis.TryGetValue(name, out var existing) && !existing.HasExited) continue;
            if (!IsFree(port)) throw new InvalidOperationException($"El puerto {port} está ocupado por otra aplicación. Ciérrala y vuelve a iniciar.");
            var exe = await EnsureApiExecutable(name);
            apis[name] = Start(exe, ["--urls", $"http://localhost:{port}"], Path.GetDirectoryName(exe), new() {
                ["ASPNETCORE_ENVIRONMENT"]="Development", ["Security__Mode"]="Demo",
                ["Storage__Directory"]=Path.Combine(Repo,"dotnet","runtime"), ["Evaluaciones__BaseUrl"]=$"http://localhost:{Ports.Evaluation}",
                ["Logging__LogLevel__Default"]="Warning", ["Logging__LogLevel__Microsoft.AspNetCore"]="Warning" });
        }
        foreach (var port in new[] { Ports.Panel, Ports.Evaluation, Ports.Decision }) await WaitUrl($"http://127.0.0.1:{port}/health", 90);
        await StartWebIII();
        await StartOperation();
        if (renovarEjemplos || !ejemplosPreparados)
            ejemplosPreparados = await PrepararEjemplos();
        Write("Sistema listo: monitoreo, módulos de gestión, banco S2 y controlador emulado disponibles. No se actúa sobre semáforos reales.");
    }

    public async Task OpenPanel()
    {
        await StartAll(true);
        Open(PanelUrl);
    }

    async Task EnsureReportsApi()
    {
        var health = PanelUrl + "/health";
        await WaitUrl(health, 90);
        const string probe = "/api/reportes/conteos?desde=2026-01-01T00:00:00Z&hasta=2026-01-02T00:00:00Z";
        using var response = await http.GetAsync(PanelUrl + probe);
        if (response.StatusCode != HttpStatusCode.NotFound) return;
        Write("Actualizando la API de monitoreo para habilitar reportes…");
        await Compose("up", "-d", "--build", "--no-deps", "api");
        await Compose("exec", "-T", "panel", "nginx", "-s", "reload");
        await WaitUrl(health, 90);
        using var updated = await http.GetAsync(PanelUrl + probe);
        if (updated.StatusCode != HttpStatusCode.Unauthorized)
            throw new InvalidOperationException("La API actualizada todavía no ofrece el reporte protegido.");
    }

    async Task PreparePanelNavigation()
    {
        var path=Path.Combine(Repo,"panel/config.json");
        var config=JsonSerializer.Deserialize<Dictionary<string,JsonElement>>(await File.ReadAllTextAsync(path))!;
        config["webApiBase"]=JsonSerializer.SerializeToElement(WebUrl);
        config["operacionBase"]=JsonSerializer.SerializeToElement(OperationUrl);
        config["panelUrl"]=JsonSerializer.SerializeToElement(PanelUrl+"/");
        await File.WriteAllTextAsync(path,JsonSerializer.Serialize(config));
        // Actualizar la configuración pública de Nginx sin tocar secretos ni regenerar cuentas.
        var nginx=Path.Combine(Repo,"infra/runtime/launcher/nginx.conf");
        if(File.Exists(nginx))
        {
            var policy = await File.ReadAllTextAsync(Path.Combine(Repo,"identidad/nginx.conf"));
            await File.WriteAllTextAsync(nginx,policy.Replace("http://localhost:8080",IdentityUrl)
                .Replace("http://localhost:* http://127.0.0.1:*", $"{WebUrl} {OperationUrl}"));
        }
    }

    internal Dictionary<string,int> RunningServices()=>apis.Where(p=>!p.Value.HasExited).ToDictionary(p=>p.Key,p=>p.Value.Id);

    async Task WaitUrl(string url, int seconds)
    {
        var end = DateTime.UtcNow.AddSeconds(seconds);
        while (DateTime.UtcNow < end)
        {
            try { using var result = await http.GetAsync(url); if (result.IsSuccessStatusCode) return; } catch (HttpRequestException) { } catch (TaskCanceledException) { }
            await Task.Delay(1000);
        }
        throw new InvalidOperationException("Un servicio no respondió a tiempo: " + new Uri(url).GetLeftPart(UriPartial.Authority));
    }

    public async Task StopAll()
    {
        if (SumoGui is { HasExited: false })
        {
            SumoGui.CloseMainWindow();
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
            try { await SumoGui.WaitForExitAsync(timeout.Token); }
            catch (OperationCanceledException) { SumoGui.Kill(true); await SumoGui.WaitForExitAsync(); }
        }
        SumoGui?.Dispose(); SumoGui = null;
        if (sumoDriver is { HasExited: false })
        {
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
            try { await sumoDriver.WaitForExitAsync(timeout.Token); }
            catch (OperationCanceledException) { sumoDriver.Kill(true); await sumoDriver.WaitForExitAsync(); }
        }
        sumoDriver?.Dispose(); sumoDriver = null;
        ejemplosPreparados = false;
        if (Detector is { HasExited: false }) { Detector.Kill(true); await Detector.WaitForExitAsync(); }
        foreach (var process in apis.Values) { if (!process.HasExited) { process.Kill(true); await process.WaitForExitAsync(); } process.Dispose(); }
        apis.Clear();
        await dockerSession.Stop(DockerAvailable, async () => { await Compose("stop"); }, Write);
        Write("Cierre de servicios finalizado. Los datos y las cuentas se conservan.");
    }

    public async Task Verify()
    {
        RequireConfigured();
        await Compose("ps");
        foreach(var url in new[]{PanelUrl+"/health",IdentityUrl+"/realms/cysa",$"http://localhost:{Ports.Evaluation}/health",$"http://localhost:{Ports.Decision}/health"})
            await WaitUrl(url,10);
        await WaitUrl(WebUrl+"/health", 10);
        await WaitOperationReady();
        foreach(var url in new[]{PanelUrl+"/api/conteos",OperationUrl+"/api/estados"})
        {
            using var response=await http.GetAsync(url);
            if(response.StatusCode!=HttpStatusCode.Unauthorized)throw new InvalidOperationException("Una consulta protegida no rechazó el acceso sin sesión.");
        }
        if(!apis.TryGetValue("Controlador S2",out var controller) || controller.HasExited)
            throw new InvalidOperationException("El controlador emulado S2 no está iniciado. Pulsa Iniciar sistema.");
        Write("Verificados: módulos de gestión, SQL Server, banco S2, MQTT y controlador emulado.");
        Write("Las consultas sin sesión se rechazan. El ingreso por rol con OTP se comprueba desde el navegador; no se intenta omitir MFA con una contraseña guardada.");
    }

    public async Task Tests()
    {
        RequireConfigured();
        await StartAll();
        await Run(Venv, ["tools/franco/probar.py"]);
        await StartAll();
        await Run(Venv, ["desktop/runtime.py", "demo-test", "--evaluation", $"http://127.0.0.1:{Ports.Evaluation}", "--decision", $"http://127.0.0.1:{Ports.Decision}"]);
        Write("Pruebas terminadas correctamente.");
    }

    public string? SavedDevice()
    {
        try { return JsonSerializer.Deserialize<Dictionary<string,string>>(File.ReadAllText(Path.Combine(Root,"detector-mode.json")))?.GetValueOrDefault("Device"); }
        catch (Exception error) when (error is IOException or JsonException) { return null; }
    }

    public void SaveDevice(string device) => File.WriteAllText(Path.Combine(Root,"detector-mode.json"), JsonSerializer.Serialize(new { Device=device }));

    void RequireDetectorStopped()
    {
        if (Detector is { HasExited:false }) throw new InvalidOperationException("Cierra el detector con Q antes de medir el equipo o preparar la GPU.");
    }

    public async Task<HardwareReport> DetectHardware()
    {
        RequireConfigured(); RequireDetectorStopped();
        var report = Path.Combine(Root,"hardware.json");
        await Run(Venv,["desktop/runtime.py","hardware","--out",report],timeoutMinutes:5);
        return JsonSerializer.Deserialize<HardwareReport>(File.ReadAllText(report)) ?? throw new InvalidOperationException("No se pudo leer la prueba del equipo.");
    }

    public async Task PrepareGpu()
    {
        RequireConfigured(); RequireDetectorStopped();
        await Run(Venv,["desktop/runtime.py","prepare-gpu"],timeoutMinutes:60);
    }

    public void StartDetector(string source, string device)
    {
        RequireConfigured();
        if (Detector is { HasExited: false }) throw new InvalidOperationException("Ya hay un detector abierto. Ciérralo con Q antes de iniciar otro.");
        SaveDevice(device);
        Detector = Start(Venv, ["desktop/runtime.py", "detector", "--source", source,"--device",device]);
        Write("Marca cuatro esquinas, ajusta carriles con 1–8 y pulsa S. D invierte el sentido; Q termina.");
    }

    public async Task OpenSumo()
    {
        RequireConfigured();
        if (SumoGui is { HasExited: false }) throw new InvalidOperationException("SUMO ya está abierto. Usa su ventana o ciérrala antes de abrir otra simulación.");
        if (sumoDriver is { HasExited: false }) throw new InvalidOperationException("SUMO está cerrando la corrida anterior. Espera unos segundos antes de abrir otra.");
        SumoGui?.Dispose();
        sumoDriver?.Dispose();
        var report = Path.Combine(Root, "sumo-scenario.json");
        await Run(Venv, ["desktop/sumo_gui.py", "--report", report]);
        var scenario = JsonSerializer.Deserialize<SumoScenario>(File.ReadAllText(report))
            ?? throw new InvalidOperationException("No se pudo preparar el escenario SUMO.");
        var socket = new TcpListener(IPAddress.Loopback, 0);
        socket.Start();
        var port = ((IPEndPoint)socket.LocalEndpoint).Port.ToString();
        socket.Stop();
        SumoGui = Start(scenario.Executable, ["-c", scenario.Config, "--remote-port", port, "--seed", "42",
            "--delay", "150", "--window-size", "1100,750"], Path.GetDirectoryName(scenario.Config));
        try { sumoDriver = Start(Venv, ["desktop/sumo_gui.py", "--drive", scenario.Config, "--port", port]); }
        catch { SumoGui.Kill(true); throw; }
        await Task.Delay(1000);
        if (SumoGui.HasExited || sumoDriver.HasExited)
        {
            if (!SumoGui.HasExited) SumoGui.Kill(true);
            throw new InvalidOperationException("La demo SUMO no pudo abrirse. Revisa el registro de la ventana.");
        }
        Write($"SUMO-GUI abierto: dos cruces, {scenario.Expected} vehículos y emergencia simulada.");
        Write("Pulsa ▶ (Ctrl+A) en SUMO para ver el plan fijo, el aviso de A a B y el retorno tras el paso de la ambulancia.");
        Write("Al terminar, consulta eventos_corredor.csv, semaforos.xml y tripinfo.xml. Archivos: " + Path.GetDirectoryName(scenario.Config));
    }

    public async Task ShowLogs()
    {
        if (Configured) await Compose("logs", "--tail", "40", "api", "consumer", "mosquitto");
        Open(Path.Combine(Root, "logs"));
    }
    public static void Open(string target) => Process.Start(new ProcessStartInfo(target) { UseShellExecute = true });
}

internal sealed partial class MainForm : Form
{
    readonly Instance instance;
    readonly RichTextBox log = new() { Multiline = true, ReadOnly = true, ScrollBars = RichTextBoxScrollBars.Both, Dock = DockStyle.Fill, Font = new Font("Consolas", 9.5f), WordWrap = false, BorderStyle = BorderStyle.None, DetectUrls = false, HideSelection = false, AccessibleName = "Registro de actividad" };
    readonly Label status = new() { AutoSize = true, Text = "Listo para configurar", ForeColor = Color.FromArgb(22, 100, 80), Margin = new Padding(0, 8, 0, 8) };
    readonly List<Button> actions = [];
    readonly RadioButton cpu = new() { Text="CPU", AutoSize=true, Padding=new Padding(12,8,12,8), Enabled=false };
    readonly RadioButton gpu = new() { Text="GPU NVIDIA (CUDA)", AutoSize=true, Padding=new Padding(12,8,12,8), Enabled=false };
    readonly Label hardwareDetail = new() { Text="Configura esta PC para medir CPU y GPU. La opción recomendada se marcará en verde.", Dock=DockStyle.Fill };
    readonly ThemedButton detectHardware = new() { Text="Detectar y recomendar", AutoSize=true };
    readonly ThemedButton prepareGpu = new() { Text="Preparar GPU", AutoSize=true, Enabled=false };
    HardwareReport? hardware;
    bool busy;

    public MainForm(Instance instance)
    {
        this.instance = instance;
        BuildInterface();
    }
    bool closing;
    string SelectedDevice()
    {
        if (hardware == null) throw new InvalidOperationException("Pulsa Detectar y recomendar después de configurar esta PC.");
        return gpu.Checked && hardware.GpuReady ? hardware.GpuDevice : "cpu";
    }
    async Task RefreshHardware()
    {
        hardwareDetail.Text="Midiendo CPU y GPU con imágenes sintéticas. El primer uso descarga el modelo…";
        hardware=null; cpu.Checked=false; gpu.Checked=false;
        StyleRecommendation(); cpu.Text="CPU"; gpu.Text="GPU NVIDIA (CUDA)";
        try
        {
            hardware=await instance.DetectHardware();
            var recommendGpu=hardware.Recommended!="cpu" && hardware.GpuReady;
            cpu.Text=recommendGpu ? "CPU" : "CPU · Recomendado";
            gpu.Text=recommendGpu ? "GPU · Recomendado" : "GPU NVIDIA (CUDA)";
            StyleRecommendation();
            var saved=instance.SavedDevice();
            var device=saved=="cpu" || (hardware.GpuReady && saved==hardware.GpuDevice) ? saved : hardware.Recommended;
            gpu.Checked=device!="cpu" && hardware.GpuReady; cpu.Checked=!gpu.Checked;
            hardwareDetail.Text=$"CPU: {hardware.CpuMs:0.0} ms/imagen"+(hardware.GpuReady ? $"  |  {hardware.GpuName}: {hardware.GpuMs:0.0} ms/imagen" : "")+"\n"+hardware.Reason+" Puedes elegir manualmente; la prueba no mide precisión de conteo.";
        }
        catch { hardwareDetail.Text="No se pudo medir el equipo. Revisa el registro y vuelve a detectar; el primer uso necesita internet para descargar YOLO."; throw; }
    }
    async Task Execute(Func<Task> action, string category = "SISTEMA", string? title = null)
    {
        if (busy) return;
        operation=category; failed=false; instance.Write("▶ " + (title ?? category)); status.ForeColor=theme.GreenInk;
        busy=true; actions.ForEach(b=>b.Enabled=false); cpu.Enabled=false; gpu.Enabled=false; detectHardware.Enabled=false; prepareGpu.Enabled=false; status.Text="Trabajando…"; UseWaitCursor=true;
        try { await action(); status.Text="● Operación completada"; instance.Write("Completado: " + (title ?? category)); }
        catch (Exception error) { failed=true; status.ForeColor=theme.Danger; instance.Write("ERROR: " + error.Message); status.Text="Revisa el aviso y vuelve a intentar"; MessageBox.Show(this,error.Message,"CYSA",MessageBoxButtons.OK,MessageBoxIcon.Warning); }
        finally { busy=false; actions.ForEach(b=>b.Enabled=true); cpu.Enabled=hardware!=null; gpu.Enabled=hardware?.GpuReady==true; detectHardware.Enabled=true; prepareGpu.Enabled=hardware?.NvidiaDetected==true && !hardware.GpuReady; UseWaitCursor=false; }
    }
    Task Credentials()
    {
        var path=Path.Combine(instance.Repo,"infra","runtime","clientes","usuarios-locales.json");
        if (!File.Exists(path)) throw new InvalidOperationException("Configura esta PC primero.");
        using var data=JsonDocument.Parse(File.ReadAllText(path));
        using var dialog=new Form { Text="Cuentas de esta PC",Size=new Size(650,260),StartPosition=FormStartPosition.CenterParent };
        dialog.Controls.Add(new TextBox { Dock=DockStyle.Fill,Multiline=true,ReadOnly=true,Font=new Font("Consolas",11),Text="Estas contraseñas pertenecen solo a esta instalación.\r\nNo compartas capturas ni estos archivos.\r\n\r\n"+string.Join("\r\n\r\n",data.RootElement.EnumerateObject().Select(p=>p.Name+": "+p.Value.GetString())) });
        ApplyControlTheme(dialog); dialog.ShowDialog(this); return Task.CompletedTask;
    }
    async Task Tokens()
    {
        await instance.StartAll();
        Instance.Open(Path.Combine(instance.Repo,"dotnet","runtime","tokens.json"));
        MessageBox.Show(this,"Tokens renovados. Copia el token en Authorize de Swagger.\nLa MFA simulada de decisiones dura 5 minutos; los tokens, 30 minutos.","Demostración local");
    }
}

internal sealed class CameraDialog : Form
{
    readonly NumericUpDown index = new() { Minimum=0,Maximum=20,Value=0,Dock=DockStyle.Top };
    public string Source => index.Value.ToString();
    public CameraDialog()
    {
        Text="Elegir cámara"; Size=new Size(420,210); StartPosition=FormStartPosition.CenterParent; Padding=new Padding(20);
        var panel=new FlowLayoutPanel { Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown };
        panel.Controls.Add(new Label { Text="Índice de cámara (0 suele ser la integrada)",AutoSize=true }); panel.Controls.Add(index);
        var button=new Button { Text="Abrir y marcar carriles",AutoSize=true,DialogResult=DialogResult.OK }; panel.Controls.Add(button); Controls.Add(panel); AcceptButton=button;
    }
}

internal static class SelfTest
{
    public static void Run(string output)
    {
        ShutdownTest.Run().GetAwaiter().GetResult();
        var root=Path.Combine(Path.GetTempPath(),"cysa-launcher-test-"+Guid.NewGuid());
        Directory.CreateDirectory(root);
        try
        {
            var a=Instance.ProjectFor(Path.Combine(root,"usuario a")); var b=Instance.ProjectFor(Path.Combine(root,"usuario b"));
            if (a==b || a!=Instance.ProjectFor(Path.Combine(root,"usuario a"))) throw new Exception("Aislamiento de proyectos incorrecto");
            var ports=Ports.Select(p=>p>19000);
            if (ports.All.Distinct().Count()!=7 || ports.All.Any(p=>p<=19000)) throw new Exception("Selección de puertos incorrecta");
            var legacy=JsonSerializer.Deserialize<Ports>("{\"Panel\":18088,\"Identity\":18080,\"Mqtt\":18883,\"Evaluation\":15181,\"Decision\":15182}")!;
            if(legacy.Web!=15183 || legacy.Operation!=15184)throw new Exception("No se conservó compatibilidad con instalaciones anteriores");
            var package=Path.Combine(root,"paquete"); Directory.CreateDirectory(Path.Combine(package,"app","infra"));
            File.WriteAllText(Path.Combine(package,"app","infra","compose.yaml"),"services: {}");
            var instance=new Instance(Path.Combine(root,"usuario"),package); instance.Seed();
            foreach(var server in SqlServerOptions.Instancias)
                if(!new SqlServerOptions(server).Cadena().Contains("Database=CYSA_WebIII_Demo;Integrated Security=True;"))throw new Exception("La conexión no conserva base y autenticación Windows");
            foreach(var invalid in new[]{"servidor-remoto", "localhost;Database=otra", "localhost,1433", "localhost;Password=secreto"})
            {
                var blocked=false;try{new SqlServerOptions(invalid).Cadena();}catch(InvalidOperationException){blocked=true;}
                if(!blocked)throw new Exception("Se aceptó una instancia ajena a la lista local");
            }
            var externalSql=Environment.GetEnvironmentVariable("CYSA_WEBIII_CONNECTION");
            try
            {
                Environment.SetEnvironmentVariable("CYSA_WEBIII_CONNECTION",null);
                instance.GuardarSqlServer(@".\SQLEXPRESS").GetAwaiter().GetResult();
                if(new Instance(instance.Root,package).SqlServerActual()!=@".\SQLEXPRESS")throw new Exception("No se conservó la instancia SQL local");
                if(new Instance(Path.Combine(root,"otro usuario sql"),package).SqlServerActual()!="localhost")throw new Exception("La conexión SQL se compartió entre usuarios");
                Environment.SetEnvironmentVariable("CYSA_WEBIII_CONNECTION","configuracion-externa-de-prueba");
                var blocked=false;try{instance.GuardarSqlServer("localhost").GetAwaiter().GetResult();}catch(InvalidOperationException){blocked=true;}
                if(!blocked||instance.SqlServerActual()!=@".\SQLEXPRESS")throw new Exception("Se ignoró la prioridad de la configuración externa");
            }
            finally{Environment.SetEnvironmentVariable("CYSA_WEBIII_CONNECTION",externalSql);}
            File.WriteAllText(Path.Combine(instance.Repo,"infra",".env"),"TEST=privado");
            instance.Seed();
            if (File.ReadAllText(Path.Combine(instance.Repo,"infra",".env"))!="TEST=privado") throw new Exception("Se alteró estado privado");
            var clients=Path.Combine(instance.Repo,"infra","runtime","clientes");Directory.CreateDirectory(clients);
            File.WriteAllText(Path.Combine(clients,"usuarios-locales.json"),"{}");
            if(!instance.Configured)throw new Exception("Falta la configuración previa para probar el cierre.");
            instance.StopAll().GetAwaiter().GetResult();
            if(!File.Exists(Path.Combine(instance.Repo,"infra",".env")))throw new Exception("El cierre borró la configuración.");
            instance.SaveDevice("cpu");
            if (new Instance(instance.Root,package).SavedDevice()!="cpu") throw new Exception("No se conservó el modo CPU del usuario");
            instance.SaveDevice("1");
            if (new Instance(instance.Root,package).SavedDevice()!="1") throw new Exception("No se conservó la GPU elegida");
            if (new Instance(Path.Combine(root,"otro usuario"),package).SavedDevice()!=null) throw new Exception("El modo se compartió entre usuarios");
            Directory.CreateDirectory(Path.Combine(package,"app","infra","runtime"));
            File.WriteAllText(Path.Combine(package,"app","infra","runtime","secreto"),"no copiar");
            var rejected=false; try { instance.Seed(); } catch (InvalidOperationException) { rejected=true; }
            if (!rejected) throw new Exception("No se rechazó un paquete con secretos");
            var sources=Path.Combine(root,"fuentes");
            var sourceBin=Path.Combine(sources,"desktop","Cysa.Launcher","bin","Debug","net10.0-windows","win-x64");
            Directory.CreateDirectory(sourceBin);Directory.CreateDirectory(Path.Combine(sources,"dotnet","src","Cysa.Web.Api"));Directory.CreateDirectory(Path.Combine(sources,"infra"));
            File.WriteAllText(Path.Combine(sources,"desktop","Cysa.Launcher","Cysa.Launcher.csproj"),"<Project />");
            File.WriteAllText(Path.Combine(sources,"dotnet","src","Cysa.Web.Api","Cysa.Web.Api.csproj"),"<Project />");
            File.WriteAllText(Path.Combine(sources,"infra","compose.yaml"),"services: {}");
            File.WriteAllText(Path.Combine(sources,"infra",".env"),"NO_COPIAR=privado");
            File.WriteAllText(Path.Combine(sources,"infra",".env.example"),"EJEMPLO=sin-secretos");
            Directory.CreateDirectory(Path.Combine(sources,"dotnet","runtime"));File.WriteAllText(Path.Combine(sources,"dotnet","runtime","token.json"),"privado");
            File.WriteAllText(Path.Combine(sourceBin,"secreto.key"),"privado");
            var sourceInstance=new Instance(Path.Combine(root,"usuario fuentes"),sourceBin);sourceInstance.Seed();
            if(sourceInstance.SourceRoot!=sources || !File.Exists(Path.Combine(sourceInstance.Repo,"infra",".env.example")))throw new Exception("No se preparó una ejecución desde fuentes");
            if(File.Exists(Path.Combine(sourceInstance.Repo,"infra",".env")) || Directory.Exists(Path.Combine(sourceInstance.Repo,"desktop","Cysa.Launcher","bin")) || Directory.Exists(Path.Combine(sourceInstance.Repo,"dotnet","runtime")))throw new Exception("Se copió estado privado desde las fuentes");
            var fingerprint=SourceLayout.WebFingerprint(sources);File.WriteAllText(Path.Combine(sourceBin,"irrelevante.txt"),"compilación");
            if(SourceLayout.WebFingerprint(sources)!=fingerprint)throw new Exception("Una compilación invalidó la caché de fuentes");
            File.WriteAllText(Path.Combine(sources,"dotnet","src","Cysa.Web.Api","Cambio.cs"),"// fuente nueva");
            if(SourceLayout.WebFingerprint(sources)==fingerprint)throw new Exception("Un cambio fuente no invalidó la caché");
            File.WriteAllText(output,"PASS: proyectos independientes, puertos libres, estado conservado, modo CPU/GPU por usuario, rechazo de secretos, conexión SQL local por usuario, prioridad de configuración externa y cierre sin Docker con configuración previa; detención IoT, daemon no disponible y reintentos verificados.");
        }
        finally { Directory.Delete(root,true); }
    }
}

internal static class IntegrationTest
{
    public static async Task Run(string root, string report)
    {
        var instance = new Instance(root);
        try
        {
            await instance.Configure();
            var secrets = SHA256.HashData(File.ReadAllBytes(Path.Combine(instance.Repo,"infra",".env")));
            await instance.Verify();
            await instance.Tests();
            await instance.StopAll();
            await instance.StartAll();
            await instance.Verify();
            var restartedSecrets = SHA256.HashData(File.ReadAllBytes(Path.Combine(instance.Repo,"infra",".env")));
            if (!secrets.SequenceEqual(restartedSecrets)) throw new Exception("Las credenciales cambiaron al reiniciar");
            File.WriteAllText(report,"PASS: instalación nueva, acceso por roles, MQTT/TLS/BD/API, pruebas Python y .NET HTTP, reinicio sin rotar secretos. Proyecto: "+instance.Project);
        }
        catch (Exception error) { File.WriteAllText(report,"FAIL: "+error.Message); Environment.ExitCode=1; }
        finally { await instance.StopAll(); }
    }
}
