using System.Text.Json;

namespace Cysa.Launcher;

internal sealed partial class MainForm
{
    Palette theme = Palette.For(false);
    readonly ComboBox themeChoice = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 112, AccessibleName = "Tema", FlatStyle = FlatStyle.Flat };
    readonly CheckBox followOutput = new() { Text = "Seguir salida", Checked = true, AutoSize = true, Margin = new Padding(12, 8, 12, 0) };
    readonly List<ConsoleEntry> entries = [];
    string operation = "SISTEMA";
    bool failed;

    void BuildInterface()
    {
        Text = "CYSA · Centro de pruebas";
        MinimumSize = new Size(1040, 850); Size = new Size(1240, 1020);
        StartPosition = FormStartPosition.CenterScreen; Font = new Font("Segoe UI", 10); Padding = new Padding(28, 22, 28, 18);
        var viewport = new Panel { Dock = DockStyle.Fill, AutoScroll = true };
        var layout = new TableLayoutPanel { Dock = DockStyle.Top, Height = 1080, ColumnCount = 1, RowCount = 9 };
        foreach (var height in new[] { 62, 30, 160, 146, 385, 32 }) layout.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 36)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        viewport.Controls.Add(layout); Controls.Add(viewport);

        var header = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2 };
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100)); header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 225));
        header.Controls.Add(new Label { Text = "CYSA  /  Centro de pruebas", Font = new Font(Font.FontFamily, 22, FontStyle.Bold), AutoSize = true, Margin = new Padding(0, 4, 0, 0) });
        var appearance = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft, Padding = new Padding(0, 10, 0, 0) };
        themeChoice.Items.AddRange(["Claro", "Oscuro"]); appearance.Controls.Add(themeChoice);
        themeChoice.DrawMode = DrawMode.OwnerDrawFixed;
        themeChoice.DrawItem += (_, e) => {
            if (e.Index < 0) return;
            var selected = e.State.HasFlag(DrawItemState.Selected);
            using var background = new SolidBrush(selected ? theme.GreenSoft : theme.Surface);
            e.Graphics.FillRectangle(background, e.Bounds);
            TextRenderer.DrawText(e.Graphics, Convert.ToString(themeChoice.Items[e.Index]) ?? "", themeChoice.Font, e.Bounds, selected ? theme.GreenInk : theme.Text, TextFormatFlags.Left | TextFormatFlags.VerticalCenter);
            e.DrawFocusRectangle();
        };
        appearance.Controls.Add(new Label { Text = "TEMA", AutoSize = true, Tag = "muted", Font = new Font(Font.FontFamily, 8, FontStyle.Bold), Margin = new Padding(0, 7, 8, 0) });
        header.Controls.Add(appearance); layout.Controls.Add(header);
        layout.Controls.Add(new Label { Text = "Configura tu equipo, prueba cada apartado y sigue su actividad en un solo lugar.", Dock = DockStyle.Fill, Tag = "muted", Margin = new Padding(0, 0, 0, 10) });
        layout.Controls.Add(BuildArduinoExplanation());

        var hardwarePanel = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 3, Padding = new Padding(14, 8, 14, 8), Margin = new Padding(0, 0, 0, 12), Tag = "surface" };
        hardwarePanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 24)); hardwarePanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 44)); hardwarePanel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        hardwarePanel.Controls.Add(new Label { Text = "MOTOR DE CONTEO", AutoSize = true, Tag = "muted", Font = new Font(Font.FontFamily, 8, FontStyle.Bold) });
        var modes = new FlowLayoutPanel { Dock = DockStyle.Fill, Margin = Padding.Empty };
        cpu.Padding = gpu.Padding = new Padding(10, 5, 10, 5);
        modes.Controls.AddRange([cpu, gpu, detectHardware, prepareGpu]); hardwarePanel.Controls.Add(modes);
        hardwareDetail.Font = new Font(Font.FontFamily, 8.5f); hardwareDetail.Tag = "muted";
        hardwarePanel.Controls.Add(hardwareDetail); layout.Controls.Add(hardwarePanel);
        detectHardware.Click += async (_, _) => await Execute(RefreshHardware, "EQUIPO");
        prepareGpu.Click += async (_, _) => await Execute(async () => { await instance.PrepareGpu(); await RefreshHardware(); }, "EQUIPO");
        cpu.CheckedChanged += (_, _) => { if (!busy && cpu.Checked) instance.SaveDevice("cpu"); };
        gpu.CheckedChanged += (_, _) => { if (!busy && gpu.Checked && hardware != null) instance.SaveDevice(hardware.GpuDevice); };

        var buttons = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 4, RowCount = 5, Margin = new Padding(-4, 0, -4, 0) };
        for (var i = 0; i < 4; i++) { buttons.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25));  }
        for (var row = 0; row < 5; row++) buttons.RowStyles.Add(new RowStyle(SizeType.Percent, 20));
        layout.Controls.Add(buttons);
        Add("Configurar esta PC", "Instala y crea tus cuentas", instance.Configure, "INSTALACIÓN", afterHardware: true);
        Add("Iniciar sistema", "Inicia todos los módulos de Proyecto de Sistemas", instance.StartAll, "SISTEMA", primary: true);
        Add("Abrir panel", "Abre el proyecto y renueva cinco ejemplos", instance.OpenPanel, "PANEL");
        Add("Credenciales", "Cuentas de esta PC", Credentials, "ACCESO");
        Add("Contar con cámara", "Conteo desde una cámara", () => { var device = SelectedDevice(); using var dialog = new CameraDialog(); ApplyControlTheme(dialog); if (dialog.ShowDialog(this) == DialogResult.OK) instance.StartDetector(dialog.Source, device); return Task.CompletedTask; }, "CÁMARA");
        Add("Contar con video", "Conteo desde un archivo", () => { var device = SelectedDevice(); using var dialog = new OpenFileDialog { Filter = "Videos|*.mp4;*.avi;*.mov;*.mkv;*.wmv|Todos|*.*" }; if (dialog.ShowDialog(this) == DialogResult.OK) instance.StartDetector(dialog.FileName, device); return Task.CompletedTask; }, "VIDEO");
        Add("Evaluaciones", "Prueba la API de evaluaciones", () => { Instance.Open($"http://localhost:{instance.Ports.Evaluation}/swagger"); return Task.CompletedTask; }, "API");
        Add("Decisiones", "Prueba la API de decisiones", () => { Instance.Open($"http://localhost:{instance.Ports.Decision}/swagger"); return Task.CompletedTask; }, "API");
        Add("Probar Arduino", "Prueba automática del banco de LEDs por USB", TestArduino, "ARDUINO");
        Add("Verificar sistema", "Revisa conexión y servicios", instance.Verify, "VERIFICACIÓN");
        Add("Ejecutar pruebas", "Comprueba los módulos", instance.Tests, "PRUEBAS");
        Add("SQL Server (Web III)", "Elige y prueba la instancia local", async () => { using var dialog = new SqlServerDialog(instance.SqlServerActual(), instance.SqlConnectionExterna, instance.ProbarSqlServer); ApplyControlTheme(dialog); if (dialog.ShowDialog(this) == DialogResult.OK) await instance.GuardarSqlServer(dialog.Instancia); }, "BASE DE DATOS");
        Add("Detener sistema", "Detiene y conserva tus datos", instance.StopAll, "DOCKER");
        Add("Swagger (Web III)", "Prepara SQL Server y API · Sin cámara ni SUMO", instance.OpenSwaggerWebIII, "API", primary: true);
        Add("Panel Web III", "Accesos a casos de uso y gestión de datos", instance.OpenDatabaseWebIII, "PANEL");
        Add("Recrear base de pruebas", "BORRA CYSA_WebIII_Demo y carga migraciones + datos", instance.ResetDatabaseWebIII, "BASE DE DATOS");
        Add("Simulación SUMO (demo)", "Dos cruces animados y prioridad para una ambulancia", instance.OpenSumo, "SUMO");
        status.Margin = new Padding(0, 5, 0, 0); layout.Controls.Add(status);

        var terminal = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 3, ColumnCount = 1, Padding = new Padding(12, 4, 12, 10), Margin = new Padding(0, 4, 0, 4), Tag = "surface" };
        terminal.RowStyles.Add(new RowStyle(SizeType.Absolute, 36)); terminal.RowStyles.Add(new RowStyle(SizeType.Absolute, 24)); terminal.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        var terminalHeader = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2 };
        terminalHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100)); terminalHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 270));
        terminalHeader.Controls.Add(new Label { Text = "REGISTRO DE ACTIVIDAD", Tag = "muted", AutoSize = true, Font = new Font(Font.FontFamily, 8, FontStyle.Bold), Margin = new Padding(0, 11, 0, 0) });
        var tools = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft };
        var clear = new Button { Text = "Limpiar vista", AutoSize = true, FlatStyle = FlatStyle.Flat, Font = new Font(Font.FontFamily, 8), Margin = new Padding(0, 3, 0, 0), Cursor = Cursors.Hand };
        clear.Click += (_, _) => { entries.Clear(); log.Clear(); }; tools.Controls.Add(clear); tools.Controls.Add(followOutput);
        terminalHeader.Controls.Add(tools); terminal.Controls.Add(terminalHeader);
        var legend = new FlowLayoutPanel { Dock = DockStyle.Fill, Margin = Padding.Empty };
        foreach (var (label, tag) in new[] { ("● Sistema", "SISTEMA"), ("● Docker", "DOCKER"), ("● Equipo", "EQUIPO"), ("● SUMO", "SUMO"), ("● Correcto", "success"), ("● Aviso", "warning"), ("● Error", "error") })
            legend.Controls.Add(new Label { Text = label, Tag = "color:" + tag, Font = new Font(Font.FontFamily, 8), AutoSize = true, Margin = new Padding(0, 0, 14, 0) });
        terminal.Controls.Add(legend); terminal.Controls.Add(log); layout.Controls.Add(terminal);
        var links = new FlowLayoutPanel { Dock = DockStyle.Fill, Margin = new Padding(0, 5, 0, 0) };
        Link("Instalar Docker Desktop", "https://docs.docker.com/desktop/setup/install/windows-install/"); Link("Abrir mis archivos", instance.Root);
        var logs = new LinkLabel { Text = "Ver registros", AutoSize = true, Margin = new Padding(10, 3, 0, 0) }; logs.LinkClicked += async (_, _) => await Execute(instance.ShowLogs, "DOCKER"); links.Controls.Add(logs);
        var tokens = new LinkLabel { Text = "Tokens de demo", AutoSize = true, Margin = new Padding(10, 3, 0, 0) }; tokens.LinkClicked += async (_, _) => await Execute(Tokens, "ACCESO"); links.Controls.Add(tokens); layout.Controls.Add(links);
        layout.Controls.Add(new Label { Text = "Entorno de pruebas · No activa semáforos reales.   Cámara: S guarda · D cambia sentido · Q sale.", AutoSize = true, Tag = "muted", Font = new Font(Font.FontFamily, 8), Margin = Padding.Empty });

        instance.Log = text => { if (IsHandleCreated && !IsDisposed) { try { BeginInvoke(() => AppendEntry(text)); } catch (InvalidOperationException) { } } };
        themeChoice.SelectedIndex = LoadDarkTheme() ? 1 : 0;
        ApplyTheme();
        themeChoice.SelectedIndexChanged += (_, _) => { ApplyTheme(); SaveTheme(); };
        HandleCreated += (_, _) => ConsoleStyle.TitleBar(this, theme.Dark);
        Shown += async (_, _) => {
            instance.Write("Datos de esta instalación: " + instance.Root + " | Proyecto Docker: " + instance.Project);
            cpu.Enabled=gpu.Enabled=false;
            hardwareDetail.Text="Para cámara o video, pulsa Detectar y recomendar. Web III puede usarse sin medir CPU/GPU ni cargar YOLO.";
            if (instance.Configured) await Execute(async () => { instance.Seed(); await instance.StartAll(); }, "SISTEMA");
        };
        FormClosing += async (_, e) => {
            if (closing) return;
            e.Cancel = true;
            if (busy) { MessageBox.Show(this, "Espera a que termine la operación actual.", "CYSA"); return; }
            await Execute(instance.StopAll, "SISTEMA"); closing = true; Close();
        };

        void Add(string title, string description, Func<Task> action, string category, bool primary = false, bool afterHardware = false)
        {
            var button = new ActionTile { Text = title, Description = description, Primary = primary, Dock = DockStyle.Fill, Margin = new Padding(4), AccessibleDescription = description };
            actions.Add(button); buttons.Controls.Add(button);
            button.Click += async (_, _) => await Execute(async () => { await action(); if (afterHardware) await RefreshHardware(); }, category, title);
        }
        void Link(string title, string target) { var link = new LinkLabel { Text = title, AutoSize = true, Margin = new Padding(0, 3, 16, 0) }; link.LinkClicked += (_, _) => Instance.Open(target); links.Controls.Add(link); }
    }

    bool LoadDarkTheme()
    {
        try { return JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(Path.Combine(instance.Root, "appearance.json")))?.GetValueOrDefault("Theme") == "dark"; }
        catch (Exception error) when (error is IOException or JsonException) { return false; }
    }
    void SaveTheme()
    {
        try { File.WriteAllText(Path.Combine(instance.Root, "appearance.json"), JsonSerializer.Serialize(new { Theme = theme.Dark ? "dark" : "light" })); }
        catch (IOException) { instance.Write("ADVERTENCIA: No se pudo guardar el tema. Puedes seguir usando la ventana."); }
    }
    void ApplyTheme()
    {
        theme = Palette.For(themeChoice.SelectedIndex == 1);
        SuspendLayout(); ApplyControlTheme(this); StyleRecommendation(); RenderEntries(); ConsoleStyle.TitleBar(this, theme.Dark); ResumeLayout(true);
    }
    void ApplyControlTheme(Control control)
    {
        control.BackColor = control.Tag as string == "surface" ? theme.Surface : control.Parent?.BackColor ?? theme.Background;
        control.ForeColor = control.Tag as string == "muted" ? theme.Muted : theme.Text;
        if (control is Form) control.BackColor = theme.Background;
        if (control is ActionTile tile) { tile.Theme = theme; tile.Invalidate(); }
        else if (control is ThemedButton themedButton) { themedButton.Theme = theme; themedButton.Invalidate(); }
        else if (control is Button button) { button.BackColor = theme.Soft; button.FlatStyle = FlatStyle.Flat; button.FlatAppearance.BorderColor = theme.Line; button.FlatAppearance.MouseOverBackColor = theme.Hover; }
        else if (control is ComboBox or TextBoxBase or NumericUpDown) control.BackColor = theme.Surface;
        if (control is LinkLabel link) { link.LinkColor = theme.GreenInk; link.ActiveLinkColor = theme.Green; link.VisitedLinkColor = theme.GreenInk; }
        if (control.Tag is string tag && tag.StartsWith("color:")) control.ForeColor = LogColor(tag[6..]);
        foreach (Control child in control.Controls) ApplyControlTheme(child);
        status.ForeColor = failed ? theme.Danger : theme.GreenInk;
    }
    void StyleRecommendation()
    {
        var recommendGpu = hardware?.Recommended != "cpu" && hardware?.GpuReady == true;
        cpu.BackColor = hardware != null && !recommendGpu ? theme.GreenSoft : cpu.Parent?.BackColor ?? theme.Surface;
        gpu.BackColor = recommendGpu ? theme.GreenSoft : gpu.Parent?.BackColor ?? theme.Surface;
        cpu.ForeColor = hardware != null && !recommendGpu ? theme.GreenInk : theme.Text;
        gpu.ForeColor = recommendGpu ? theme.GreenInk : theme.Text;
    }
    Color LogColor(string category) => category switch { "success" => theme.GreenInk, "warning" => theme.Amber, "error" => theme.Danger, _ => ConsoleStyle.CategoryColor(theme, category) };
    void AppendEntry(string text)
    {
        foreach (var line in text.Replace("\r", "").Split('\n', StringSplitOptions.RemoveEmptyEntries))
        {
            ExplainArduino(line);
            var entry = ConsoleStyle.Parse(line, operation); entries.Add(entry);
            if (entries.Count > 800 || log.TextLength > 180000) { entries.RemoveRange(0, Math.Min(200, entries.Count - 1)); RenderEntries(); }
            else DrawEntry(entry);
        }
    }
    void DrawEntry(ConsoleEntry entry)
    {
        var selection = log.SelectionStart; var length = log.SelectionLength;
        void Write(string value, Color color) { log.Select(log.TextLength, 0); log.SelectionColor = color; log.AppendText(value); }
        Write($"{entry.Time:HH:mm:ss}  ", theme.Muted);
        Write($"[{entry.Category}] ", ConsoleStyle.CategoryColor(theme, entry.Category));
        Write(entry.Text + Environment.NewLine, entry.Kind switch { EntryKind.Error => theme.Danger, EntryKind.Warning => theme.Amber, EntryKind.Success => theme.GreenInk, EntryKind.Action => theme.Blue, _ => theme.Text });
        if (followOutput.Checked) { log.Select(log.TextLength, 0); log.ScrollToCaret(); }
        else log.Select(Math.Min(selection, log.TextLength), Math.Min(length, Math.Max(0, log.TextLength - selection)));
    }
    void RenderEntries()
    {
        var selection = log.SelectionStart; var length = log.SelectionLength;
        log.SuspendLayout(); log.Clear(); foreach (var entry in entries) DrawEntry(entry);
        if (!followOutput.Checked) log.Select(Math.Min(selection, log.TextLength), Math.Min(length, Math.Max(0, log.TextLength - selection)));
        log.ResumeLayout();
    }
}
