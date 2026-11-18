using System.Security.Claims;
using System.Text.Json;
using Cysa.Core;
using Cysa.Infrastructure;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Evaluaciones.Api.Controllers;

[ApiController, Route("api/evaluaciones"), Authorize(Policy = "Leer")]
public sealed class EvaluacionesController(EvaluacionesDb db, EvaluadorPlanes evaluador) : ControllerBase
{
    [HttpPost, Authorize(Policy = "Importar")]
    [ProducesResponseType<ResultadoEvaluacion>(StatusCodes.Status201Created)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status409Conflict)]
    public async Task<ActionResult<ResultadoEvaluacion>> Crear(SolicitudEvaluacion solicitud, CancellationToken ct)
    {
        var resultado = evaluador.Evaluar(solicitud, User.FindFirstValue("sub")!);
        db.Evaluaciones.Add(new() { Id = resultado.Id, PlanId = solicitud.PlanId,
            Version = solicitud.Version, Json = JsonSerializer.Serialize(resultado) });
        try { await db.SaveChangesAsync(ct); }
        catch (DbUpdateException e) when (e.InnerException is SqliteException { SqliteErrorCode: 19 }
            or Microsoft.Data.SqlClient.SqlException { Number: 2601 or 2627 })
        {
            return Problem(statusCode: 409, title: "La versión del plan ya tiene una evaluación inmutable.",
                detail: "Envía una nueva versión para evaluar cambios; no se sobrescribe la evidencia anterior.");
        }
        return CreatedAtAction(nameof(Obtener), new { id = resultado.Id }, resultado);
    }

    [HttpGet("{id:guid}")]
    [ProducesResponseType<ResultadoEvaluacion>(StatusCodes.Status200OK)]
    public async Task<ActionResult<ResultadoEvaluacion>> Obtener(Guid id, CancellationToken ct)
    {
        var row = await db.Evaluaciones.AsNoTracking().SingleOrDefaultAsync(e => e.Id == id, ct);
        return row is null ? NotFound() : Ok(JsonSerializer.Deserialize<ResultadoEvaluacion>(row.Json));
    }

    [HttpGet]
    public async Task<ActionResult<List<ResultadoEvaluacion>>> Listar(
        [FromQuery] string planId, [FromQuery] int pagina = 1, CancellationToken ct = default)
    {
        if (pagina < 1 || pagina > 10000 || string.IsNullOrWhiteSpace(planId))
            return Problem(statusCode: 400, title: "Indica planId y una página entre 1 y 10000.");
        var rows = await db.Evaluaciones.AsNoTracking().Where(e => e.PlanId == planId)
            .OrderByDescending(e => e.Version).Skip((pagina - 1) * 50).Take(50).ToListAsync(ct);
        return Ok(rows.Select(e => JsonSerializer.Deserialize<ResultadoEvaluacion>(e.Json)));
    }
}
