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
        ApplicationConfiguration.Initialize();
        using var mutex = new Mutex(true, "Local\\CYSA-" + Instance.ProjectFor(Instance.Home), out var first);
        if (!first) { MessageBox.Show("CYSA ya está abierto para este usuario."); return; }
        try { Application.Run(new MainForm(new Instance())); }
        catch (Exception error) { MessageBox.Show(error.Message, "CYSA", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }
}

internal sealed record Ports(int Panel, int Identity, int Mqtt, int Evaluation, int Decision)
{
    public int[] All => [Panel, Identity, Mqtt, Evaluation, Decision];
    public static Ports Select(Func<int, bool> free)
    {
        for (var offset = 0; offset < 20000; offset += 100)
        {
            var ports = new Ports(18088 + offset, 18080 + offset, 18883 + offset, 15181 + offset, 15182 + offset);
            if (ports.All.All(free)) return ports;
        }
        throw new InvalidOperationException("No se encontró un grupo de puertos libres.");
    }
}

internal sealed class Instance
{
    public static string Home => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CYSA");
    public static string ProjectFor(string path) => "cysa-" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(path).ToUpperInvariant())))[..12].ToLowerInvariant();
    public string Root { get; }
    public string Package { get; }
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
    readonly Dictionary<string, Process> apis = [];
    readonly HttpClient http = new() { Timeout = TimeSpan.FromSeconds(3) };
    readonly string logPath;

    public Instance(string? root = null, string? package = null)
    {
        Root = root ?? Home;
        Package = package ?? AppContext.BaseDirectory;
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
        if (!File.Exists(Path.Combine(source, "infra", "compose.yaml"))) throw new InvalidOperationException("Extrae todo el ZIP antes de abrir CYSA.exe. Falta la carpeta app.");
        Directory.CreateDirectory(Repo);
        foreach (var file in Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories))
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
    Task<int> Compose(params string[] args) => Run(Docker, ComposeArgs(args));
    void RequireConfigured()
    {
        if (!Configured || !File.Exists(Path.Combine(Root, "configurado"))) throw new InvalidOperationException("Pulsa Configurar esta PC para completar la instalación.");
    }

    public async Task StartAll()
    {
        RequireConfigured();
        await EnsureDocker();
        await Compose("up", "-d");
        await WaitUrl($"http://127.0.0.1:{Ports.Identity}/realms/cysa", 180);
        await Run("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", Path.Combine(Repo, "dotnet", "scripts", "Preparar-Demo.ps1"), "-Directorio", Path.Combine(Repo, "dotnet", "runtime")]);
        foreach (var (name, port) in new[] { ("Cysa.Evaluaciones.Api", Ports.Evaluation), ("Cysa.Decisiones.Api", Ports.Decision) })
        {
            if (apis.TryGetValue(name, out var existing) && !existing.HasExited) continue;
            if (!IsFree(port)) throw new InvalidOperationException($"El puerto {port} está ocupado por otra aplicación. Ciérrala y vuelve a iniciar.");
            var exe = Path.Combine(Package, "services", name, name + ".exe");
            apis[name] = Start(exe, ["--urls", $"http://localhost:{port}"], Path.GetDirectoryName(exe), new() {
                ["ASPNETCORE_ENVIRONMENT"]="Development", ["Security__Mode"]="Demo",
                ["Storage__Directory"]=Path.Combine(Repo,"dotnet","runtime"), ["Evaluaciones__BaseUrl"]=$"http://localhost:{Ports.Evaluation}",
                ["Logging__LogLevel__Default"]="Warning", ["Logging__LogLevel__Microsoft.AspNetCore"]="Warning" });
        }
        foreach (var port in new[] { Ports.Panel, Ports.Evaluation, Ports.Decision }) await WaitUrl($"http://127.0.0.1:{port}/health", 90);
        Write("Sistema listo. Las APIs operan en modo demo y no activan semáforos.");
    }

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
        if (Detector is { HasExited: false }) { Detector.Kill(true); await Detector.WaitForExitAsync(); }
        foreach (var process in apis.Values) { if (!process.HasExited) { process.Kill(true); await process.WaitForExitAsync(); } process.Dispose(); }
        apis.Clear();
        if (Configured) await Compose("stop");
        Write("Servicios detenidos. Los datos y las cuentas se conservan.");
    }

    public async Task Verify()
    {
        RequireConfigured();
        await Compose("ps");
        await Run(Venv, ["desktop/runtime.py", "verify", "--panel", PanelUrl, "--evaluation", $"http://127.0.0.1:{Ports.Evaluation}", "--decision", $"http://127.0.0.1:{Ports.Decision}"]);
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

    public void StartDetector(string source)
    {
        RequireConfigured();
        if (Detector is { HasExited: false }) throw new InvalidOperationException("Ya hay un detector abierto. Ciérralo con Q antes de iniciar otro.");
        Detector = Start(Venv, ["desktop/runtime.py", "detector", "--source", source]);
        Write("Marca cuatro esquinas, ajusta carriles con 1–8 y pulsa S. D invierte el sentido; Q termina.");
    }

    public async Task ShowLogs()
    {
        if (Configured) await Compose("logs", "--tail", "40", "api", "consumer", "mosquitto");
        Open(Path.Combine(Root, "logs"));
    }
    public static void Open(string target) => Process.Start(new ProcessStartInfo(target) { UseShellExecute = true });
}

internal sealed class MainForm : Form
{
    readonly Instance instance;
    readonly TextBox log = new() { Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Both, Dock = DockStyle.Fill, Font = new Font("Consolas", 10), WordWrap = false, BackColor = Color.FromArgb(20, 29, 43), ForeColor = Color.WhiteSmoke };
    readonly Label status = new() { AutoSize = true, Text = "Listo para configurar", ForeColor = Color.FromArgb(22, 100, 80), Margin = new Padding(0, 8, 0, 8) };
    readonly List<Button> actions = [];
    bool busy;

    public MainForm(Instance instance)
    {
        this.instance = instance;
        Text = "CYSA · Centro de pruebas"; MinimumSize = new Size(960, 720); Size = new Size(1100, 850); StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Segoe UI", 10); BackColor = Color.FromArgb(244, 247, 251); Padding = new Padding(24);
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 7 };
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 52)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 64));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 180)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 36));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 38)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 30));
        Controls.Add(layout);
        layout.Controls.Add(new Label { Text = "CYSA  /  Centro de pruebas", Font = new Font("Segoe UI", 23, FontStyle.Bold), AutoSize = true, ForeColor = Color.FromArgb(24, 46, 70) });
        layout.Controls.Add(new Label { Text = "1. Instala Docker Desktop   2. Configura esta PC   3. Prueba cada apartado\nLa primera configuración necesita internet. Cada usuario tiene sus propias cuentas y datos.", Dock = DockStyle.Fill });
        var buttons = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 4, RowCount = 3 };
        for (var i=0;i<4;i++) buttons.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,25));
        for (var i=0;i<3;i++) buttons.RowStyles.Add(new RowStyle(SizeType.Percent,33));
        layout.Controls.Add(buttons);
        Add("Configurar esta PC", instance.Configure);
        Add("Iniciar sistema", instance.StartAll);
        Add("Abrir panel", () => { Instance.Open(instance.PanelUrl); return Task.CompletedTask; });
        Add("Credenciales", Credentials);
        Add("Contar con cámara", () => { using var dialog = new CameraDialog(); if (dialog.ShowDialog(this)==DialogResult.OK) instance.StartDetector(dialog.Source); return Task.CompletedTask; });
        Add("Contar con video", () => { using var dialog = new OpenFileDialog { Filter="Videos|*.mp4;*.avi;*.mov;*.mkv;*.wmv|Todos|*.*" }; if (dialog.ShowDialog(this)==DialogResult.OK) instance.StartDetector(dialog.FileName); return Task.CompletedTask; });
        Add("Evaluaciones", () => { Instance.Open($"http://localhost:{instance.Ports.Evaluation}/swagger"); return Task.CompletedTask; });
        Add("Decisiones", () => { Instance.Open($"http://localhost:{instance.Ports.Decision}/swagger"); return Task.CompletedTask; });
        Add("Verificar sistema", instance.Verify);
        Add("Ejecutar pruebas", instance.Tests);
        Add("Tokens de demo", Tokens);
        Add("Detener sistema", instance.StopAll);
        layout.Controls.Add(status); layout.Controls.Add(log);
        var links = new FlowLayoutPanel { Dock = DockStyle.Fill };
        Link("Instalar Docker Desktop", "https://docs.docker.com/desktop/setup/install/windows-install/");
        Link("Abrir mis archivos", instance.Root);
        var logs = new LinkLabel { Text="Ver registros", AutoSize=true, Margin=new Padding(12,6,12,0) }; logs.LinkClicked += async (_,_) => await Execute(instance.ShowLogs); links.Controls.Add(logs);
        layout.Controls.Add(links);
        layout.Controls.Add(new Label { Text="Solo pruebas: no activa semáforos. Cámara: S guarda carriles · D cambia sentido · Q sale.", AutoSize=true, ForeColor=Color.DimGray });
        instance.Log = text => { if (IsHandleCreated && !IsDisposed) { try { BeginInvoke(() => { if (log.TextLength > 180000) log.Clear(); log.AppendText(text + Environment.NewLine); }); } catch (InvalidOperationException) { } } };
        Shown += (_,_) => instance.Write("Datos de esta instalación: " + instance.Root + " | Proyecto Docker: " + instance.Project);
        FormClosing += async (_,e) => {
            if (closing) return;
            if (busy) { e.Cancel=true; MessageBox.Show(this,"Espera a que termine la operación actual.","CYSA"); return; }
            e.Cancel=true; await Execute(instance.StopAll); FormClosing -= CloseHandler;
            closing=true; Close();
        };
        FormClosing += CloseHandler;
        void Add(string text, Func<Task> action) { var button = new Button { Text=text, Dock=DockStyle.Fill, Margin=new Padding(4), FlatStyle=FlatStyle.Flat, BackColor=Color.White }; actions.Add(button); buttons.Controls.Add(button); button.Click += async (_,_)=>await Execute(action); }
        void Link(string text,string url) { var link=new LinkLabel { Text=text,AutoSize=true,Margin=new Padding(0,6,12,0) }; link.LinkClicked+=(_,_)=>Instance.Open(url); links.Controls.Add(link); }
    }
    bool closing;
    void CloseHandler(object? sender, FormClosingEventArgs e) { if (closing) e.Cancel=false; }
    async Task Execute(Func<Task> action)
    {
        if (busy) return;
        busy=true; actions.ForEach(b=>b.Enabled=false); status.Text="Trabajando…"; UseWaitCursor=true;
        try { await action(); status.Text="Operación completada"; }
        catch (Exception error) { instance.Write("ERROR: " + error.Message); status.Text="Revisa el aviso y vuelve a intentar"; MessageBox.Show(this,error.Message,"CYSA",MessageBoxButtons.OK,MessageBoxIcon.Warning); }
        finally { busy=false; actions.ForEach(b=>b.Enabled=true); UseWaitCursor=false; }
    }
    Task Credentials()
    {
        var path=Path.Combine(instance.Repo,"infra","runtime","clientes","usuarios-locales.json");
        if (!File.Exists(path)) throw new InvalidOperationException("Configura esta PC primero.");
        using var data=JsonDocument.Parse(File.ReadAllText(path));
        using var dialog=new Form { Text="Cuentas de esta PC",Size=new Size(650,260),StartPosition=FormStartPosition.CenterParent };
        dialog.Controls.Add(new TextBox { Dock=DockStyle.Fill,Multiline=true,ReadOnly=true,Font=new Font("Consolas",11),Text="Estas contraseñas pertenecen solo a esta instalación.\r\nNo compartas capturas ni estos archivos.\r\n\r\n"+string.Join("\r\n\r\n",data.RootElement.EnumerateObject().Select(p=>p.Name+": "+p.Value.GetString())) });
        dialog.ShowDialog(this); return Task.CompletedTask;
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
        var root=Path.Combine(Path.GetTempPath(),"cysa-launcher-test-"+Guid.NewGuid());
        Directory.CreateDirectory(root);
        try
        {
            var a=Instance.ProjectFor(Path.Combine(root,"usuario a")); var b=Instance.ProjectFor(Path.Combine(root,"usuario b"));
            if (a==b || a!=Instance.ProjectFor(Path.Combine(root,"usuario a"))) throw new Exception("Aislamiento de proyectos incorrecto");
            var ports=Ports.Select(p=>p>19000);
            if (ports.All.Distinct().Count()!=5 || ports.All.Any(p=>p<=19000)) throw new Exception("Selección de puertos incorrecta");
            var package=Path.Combine(root,"paquete"); Directory.CreateDirectory(Path.Combine(package,"app","infra"));
            File.WriteAllText(Path.Combine(package,"app","infra","compose.yaml"),"services: {}");
            var instance=new Instance(Path.Combine(root,"usuario"),package); instance.Seed();
            File.WriteAllText(Path.Combine(instance.Repo,"infra",".env"),"TEST=privado");
            instance.Seed();
            if (File.ReadAllText(Path.Combine(instance.Repo,"infra",".env"))!="TEST=privado") throw new Exception("Se alteró estado privado");
            Directory.CreateDirectory(Path.Combine(package,"app","infra","runtime"));
            File.WriteAllText(Path.Combine(package,"app","infra","runtime","secreto"),"no copiar");
            var rejected=false; try { instance.Seed(); } catch (InvalidOperationException) { rejected=true; }
            if (!rejected) throw new Exception("No se rechazó un paquete con secretos");
            File.WriteAllText(output,"PASS: proyectos independientes, puertos libres, estado conservado y rechazo de secretos.");
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
