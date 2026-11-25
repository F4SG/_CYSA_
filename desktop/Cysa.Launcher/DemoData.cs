using System.Globalization;
using System.Text.Json;

namespace Cysa.Launcher;

internal sealed partial class Instance
{
    const string PrepareDemoCounts = """
        BEGIN;
        SELECT pg_advisory_xact_lock(83217641);
        ALTER TABLE conteos ADD COLUMN IF NOT EXISTS origen_demo text;
        """;

    async Task RunDemoSql(string sql, Action<string>? onOutput = null, params string[] variables)
    {
        var bindings = variables.SelectMany(value => new[] { "-v", value });
        var args = ComposeArgs(["exec", "-T", "db", "psql", "-XqAt", "-U", "cysa", "-d", "cysa",
            "-v", "ON_ERROR_STOP=1", .. bindings, "-f", "-"]);
        await Run(Docker, args, timeoutMinutes: 2, input: PrepareDemoCounts + "\n" + sql + "\nCOMMIT;\n",
            onStandardOutput: onOutput);
    }

    string CountRevisionFile => Path.Combine(Repo, "panel", "runtime", "conteos.json");

    async Task PublishCountRevision()
    {
        var path = CountRevisionFile;
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            var payload = JsonSerializer.Serialize(new { revision = Guid.NewGuid().ToString("N") });
            await File.WriteAllTextAsync(path + ".tmp", payload);
            File.Move(path + ".tmp", path, true);
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            Write("No se pudo avisar al panel. Pulsa Actualizar o Consultar para volver a cargar los conteos.");
        }
    }

    Task<string> DemoSql(string name) => File.ReadAllTextAsync(Path.Combine(Repo, "data", "franco", "ejemplos", name));

    bool demoSourcesReady;

    void PrepareDemoSources()
    {
        RequireConfigured();
        if (!demoSourcesReady && SourceRoot is not null)
        {
            Seed(); // Actualiza el código de la instalación sin reiniciar la configuración.
            demoSourcesReady = true;
        }
    }

    async Task StartDemoDatabase()
    {
        RequireConfigured();
        await EnsureDocker();
        await Compose("up", "-d", "--wait", "db");
    }

    string PracticeRuns => Path.Combine(Root, "sumo-practica");

    async Task LoadPracticeCounts()
    {
        var folder = Path.Combine(PracticeRuns, Guid.NewGuid().ToString());
        Write("Ejecutando un día de tráfico sintético en SUMO y midiendo cruces por carril y clase…");
        await Run(Venv, ["desktop/sumo_practica.py", folder], timeoutMinutes: 3);
        var counts = (await File.ReadAllTextAsync(Path.Combine(folder, "conteos.csv"))).ReplaceLineEndings("\n");
        if (!counts.StartsWith("mensaje_id,interseccion,acceso,carril,clase,cantidad,inicio,fin\n",
            StringComparison.Ordinal) || counts.Contains("\n\\.\n") || !counts.EndsWith('\n'))
            throw new InvalidOperationException("SUMO no produjo el formato de conteos esperado.");

        var cleanup = await DemoSql("limpiar_conteos_practica.sql");
        var inventory = await DemoSql("practica.sql");
        await RunDemoSql(cleanup + "\n" + inventory + "\n" + """
            CREATE TEMP TABLE practica_sumo (
                mensaje_id uuid, interseccion text, acceso text, carril text, clase text,
                cantidad integer, inicio timestamptz, fin timestamptz
            ) ON COMMIT DROP;
            COPY practica_sumo FROM STDIN WITH (FORMAT csv, HEADER true);
            """ + "\n" + counts + "\\.\n" + """
            INSERT INTO conteos (mensaje_id, interseccion, acceso, carril, clase, cantidad, inicio, fin, prueba, origen_demo)
            SELECT mensaje_id, interseccion, acceso, carril, clase, cantidad, inicio, fin, true, 'practica'
            FROM practica_sumo;
            """);
    }

    public async Task OpenPracticeSumo()
    {
        PrepareDemoSources();
        RequireSumoClosed();
        await StartDemoDatabase();
        Guid? batch = null;
        await RunDemoSql("""
            SELECT mensaje_id FROM conteos
            WHERE origen_demo = 'practica' AND interseccion = 'DEMO_INT_01' AND carril = 'E_0' AND clase = 'auto'
            ORDER BY inicio LIMIT 1;
            """, line => { if (Guid.TryParse(line, out var id)) batch = id; });
        var config = batch is Guid run ? Path.Combine(PracticeRuns, run.ToString(), "practica.sumocfg") : null;
        if (config is null || !File.Exists(config))
            throw new InvalidOperationException("No hay una simulación asociada a los conteos actuales. Pulsa Cargar datos de práctica para generarla.");

        string? executable = null;
        var exit = await Run(Venv, ["desktop/sumo_gui.py", "--gui-binary"], check: false, output: false,
            onStandardOutput: line => executable = line);
        if (exit != 0 || !File.Exists(executable))
            throw new InvalidOperationException("Falta SUMO-GUI. Pulsa Configurar esta PC para reparar la instalación.");
        SumoGui = Start(executable!, ["-c", config, "--start", "--delay", "15", "--window-size", "1100,750",
            "--output-prefix", "reproduccion-"], Path.GetDirectoryName(config));
        await Task.Delay(1000);
        if (SumoGui.HasExited)
            throw new InvalidOperationException("La simulación de práctica no pudo abrirse. Revisa el registro de la ventana.");
        Write("SUMO-GUI reproduce el escenario de DEMO_INT_01 que generó los conteos de práctica. Puedes pausar y ajustar la velocidad.");
    }

    public async Task LoadVideoData(string file, string device)
    {
        RequireDetectorStopped();
        PrepareDemoSources();
        var csv = Path.Combine(Path.GetTempPath(), "cysa-video-" + Guid.NewGuid().ToString("N") + ".csv");
        try
        {
            Write("Calibra tres carriles y pulsa S. Al terminar el video, o al pulsar Q, se importan los intervalos procesados.");
            var exit = await Run(Venv, ["desktop/runtime.py", "detector", "--source", file,
                "--device", device, "--csv-video", csv], check: false, timeoutMinutes: 60);
            if (exit == 130)
            {
                Write("Carga cancelada. Se conservó la importación anterior.");
                return;
            }
            if (exit != 0 || !File.Exists(csv) || new FileInfo(csv).Length == 0)
                throw new InvalidOperationException("El video no produjo conteos importables. Revisa el registro y la calibración.");

            var counts = (await File.ReadAllTextAsync(csv)).ReplaceLineEndings("\n");
            if (!counts.StartsWith("version,mensaje_id,interseccion,acceso,carril,clase,cantidad,inicio,fin,prueba\n",
                StringComparison.Ordinal) || counts.Contains("\n\\.\n") || !counts.EndsWith('\n'))
                throw new InvalidOperationException("El detector no produjo el formato de conteos esperado.");

            await StartDemoDatabase();
            await RunDemoSql("""
                CREATE TEMP TABLE video_importado (
                    version text, mensaje_id uuid, interseccion text, acceso text,
                    carril text, clase text, cantidad integer, inicio timestamptz,
                    fin timestamptz, prueba boolean
                ) ON COMMIT DROP;
                COPY video_importado FROM STDIN WITH (FORMAT csv, HEADER true);
                """ + "\n" + counts + "\\.\n" + """
                DO $$
                BEGIN
                    IF (SELECT count(DISTINCT (acceso, carril)) FROM video_importado) <> 3
                       OR (SELECT count(DISTINCT acceso) FROM video_importado) <> 1 OR EXISTS (
                        SELECT 1 FROM video_importado
                        WHERE version IS DISTINCT FROM '1.0' OR interseccion IS DISTINCT FROM 'DEMO_VIDEO'
                           OR prueba IS DISTINCT FROM true
                    ) THEN
                        RAISE EXCEPTION 'El archivo debe contener conteos de tres carriles del mismo acceso';
                    END IF;
                END $$;

                DELETE FROM conteos WHERE origen_demo = 'video';
                INSERT INTO conteos (mensaje_id, interseccion, acceso, carril, clase, cantidad, inicio, fin, prueba, origen_demo)
                SELECT mensaje_id, interseccion, acceso, carril, clase, cantidad,
                       inicio + d.ajuste, fin + d.ajuste, prueba, 'video'
                FROM video_importado
                CROSS JOIN (SELECT now() - max(fin) AS ajuste FROM video_importado) AS d;
                """);
            await PublishCountRevision();
            Write("Video importado. En el panel selecciona Validación y DEMO_VIDEO. Los intervalos conservan la duración del video y terminan en la hora de carga.");
        }
        finally
        {
            File.Delete(csv);
        }
    }

    string ControllerIdleFile => Path.Combine(Root, "banco-sin-datos");
    internal bool ControllerIdle => File.Exists(ControllerIdleFile);

    Task KeepControllerIdle() => File.WriteAllTextAsync(ControllerIdleFile, "Espera una carga de práctica o la activación del Arduino.");

    string ProjectDataMarker => Path.Combine(Root, "proyecto-datos-aislados");
    bool ProjectDataIsolated => File.Exists(ProjectDataMarker);

    Task IsolateProjectData() => File.WriteAllTextAsync(ProjectDataMarker, "Configuraciones del panel en CYSA_Proyecto.");

    public async Task ResetDemoData()
    {
        PrepareDemoSources();
        await EnsureDocker();
        var web = await EnsureWebExecutable();
        var environment = OperationEnvironment();
        var webEnvironment = WebEnvironment(isolatedProject: true);
        await Run(web, ["--preparar-proyecto-esquema"], Path.GetDirectoryName(web), webEnvironment, timeoutMinutes: 5);
        await EnsureOperationRequirements(environment);
        await KeepControllerIdle();
        await IsolateProjectData();
        dockerSession.MarkUsed();
        await StopAll();

        arduinoResumePlan = null;
        if (arduinoControllerPort is not null)
        {
            arduinoPaused = true;
            SaveArduinoControl();
        }
        var telemetry = Path.Combine(Repo, "infra", "runtime", "control", "arduino-estado.json");
        var receipts = Path.Combine(Repo, "resultados", "controlador", "recibos.json");
        if (File.Exists(telemetry)) File.Delete(telemetry);
        if (File.Exists(receipts)) File.Delete(receipts);

        await StartDemoDatabase();
        await Run(web, ["--vaciar-proyecto"], Path.GetDirectoryName(web), webEnvironment, timeoutMinutes: 5);
        await Run(Venv, ["-m", "operacion.restablecer"], environment: environment, timeoutMinutes: 2);
        await RunDemoSql(await DemoSql("restablecer_postgresql.sql"));
        try
        {
            if (Directory.Exists(PracticeRuns)) Directory.Delete(PracticeRuns, recursive: true);
        }
        catch (Exception error) when (error is IOException or UnauthorizedAccessException)
        {
            Write("Los conteos se eliminaron, pero no se pudieron quitar todos los archivos de simulación guardados.");
        }
        Write("Datos de Proyecto de Sistemas eliminados. Preparando el panel vacío…");
        await StartAll(prepareWebIII: false);
        await PublishCountRevision();
    }
}

internal sealed partial class MainForm
{
    async Task LoadVideoData()
    {
        var device = SelectedDevice();
        using var picker = new OpenFileDialog
        {
            Title = "Cargar datos con video",
            Filter = "Videos|*.mp4;*.avi;*.mov;*.mkv;*.wmv|Todos|*.*"
        };
        if (picker.ShowDialog(this) == DialogResult.OK)
            await instance.LoadVideoData(picker.FileName, device);
    }

    async Task DeleteDemoData()
    {
        const string detail = "Se eliminarán los datos de Proyecto de Sistemas: conteos, inventario, estados, "
            + "configuraciones del panel, planes, decisiones y bitácoras. Se conservarán los datos de Web III, "
            + "tus cuentas de acceso, los ajustes de esta PC y los videos originales.\n\n"
            + "¿Quieres restablecer Proyecto de Sistemas?";
        if (MessageBox.Show(this, detail, "Eliminar datos", MessageBoxButtons.YesNo,
            MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2) != DialogResult.Yes) return;

        await instance.ResetDemoData();
        MessageBox.Show(this, "Proyecto de Sistemas quedó sin datos. Usa Cargar datos de práctica o Cargar datos con video cuando lo necesites.",
            "Eliminar datos", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }
}
