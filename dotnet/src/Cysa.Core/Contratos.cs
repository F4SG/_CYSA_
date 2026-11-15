using System.ComponentModel.DataAnnotations;

namespace Cysa.Core;

public sealed record AccesoEvaluado
{
    [Required, RegularExpression(@"^[A-Za-z0-9_-]{1,64}$")]
    public string Id { get; init; } = "";
    [Range(typeof(decimal), "0.001", "86400", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal DemoraBaseSegundos { get; init; }
    [Range(typeof(decimal), "0", "86400", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal DemoraCandidataSegundos { get; init; }
    [Range(typeof(decimal), "0.1", "500", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal LongitudCruceMetros { get; init; }
}

public sealed record FaseEvaluada
{
    [Required, RegularExpression(@"^[A-Za-z0-9_-]{1,64}$")]
    public string Id { get; init; } = "";
    [Required, MinLength(1), MaxLength(32)]
    public List<string> Accesos { get; init; } = [];
    [Range(typeof(decimal), "0", "3600", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal TiempoPeatonalSegundos { get; init; }
}

public sealed record SolicitudEvaluacion : IValidatableObject
{
    [Required, RegularExpression(@"^[A-Za-z0-9_-]{1,64}$")]
    public string PlanId { get; init; } = "";
    [Range(1, 1000000)]
    public int Version { get; init; }
    [Required, RegularExpression(@"^[A-Za-z0-9_-]{1,64}$")]
    public string InterseccionId { get; init; } = "";
    [Required, RegularExpression(@"^[A-Za-z0-9_-]{1,64}$")]
    public string PlanBaseId { get; init; } = "";
    [Required, StringLength(200, MinimumLength = 1)]
    public string Escenario { get; init; } = "";
    // Se importan métricas; esta API no ejecuta ni certifica la procedencia de SUMO.
    [Required, RegularExpression("^(demo|sumo-importado)$")]
    public string Origen { get; init; } = "demo";
    [Required, MinLength(1), MaxLength(32)]
    public List<AccesoEvaluado> Accesos { get; init; } = [];
    [Required, MinLength(1), MaxLength(64)]
    public List<FaseEvaluada> Fases { get; init; } = [];

    public IEnumerable<ValidationResult> Validate(ValidationContext context)
    {
        if (Accesos is null || Fases is null) yield break;
        if (Accesos.Any(a => a is null) || Fases.Any(f => f is null))
        {
            yield return new("No se admiten accesos ni fases nulos.");
            yield break;
        }
        if (PlanId == PlanBaseId) yield return new("El candidato y la referencia deben ser planes distintos.");
        if (Accesos.Select(a => a.Id).Distinct().Count() != Accesos.Count)
            yield return new("Los accesos no pueden repetirse.");
        if (Fases.Select(f => f.Id).Distinct().Count() != Fases.Count)
            yield return new("Las fases no pueden repetirse.");
        var ids = Accesos.Select(a => a.Id).ToHashSet();
        foreach (var fase in Fases)
            if (fase.Accesos is null || fase.Accesos.Distinct().Count() != fase.Accesos.Count || fase.Accesos.Any(id => !ids.Contains(id)))
                yield return new("Cada fase debe referir accesos existentes sin repetirlos.");
        var cubiertos = Fases.Where(f => f.Accesos is not null).SelectMany(f => f.Accesos).ToHashSet();
        if (!ids.IsSubsetOf(cubiertos)) yield return new("Todos los accesos necesitan una fase peatonal.");
    }
}

public sealed record MetricaAcceso(string AccesoId, decimal VariacionPorcentaje, decimal MinimoPeatonalSegundos);
public sealed record ResultadoEvaluacion(Guid Id, SolicitudEvaluacion Plan, string HuellaSha256,
    bool Aprobada, List<string> Motivos, List<MetricaAcceso> Metricas,
    DateTimeOffset CreadaUtc, DateTimeOffset VenceUtc, string EvaluadaPor, bool SoloPrueba = true);

public sealed record SolicitudDecision : IValidatableObject
{
    public Guid SolicitudId { get; init; }
    public Guid EvaluacionId { get; init; }
    [Range(1, 1000000)] public int Version { get; init; }
    [Required, RegularExpression("^(autorizar|rechazar)$")]
    public string Accion { get; init; } = "";
    [Required, StringLength(1000, MinimumLength = 5)]
    public string Motivo { get; init; } = "";

    public IEnumerable<ValidationResult> Validate(ValidationContext context)
    {
        if (SolicitudId == Guid.Empty || EvaluacionId == Guid.Empty)
            yield return new("Se requieren identificadores UUID no vacíos.");
        if (string.IsNullOrWhiteSpace(Motivo) || Motivo.Trim().Length < 5)
            yield return new("Explica el motivo con al menos cinco caracteres.");
    }
}

public sealed record ResultadoDecision(Guid Id, Guid SolicitudId, string PlanId, int Version,
    Guid EvaluacionId, string HuellaSha256, string EstadoAnterior, string EstadoPosterior,
    string Motivo, string UsuarioId, bool MfaVerificado, DateTimeOffset FechaUtc, bool SoloPrueba = true);
