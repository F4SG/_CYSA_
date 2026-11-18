using Cysa.Web.Api.Data;
using Cysa.Web.Api.Dto;
using Cysa.Web.Api.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Web.Api.Controllers;

[ApiController,Authorize(Policy="Leer"),Tags("Gestionar infraestructura")]
public sealed class RelacionesController(CysaDb db) : ControllerBase
{
    [HttpGet("api/intersecciones/{id:int}/accesos"),ProducesResponseType<List<AccesoSalida>>(200),ProducesResponseType<ProblemDetails>(404)]
    public async Task<IActionResult> Accesos(int id,CancellationToken ct)
    {
        if(!await db.Intersecciones.AnyAsync(e=>e.Id==id,ct))return NotFound();
        return Ok((await db.Accesos.AsNoTracking().Where(e=>e.InterseccionId==id).OrderBy(e=>e.Id).ToListAsync(ct)).Select(AccesoSalida.Desde));
    }
    [HttpGet("api/accesos/{id:int}/carriles"),ProducesResponseType<List<CarrilSalida>>(200),ProducesResponseType<ProblemDetails>(404)]
    public async Task<IActionResult> Carriles(int id,CancellationToken ct)
    {
        if(!await db.Accesos.AnyAsync(e=>e.Id==id,ct))return NotFound();
        return Ok((await db.Set<Carril>().AsNoTracking().Where(e=>e.AccesoId==id).OrderBy(e=>e.Numero).ToListAsync(ct)).Select(CarrilSalida.Desde));
    }
}
