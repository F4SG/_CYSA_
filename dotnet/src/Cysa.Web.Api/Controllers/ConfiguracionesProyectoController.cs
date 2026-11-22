using Cysa.Web.Api.Dto;
using Cysa.Web.Api.Models;
using Cysa.Web.Api.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Cors;
using Microsoft.AspNetCore.Mvc;

namespace Cysa.Web.Api.Controllers;

// Estas rutas exigen Keycloak real. Un token del laboratorio Web III no concede acceso.
[Route("api/proyecto/configuraciones"),Authorize(AuthenticationSchemes="Proyecto"),Tags("Configuraciones con Keycloak")]
[EnableCors("PanelProyecto")]
public sealed class ConfiguracionesProyectoController(RecursoService<ConfigTecnica,ConfigTecnicaEntrada,ConfigTecnicaSalida> service)
    : CrudController<ConfigTecnica,ConfigTecnicaEntrada,ConfigTecnicaSalida>(service);

[Route("api/proyecto/intersecciones"),Authorize(AuthenticationSchemes="Proyecto"),Tags("Configuraciones con Keycloak")]
[EnableCors("PanelProyecto")]
public sealed class InterseccionesProyectoController(RecursoService<Interseccion,InterseccionEntrada,InterseccionSalida> service)
    : ConsultaController<Interseccion,InterseccionEntrada,InterseccionSalida>(service);

[Route("api/proyecto/bitacoras"),Authorize(AuthenticationSchemes="Proyecto"),Tags("Configuraciones con Keycloak")]
[EnableCors("PanelProyecto")]
public sealed class BitacorasProyectoController(RecursoService<Bitacora,BitacoraEntrada,BitacoraSalida> service)
    : ConsultaController<Bitacora,BitacoraEntrada,BitacoraSalida>(service);

[Route("api/proyecto/versiones-modelo"),Authorize(AuthenticationSchemes="Proyecto"),Tags("Configuraciones con Keycloak")]
[EnableCors("PanelProyecto")]
public sealed class VersionesProyectoController(RecursoService<VersionModelo,VersionModeloEntrada,VersionModeloSalida> service)
    : ConsultaController<VersionModelo,VersionModeloEntrada,VersionModeloSalida>(service);
