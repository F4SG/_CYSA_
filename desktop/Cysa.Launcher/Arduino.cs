using System.Diagnostics;
using System.Text.Json;

namespace Cysa.Launcher;

internal sealed record ArduinoPort(string Device, string Description)
{
    public override string ToString() => $"{Device} — {Description}";
}

internal sealed partial class Instance
{
    string ArduinoSources => SourceRoot ?? Repo;
    string ArduinoPython => File.Exists(Path.Combine(ArduinoSources, ".venv", "Scripts", "python.exe"))
        ? Path.Combine(ArduinoSources, ".venv", "Scripts", "python.exe") : Venv;

    public async Task<ArduinoPort[]> ArduinoPorts()
    {
        if (!File.Exists(ArduinoPython))
            throw new InvalidOperationException("Configura esta PC primero para preparar Python y las dependencias del controlador.");
        var info = new ProcessStartInfo(ArduinoPython) { UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true };
        info.ArgumentList.Add("-c");
        info.ArgumentList.Add("import json; from serial.tools import list_ports; print(json.dumps([dict(Device=p.device, Description=p.description) for p in list_ports.comports()]))");
        using var process = Process.Start(info) ?? throw new InvalidOperationException("No se pudo consultar los puertos.");
        var output = process.StandardOutput.ReadToEndAsync();
        var error = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        try { await process.WaitForExitAsync(timeout.Token); }
        catch (OperationCanceledException) { process.Kill(true); throw new InvalidOperationException("La consulta de puertos excedió 15 segundos."); }
        var text = await output;
        var detail = await error;
        if (process.ExitCode != 0)
            throw new InvalidOperationException("No se pudieron listar los puertos. Comprueba las dependencias del controlador. " + detail);
        return JsonSerializer.Deserialize<ArduinoPort[]>(text) ?? [];
    }

    public async Task TestArduino(string port)
    {
        Write($"Probando Arduino en {port}. Cierra el Monitor Serie y otros controladores que usen ese puerto.");
        Write("La prueba cambia los LEDs y provoca fallas controladas del MMU en el banco de pruebas. No verifica visualmente el cableado.");
        var environment = new Dictionary<string, string> {
            ["PYTHONPATH"] = string.Join(Path.PathSeparator, new[] { "shared", "controlador" }.Select(p => Path.Combine(ArduinoSources, p)))
        };
        var code = await Run(ArduinoPython, ["-m", "cysa_controlador.probar_placa", "--config",
            "controlador/config/demo_int_01.yaml", "--puerto", port, "--no-interactivo"],
            cwd: ArduinoSources, environment: environment, check: false, timeoutMinutes: 2);
        if (code != 0) throw new InvalidOperationException("La prueba del Arduino detectó problemas. Revisa el registro: puerto ocupado, firmware mmu_cysa, cable USB o RESET manual.");
        Write("Arduino: TODO CORRECTO. Al cerrar el puerto quedará en rojo intermitente; se reinicia al iniciar el controlador.");
    }
}

internal sealed partial class MainForm
{
    readonly Label arduinoStep = new() { Dock = DockStyle.Fill, AutoEllipsis = true,
        Text = "Preparado · Pulsa Probar Arduino para comenzar.", AccessibleName = "Paso actual de la prueba Arduino" };
    bool testingArduino;

    Control BuildArduinoExplanation()
    {
        var panel = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 4,
            Padding = new Padding(14, 8, 14, 8), Margin = new Padding(0, 0, 0, 10), Tag = "surface" };
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 40));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        panel.Controls.Add(new Label { Text = "ARDUINO · SECUENCIA Y DEMOSTRACIÓN", Dock = DockStyle.Fill,
            Font = new Font(Font.FontFamily, 9, FontStyle.Bold) });
        panel.Controls.Add(new Label { Dock = DockStyle.Fill, Text = "1 Conexión USB  →  2 Verde / ámbar / rojo por sentido  →  3 Pérdida de señal\n4 Verdes en conflicto  →  5 Ámbar corto · Se reinicia la placa entre las pruebas de falla." });
        panel.Controls.Add(arduinoStep);
        panel.Controls.Add(new Label { Dock = DockStyle.Fill, Tag = "muted", Font = new Font(Font.FontFamily, 8),
            Text = "Comprueba comunicación y protecciones del Arduino. Observa los LEDs: el software no verifica el cableado ni la gestión del tráfico." });
        return panel;
    }

    void ExplainArduino(string text)
    {
        if (!testingArduino) return;
        var line = text.Trim();
        if (line.StartsWith("1)")) arduinoStep.Text = "PASO 1 · Conexión USB: espera LISTO:2. Demuestra que responde el firmware del Arduino para los dos grupos.";
        else if (line.StartsWith("2)")) arduinoStep.Text = "PASO 2 · Ciclo seguro: verde → ámbar → rojo en cada sentido. Demuestra que el programa acepta la secuencia normal sin reportar fallas.";
        else if (line.StartsWith("3)")) arduinoStep.Text = "PASO 3 · Se dejan de enviar órdenes. Debe detectar SIN_SEÑAL y pasar a rojo intermitente: protección cuando se pierde la comunicación.";
        else if (line.StartsWith("4)")) arduinoStep.Text = "PASO 4 · Se envían verdes incompatibles a propósito. Debe detectar CONFLICTO y pasar a rojo intermitente: protección contra un cruce peligroso.";
        else if (line.StartsWith("5)")) arduinoStep.Text = "PASO 5 · Se acorta el ámbar a propósito. Debe detectar AMBAR_CORTO: protección que impide omitir el tiempo mínimo antes del rojo.";
        else if (line.Contains("=VERDE") || line.Contains("=AMBAR") || line.Contains("=ROJO"))
            arduinoStep.Text = "PASO 2 · Luces ordenadas: " + line + ".\nNS = norte-sur; EO = este-oeste. Compara los LEDs con esta orden; se verifica que el Arduino no reporte una falla.";
        else if (line.StartsWith("ERROR:") || line.StartsWith("FALLA")) arduinoStep.Text = "PRUEBA CON PROBLEMAS · " + line + " · Revisa el registro de actividad.";
        else if (line.StartsWith("Resultado:")) arduinoStep.Text = line.Contains("TODO CORRECTO")
            ? "PRUEBA COMPLETADA · El Arduino respondió y detectó las fallas provocadas. Confirma visualmente los LEDs. Al cerrar el puerto queda en rojo intermitente."
            : "PRUEBA CON PROBLEMAS · " + line + ". Revisa los resultados de cada paso en el registro.";
    }

    async Task TestArduino()
    {
        var ports = await instance.ArduinoPorts();
        if (ports.Length == 0) throw new InvalidOperationException("No se detectaron puertos serie. Conecta el Arduino con un cable USB de datos y vuelve a intentar.");
        using var dialog = new Form { Text = "Probar Arduino", ClientSize = new Size(620, 240),
            StartPosition = FormStartPosition.CenterParent, FormBorderStyle = FormBorderStyle.FixedDialog,
            MaximizeBox = false, MinimizeBox = false };
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(16), RowCount = 3, ColumnCount = 1 };
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 44));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 44));
        layout.Controls.Add(new Label { Dock = DockStyle.Fill, Text = "Selecciona el puerto del Arduino con mmu_cysa cargado. Cierra el Monitor Serie.\n\nSe probarán la conexión, las luces y las protecciones del MMU. Usa solo el banco de LEDs. Si no reinicia automáticamente, el registro pedirá repetir tras pulsar RESET." });
        var choice = new ComboBox { Dock = DockStyle.Fill, DropDownStyle = ComboBoxStyle.DropDownList, AccessibleName = "Puerto del Arduino" };
        choice.Items.AddRange(ports.Cast<object>().ToArray()); choice.SelectedIndex = 0;
        layout.Controls.Add(choice);
        var buttons = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft };
        var start = new Button { Text = "Probar", DialogResult = DialogResult.OK, AutoSize = true };
        buttons.Controls.Add(start);
        buttons.Controls.Add(new Button { Text = "Cancelar", DialogResult = DialogResult.Cancel, AutoSize = true });
        layout.Controls.Add(buttons); dialog.Controls.Add(layout); dialog.AcceptButton = start;
        ApplyControlTheme(dialog);
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        testingArduino = true;
        arduinoStep.Text = "INICIANDO · Abriendo el puerto USB del Arduino…";
        try {
            await instance.TestArduino(((ArduinoPort)choice.SelectedItem!).Device);
            arduinoStep.Text = "PRUEBA COMPLETADA · El Arduino respondió y detectó las fallas provocadas. Confirma visualmente los LEDs. Al cerrar el puerto queda en rojo intermitente.";
        }
        catch { arduinoStep.Text = "PRUEBA CON PROBLEMAS · Revisa el registro: comunicación, firmware o reinicio de la placa."; throw; }
        finally { testingArduino = false; }
    }
}
