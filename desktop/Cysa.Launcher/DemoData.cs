namespace Cysa.Launcher;

internal sealed partial class Instance
{
    const string PrepareDemoCounts = """
        BEGIN;
        SELECT pg_advisory_xact_lock(83217641);
        ALTER TABLE conteos ADD COLUMN IF NOT EXISTS origen_demo text;
        """;

    async Task RunDemoSql(string sql, params string[] variables)
    {
        var bindings = variables.SelectMany(value => new[] { "-v", value });
        var args = ComposeArgs(["exec", "-T", "db", "psql", "-X", "-U", "cysa", "-d", "cysa",
            "-v", "ON_ERROR_STOP=1", .. bindings, "-f", "-"]);
        await Run(Docker, args, timeoutMinutes: 2, input: PrepareDemoCounts + "\n" + sql + "\nCOMMIT;\n");
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
            Write("Video importado. En el panel selecciona Validación y DEMO_VIDEO. Los intervalos conservan la duración del video y terminan en la hora de carga.");
        }
        finally
        {
            File.Delete(csv);
        }
    }

    void EnsureVideoStopped()
    {
        if (Detector is { HasExited: false })
            throw new InvalidOperationException("Cierra el detector con Q y espera a que termine antes de eliminar los conteos.");
    }

    public async Task DeletePreviousVideo(DateTimeOffset from, DateTimeOffset to)
    {
        EnsureVideoStopped();
        if (to <= from || to - from > TimeSpan.FromSeconds(31))
            throw new ArgumentException("Indica el inicio y el fin de un intervalo del panel, de hasta 31 segundos.");
        PrepareDemoSources();
        await StartDemoDatabase();
        await RunDemoSql(await DemoSql("limpiar_video_anterior.sql"),
            "video_desde=" + from.ToString("O"), "video_hasta=" + to.ToString("O"));
    }

    public async Task DeleteDemoData(bool video)
    {
        if (video) EnsureVideoStopped();
        PrepareDemoSources();
        await StartDemoDatabase();
        if (video)
        {
            await RunDemoSql(await DemoSql("limpiar_conteos_video.sql"));
            return;
        }

        await Run(Venv, ["tools/franco/preparar_planes_demo.py", "--instalacion", Root, "--eliminar"],
            environment: OperationEnvironment(), timeoutMinutes: 2);
        await RunDemoSql(await DemoSql("limpiar_conteos_practica.sql") + "\n" + """
            DELETE FROM inventario
            WHERE interseccion = 'DEMO_INT_01' AND prueba AND (
                (activo_id IN ('DEMO_INT_01', 'DEMO_ACCESO_N', 'DEMO_ACCESO_S', 'DEMO_ACCESO_E', 'DEMO_ACCESO_W')
                    AND ubicacion = 'UBICACION_SINTETICA' AND protocolo = 'no_aplica')
                OR (activo_id = 'DEMO_CAM_01' AND tipo = 'camara' AND ubicacion = 'WEBCAM_DE_PRUEBA' AND protocolo = 'USB')
                OR (activo_id = 'DEMO_CTL_01' AND tipo = 'controlador' AND ubicacion = 'CONTROLADOR_FICTICIO' AND protocolo = 'MQTT_TLS')
            );
            """);
        Write("Datos de práctica retirados del panel. Las decisiones anteriores se conservan en el historial.");
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
        using var dialog = new Form
        {
            Text = "Eliminar datos", StartPosition = FormStartPosition.CenterParent,
            ClientSize = new Size(470, 254), FormBorderStyle = FormBorderStyle.FixedDialog,
            MinimizeBox = false, MaximizeBox = false, Padding = new Padding(16)
        };
        using var layout = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false };
        using var choices = new ComboBox { Width = 418, DropDownStyle = ComboBoxStyle.DropDownList, AccessibleName = "Conjunto de datos" };
        choices.Items.AddRange(["Conteos de video (en vivo e importados)", "Datos precargados de práctica",
            "Video anterior (buscar por intervalo)"]);
        using var legacy = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.TopDown, Visible = false };
        legacy.Controls.Add(new Label { Text = "Copia la fecha y las dos horas del período mostrado en el panel.", AutoSize = true });
        var now = DateTime.Now;
        DateTimePicker AddTime(string label, DateTime value)
        {
            var row = new FlowLayoutPanel { AutoSize = true, WrapContents = false };
            row.Controls.Add(new Label { Text = label, Width = 76, TextAlign = ContentAlignment.MiddleLeft });
            var field = new DateTimePicker
            {
                Format = DateTimePickerFormat.Custom, CustomFormat = "dd/MM/yyyy HH:mm:ss",
                Width = 248, Value = value, AccessibleName = label
            };
            row.Controls.Add(field);
            legacy.Controls.Add(row);
            return field;
        }
        var from = AddTime("Desde", now.AddSeconds(-20));
        var to = AddTime("Hasta", now);
        using var buttons = new FlowLayoutPanel { AutoSize = true };
        using var remove = new Button { Text = "Eliminar", AutoSize = true, Enabled = false };
        using var cancel = new Button { Text = "Cancelar", AutoSize = true, DialogResult = DialogResult.Cancel };
        choices.SelectedIndexChanged += (_, _) =>
        {
            remove.Enabled = choices.SelectedIndex >= 0;
            legacy.Visible = choices.SelectedIndex == 2;
        };
        remove.Click += (_, _) =>
        {
            if (choices.SelectedIndex == 2 && (to.Value <= from.Value || to.Value - from.Value > TimeSpan.FromSeconds(31)))
            {
                MessageBox.Show(dialog, "Indica el inicio y el fin de un intervalo del panel, de hasta 31 segundos.", "Eliminar datos");
                return;
            }
            var detail = choices.SelectedIndex switch
            {
                0 => "Se borrarán los conteos de video en vivo y los importados.",
                2 => $"Se buscará un lote de video anterior en DEMO_INT_01 entre {from.Value:dd/MM/yyyy HH:mm:ss} y {to.Value:HH:mm:ss} (hora local). Confirma que corresponde al video.",
                _ => "Se retirarán los conteos, activos de ejemplo y propuestas de práctica. Se conservarán las decisiones registradas."
            };
            if (MessageBox.Show(dialog, detail + "\n\n¿Confirmas la eliminación?", "Eliminar datos",
                MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2) == DialogResult.Yes)
                dialog.DialogResult = DialogResult.OK;
        };
        buttons.Controls.AddRange([remove, cancel]);
        layout.Controls.Add(new Label { Text = "Elige qué conjunto quieres eliminar.", AutoSize = true });
        layout.Controls.Add(choices);
        layout.Controls.Add(legacy);
        layout.Controls.Add(buttons);
        dialog.Controls.Add(layout);
        dialog.CancelButton = cancel;
        ApplyControlTheme(dialog);
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        if (choices.SelectedIndex == 2)
        {
            DateTimeOffset ToSecond(DateTime value) =>
                new(value.AddTicks(-(value.Ticks % TimeSpan.TicksPerSecond)));
            await instance.DeletePreviousVideo(ToSecond(from.Value), ToSecond(to.Value));
        }
        else
        {
            await instance.DeleteDemoData(video: choices.SelectedIndex == 0);
        }
    }
}
