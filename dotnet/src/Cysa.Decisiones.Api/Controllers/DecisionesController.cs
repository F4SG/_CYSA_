using System.Net;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text.Json;
using Cysa.Core;
using Cysa.Infrastructure;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Decisiones.Api.Controllers;

[ApiController, Route("api/planes/{planId}/decisiones"), Authorize(Policy = "Leer")]
public sealed class DecisionesController(DecisionesDb db, IHttpClientFactory clients, TimeProvider reloj) : ControllerBase
{
    [HttpPost, Authorize(Policy = "Decidir")]
    [ProducesResponseType<ResultadoDecision>(StatusCodes.Status201Created)]
    public async Task<ActionResult<ResultadoDecision>> Crear(string planId, SolicitudDecision solicitud, CancellationToken ct)
    {
        var usuario = User.FindFirstValue("sub")!;
        var solicitudJson = JsonSerializer.Serialize(solicitud);
        var existente = await db.Decisiones.AsNoTracking().SingleOrDefaultAsync(d => d.SolicitudId == solicitud.SolicitudId, ct);
        if (existente is not null) return Reintento(existente, planId, usuario, solicitudJson);

        ResultadoEvaluacion? evaluacion;
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, $"api/evaluaciones/{solicitud.EvaluacionId}");
            request.Headers.Authorization = AuthenticationHeaderValue.Parse(Request.Headers.Authorization.ToString());
            using var response = await clients.CreateClient("evaluaciones").SendAsync(request, ct);
            if (response.StatusCode == HttpStatusCode.NotFound)
                return Problem(statusCode: 404, title: "La evaluación no existe.");
            if (!response.IsSuccessStatusCode)
                return Problem(statusCode: 503, title: "No se pudo verificar la evaluación. No se guardó ninguna decisión.");
            evaluacion = await response.Content.ReadFromJsonAsync<ResultadoEvaluacion>(ct);
        }
        catch (Exception e) when (e is HttpRequestException or JsonException || e is TaskCanceledException && !ct.IsCancellationRequested)
        {
            return Problem(statusCode: 503, title: "Evaluaciones no disponible. Reintenta con el mismo solicitudId.");
        }
        if (evaluacion is null || evaluacion.Id != solicitud.EvaluacionId || evaluacion.Plan is null)
            return Problem(statusCode: 502, title: "Respuesta inválida del servicio de evaluaciones.");
        if (evaluacion.Plan.PlanId != planId || evaluacion.Plan.Version != solicitud.Version)
            return Problem(statusCode: 409, title: "La evaluación no corresponde al plan y versión solicitados.");
        if (!evaluacion.Aprobada || !evaluacion.SoloPrueba || evaluacion.VenceUtc <= reloj.GetUtcNow())
            return Problem(statusCode: 409, title: "Se requiere una evaluación de prueba aprobada y vigente.");

        var resultado = new ResultadoDecision(Guid.NewGuid(), solicitud.SolicitudId, planId, solicitud.Version,
            evaluacion.Id, evaluacion.HuellaSha256, "validado", solicitud.Accion == "autorizar" ? "autorizado" : "rechazado",
            solicitud.Motivo.Trim(), usuario, true, reloj.GetUtcNow());
        db.Decisiones.Add(new() { Id = resultado.Id, SolicitudId = solicitud.SolicitudId, PlanId = planId,
            Version = solicitud.Version, UsuarioId = usuario, SolicitudJson = solicitudJson,
            ResultadoJson = JsonSerializer.Serialize(resultado), EvaluacionJson = JsonSerializer.Serialize(evaluacion) });
        // Una sola escritura transaccional conserva decisión, actor e instantánea de la evaluación.
        // Los índices únicos también protegen solicitudes concurrentes entre procesos.
        try { await db.SaveChangesAsync(ct); }
        catch (DbUpdateException e) when (e.InnerException is SqliteException { SqliteErrorCode: 19 })
        {
            db.ChangeTracker.Clear();
            existente = await db.Decisiones.AsNoTracking().SingleOrDefaultAsync(d => d.SolicitudId == solicitud.SolicitudId, ct);
            if (existente is not null) return Reintento(existente, planId, usuario, solicitudJson);
            return Problem(statusCode: 409, title: "Esta versión del plan ya tiene una decisión definitiva.");
        }
        return CreatedAtAction(nameof(Obtener), new { planId, id = resultado.Id }, resultado);
    }

    private ActionResult<ResultadoDecision> Reintento(DecisionGuardada row, string planId, string usuario, string json)
    {
        if (row.PlanId != planId || row.UsuarioId != usuario || row.SolicitudJson != json)
            return Problem(statusCode: 409, title: "solicitudId ya fue usado para otra operación.");
        return Ok(JsonSerializer.Deserialize<ResultadoDecision>(row.ResultadoJson));
    }

    [HttpGet("{id:guid}")]
    public async Task<ActionResult<ResultadoDecision>> Obtener(string planId, Guid id, CancellationToken ct)
    {
        var row = await db.Decisiones.AsNoTracking().SingleOrDefaultAsync(d => d.Id == id && d.PlanId == planId, ct);
        return row is null ? NotFound() : Ok(JsonSerializer.Deserialize<ResultadoDecision>(row.ResultadoJson));
    }

    [HttpGet("/api/planes/{planId}/historial")]
    public async Task<ActionResult<List<ResultadoDecision>>> Historial(string planId, [FromQuery] int pagina = 1, CancellationToken ct = default)
    {
        if (pagina < 1 || pagina > 10000) return Problem(statusCode: 400, title: "Página fuera de rango.");
        var rows = await db.Decisiones.AsNoTracking().Where(d => d.PlanId == planId)
            .OrderByDescending(d => d.Version).Skip((pagina - 1) * 50).Take(50).ToListAsync(ct);
        return Ok(rows.Select(d => JsonSerializer.Deserialize<ResultadoDecision>(d.ResultadoJson)));
    }
}
