namespace Cysa.Web.Api.Models;

public abstract class Entidad { public int Id { get; set; } public bool Prueba { get; set; } = true; }

public sealed class Corredor : Entidad
{
    public string Nombre { get; set; } = "";
    public string Descripcion { get; set; } = "";
}

public sealed class Interseccion : Entidad
{
    public int CorredorId { get; set; } = 0;
    public string Nombre { get; set; } = "";
    public decimal Latitud { get; set; } = 0;
    public decimal Longitud { get; set; } = 0;
    public string EstadoOperativo { get; set; } = "";
}

public sealed class Acceso : Entidad
{
    public int InterseccionId { get; set; } = 0;
    public string Identificador { get; set; } = "";
    public string Aproximacion { get; set; } = "";
    public decimal LongitudCrucePeatonalMetros { get; set; } = 0;
}

public sealed class Carril : Entidad
{
    public int AccesoId { get; set; } = 0;
    public int Numero { get; set; } = 0;
    public string Sentido { get; set; } = "";
}

public sealed class FuenteDeteccion : Entidad
{
    public int AccesoId { get; set; } = 0;
    public string TipoCamara { get; set; } = "";
    public string Ubicacion { get; set; } = "";
    public string Protocolo { get; set; } = "";
    public bool Activa { get; set; } = true;
    public string ModeloIa { get; set; } = "";
    public decimal UmbralConfianza { get; set; } = 0;
}

public sealed class ControladorLocal : Entidad
{
    public int InterseccionId { get; set; } = 0;
    public string Tipo { get; set; } = "";
    public string Protocolo { get; set; } = "";
    public string Ubicacion { get; set; } = "";
    public bool Emulado { get; set; } = true;
}

public sealed class ConfigTecnica : Entidad
{
    public int InterseccionId { get; set; } = 0;
    public int Version { get; set; } = 0;
    public decimal VerdeMinSegundos { get; set; } = 0;
    public decimal VerdeMaxSegundos { get; set; } = 0;
    public decimal AmbarSegundos { get; set; } = 0;
    public decimal TodoRojoSegundos { get; set; } = 0;
    public decimal ExtensionPrioridadSegundos { get; set; } = 0;
    public string ResponsableTecnico { get; set; } = "";
    public DateTimeOffset AprobadaUtc { get; set; } = default;
    public string Estado { get; set; } = "";
}

public sealed class Plan : Entidad
{
    public int InterseccionId { get; set; } = 0;
    public int ConfigTecnicaId { get; set; } = 0;
    public int Version { get; set; } = 0;
    public string Tipo { get; set; } = "";
    public string MetodoCalculo { get; set; } = "";
    public decimal CicloSegundos { get; set; } = 0;
    public DateTimeOffset CalculadoUtc { get; set; } = default;
    public string Estado { get; set; } = "";
}

public sealed class Fase : Entidad
{
    public int PlanId { get; set; } = 0;
    public int AccesoId { get; set; } = 0;
    public int Orden { get; set; } = 0;
    public string Tipo { get; set; } = "";
    public decimal VerdeSegundos { get; set; } = 0;
    public decimal AmbarSegundos { get; set; } = 0;
    public decimal TodoRojoSegundos { get; set; } = 0;
    public decimal TiempoPeatonalSegundos { get; set; } = 0;
}

public sealed class EstadoControl : Entidad
{
    public int ControladorLocalId { get; set; } = 0;
    public int PlanId { get; set; } = 0;
    public int FaseId { get; set; } = 0;
    public DateTimeOffset FechaUtc { get; set; } = default;
    public bool ComunicacionDisponible { get; set; } = true;
    public string Modo { get; set; } = "";
}

public sealed class Medicion : Entidad
{
    public int CarrilId { get; set; } = 0;
    public int FuenteDeteccionId { get; set; } = 0;
    public string MensajeId { get; set; } = "";
    public DateTimeOffset InicioUtc { get; set; } = default;
    public DateTimeOffset FinUtc { get; set; } = default;
    public string ClaseVehiculo { get; set; } = "";
    public int Cantidad { get; set; } = 0;
    public decimal ColaEstimadaMetros { get; set; } = 0;
}

public sealed class EventoPrioridad : Entidad
{
    public int InterseccionId { get; set; } = 0;
    public int PlanId { get; set; } = 0;
    public string Tipo { get; set; } = "";
    public string Origen { get; set; } = "";
    public DateTimeOffset DetectadoUtc { get; set; } = default;
    public DateTimeOffset AtendidoUtc { get; set; } = default;
    public string Resultado { get; set; } = "";
    public string Accion { get; set; } = "";
    public decimal ExtensionSegundos { get; set; } = 0;
    public int Ciclo { get; set; } = 0;
}

public sealed class Alerta : Entidad
{
    public int InterseccionId { get; set; } = 0;
    public string Tipo { get; set; } = "";
    public DateTimeOffset FechaUtc { get; set; } = default;
    public string Severidad { get; set; } = "";
    public string Descripcion { get; set; } = "";
    public string Estado { get; set; } = "";
}

public sealed class ValidacionSumo : Entidad
{
    public int PlanId { get; set; } = 0;
    public string Escenario { get; set; } = "";
    public int Semilla { get; set; } = 0;
    public DateTimeOffset EjecutadaUtc { get; set; } = default;
    public string Resultado { get; set; } = "";
    public string Motivo { get; set; } = "";
    public decimal DemoraGlobalBaseSegundos { get; set; } = 0;
    public decimal DemoraGlobalCandidataSegundos { get; set; } = 0;
    public bool CumpleMinimoPeatonal { get; set; } = false;
    public bool CumpleDespejePeatonal { get; set; } = false;
}

public sealed class MetricaPorAcceso : Entidad
{
    public int ValidacionSumoId { get; set; } = 0;
    public int AccesoId { get; set; } = 0;
    public string Grupo { get; set; } = "";
    public int VehiculosBase { get; set; } = 0;
    public int VehiculosCandidatos { get; set; } = 0;
    public decimal DemoraBaseSegundos { get; set; } = 0;
    public decimal DemoraCandidataSegundos { get; set; } = 0;
}

public sealed class Recomendacion : Entidad
{
    public int ValidacionSumoId { get; set; } = 0;
    public DateTimeOffset EmitidaUtc { get; set; } = default;
    public string JustificacionTecnica { get; set; } = "";
}

public sealed class Rol : Entidad
{
    public string Nombre { get; set; } = "";
    public string Descripcion { get; set; } = "";
}

public sealed class Usuario : Entidad
{
    public int RolId { get; set; } = 0;
    public string IdentificadorIdp { get; set; } = "";
    public string Nombre { get; set; } = "";
    public bool Activo { get; set; } = true;
    public bool MfaHabilitado { get; set; } = false;
}

public sealed class Bitacora : Entidad
{
    public int UsuarioId { get; set; } = 0;
    public string Operacion { get; set; } = "";
    public DateTimeOffset FechaUtc { get; set; } = default;
    public string Motivo { get; set; } = "";
    public string ObjetoTipo { get; set; } = "";
    public string ObjetoId { get; set; } = "";
    public string ValorAnterior { get; set; } = "";
    public string ValorPosterior { get; set; } = "";
    public bool MfaVerificado { get; set; } = false;
    public Guid? SolicitudId { get; set; } = null;
}

public sealed class VersionModelo : Entidad
{
    public string Tipo { get; set; } = "";
    public string Identificador { get; set; } = "";
    public string Descripcion { get; set; } = "";
    public string Estado { get; set; } = "";
    public DateTimeOffset? ActivadaUtc { get; set; } = null;
}

public sealed class Reporte : Entidad
{
    public int CorredorId { get; set; } = 0;
    public string Tipo { get; set; } = "";
    public DateTimeOffset DesdeUtc { get; set; } = default;
    public DateTimeOffset HastaUtc { get; set; } = default;
    public DateTimeOffset GeneradoUtc { get; set; } = default;
    public string Modo { get; set; } = "";
    public string Estado { get; set; } = "";
}

public sealed class FaseAcceso : Entidad
{
    public int FaseId { get; set; } = 0;
    public int AccesoId { get; set; } = 0;
}

public sealed class ValidacionMedicion : Entidad
{
    public int ValidacionSumoId { get; set; } = 0;
    public int MedicionId { get; set; } = 0;
}

public sealed class ValidacionEvento : Entidad
{
    public int ValidacionSumoId { get; set; } = 0;
    public int EventoPrioridadId { get; set; } = 0;
}
