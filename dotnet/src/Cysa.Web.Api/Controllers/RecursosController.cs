using Cysa.Web.Api.Data;
using Cysa.Web.Api.Dto;
using Cysa.Web.Api.Models;
using Cysa.Web.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace Cysa.Web.Api.Controllers;

[Route("api/corredores"), Tags("Gestionar infraestructura")]
public sealed class CorredorController(RecursoService<Corredor, CorredorEntrada, CorredorSalida> service) : CrudController<Corredor, CorredorEntrada, CorredorSalida>(service);

[Route("api/intersecciones"), Tags("Gestionar infraestructura")]
public sealed class InterseccionController(RecursoService<Interseccion, InterseccionEntrada, InterseccionSalida> service) : CrudController<Interseccion, InterseccionEntrada, InterseccionSalida>(service);

[Route("api/accesos"), Tags("Gestionar infraestructura")]
public sealed class AccesoController(RecursoService<Acceso, AccesoEntrada, AccesoSalida> service) : CrudController<Acceso, AccesoEntrada, AccesoSalida>(service);

[Route("api/carriles"), Tags("Gestionar infraestructura")]
public sealed class CarrilController(RecursoService<Carril, CarrilEntrada, CarrilSalida> service) : CrudController<Carril, CarrilEntrada, CarrilSalida>(service);

[Route("api/fuentes-deteccion"), Tags("Gestionar infraestructura")]
public sealed class FuenteDeteccionController(RecursoService<FuenteDeteccion, FuenteDeteccionEntrada, FuenteDeteccionSalida> service) : CrudController<FuenteDeteccion, FuenteDeteccionEntrada, FuenteDeteccionSalida>(service);

[Route("api/controladores"), Tags("Gestionar infraestructura")]
public sealed class ControladorLocalController(RecursoService<ControladorLocal, ControladorLocalEntrada, ControladorLocalSalida> service) : CrudController<ControladorLocal, ControladorLocalEntrada, ControladorLocalSalida>(service);

[Route("api/configuraciones"), Tags("Gestionar configuraciones del corredor")]
public sealed class ConfigTecnicaController(RecursoService<ConfigTecnica, ConfigTecnicaEntrada, ConfigTecnicaSalida> service) : CrudController<ConfigTecnica, ConfigTecnicaEntrada, ConfigTecnicaSalida>(service);

[Route("api/planes"), Tags("Gestionar planes semafóricos")]
public sealed class PlanController(RecursoService<Plan, PlanEntrada, PlanSalida> service) : CrudController<Plan, PlanEntrada, PlanSalida>(service);

[Route("api/fases"), Tags("Gestionar planes semafóricos")]
public sealed class FaseController(RecursoService<Fase, FaseEntrada, FaseSalida> service) : CrudController<Fase, FaseEntrada, FaseSalida>(service);

[Route("api/estados-control"), Tags("Monitorear operación semafórica")]
public sealed class EstadoControlController(RecursoService<EstadoControl, EstadoControlEntrada, EstadoControlSalida> service) : RegistroController<EstadoControl, EstadoControlEntrada, EstadoControlSalida>(service);

[Route("api/mediciones"), Tags("Monitorear operación semafórica")]
public sealed class MedicionController(RecursoService<Medicion, MedicionEntrada, MedicionSalida> service) : RegistroController<Medicion, MedicionEntrada, MedicionSalida>(service);

[Route("api/eventos-prioridad"), Tags("Monitorear operación semafórica")]
public sealed class EventoPrioridadController(RecursoService<EventoPrioridad, EventoPrioridadEntrada, EventoPrioridadSalida> service) : RegistroController<EventoPrioridad, EventoPrioridadEntrada, EventoPrioridadSalida>(service);

[Route("api/alertas"), Tags("Monitorear operación semafórica")]
public sealed class AlertaController(RecursoService<Alerta, AlertaEntrada, AlertaSalida> service) : CrudController<Alerta, AlertaEntrada, AlertaSalida>(service);

[Route("api/validaciones-sumo"), Tags("Gestionar planes semafóricos")]
public sealed class ValidacionSumoController(RecursoService<ValidacionSumo, ValidacionSumoEntrada, ValidacionSumoSalida> service) : RegistroController<ValidacionSumo, ValidacionSumoEntrada, ValidacionSumoSalida>(service);

[Route("api/metricas-acceso"), Tags("Gestionar planes semafóricos")]
public sealed class MetricaPorAccesoController(RecursoService<MetricaPorAcceso, MetricaPorAccesoEntrada, MetricaPorAccesoSalida> service) : RegistroController<MetricaPorAcceso, MetricaPorAccesoEntrada, MetricaPorAccesoSalida>(service);

[Route("api/recomendaciones"), Tags("Gestionar planes semafóricos")]
public sealed class RecomendacionController(RecursoService<Recomendacion, RecomendacionEntrada, RecomendacionSalida> service) : RegistroController<Recomendacion, RecomendacionEntrada, RecomendacionSalida>(service);

[Route("api/roles"), Tags("Administrar usuario y roles")]
public sealed class RolController(RecursoService<Rol, RolEntrada, RolSalida> service) : ConsultaController<Rol, RolEntrada, RolSalida>(service);

[Route("api/usuarios"), Tags("Administrar usuario y roles")]
public sealed class UsuarioController(RecursoService<Usuario, UsuarioEntrada, UsuarioSalida> service) : CrudController<Usuario, UsuarioEntrada, UsuarioSalida>(service);

[Route("api/bitacoras"), Tags("Gestionar configuraciones del corredor")]
public sealed class BitacoraController(RecursoService<Bitacora, BitacoraEntrada, BitacoraSalida> service) : ConsultaController<Bitacora, BitacoraEntrada, BitacoraSalida>(service);

[Route("api/versiones-modelo"), Tags("Gestionar configuraciones del corredor")]
public sealed class VersionModeloController(RecursoService<VersionModelo, VersionModeloEntrada, VersionModeloSalida> service) : ConsultaController<VersionModelo, VersionModeloEntrada, VersionModeloSalida>(service);

[Route("api/reportes"), Tags("Consultar reportes de desempeño")]
public sealed class ReporteController(RecursoService<Reporte, ReporteEntrada, ReporteSalida> service) : ConsultaController<Reporte, ReporteEntrada, ReporteSalida>(service);

[Route("api/fases-accesos"), Tags("Gestionar planes semafóricos")]
public sealed class FaseAccesoController(RecursoService<FaseAcceso, FaseAccesoEntrada, FaseAccesoSalida> service) : CrudController<FaseAcceso, FaseAccesoEntrada, FaseAccesoSalida>(service);

[Route("api/validaciones-mediciones"), Tags("Gestionar planes semafóricos")]
public sealed class ValidacionMedicionController(RecursoService<ValidacionMedicion, ValidacionMedicionEntrada, ValidacionMedicionSalida> service) : RegistroController<ValidacionMedicion, ValidacionMedicionEntrada, ValidacionMedicionSalida>(service);

[Route("api/validaciones-eventos"), Tags("Gestionar planes semafóricos")]
public sealed class ValidacionEventoController(RecursoService<ValidacionEvento, ValidacionEventoEntrada, ValidacionEventoSalida> service) : RegistroController<ValidacionEvento, ValidacionEventoEntrada, ValidacionEventoSalida>(service);
