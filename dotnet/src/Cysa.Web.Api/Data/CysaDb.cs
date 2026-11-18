using Cysa.Infrastructure;
using Cysa.Web.Api.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace Cysa.Web.Api.Data;

public sealed class CysaDb(DbContextOptions<CysaDb> options) : DbContext(options)
{
    public DbSet<Interseccion> Intersecciones => Set<Interseccion>();
    public DbSet<Acceso> Accesos => Set<Acceso>();
    protected override void OnModelCreating(ModelBuilder m)
    {
        foreach (var t in typeof(Entidad).Assembly.GetTypes().Where(t => t.IsSubclassOf(typeof(Entidad))))
        {
            var b = m.Entity(t);
            b.ToTable(t.Name);
            b.HasKey(nameof(Entidad.Id));
            b.Property(nameof(Entidad.Id)).ValueGeneratedOnAdd();
            foreach (var p in t.GetProperties())
            {
                if (p.PropertyType == typeof(string)) b.Property(p.Name).IsRequired().HasMaxLength(
                    p.Name is "ValorAnterior" or "ValorPosterior" ? 16000 : p.Name is "Motivo" or "JustificacionTecnica" ? 1000 : 500);
                if (p.PropertyType == typeof(decimal)) b.Property(p.Name).HasPrecision(18, 6);
            }
        }
        m.Entity<Corredor>().HasIndex(e => e.Nombre).IsUnique();
        Link<Interseccion, Corredor>(m, "CorredorId");
        m.Entity<Interseccion>().HasIndex(e => new { e.CorredorId, e.Nombre }).IsUnique();
        Link<Acceso, Interseccion>(m, "InterseccionId");
        m.Entity<Acceso>().HasIndex(e => new { e.InterseccionId, e.Identificador }).IsUnique();
        Check<Acceso>(m,"LongitudPositiva","[LongitudCrucePeatonalMetros] > 0");
        Link<Carril, Acceso>(m,"AccesoId");
        m.Entity<Carril>().HasIndex(e => new { e.AccesoId,e.Numero }).IsUnique();
        Link<FuenteDeteccion, Acceso>(m,"AccesoId");
        Link<ControladorLocal, Interseccion>(m,"InterseccionId");
        m.Entity<ControladorLocal>().HasIndex(e => e.InterseccionId).IsUnique();
        Link<ConfigTecnica, Interseccion>(m,"InterseccionId");
        m.Entity<ConfigTecnica>().HasIndex(e=>new{e.InterseccionId,e.Version}).IsUnique();
        Check<ConfigTecnica>(m,"Limites","[VerdeMinSegundos] > 0 AND [VerdeMaxSegundos] >= [VerdeMinSegundos] AND [ExtensionPrioridadSegundos] BETWEEN 0 AND 10");
        Link<Plan, Interseccion>(m,"InterseccionId"); Link<Plan,ConfigTecnica>(m,"ConfigTecnicaId");
        m.Entity<Plan>().HasIndex(e=>new{e.InterseccionId,e.Version,e.Tipo}).IsUnique();
        Link<Fase,Plan>(m,"PlanId"); Link<Fase,Acceso>(m,"AccesoId");
        m.Entity<Fase>().HasIndex(e=>new{e.PlanId,e.Orden}).IsUnique();
        Link<EstadoControl,ControladorLocal>(m,"ControladorLocalId"); Link<EstadoControl,Plan>(m,"PlanId"); Link<EstadoControl,Fase>(m,"FaseId");
        m.Entity<EstadoControl>().HasIndex(e=>new{e.ControladorLocalId,e.Prueba,e.FechaUtc});
        Link<Medicion,Carril>(m,"CarrilId"); Link<Medicion,FuenteDeteccion>(m,"FuenteDeteccionId");
        m.Entity<Medicion>().HasIndex(e=>e.MensajeId).IsUnique();
        Check<Medicion>(m,"Intervalo","[FinUtc] > [InicioUtc] AND [Cantidad] >= 0");
        Link<EventoPrioridad,Interseccion>(m,"InterseccionId"); Link<EventoPrioridad,Plan>(m,"PlanId");
        Check<EventoPrioridad>(m,"Tiempo","[AtendidoUtc] >= [DetectadoUtc] AND [ExtensionSegundos] BETWEEN 0 AND 10");
        Link<Alerta,Interseccion>(m,"InterseccionId");
        Link<ValidacionSumo,Plan>(m,"PlanId");
        m.Entity<ValidacionSumo>().HasIndex(e=>e.PlanId).IsUnique();
        Link<MetricaPorAcceso,ValidacionSumo>(m,"ValidacionSumoId"); Link<MetricaPorAcceso,Acceso>(m,"AccesoId");
        m.Entity<MetricaPorAcceso>().HasIndex(e=>new{e.ValidacionSumoId,e.AccesoId,e.Grupo}).IsUnique();
        Link<Recomendacion,ValidacionSumo>(m,"ValidacionSumoId");
        m.Entity<Recomendacion>().HasIndex(e=>e.ValidacionSumoId).IsUnique();
        m.Entity<Rol>().HasIndex(e=>e.Nombre).IsUnique();
        Check<Rol>(m,"DosRoles","[Nombre] IN ('administrador','operador')");
        Link<Usuario,Rol>(m,"RolId"); m.Entity<Usuario>().HasIndex(e=>e.IdentificadorIdp).IsUnique();
        Link<Bitacora,Usuario>(m,"UsuarioId");
        m.Entity<Bitacora>().HasIndex(e=>e.SolicitudId).IsUnique().HasFilter("[SolicitudId] IS NOT NULL");
        m.Entity<VersionModelo>().HasIndex(e=>e.Identificador).IsUnique();
        Link<Reporte,Corredor>(m,"CorredorId");
        Check<Reporte>(m,"Periodo","[HastaUtc] > [DesdeUtc]");
        Link<FaseAcceso,Fase>(m,"FaseId"); Link<FaseAcceso,Acceso>(m,"AccesoId");
        m.Entity<FaseAcceso>().HasIndex(e=>new{e.FaseId,e.AccesoId}).IsUnique();
        Link<ValidacionMedicion,ValidacionSumo>(m,"ValidacionSumoId"); Link<ValidacionMedicion,Medicion>(m,"MedicionId");
        m.Entity<ValidacionMedicion>().HasIndex(e=>new{e.ValidacionSumoId,e.MedicionId}).IsUnique();
        Link<ValidacionEvento,ValidacionSumo>(m,"ValidacionSumoId"); Link<ValidacionEvento,EventoPrioridad>(m,"EventoPrioridadId");
        m.Entity<ValidacionEvento>().HasIndex(e=>new{e.ValidacionSumoId,e.EventoPrioridadId}).IsUnique();
        // Conserva los contratos inmutables de las APIs existentes en el mismo host y SQL Server.
        m.Entity<EvaluacionGuardada>().ToTable("Evaluaciones");
        m.Entity<EvaluacionGuardada>().Property(e=>e.PlanId).HasMaxLength(64);
        m.Entity<EvaluacionGuardada>().HasIndex(e=>new{e.PlanId,e.Version}).IsUnique();
        m.Entity<DecisionGuardada>().ToTable("Decisiones");
        m.Entity<DecisionGuardada>().Property(e=>e.PlanId).HasMaxLength(64);
        m.Entity<DecisionGuardada>().HasIndex(e=>e.SolicitudId).IsUnique();
        m.Entity<DecisionGuardada>().HasIndex(e=>new{e.PlanId,e.Version}).IsUnique();
    }
    static void Link<T,TParent>(ModelBuilder m,string property) where T:Entidad where TParent:Entidad =>
        m.Entity<T>().HasOne<TParent>().WithMany().HasForeignKey(property).OnDelete(DeleteBehavior.Restrict);
    static void Check<T>(ModelBuilder m,string name,string sql) where T:Entidad =>
        m.Entity<T>().ToTable(typeof(T).Name,t=>t.HasCheckConstraint($"CK_{typeof(T).Name}_{name}",sql));
}

public sealed class CysaDbFactory : IDesignTimeDbContextFactory<CysaDb>
{
    public CysaDb CreateDbContext(string[] args) => new(new DbContextOptionsBuilder<CysaDb>().UseSqlServer(
        Environment.GetEnvironmentVariable("ConnectionStrings__Cysa") ??
        "Server=localhost;Database=CYSA_WebIII_Demo;Integrated Security=True;TrustServerCertificate=True").Options);
}
