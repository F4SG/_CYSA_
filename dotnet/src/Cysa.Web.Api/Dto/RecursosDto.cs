using System.ComponentModel.DataAnnotations;
using Cysa.Web.Api.Models;

namespace Cysa.Web.Api.Dto;

public interface IEntrada<T> { void Aplicar(T entity); }
public interface ISalida<T, TSelf> { static abstract TSelf Desde(T entity); }

public class CorredorEntrada : IEntrada<Corredor>
{
    public bool Prueba { get; set; } = true;
    [Required, StringLength(120, MinimumLength = 1)]
    public string Nombre { get; set; } = "";
    [Required, StringLength(500, MinimumLength = 1)]
    public string Descripcion { get; set; } = "";
    public void Aplicar(Corredor e)
    {
        e.Prueba = Prueba;
        e.Nombre = Nombre;
        e.Descripcion = Descripcion;
    }
}
public sealed class CorredorSalida : CorredorEntrada, ISalida<Corredor, CorredorSalida>
{
    public int Id { get; set; }
    public static CorredorSalida Desde(Corredor e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        Nombre = e.Nombre,
        Descripcion = e.Descripcion,
    };
}

public class InterseccionEntrada : IEntrada<Interseccion>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int CorredorId { get; set; } = 0;
    [Required, StringLength(120, MinimumLength = 1)]
    public string Nombre { get; set; } = "";
    [Range(typeof(decimal), "-90", "90", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal Latitud { get; set; } = 0;
    [Range(typeof(decimal), "-180", "180", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal Longitud { get; set; } = 0;
    [Required, RegularExpression("^(activo|inactivo)$")]
    public string EstadoOperativo { get; set; } = "";
    public void Aplicar(Interseccion e)
    {
        e.Prueba = Prueba;
        e.CorredorId = CorredorId;
        e.Nombre = Nombre;
        e.Latitud = Latitud;
        e.Longitud = Longitud;
        e.EstadoOperativo = EstadoOperativo;
    }
}
public sealed class InterseccionSalida : InterseccionEntrada, ISalida<Interseccion, InterseccionSalida>
{
    public int Id { get; set; }
    public static InterseccionSalida Desde(Interseccion e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        CorredorId = e.CorredorId,
        Nombre = e.Nombre,
        Latitud = e.Latitud,
        Longitud = e.Longitud,
        EstadoOperativo = e.EstadoOperativo,
    };
}

public class AccesoEntrada : IEntrada<Acceso>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int InterseccionId { get; set; } = 0;
    [Required, StringLength(32, MinimumLength = 1)]
    public string Identificador { get; set; } = "";
    [Required, StringLength(60, MinimumLength = 1)]
    public string Aproximacion { get; set; } = "";
    [Range(typeof(decimal), "0.1", "500", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal LongitudCrucePeatonalMetros { get; set; } = 0;
    public void Aplicar(Acceso e)
    {
        e.Prueba = Prueba;
        e.InterseccionId = InterseccionId;
        e.Identificador = Identificador;
        e.Aproximacion = Aproximacion;
        e.LongitudCrucePeatonalMetros = LongitudCrucePeatonalMetros;
    }
}
public sealed class AccesoSalida : AccesoEntrada, ISalida<Acceso, AccesoSalida>
{
    public int Id { get; set; }
    public static AccesoSalida Desde(Acceso e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        InterseccionId = e.InterseccionId,
        Identificador = e.Identificador,
        Aproximacion = e.Aproximacion,
        LongitudCrucePeatonalMetros = e.LongitudCrucePeatonalMetros,
    };
}

public class CarrilEntrada : IEntrada<Carril>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int AccesoId { get; set; } = 0;
    [Range(1, 20)]
    public int Numero { get; set; } = 0;
    [Required, RegularExpression("^(entrada|salida)$")]
    public string Sentido { get; set; } = "";
    public void Aplicar(Carril e)
    {
        e.Prueba = Prueba;
        e.AccesoId = AccesoId;
        e.Numero = Numero;
        e.Sentido = Sentido;
    }
}
public sealed class CarrilSalida : CarrilEntrada, ISalida<Carril, CarrilSalida>
{
    public int Id { get; set; }
    public static CarrilSalida Desde(Carril e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        AccesoId = e.AccesoId,
        Numero = e.Numero,
        Sentido = e.Sentido,
    };
}

public class FuenteDeteccionEntrada : IEntrada<FuenteDeteccion>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int AccesoId { get; set; } = 0;
    [Required, StringLength(60, MinimumLength = 1)]
    public string TipoCamara { get; set; } = "";
    [Required, StringLength(200, MinimumLength = 1)]
    public string Ubicacion { get; set; } = "";
    [Required, StringLength(40, MinimumLength = 1)]
    public string Protocolo { get; set; } = "";

    public bool Activa { get; set; } = true;
    [Required, StringLength(80, MinimumLength = 1)]
    public string ModeloIa { get; set; } = "";
    [Range(typeof(decimal), "0.01", "1", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal UmbralConfianza { get; set; } = 0;
    public void Aplicar(FuenteDeteccion e)
    {
        e.Prueba = Prueba;
        e.AccesoId = AccesoId;
        e.TipoCamara = TipoCamara;
        e.Ubicacion = Ubicacion;
        e.Protocolo = Protocolo;
        e.Activa = Activa;
        e.ModeloIa = ModeloIa;
        e.UmbralConfianza = UmbralConfianza;
    }
}
public sealed class FuenteDeteccionSalida : FuenteDeteccionEntrada, ISalida<FuenteDeteccion, FuenteDeteccionSalida>
{
    public int Id { get; set; }
    public static FuenteDeteccionSalida Desde(FuenteDeteccion e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        AccesoId = e.AccesoId,
        TipoCamara = e.TipoCamara,
        Ubicacion = e.Ubicacion,
        Protocolo = e.Protocolo,
        Activa = e.Activa,
        ModeloIa = e.ModeloIa,
        UmbralConfianza = e.UmbralConfianza,
    };
}

public class ControladorLocalEntrada : IEntrada<ControladorLocal>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int InterseccionId { get; set; } = 0;
    [Required, StringLength(60, MinimumLength = 1)]
    public string Tipo { get; set; } = "";
    [Required, StringLength(40, MinimumLength = 1)]
    public string Protocolo { get; set; } = "";
    [Required, StringLength(200, MinimumLength = 1)]
    public string Ubicacion { get; set; } = "";

    public bool Emulado { get; set; } = true;
    public void Aplicar(ControladorLocal e)
    {
        e.Prueba = Prueba;
        e.InterseccionId = InterseccionId;
        e.Tipo = Tipo;
        e.Protocolo = Protocolo;
        e.Ubicacion = Ubicacion;
        e.Emulado = Emulado;
    }
}
public sealed class ControladorLocalSalida : ControladorLocalEntrada, ISalida<ControladorLocal, ControladorLocalSalida>
{
    public int Id { get; set; }
    public static ControladorLocalSalida Desde(ControladorLocal e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        InterseccionId = e.InterseccionId,
        Tipo = e.Tipo,
        Protocolo = e.Protocolo,
        Ubicacion = e.Ubicacion,
        Emulado = e.Emulado,
    };
}

public class ConfigTecnicaEntrada : IEntrada<ConfigTecnica>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int InterseccionId { get; set; } = 0;
    [Range(1, 1000000)]
    public int Version { get; set; } = 0;
    [Range(typeof(decimal), "1", "3600", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal VerdeMinSegundos { get; set; } = 0;
    [Range(typeof(decimal), "1", "3600", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal VerdeMaxSegundos { get; set; } = 0;
    [Range(typeof(decimal), "1", "30", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal AmbarSegundos { get; set; } = 0;
    [Range(typeof(decimal), "1", "60", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal TodoRojoSegundos { get; set; } = 0;
    [Required, StringLength(120, MinimumLength = 1)]
    public string ResponsableTecnico { get; set; } = "";
    [Required]
    public DateTimeOffset AprobadaUtc { get; set; } = default;
    [Required, RegularExpression("^(aprobada|retirada)$")]
    public string Estado { get; set; } = "";
    public void Aplicar(ConfigTecnica e)
    {
        e.Prueba = Prueba;
        e.InterseccionId = InterseccionId;
        e.Version = Version;
        e.VerdeMinSegundos = VerdeMinSegundos;
        e.VerdeMaxSegundos = VerdeMaxSegundos;
        e.AmbarSegundos = AmbarSegundos;
        e.TodoRojoSegundos = TodoRojoSegundos;
        e.ExtensionPrioridadSegundos = 0;
        e.ResponsableTecnico = ResponsableTecnico;
        e.AprobadaUtc = AprobadaUtc;
        e.Estado = Estado;
    }
}
public sealed class ConfigTecnicaSalida : ConfigTecnicaEntrada, ISalida<ConfigTecnica, ConfigTecnicaSalida>
{
    public int Id { get; set; }
    public decimal ExtensionPrioridadSegundos { get; set; }
    public static ConfigTecnicaSalida Desde(ConfigTecnica e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        InterseccionId = e.InterseccionId,
        Version = e.Version,
        VerdeMinSegundos = e.VerdeMinSegundos,
        VerdeMaxSegundos = e.VerdeMaxSegundos,
        AmbarSegundos = e.AmbarSegundos,
        TodoRojoSegundos = e.TodoRojoSegundos,
        ExtensionPrioridadSegundos = e.ExtensionPrioridadSegundos,
        ResponsableTecnico = e.ResponsableTecnico,
        AprobadaUtc = e.AprobadaUtc,
        Estado = e.Estado,
    };
}

public class PlanEntrada : IEntrada<Plan>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int InterseccionId { get; set; } = 0;
    [Range(1, 1000000)]
    public int ConfigTecnicaId { get; set; } = 0;
    [Range(1, 1000000)]
    public int Version { get; set; } = 0;
    [Required, RegularExpression("^(fijo|optimizado|seguro)$")]
    public string Tipo { get; set; } = "";
    [Required, StringLength(60, MinimumLength = 1)]
    public string MetodoCalculo { get; set; } = "";
    [Range(typeof(decimal), "10", "3600", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal CicloSegundos { get; set; } = 0;
    [Required]
    public DateTimeOffset CalculadoUtc { get; set; } = default;
    [Required, RegularExpression("^(borrador|validado|autorizado|rechazado)$")]
    public string Estado { get; set; } = "";
    public void Aplicar(Plan e)
    {
        e.Prueba = Prueba;
        e.InterseccionId = InterseccionId;
        e.ConfigTecnicaId = ConfigTecnicaId;
        e.Version = Version;
        e.Tipo = Tipo;
        e.MetodoCalculo = MetodoCalculo;
        e.CicloSegundos = CicloSegundos;
        e.CalculadoUtc = CalculadoUtc;
        e.Estado = Estado;
    }
}
public sealed class PlanSalida : PlanEntrada, ISalida<Plan, PlanSalida>
{
    public int Id { get; set; }
    public static PlanSalida Desde(Plan e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        InterseccionId = e.InterseccionId,
        ConfigTecnicaId = e.ConfigTecnicaId,
        Version = e.Version,
        Tipo = e.Tipo,
        MetodoCalculo = e.MetodoCalculo,
        CicloSegundos = e.CicloSegundos,
        CalculadoUtc = e.CalculadoUtc,
        Estado = e.Estado,
    };
}

public class FaseEntrada : IEntrada<Fase>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int PlanId { get; set; } = 0;
    [Range(1, 1000000)]
    public int AccesoId { get; set; } = 0;
    [Range(1, 64)]
    public int Orden { get; set; } = 0;
    [Required, RegularExpression("^(vehicular|peatonal)$")]
    public string Tipo { get; set; } = "";
    [Range(typeof(decimal), "1", "3600", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal VerdeSegundos { get; set; } = 0;
    [Range(typeof(decimal), "1", "30", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal AmbarSegundos { get; set; } = 0;
    [Range(typeof(decimal), "1", "60", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal TodoRojoSegundos { get; set; } = 0;
    [Range(typeof(decimal), "0", "3600", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal TiempoPeatonalSegundos { get; set; } = 0;
    public void Aplicar(Fase e)
    {
        e.Prueba = Prueba;
        e.PlanId = PlanId;
        e.AccesoId = AccesoId;
        e.Orden = Orden;
        e.Tipo = Tipo;
        e.VerdeSegundos = VerdeSegundos;
        e.AmbarSegundos = AmbarSegundos;
        e.TodoRojoSegundos = TodoRojoSegundos;
        e.TiempoPeatonalSegundos = TiempoPeatonalSegundos;
    }
}
public sealed class FaseSalida : FaseEntrada, ISalida<Fase, FaseSalida>
{
    public int Id { get; set; }
    public static FaseSalida Desde(Fase e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        PlanId = e.PlanId,
        AccesoId = e.AccesoId,
        Orden = e.Orden,
        Tipo = e.Tipo,
        VerdeSegundos = e.VerdeSegundos,
        AmbarSegundos = e.AmbarSegundos,
        TodoRojoSegundos = e.TodoRojoSegundos,
        TiempoPeatonalSegundos = e.TiempoPeatonalSegundos,
    };
}

public class EstadoControlEntrada : IEntrada<EstadoControl>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int ControladorLocalId { get; set; } = 0;
    [Range(1, 1000000)]
    public int PlanId { get; set; } = 0;
    [Range(1, 1000000)]
    public int FaseId { get; set; } = 0;
    [Required]
    public DateTimeOffset FechaUtc { get; set; } = default;

    public bool ComunicacionDisponible { get; set; } = true;
    [Required, RegularExpression("^(central|seguro)$")]
    public string Modo { get; set; } = "";
    public void Aplicar(EstadoControl e)
    {
        e.Prueba = Prueba;
        e.ControladorLocalId = ControladorLocalId;
        e.PlanId = PlanId;
        e.FaseId = FaseId;
        e.FechaUtc = FechaUtc;
        e.ComunicacionDisponible = ComunicacionDisponible;
        e.Modo = Modo;
    }
}
public sealed class EstadoControlSalida : EstadoControlEntrada, ISalida<EstadoControl, EstadoControlSalida>
{
    public int Id { get; set; }
    public static EstadoControlSalida Desde(EstadoControl e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        ControladorLocalId = e.ControladorLocalId,
        PlanId = e.PlanId,
        FaseId = e.FaseId,
        FechaUtc = e.FechaUtc,
        ComunicacionDisponible = e.ComunicacionDisponible,
        Modo = e.Modo,
    };
}

public class MedicionEntrada : IEntrada<Medicion>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int CarrilId { get; set; } = 0;
    [Range(1, 1000000)]
    public int FuenteDeteccionId { get; set; } = 0;
    [Required, StringLength(64, MinimumLength = 1)]
    public string MensajeId { get; set; } = "";
    [Required]
    public DateTimeOffset InicioUtc { get; set; } = default;
    [Required]
    public DateTimeOffset FinUtc { get; set; } = default;
    [Required, RegularExpression("^(auto|micro|moto)$")]
    public string ClaseVehiculo { get; set; } = "";
    [Range(0, 100000)]
    public int Cantidad { get; set; } = 0;
    [Range(typeof(decimal), "0", "10000", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal ColaEstimadaMetros { get; set; } = 0;
    public void Aplicar(Medicion e)
    {
        e.Prueba = Prueba;
        e.CarrilId = CarrilId;
        e.FuenteDeteccionId = FuenteDeteccionId;
        e.MensajeId = MensajeId;
        e.InicioUtc = InicioUtc;
        e.FinUtc = FinUtc;
        e.ClaseVehiculo = ClaseVehiculo;
        e.Cantidad = Cantidad;
        e.ColaEstimadaMetros = ColaEstimadaMetros;
    }
}
public sealed class MedicionSalida : MedicionEntrada, ISalida<Medicion, MedicionSalida>
{
    public int Id { get; set; }
    public static MedicionSalida Desde(Medicion e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        CarrilId = e.CarrilId,
        FuenteDeteccionId = e.FuenteDeteccionId,
        MensajeId = e.MensajeId,
        InicioUtc = e.InicioUtc,
        FinUtc = e.FinUtc,
        ClaseVehiculo = e.ClaseVehiculo,
        Cantidad = e.Cantidad,
        ColaEstimadaMetros = e.ColaEstimadaMetros,
    };
}

public class EventoPrioridadEntrada : IEntrada<EventoPrioridad>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int InterseccionId { get; set; } = 0;
    [Range(1, 1000000)]
    public int PlanId { get; set; } = 0;
    [Required, RegularExpression("^emergencia$")]
    public string Tipo { get; set; } = "";
    [Required, RegularExpression("^sumo$")]
    public string Origen { get; set; } = "";
    [Required]
    public DateTimeOffset DetectadoUtc { get; set; } = default;
    [Required]
    public DateTimeOffset AtendidoUtc { get; set; } = default;
    [Required, RegularExpression("^(atendido|conflicto_peatonal|rechazado)$")]
    public string Resultado { get; set; } = "";
    [Required, RegularExpression("^(extension|adelanto)$")]
    public string Accion { get; set; } = "";
    [Range(typeof(decimal), "0", "10", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal ExtensionSegundos { get; set; } = 0;
    [Range(1, 1000000)]
    public int Ciclo { get; set; } = 0;
    public void Aplicar(EventoPrioridad e)
    {
        e.Prueba = Prueba;
        e.InterseccionId = InterseccionId;
        e.PlanId = PlanId;
        e.Tipo = Tipo;
        e.Origen = Origen;
        e.DetectadoUtc = DetectadoUtc;
        e.AtendidoUtc = AtendidoUtc;
        e.Resultado = Resultado;
        e.Accion = Accion;
        e.ExtensionSegundos = ExtensionSegundos;
        e.Ciclo = Ciclo;
    }
}
public sealed class EventoPrioridadSalida : EventoPrioridadEntrada, ISalida<EventoPrioridad, EventoPrioridadSalida>
{
    public int Id { get; set; }
    public static EventoPrioridadSalida Desde(EventoPrioridad e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        InterseccionId = e.InterseccionId,
        PlanId = e.PlanId,
        Tipo = e.Tipo,
        Origen = e.Origen,
        DetectadoUtc = e.DetectadoUtc,
        AtendidoUtc = e.AtendidoUtc,
        Resultado = e.Resultado,
        Accion = e.Accion,
        ExtensionSegundos = e.ExtensionSegundos,
        Ciclo = e.Ciclo,
    };
}

public class AlertaEntrada : IEntrada<Alerta>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int InterseccionId { get; set; } = 0;
    [Required, RegularExpression("^(operacion|comunicacion)$")]
    public string Tipo { get; set; } = "";
    [Required]
    public DateTimeOffset FechaUtc { get; set; } = default;
    [Required, RegularExpression("^(informativa|advertencia|critica)$")]
    public string Severidad { get; set; } = "";
    [Required, StringLength(500, MinimumLength = 1)]
    public string Descripcion { get; set; } = "";
    [Required, RegularExpression("^(abierta|cerrada)$")]
    public string Estado { get; set; } = "";
    public void Aplicar(Alerta e)
    {
        e.Prueba = Prueba;
        e.InterseccionId = InterseccionId;
        e.Tipo = Tipo;
        e.FechaUtc = FechaUtc;
        e.Severidad = Severidad;
        e.Descripcion = Descripcion;
        e.Estado = Estado;
    }
}
public sealed class AlertaSalida : AlertaEntrada, ISalida<Alerta, AlertaSalida>
{
    public int Id { get; set; }
    public static AlertaSalida Desde(Alerta e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        InterseccionId = e.InterseccionId,
        Tipo = e.Tipo,
        FechaUtc = e.FechaUtc,
        Severidad = e.Severidad,
        Descripcion = e.Descripcion,
        Estado = e.Estado,
    };
}

public class ValidacionSumoEntrada : IEntrada<ValidacionSumo>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int PlanId { get; set; } = 0;
    [Required, StringLength(200, MinimumLength = 1)]
    public string Escenario { get; set; } = "";
    [Range(0, 1000000)]
    public int Semilla { get; set; } = 0;
    [Required]
    public DateTimeOffset EjecutadaUtc { get; set; } = default;
    [Required, RegularExpression("^(aprobada|rechazada)$")]
    public string Resultado { get; set; } = "";
    [Required, StringLength(1000, MinimumLength = 1)]
    public string Motivo { get; set; } = "";
    [Range(typeof(decimal), "0.001", "86400", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal DemoraGlobalBaseSegundos { get; set; } = 0;
    [Range(typeof(decimal), "0", "86400", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal DemoraGlobalCandidataSegundos { get; set; } = 0;

    public bool CumpleMinimoPeatonal { get; set; } = false;

    public bool CumpleDespejePeatonal { get; set; } = false;
    public void Aplicar(ValidacionSumo e)
    {
        e.Prueba = Prueba;
        e.PlanId = PlanId;
        e.Escenario = Escenario;
        e.Semilla = Semilla;
        e.EjecutadaUtc = EjecutadaUtc;
        e.Resultado = Resultado;
        e.Motivo = Motivo;
        e.DemoraGlobalBaseSegundos = DemoraGlobalBaseSegundos;
        e.DemoraGlobalCandidataSegundos = DemoraGlobalCandidataSegundos;
        e.CumpleMinimoPeatonal = CumpleMinimoPeatonal;
        e.CumpleDespejePeatonal = CumpleDespejePeatonal;
    }
}
public sealed class ValidacionSumoSalida : ValidacionSumoEntrada, ISalida<ValidacionSumo, ValidacionSumoSalida>
{
    public int Id { get; set; }
    public static ValidacionSumoSalida Desde(ValidacionSumo e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        PlanId = e.PlanId,
        Escenario = e.Escenario,
        Semilla = e.Semilla,
        EjecutadaUtc = e.EjecutadaUtc,
        Resultado = e.Resultado,
        Motivo = e.Motivo,
        DemoraGlobalBaseSegundos = e.DemoraGlobalBaseSegundos,
        DemoraGlobalCandidataSegundos = e.DemoraGlobalCandidataSegundos,
        CumpleMinimoPeatonal = e.CumpleMinimoPeatonal,
        CumpleDespejePeatonal = e.CumpleDespejePeatonal,
    };
}

public class MetricaPorAccesoEntrada : IEntrada<MetricaPorAcceso>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int ValidacionSumoId { get; set; } = 0;
    [Range(1, 1000000)]
    public int AccesoId { get; set; } = 0;
    [Required, RegularExpression("^(total|micro|resto)$")]
    public string Grupo { get; set; } = "";
    [Range(0, 1000000)]
    public int VehiculosBase { get; set; } = 0;
    [Range(0, 1000000)]
    public int VehiculosCandidatos { get; set; } = 0;
    [Range(typeof(decimal), "0.001", "86400", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal DemoraBaseSegundos { get; set; } = 0;
    [Range(typeof(decimal), "0", "86400", ParseLimitsInInvariantCulture = true, ConvertValueInInvariantCulture = true)]
    public decimal DemoraCandidataSegundos { get; set; } = 0;
    public void Aplicar(MetricaPorAcceso e)
    {
        e.Prueba = Prueba;
        e.ValidacionSumoId = ValidacionSumoId;
        e.AccesoId = AccesoId;
        e.Grupo = Grupo;
        e.VehiculosBase = VehiculosBase;
        e.VehiculosCandidatos = VehiculosCandidatos;
        e.DemoraBaseSegundos = DemoraBaseSegundos;
        e.DemoraCandidataSegundos = DemoraCandidataSegundos;
    }
}
public sealed class MetricaPorAccesoSalida : MetricaPorAccesoEntrada, ISalida<MetricaPorAcceso, MetricaPorAccesoSalida>
{
    public int Id { get; set; }
    public static MetricaPorAccesoSalida Desde(MetricaPorAcceso e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        ValidacionSumoId = e.ValidacionSumoId,
        AccesoId = e.AccesoId,
        Grupo = e.Grupo,
        VehiculosBase = e.VehiculosBase,
        VehiculosCandidatos = e.VehiculosCandidatos,
        DemoraBaseSegundos = e.DemoraBaseSegundos,
        DemoraCandidataSegundos = e.DemoraCandidataSegundos,
    };
}

public class RecomendacionEntrada : IEntrada<Recomendacion>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int ValidacionSumoId { get; set; } = 0;
    [Required]
    public DateTimeOffset EmitidaUtc { get; set; } = default;
    [Required, StringLength(1000, MinimumLength = 1)]
    public string JustificacionTecnica { get; set; } = "";
    public void Aplicar(Recomendacion e)
    {
        e.Prueba = Prueba;
        e.ValidacionSumoId = ValidacionSumoId;
        e.EmitidaUtc = EmitidaUtc;
        e.JustificacionTecnica = JustificacionTecnica;
    }
}
public sealed class RecomendacionSalida : RecomendacionEntrada, ISalida<Recomendacion, RecomendacionSalida>
{
    public int Id { get; set; }
    public static RecomendacionSalida Desde(Recomendacion e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        ValidacionSumoId = e.ValidacionSumoId,
        EmitidaUtc = e.EmitidaUtc,
        JustificacionTecnica = e.JustificacionTecnica,
    };
}

public class RolEntrada : IEntrada<Rol>
{
    public bool Prueba { get; set; } = true;
    [Required, RegularExpression("^(administrador|operador)$")]
    public string Nombre { get; set; } = "";
    [Required, StringLength(300, MinimumLength = 1)]
    public string Descripcion { get; set; } = "";
    public void Aplicar(Rol e)
    {
        e.Prueba = Prueba;
        e.Nombre = Nombre;
        e.Descripcion = Descripcion;
    }
}
public sealed class RolSalida : RolEntrada, ISalida<Rol, RolSalida>
{
    public int Id { get; set; }
    public static RolSalida Desde(Rol e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        Nombre = e.Nombre,
        Descripcion = e.Descripcion,
    };
}

public class UsuarioEntrada : IEntrada<Usuario>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int RolId { get; set; } = 0;
    [Required, StringLength(128, MinimumLength = 1)]
    public string IdentificadorIdp { get; set; } = "";
    [Required, StringLength(120, MinimumLength = 1)]
    public string Nombre { get; set; } = "";

    public bool Activo { get; set; } = true;

    public bool MfaHabilitado { get; set; } = false;
    public void Aplicar(Usuario e)
    {
        e.Prueba = Prueba;
        e.RolId = RolId;
        e.IdentificadorIdp = IdentificadorIdp;
        e.Nombre = Nombre;
        e.Activo = Activo;
        e.MfaHabilitado = MfaHabilitado;
    }
}
public sealed class UsuarioSalida : UsuarioEntrada, ISalida<Usuario, UsuarioSalida>
{
    public int Id { get; set; }
    public static UsuarioSalida Desde(Usuario e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        RolId = e.RolId,
        IdentificadorIdp = e.IdentificadorIdp,
        Nombre = e.Nombre,
        Activo = e.Activo,
        MfaHabilitado = e.MfaHabilitado,
    };
}

public class BitacoraEntrada : IEntrada<Bitacora>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int UsuarioId { get; set; } = 0;
    [Required, StringLength(80, MinimumLength = 1)]
    public string Operacion { get; set; } = "";
    [Required]
    public DateTimeOffset FechaUtc { get; set; } = default;
    [Required, StringLength(1000, MinimumLength = 1)]
    public string Motivo { get; set; } = "";
    [Required, StringLength(80, MinimumLength = 1)]
    public string ObjetoTipo { get; set; } = "";
    [Required, StringLength(80, MinimumLength = 1)]
    public string ObjetoId { get; set; } = "";
    [Required, StringLength(16000, MinimumLength = 1)]
    public string ValorAnterior { get; set; } = "";
    [Required, StringLength(16000, MinimumLength = 1)]
    public string ValorPosterior { get; set; } = "";

    public bool MfaVerificado { get; set; } = false;

    public Guid? SolicitudId { get; set; } = null;
    public void Aplicar(Bitacora e)
    {
        e.Prueba = Prueba;
        e.UsuarioId = UsuarioId;
        e.Operacion = Operacion;
        e.FechaUtc = FechaUtc;
        e.Motivo = Motivo;
        e.ObjetoTipo = ObjetoTipo;
        e.ObjetoId = ObjetoId;
        e.ValorAnterior = ValorAnterior;
        e.ValorPosterior = ValorPosterior;
        e.MfaVerificado = MfaVerificado;
        e.SolicitudId = SolicitudId;
    }
}
public sealed class BitacoraSalida : BitacoraEntrada, ISalida<Bitacora, BitacoraSalida>
{
    public int Id { get; set; }
    public static BitacoraSalida Desde(Bitacora e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        UsuarioId = e.UsuarioId,
        Operacion = e.Operacion,
        FechaUtc = e.FechaUtc,
        Motivo = e.Motivo,
        ObjetoTipo = e.ObjetoTipo,
        ObjetoId = e.ObjetoId,
        ValorAnterior = e.ValorAnterior,
        ValorPosterior = e.ValorPosterior,
        MfaVerificado = e.MfaVerificado,
        SolicitudId = e.SolicitudId,
    };
}

public class VersionModeloEntrada : IEntrada<VersionModelo>
{
    public bool Prueba { get; set; } = true;
    [Required, StringLength(80, MinimumLength = 1)]
    public string Tipo { get; set; } = "";
    [Required, StringLength(120, MinimumLength = 1)]
    public string Identificador { get; set; } = "";
    [Required, StringLength(500, MinimumLength = 1)]
    public string Descripcion { get; set; } = "";
    [Required, RegularExpression("^(futuro)$")]
    public string Estado { get; set; } = "";

    public DateTimeOffset? ActivadaUtc { get; set; } = null;
    public void Aplicar(VersionModelo e)
    {
        e.Prueba = Prueba;
        e.Tipo = Tipo;
        e.Identificador = Identificador;
        e.Descripcion = Descripcion;
        e.Estado = Estado;
        e.ActivadaUtc = ActivadaUtc;
    }
}
public sealed class VersionModeloSalida : VersionModeloEntrada, ISalida<VersionModelo, VersionModeloSalida>
{
    public int Id { get; set; }
    public static VersionModeloSalida Desde(VersionModelo e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        Tipo = e.Tipo,
        Identificador = e.Identificador,
        Descripcion = e.Descripcion,
        Estado = e.Estado,
        ActivadaUtc = e.ActivadaUtc,
    };
}

public class ReporteEntrada : IEntrada<Reporte>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int CorredorId { get; set; } = 0;
    [Required, StringLength(80, MinimumLength = 1)]
    public string Tipo { get; set; } = "";
    [Required]
    public DateTimeOffset DesdeUtc { get; set; } = default;
    [Required]
    public DateTimeOffset HastaUtc { get; set; } = default;
    [Required]
    public DateTimeOffset GeneradoUtc { get; set; } = default;
    [Required, RegularExpression("^(auto|micro|moto)$")]
    public string Modo { get; set; } = "";
    [Required, RegularExpression("^(futuro)$")]
    public string Estado { get; set; } = "";
    public void Aplicar(Reporte e)
    {
        e.Prueba = Prueba;
        e.CorredorId = CorredorId;
        e.Tipo = Tipo;
        e.DesdeUtc = DesdeUtc;
        e.HastaUtc = HastaUtc;
        e.GeneradoUtc = GeneradoUtc;
        e.Modo = Modo;
        e.Estado = Estado;
    }
}
public sealed class ReporteSalida : ReporteEntrada, ISalida<Reporte, ReporteSalida>
{
    public int Id { get; set; }
    public static ReporteSalida Desde(Reporte e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        CorredorId = e.CorredorId,
        Tipo = e.Tipo,
        DesdeUtc = e.DesdeUtc,
        HastaUtc = e.HastaUtc,
        GeneradoUtc = e.GeneradoUtc,
        Modo = e.Modo,
        Estado = e.Estado,
    };
}

public class FaseAccesoEntrada : IEntrada<FaseAcceso>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int FaseId { get; set; } = 0;
    [Range(1, 1000000)]
    public int AccesoId { get; set; } = 0;
    public void Aplicar(FaseAcceso e)
    {
        e.Prueba = Prueba;
        e.FaseId = FaseId;
        e.AccesoId = AccesoId;
    }
}
public sealed class FaseAccesoSalida : FaseAccesoEntrada, ISalida<FaseAcceso, FaseAccesoSalida>
{
    public int Id { get; set; }
    public static FaseAccesoSalida Desde(FaseAcceso e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        FaseId = e.FaseId,
        AccesoId = e.AccesoId,
    };
}

public class ValidacionMedicionEntrada : IEntrada<ValidacionMedicion>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int ValidacionSumoId { get; set; } = 0;
    [Range(1, 1000000)]
    public int MedicionId { get; set; } = 0;
    public void Aplicar(ValidacionMedicion e)
    {
        e.Prueba = Prueba;
        e.ValidacionSumoId = ValidacionSumoId;
        e.MedicionId = MedicionId;
    }
}
public sealed class ValidacionMedicionSalida : ValidacionMedicionEntrada, ISalida<ValidacionMedicion, ValidacionMedicionSalida>
{
    public int Id { get; set; }
    public static ValidacionMedicionSalida Desde(ValidacionMedicion e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        ValidacionSumoId = e.ValidacionSumoId,
        MedicionId = e.MedicionId,
    };
}

public class ValidacionEventoEntrada : IEntrada<ValidacionEvento>
{
    public bool Prueba { get; set; } = true;
    [Range(1, 1000000)]
    public int ValidacionSumoId { get; set; } = 0;
    [Range(1, 1000000)]
    public int EventoPrioridadId { get; set; } = 0;
    public void Aplicar(ValidacionEvento e)
    {
        e.Prueba = Prueba;
        e.ValidacionSumoId = ValidacionSumoId;
        e.EventoPrioridadId = EventoPrioridadId;
    }
}
public sealed class ValidacionEventoSalida : ValidacionEventoEntrada, ISalida<ValidacionEvento, ValidacionEventoSalida>
{
    public int Id { get; set; }
    public static ValidacionEventoSalida Desde(ValidacionEvento e) => new()
    {
        Id = e.Id, Prueba = e.Prueba,
        ValidacionSumoId = e.ValidacionSumoId,
        EventoPrioridadId = e.EventoPrioridadId,
    };
}
