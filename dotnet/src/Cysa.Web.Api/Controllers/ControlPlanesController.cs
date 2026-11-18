using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using System.Text.Json;
using Cysa.Web.Api.Data;
using Cysa.Web.Api.Dto;
using Cysa.Web.Api.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Web.Api.Controllers;

public sealed record DecisionControlEntrada : IValidatableObject
{
    public Guid SolicitudId {get;init;}
    [Range(1,int.MaxValue)] public int ValidacionSumoId {get;init;}
    [Required,RegularExpression("^(autorizar|rechazar)$")] public string Accion {get;init;}="";
    [Required,StringLength(1000,MinimumLength=5)] public string Motivo {get;init;}="";
    public IEnumerable<ValidationResult> Validate(ValidationContext context)
    {
        if(SolicitudId==Guid.Empty)yield return new("SolicitudId debe ser un UUID no vacío.");
        if(Motivo.Trim().Length<5)yield return new("El motivo requiere al menos cinco caracteres.");
    }
}
public sealed record DecisionControlSalida(Guid SolicitudId,int PlanId,int ValidacionSumoId,string Accion,string Estado,string Motivo,string UsuarioId,DateTimeOffset FechaUtc,bool SoloPrueba=true);

[ApiController,Route("api/planes/{id:int}"),Authorize(Policy="Leer"),Tags("Gestionar planes semafóricos")]
public sealed class ControlPlanesController(CysaDb db) : ControllerBase
{
    [HttpGet("validacion"),ProducesResponseType<ValidacionSumoSalida>(200),ProducesResponseType(404)]
    public async Task<IActionResult> Validacion(int id,CancellationToken ct)
    {
        var v=await db.Set<ValidacionSumo>().AsNoTracking().SingleOrDefaultAsync(v=>v.PlanId==id,ct);
        return v is null?NotFound():Ok(ValidacionSumoSalida.Desde(v));
    }
    [HttpGet("decisiones-control"),ProducesResponseType<List<DecisionControlSalida>>(200),ProducesResponseType(404)]
    public async Task<IActionResult> Historial(int id,CancellationToken ct)
    {
        if(!await db.Set<Plan>().AnyAsync(p=>p.Id==id,ct))return NotFound();
        var rows=await db.Set<Bitacora>().AsNoTracking().Where(b=>b.ObjetoTipo=="Plan" && b.ObjetoId==id.ToString() && b.Operacion=="decidir-plan").OrderByDescending(b=>b.FechaUtc).ToListAsync(ct);
        return Ok(rows.Select(r=>JsonSerializer.Deserialize<DecisionControlSalida>(r.ValorPosterior)));
    }
    [HttpPost("decisiones-control"),Authorize(Policy="Decidir"),ProducesResponseType<DecisionControlSalida>(201),ProducesResponseType(200),ProducesResponseType(404),ProducesResponseType(409)]
    public async Task<IActionResult> Decidir(int id,DecisionControlEntrada input,CancellationToken ct)
    {
        var subject=User.FindFirstValue("sub")!;
        var previous=await db.Set<Bitacora>().AsNoTracking().SingleOrDefaultAsync(b=>b.SolicitudId==input.SolicitudId,ct);
        if(previous is not null)
        {
            var saved=JsonSerializer.Deserialize<DecisionControlSalida>(previous.ValorPosterior)!;
            if(saved.PlanId!=id || saved.ValidacionSumoId!=input.ValidacionSumoId || saved.Accion!=input.Accion || saved.Motivo!=input.Motivo.Trim() || saved.UsuarioId!=subject)
                return Problem(statusCode:409,title:"SolicitudId ya fue utilizado para otra decisión.");
            return Ok(saved);
        }
        var plan=await db.Set<Plan>().SingleOrDefaultAsync(p=>p.Id==id,ct); if(plan is null)return NotFound();
        if(!plan.Prueba || plan.Estado is "autorizado" or "rechazado")return Problem(statusCode:409,title:"Solo se decide una vez sobre un plan de prueba validado.");
        var v=await db.Set<ValidacionSumo>().SingleOrDefaultAsync(v=>v.Id==input.ValidacionSumoId && v.PlanId==id,ct);
        if(v is null || v.Resultado!="aprobada" || !v.CumpleMinimoPeatonal || !v.CumpleDespejePeatonal || plan.Estado!="validado"
            || !await db.Set<Recomendacion>().AnyAsync(r=>r.ValidacionSumoId==v.Id,ct))
            return Problem(statusCode:409,title:"Se requiere la validación aprobada y recomendación de esta versión exacta del plan.");
        var phases=await db.Set<Fase>().Where(f=>f.PlanId==id).ToListAsync(ct);
        if(phases.Count==0)return Problem(statusCode:409,title:"El plan no tiene fases verificables.");
        foreach(var phase in phases)
        {
            var access=await db.Set<Acceso>().FindAsync([phase.AccesoId],ct);
            if(access is null || phase.TiempoPeatonalSegundos<access.LongitudCrucePeatonalMetros/0.9m+5m)
                return Problem(statusCode:409,title:"El plan incumple el mínimo peatonal.");
        }
        var actor=await db.Set<Usuario>().SingleOrDefaultAsync(u=>u.IdentificadorIdp==subject && u.Activo,ct);
        if(actor is null)return Forbid();
        var before=plan.Estado;plan.Estado=input.Accion=="autorizar"?"autorizado":"rechazado";
        var result=new DecisionControlSalida(input.SolicitudId,id,v.Id,input.Accion,plan.Estado,input.Motivo.Trim(),subject,DateTimeOffset.UtcNow);
        db.Add(new Bitacora{UsuarioId=actor.Id,Operacion="decidir-plan",SolicitudId=input.SolicitudId,FechaUtc=result.FechaUtc,Motivo=result.Motivo,
            ObjetoTipo="Plan",ObjetoId=id.ToString(),ValorAnterior=before,ValorPosterior=JsonSerializer.Serialize(result),MfaVerificado=true,Prueba=true});
        await db.SaveChangesAsync(ct);
        return CreatedAtAction(nameof(Historial),new{id},result);
    }
}
