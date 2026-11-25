using System.Text.Json;

namespace Cysa.Launcher;

internal sealed partial class MainForm
{
    const int TerminalMessageLimit = 200;
    Palette theme = Palette.For(false);
    readonly ComboBox themeChoice = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 112, AccessibleName = "Tema", FlatStyle = FlatStyle.Flat };
    readonly CheckBox followOutput = new() { Text = "Seguir salida", Checked = true, AutoSize = true, Margin = new Padding(12, 8, 12, 0) };
    readonly List<ConsoleEntry> entries = [];
    string operation = "SISTEMA";
    bool failed;

    void BuildInterface()
    {
        Text = "CYSA · Centro de pruebas";
        AutoScaleDimensions = new SizeF(96, 96);
        AutoScaleMode = AutoScaleMode.Dpi;
        Font = new Font("Segoe UI", 10);
        Padding = new Padding(14, 10, 14, 10);
        StartPosition = FormStartPosition.Manual;
        var initialScreen = Screen.FromPoint(Cursor.Position);
        Location = initialScreen.WorkingArea.Location;

        var window = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 2 };
        window.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        window.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        window.RowStyles.Add(new RowStyle(SizeType.Absolute, 160));
        var viewport = new Panel { Dock = DockStyle.Fill, AutoScroll = true };
        var layout = new TableLayoutPanel { Dock = DockStyle.Top, ColumnCount = 1, RowCount = 7, AutoSize = true, AutoSizeMode = AutoSizeMode.GrowAndShrink };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        foreach (var height in new[] { 46, 218, 24, 480, 28, 28, 20 }) layout.RowStyles.Add(new RowStyle(SizeType.Absolute, height));
        viewport.Controls.Add(layout);
        window.Controls.Add(viewport, 0, 0);
        Controls.Add(window);

        var header = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2 };
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100)); header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 178));
        var titleLabel = new Label { Text = "CYSA  /  Centro de pruebas", Font = new Font(Font.FontFamily, 19, FontStyle.Bold), Dock = DockStyle.Fill, AutoEllipsis = true, TextAlign = ContentAlignment.MiddleLeft, Margin = Padding.Empty };
        header.Controls.Add(titleLabel);
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
        layout.Controls.Add(new Label { Text = "Sigue la numeración dentro de cada columna según la tarea que quieras realizar.", Dock = DockStyle.Fill, Tag = "muted", Margin = new Padding(0, 0, 0, 4) }, 0, 2);
        var equipment = new TableLayoutPanel { Dock = DockStyle.Fill, Margin = Padding.Empty, ColumnCount = 2, RowCount = 2 };
        equipment.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 56));
        equipment.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 44));
        equipment.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        equipment.RowStyles.Add(new RowStyle(SizeType.Absolute, 0));
        var arduino = BuildArduinoExplanation();
        arduino.Margin = new Padding(0, 0, 0, 8);
        equipment.Controls.Add(arduino, 0, 0);
        layout.Controls.Add(equipment, 0, 1);

        var hardwarePanel = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 3, Padding = new Padding(14, 8, 14, 8), Margin = new Padding(0, 0, 0, 8), Tag = "surface" };
        hardwarePanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 21)); hardwarePanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 68)); hardwarePanel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        hardwarePanel.Controls.Add(new Label { Text = "MOTOR DE CONTEO", AutoSize = true, Tag = "muted", Font = new Font(Font.FontFamily, 8, FontStyle.Bold) });
        var modes = new FlowLayoutPanel { Dock = DockStyle.Fill, Margin = Padding.Empty };
        cpu.Padding = gpu.Padding = new Padding(10, 5, 10, 5);
        modes.Controls.AddRange([cpu, gpu, prepareGpu]); hardwarePanel.Controls.Add(modes);
        hardwareDetail.Font = new Font(Font.FontFamily, 8.5f); hardwareDetail.Tag = "muted";
        hardwarePanel.Controls.Add(hardwareDetail); equipment.Controls.Add(hardwarePanel, 1, 0);
        prepareGpu.Click += async (_, _) => await Execute(async () => { await instance.PrepareGpu(); await RefreshHardware(); }, "EQUIPO");
        cpu.CheckedChanged += (_, _) => { if (!busy && cpu.Checked) instance.SaveDevice("cpu"); };
        gpu.CheckedChanged += (_, _) => { if (!busy && gpu.Checked && hardware != null) instance.SaveDevice(hardware.GpuDevice); };

        var buttons = new FlowLayoutPanel { Dock = DockStyle.Fill, Margin = Padding.Empty };
        layout.Controls.Add(buttons, 0, 3);
        var startup = Group("Inicio del sistema");
        Add(startup, "Configurar esta PC", "Primera vez · instala y crea tus cuentas", instance.Configure, "INSTALACIÓN", afterHardware: true);
        Add(startup, "Iniciar sistema", "Arranca los servicios de Proyecto de Sistemas", instance.StartAll, "SISTEMA", primary: true);
        Add(startup, "Credenciales", "Consulta las cuentas de esta PC", Credentials, "ACCESO");
        Add(startup, "Abrir panel", "Entra al panel de Proyecto de Sistemas", instance.OpenPanel, "PANEL");
        Add(startup, "Detener sistema", "Al terminar · detiene los servicios y conserva los datos", instance.StopAll, "DOCKER");

        var tests = Group("Pruebas y práctica");
        Add(tests, "Verificar sistema", "Revisa la conexión y los servicios", instance.Verify, "VERIFICACIÓN");
        Add(tests, "Cargar datos de práctica", "Prepara inventario, conteos sintéticos y cinco planes", instance.LoadPracticeData, "PRUEBAS", primary: true);
        Add(tests, "Cargar datos con video", "Importa al panel únicamente los conteos del archivo", LoadVideoData, "VIDEO");
        Add(tests, "Eliminar datos", "Elige conteos de video o datos precargados", DeleteDemoData, "PRUEBAS");
        Add(tests, "Ejecutar pruebas", "Ejecuta las comprobaciones automáticas", instance.Tests, "PRUEBAS");
        Add(tests, "Probar Arduino", "Opcional · prueba los LEDs del banco por USB", TestArduino, "ARDUINO");
        Add(tests, "Simulación SUMO", "Opcional · abre la demostración de dos cruces", instance.OpenSumo, "SUMO");

        var detection = Group("Conteo vehicular");
        Add(detection, "Detectar y recomendar", "Mide el equipo y sugiere CPU o GPU", RefreshHardware, "EQUIPO");
        Add(detection, "Contar con cámara", "Elige cámara o video como fuente", () => { var device = SelectedDevice(); using var dialog = new CameraDialog(); ApplyControlTheme(dialog); if (dialog.ShowDialog(this) == DialogResult.OK) instance.StartDetector(dialog.Source, device); return Task.CompletedTask; }, "CÁMARA");
        Add(detection, "Contar con video", "Alternativa a cámara · elige un archivo", () => { var device = SelectedDevice(); using var dialog = new OpenFileDialog { Filter = "Videos|*.mp4;*.avi;*.mov;*.mkv;*.wmv|Todos|*.*" }; if (dialog.ShowDialog(this) == DialogResult.OK) instance.StartDetector(dialog.FileName, device); return Task.CompletedTask; }, "VIDEO");

        var web = Group("Web III y APIs");
        Add(web, "SQL Server (Web III)", "Elige y prueba la instancia local", async () => { using var dialog = new SqlServerDialog(instance.SqlServerActual(), instance.SqlConnectionExterna, instance.ProbarSqlServer); ApplyControlTheme(dialog); if (dialog.ShowDialog(this) == DialogResult.OK) await instance.GuardarSqlServer(dialog.Instancia); }, "BASE DE DATOS");
        Add(web, "Swagger (Web III)", "Abre la documentación interactiva de la API", instance.OpenSwaggerWebIII, "API", primary: true);
        Add(web, "Panel Web III", "Abre los casos de uso y la gestión de datos", instance.OpenDatabaseWebIII, "PANEL");
        Add(web, "Evaluaciones", "Con el sistema iniciado, abre su Swagger", () => { Instance.Open($"http://localhost:{instance.Ports.Evaluation}/swagger"); return Task.CompletedTask; }, "API");
        Add(web, "Decisiones", "Con el sistema iniciado, abre su Swagger", () => { Instance.Open($"http://localhost:{instance.Ports.Decision}/swagger"); return Task.CompletedTask; }, "API");
        Add(web, "Recrear base de pruebas", "Opcional · borra y vuelve a cargar CYSA_WebIII_Demo", instance.ResetDatabaseWebIII, "BASE DE DATOS");
        status.Margin = new Padding(0, 5, 0, 0); layout.Controls.Add(status, 0, 4);
        var terminal = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 3, ColumnCount = 1, Padding = new Padding(12, 4, 12, 10), Margin = new Padding(0, 4, 0, 4), Tag = "surface" };
        terminal.RowStyles.Add(new RowStyle(SizeType.Absolute, 36)); terminal.RowStyles.Add(new RowStyle(SizeType.Absolute, 24)); terminal.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        var terminalHeader = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2 };
        terminalHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100)); terminalHeader.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 270));
        terminalHeader.Controls.Add(new Label { Text = "REGISTRO DE ACTIVIDAD", Tag = "muted", AutoSize = true, Font = new Font(Font.FontFamily, 8, FontStyle.Bold), Margin = new Padding(0, 11, 0, 0) });
        var tools = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft };
        var clear = new Button { Text = "Limpiar vista", AutoSize = true, FlatStyle = FlatStyle.Flat, Font = new Font(Font.FontFamily, 8), Margin = new Padding(0, 3, 0, 0), Cursor = Cursors.Hand };
        clear.Click += (_, _) => ClearEntries(); tools.Controls.Add(clear); tools.Controls.Add(followOutput);
        terminalHeader.Controls.Add(tools); terminal.Controls.Add(terminalHeader);
        var legend = new FlowLayoutPanel { Dock = DockStyle.Fill, Margin = Padding.Empty };
        foreach (var (label, tag) in new[] { ("● Sistema", "SISTEMA"), ("● Docker", "DOCKER"), ("● Equipo", "EQUIPO"), ("● SUMO", "SUMO"), ("● Correcto", "success"), ("● Aviso", "warning"), ("● Error", "error") })
            legend.Controls.Add(new Label { Text = label, Tag = "color:" + tag, Font = new Font(Font.FontFamily, 8), AutoSize = true, Margin = new Padding(0, 0, 14, 0) });
        terminal.Controls.Add(legend); terminal.Controls.Add(log); window.Controls.Add(terminal, 0, 1);
        var links = new FlowLayoutPanel { Dock = DockStyle.Fill, Margin = new Padding(0, 5, 0, 0) };
        Link("Instalar Docker Desktop", "https://docs.docker.com/desktop/setup/install/windows-install/"); Link("Abrir mis archivos", instance.Root);
        var logs = new LinkLabel { Text = "Ver registros", AutoSize = true, Margin = new Padding(10, 3, 0, 0) }; logs.LinkClicked += async (_, _) => await Execute(instance.ShowLogs, "DOCKER"); links.Controls.Add(logs);
        var tokens = new LinkLabel { Text = "Tokens de demo", AutoSize = true, Margin = new Padding(10, 3, 0, 0) }; tokens.LinkClicked += async (_, _) => await Execute(Tokens, "ACCESO"); links.Controls.Add(tokens); layout.Controls.Add(links, 0, 5);
        layout.Controls.Add(new Label { Text = "Entorno de pruebas · No activa semáforos reales.   Cámara: S guarda · D cambia sentido · Q sale.", AutoSize = true, Tag = "muted", Font = new Font(Font.FontFamily, 8), Margin = Padding.Empty });

        Load += (_, _) => {
            var workArea = initialScreen.WorkingArea;
            MinimumSize = new Size(Math.Min(workArea.Width, LogicalToDeviceUnits(460)), Math.Min(workArea.Height, LogicalToDeviceUnits(360)));
            var width = Math.Min(workArea.Width, LogicalToDeviceUnits(1300));
            var height = Math.Min(workArea.Height, LogicalToDeviceUnits(915));
            Bounds = new Rectangle(workArea.X + (workArea.Width - width) / 2, workArea.Y + (workArea.Height - height) / 2, width, height);
            ArrangeWindow();
            window.SizeChanged += (_, _) => ArrangeWindow();
            DpiChanged += (_, _) => BeginInvoke(ArrangeWindow);
        };

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

        void ArrangeWindow()
        {
            int Px(int value) => LogicalToDeviceUnits(value);
            // Keep the terminal in its own row. Only the controls above it scroll.
            window.SuspendLayout();
            layout.SuspendLayout();
            var wrapLegend = window.ClientSize.Width < Px(590);
            window.RowStyles[1].Height = Math.Clamp(window.ClientSize.Height / 5, Px(wrapLegend ? 182 : 166), Px(225));
            terminal.RowStyles[1].Height = Px(wrapLegend ? 40 : 24);

            // Account for the scrollbar up front so crossing a breakpoint cannot toggle it repeatedly.
            var contentWidth = window.ClientSize.Width - viewport.Margin.Horizontal - SystemInformation.VerticalScrollBarWidth;
            var wide = contentWidth >= Px(970);
            var narrow = contentWidth < Px(545);
            titleLabel.Text = narrow ? "CYSA" : "CYSA  /  Centro de pruebas";
            layout.RowStyles[2].Height = Px(narrow ? 40 : 24);
            var hardwareHeight = wide ? 0 : narrow ? 178 : 144;
            hardwarePanel.RowStyles[1].Height = Px(wide || contentWidth < Px(625) ? 68 : 42);
            hardwarePanel.Margin = new Padding(wide ? Px(8) : 0, 0, 0, Px(8));
            equipment.SuspendLayout();
            equipment.SetColumnSpan(hardwarePanel, 1);
            equipment.SetCellPosition(hardwarePanel, new TableLayoutPanelCellPosition(wide ? 1 : 0, wide ? 0 : 1));
            equipment.SetColumnSpan(arduino, wide ? 1 : 2);
            equipment.SetColumnSpan(hardwarePanel, wide ? 1 : 2);
            equipment.RowStyles[1].Height = Px(hardwareHeight);
            layout.RowStyles[1].Height = Px((narrow ? 239 : 218) + hardwareHeight);
            equipment.ResumeLayout();

            var columns = contentWidth >= Px(1000) ? 4 : contentWidth >= Px(530) ? 2 : 1;
            var columnWidth = Math.Max(Px(100), contentWidth / columns);
            var groups = buttons.Controls.Cast<TableLayoutPanel>().ToArray();
            buttons.SuspendLayout();
            foreach (var group in groups)
            {
                group.RowStyles[0].Height = Px(34);
                foreach (RowStyle row in group.RowStyles.Cast<RowStyle>().Skip(1)) row.Height = Px(74);
                var height = Px(34) + (group.RowCount - 1) * Px(74);
                group.Size = new Size(columnWidth - group.Margin.Horizontal, height);
            }
            layout.RowStyles[3].Height = groups.Chunk(columns).Sum(row => row.Max(group => group.Height + group.Margin.Vertical));
            buttons.ResumeLayout();
            layout.RowStyles[5].Height = Px(narrow ? 53 : 28);
            layout.RowStyles[6].Height = Px(narrow ? 34 : 20);
            layout.ResumeLayout(true);
            window.ResumeLayout(true);
        }

        TableLayoutPanel Group(string title)
        {
            var number = buttons.Controls.Count + 1;
            var group = new TableLayoutPanel { ColumnCount = 1, RowCount = 1, Margin = new Padding(0, 0, 8, 10), TabIndex = number - 1 };
            group.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            group.RowStyles.Add(new RowStyle(SizeType.Absolute, 34));
            group.Controls.Add(new Label { Text = $"{number}. {title}", Dock = DockStyle.Fill, TextAlign = ContentAlignment.MiddleLeft,
                Font = new Font(Font.FontFamily, 11, FontStyle.Bold), Margin = new Padding(5, 0, 0, 0) }, 0, 0);
            buttons.Controls.Add(group);
            return group;
        }

        void Add(TableLayoutPanel group, string title, string description, Func<Task> action, string category, bool primary = false, bool afterHardware = false)
        {
            var row = group.RowCount++;
            var button = new ActionTile { Text = $"{group.TabIndex + 1}.{row}  {title}", Description = description, Primary = primary,
                Dock = DockStyle.Fill, Margin = new Padding(4), TabIndex = row, AccessibleDescription = description };
            group.RowStyles.Add(new RowStyle(SizeType.Absolute, 74));
            actions.Add(button); group.Controls.Add(button, 0, row);
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
            var entry = ConsoleStyle.Parse(line, operation);
            entries.Add(entry);
            if (entries.Count == TerminalMessageLimit) ClearEntries();
            else DrawEntry(entry);
        }
    }
    void ClearEntries()
    {
        entries.Clear();
        log.Clear();
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
