using Microsoft.EntityFrameworkCore;

namespace Cysa.Infrastructure;

public sealed class EvaluacionGuardada
{
    public Guid Id { get; set; }
    public string PlanId { get; set; } = "";
    public int Version { get; set; }
    public string Json { get; set; } = "";
}

public sealed class DecisionGuardada
{
    public Guid Id { get; set; }
    public Guid SolicitudId { get; set; }
    public string PlanId { get; set; } = "";
    public int Version { get; set; }
    public string UsuarioId { get; set; } = "";
    public string SolicitudJson { get; set; } = "";
    public string ResultadoJson { get; set; } = "";
    public string EvaluacionJson { get; set; } = "";
}

public sealed class EvaluacionesDb(DbContextOptions<EvaluacionesDb> options) : DbContext(options)
{
    public DbSet<EvaluacionGuardada> Evaluaciones => Set<EvaluacionGuardada>();
    protected override void OnModelCreating(ModelBuilder model)
    {
        model.Entity<EvaluacionGuardada>().HasIndex(e => new { e.PlanId, e.Version }).IsUnique();
    }
}

public sealed class DecisionesDb(DbContextOptions<DecisionesDb> options) : DbContext(options)
{
    public DbSet<DecisionGuardada> Decisiones => Set<DecisionGuardada>();
    protected override void OnModelCreating(ModelBuilder model)
    {
        model.Entity<DecisionGuardada>().HasIndex(d => d.SolicitudId).IsUnique();
        model.Entity<DecisionGuardada>().HasIndex(d => new { d.PlanId, d.Version }).IsUnique();
    }
}
