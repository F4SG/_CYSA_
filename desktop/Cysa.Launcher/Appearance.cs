using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;
using System.ComponentModel;

namespace Cysa.Launcher;

// Paleta compartida visualmente con panel/tokens.css.
internal sealed record Palette(bool Dark, Color Background, Color Surface, Color Soft, Color Hover,
    Color Text, Color Muted, Color Line, Color Green, Color GreenSoft, Color GreenInk, Color Inverse,
    Color Danger, Color Blue, Color Purple, Color Amber)
{
    static Color Hex(string value) => ColorTranslator.FromHtml(value);
    public static Palette For(bool dark) => dark
        ? new(true, Hex("#101512"), Hex("#18201b"), Hex("#1d2720"), Hex("#26352b"), Hex("#edf3ef"), Hex("#a3b1a8"), Hex("#304036"), Hex("#83d9ac"), Hex("#213c2b"), Hex("#9de6bc"), Hex("#0e2417"), Hex("#ffaaa3"), Hex("#8dc5ff"), Hex("#d3afff"), Hex("#efc782"))
        : new(false, Hex("#f4f6f5"), Hex("#ffffff"), Hex("#f8faf9"), Hex("#eef3f0"), Hex("#17211c"), Hex("#647169"), Hex("#dfe6e1"), Hex("#176b47"), Hex("#e9f5ee"), Hex("#176b47"), Color.White, Hex("#a43b37"), Hex("#235eaa"), Hex("#7551a4"), Hex("#875b09"));
}

internal sealed class ThemedButton : Button
{
    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public Palette Theme { get; set; } = Palette.For(false);
    bool hovered;
    public ThemedButton()
    {
        SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
        FlatStyle = FlatStyle.Flat; UseVisualStyleBackColor = false;
    }
    protected override void OnMouseEnter(EventArgs e) { hovered = true; Invalidate(); base.OnMouseEnter(e); }
    protected override void OnMouseLeave(EventArgs e) { hovered = false; Invalidate(); base.OnMouseLeave(e); }
    protected override void OnEnabledChanged(EventArgs e) { Invalidate(); base.OnEnabledChanged(e); }
    protected override void OnPaint(PaintEventArgs e)
    {
        // El dibujado nativo ignora ForeColor cuando el botón está deshabilitado.
        // Pintar también ese estado evita texto negro sobre el fondo oscuro.
        e.Graphics.Clear(Enabled && hovered ? Theme.Hover : Theme.Soft);
        using var border = new Pen(Focused && ShowFocusCues ? Theme.Green : Theme.Line);
        e.Graphics.DrawRectangle(border, 0, 0, Width - 1, Height - 1);
        TextRenderer.DrawText(e.Graphics, Text, Font, ClientRectangle,
            Enabled ? Theme.Text : Theme.Muted,
            TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.SingleLine | TextFormatFlags.EndEllipsis);
        if (Focused && ShowFocusCues) ControlPaint.DrawFocusRectangle(e.Graphics, Rectangle.Inflate(ClientRectangle, -4, -4), Theme.Text, Theme.Soft);
    }
}

internal sealed class ActionTile : Button
{
    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public string Description { get; init; } = "";
    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool Primary { get; init; }
    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public Palette Theme { get; set; } = Palette.For(false);
    bool hovered;
    public ActionTile()
    {
        SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
        FlatStyle = FlatStyle.Flat; FlatAppearance.BorderSize = 0;
        Cursor = Cursors.Hand; UseVisualStyleBackColor = false;
    }
    protected override void OnMouseEnter(EventArgs e) { hovered = true; Invalidate(); base.OnMouseEnter(e); }
    protected override void OnMouseLeave(EventArgs e) { hovered = false; Invalidate(); base.OnMouseLeave(e); }
    protected override void OnEnabledChanged(EventArgs e) { Invalidate(); base.OnEnabledChanged(e); }
    protected override void OnPaint(PaintEventArgs e)
    {
        var p = Theme;
        float scale = DeviceDpi / 96f;
        int S(int n) => (int)(n * scale);
        e.Graphics.Clear(Parent?.BackColor ?? p.Background);
        e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        var box = new Rectangle(1, 1, Width - 3, Height - 3);
        var radius = S(12);
        using var shape = new GraphicsPath();
        shape.AddArc(box.Left, box.Top, radius, radius, 180, 90);
        shape.AddArc(box.Right - radius, box.Top, radius, radius, 270, 90);
        shape.AddArc(box.Right - radius, box.Bottom - radius, radius, radius, 0, 90);
        shape.AddArc(box.Left, box.Bottom - radius, radius, radius, 90, 90); shape.CloseFigure();
        var fill = Primary && Enabled ? (hovered ? p.GreenSoft : p.Green) : hovered && Enabled ? p.Hover : p.Surface;
        using var brush = new SolidBrush(fill); e.Graphics.FillPath(brush, shape);
        using var pen = new Pen(Focused && ShowFocusCues ? p.Green : Primary && Enabled ? p.Green : p.Line, Focused && ShowFocusCues ? 2 : 1);
        e.Graphics.DrawPath(pen, shape);
        var title = !Enabled ? p.Muted : Primary && !hovered ? p.Inverse : p.Text;
        var detail = !Enabled ? p.Muted : Primary && !hovered ? p.Inverse : p.Muted;
        using var heading = new Font(Font.FontFamily, 10, FontStyle.Bold);
        using var small = new Font(Font.FontFamily, 8.3f);
        TextRenderer.DrawText(e.Graphics, Text, heading, new Rectangle(S(16), S(12), Width - S(30), S(24)), title, TextFormatFlags.EndEllipsis | TextFormatFlags.SingleLine);
        TextRenderer.DrawText(e.Graphics, Description, small, new Rectangle(S(16), S(37), Width - S(30), Height - S(42)), detail, TextFormatFlags.EndEllipsis | TextFormatFlags.WordBreak);
    }
}

internal enum EntryKind { Normal, Action, Success, Warning, Error }
internal sealed record ConsoleEntry(DateTime Time, string Category, string Text, EntryKind Kind);

internal static partial class ConsoleStyle
{
    [GeneratedRegex(@"\x1b\[[0-?]*[ -/]*[@-~]")]
    private static partial Regex Ansi();
    public static ConsoleEntry Parse(string text, string operation)
    {
        text = Ansi().Replace(text, "");
        var lower = text.ToLowerInvariant();
        var kind = lower.StartsWith("error:") || lower.Contains("traceback (") || lower.Contains("exception:") || lower.Contains(" failed") && !lower.Contains("0 failed") ? EntryKind.Error
            : lower.Contains("warning") || lower.Contains("advertencia") ? EntryKind.Warning
            : text.StartsWith("▶") ? EntryKind.Action
            : lower.Contains("pass:") || lower.Contains(" passed") || lower.Contains("completad") || lower.Contains("terminad") || lower.Contains("recomendado:") || lower.Contains("sistema listo") ? EntryKind.Success : EntryKind.Normal;
        var category = lower.Contains("sumo") ? "SUMO"
            : lower.Contains("cuda") || lower.StartsWith("gpu") || lower.StartsWith("cpu:") || lower.Contains("yolo") ? "EQUIPO"
            : lower.Contains("container ") || lower.Contains("docker") || lower.Contains("mosquitto") || lower.Contains("keycloak") || lower.StartsWith("#") ? "DOCKER"
            : lower.Contains("pytest") || lower.Contains(" passed") || lower.Contains("pass:") ? "PRUEBAS" : operation;
        return new(DateTime.Now, category, text, kind);
    }
    public static Color CategoryColor(Palette p, string category) => category switch
    {
        "SUMO" => p.Purple,
        "DOCKER" => p.Blue,
        "EQUIPO" => p.Amber,
        "PRUEBAS" => p.GreenInk,
        _ => p.Blue
    };

    [DllImport("dwmapi.dll")]
    static extern int DwmSetWindowAttribute(IntPtr window, int attribute, ref int value, int size);
    public static void TitleBar(Form form, bool dark)
    {
        if (!form.IsHandleCreated) return;
        var value = dark ? 1 : 0;
        DwmSetWindowAttribute(form.Handle, 20, ref value, sizeof(int));
    }
}
