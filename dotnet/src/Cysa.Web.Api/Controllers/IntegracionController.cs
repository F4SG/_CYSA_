using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;
using Cysa.Web.Api.Data;
using Cysa.Web.Api.Dto;
using Cysa.Web.Api.Models;
using Cysa.Web.Api.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Web.Api.Controllers;

public sealed record ConteoImportado
{
    [Required,RegularExpression(@"^1\.0$")] public string Version {get;init;}="1.0";
    [JsonPropertyName("mensaje_id")] public Guid MensajeId {get;init;}
    [Required] public string Interseccion {get;init;}="";
    [Required] public string Acceso {get;init;}="";
    [Required] public string Carril {get;init;}="";
    [Required,RegularExpression("^(auto|micro|moto)$")] public string Clase {get;init;}="";
    [Range(0,100000)] public int Cantidad {get;init;}
    public DateTimeOffset Inicio {get;init;}
    public DateTimeOffset Fin {get;init;}
    public bool Prueba {get;init;}
}

[ApiController,Route("api/integracion"),Tags("Monitorear operación semafórica")]
public sealed class IntegracionController(CysaDb db,ReglasDominio reglas) : ControllerBase
{
    [HttpGet("health"),Authorize(Policy="Leer")]
    public async Task<IActionResult> Health(CancellationToken ct)=>await db.Database.CanConnectAsync(ct)?Ok(new{status="ok",persistencia="SQL Server"}):StatusCode(503);
    [HttpPost("conteos"),Authorize(Policy="Importar"),ProducesResponseType(201),ProducesResponseType(200),ProducesResponseType(400),ProducesResponseType(409)]
    public async Task<IActionResult> Conteo(ConteoImportado input,CancellationToken ct)
    {
        if(input.MensajeId==Guid.Empty || input.Fin<=input.Inicio || (input.Fin-input.Inicio).TotalSeconds>30.5)return BadRequest(new{error="UUID e intervalo de conteo válidos requeridos: hasta 30,5 s."});
        var intersection=await db.Set<Interseccion>().SingleOrDefaultAsync(i=>i.Nombre==input.Interseccion && i.Prueba==input.Prueba,ct);
        if(intersection is null)return BadRequest(new{error="Registre primero la intersección en Gestionar infraestructura."});
        var access=await db.Set<Acceso>().SingleOrDefaultAsync(a=>a.InterseccionId==intersection.Id && a.Identificador==input.Acceso,ct);
        if(access is null || !int.TryParse(input.Carril,out var laneNumber))return BadRequest(new{error="Acceso o número de carril inválido."});
        var lane=await db.Set<Carril>().SingleOrDefaultAsync(l=>l.AccesoId==access.Id && l.Numero==laneNumber,ct);
        var cameras=await db.Set<FuenteDeteccion>().Where(c=>c.AccesoId==access.Id && c.Activa).ToListAsync(ct);
        if(lane is null || cameras.Count!=1)return BadRequest(new{error="El carril debe existir y su acceso debe tener una cámara activa inequívoca."});
        var message=input.MensajeId.ToString();
        var previous=await db.Set<Medicion>().AsNoTracking().SingleOrDefaultAsync(m=>m.MensajeId==message,ct);
        if(previous is not null)
        {
            if(previous.CarrilId!=lane.Id || previous.ClaseVehiculo!=input.Clase || previous.Cantidad!=input.Cantidad || previous.InicioUtc!=input.Inicio || previous.FinUtc!=input.Fin || previous.Prueba!=input.Prueba)
                return Problem(statusCode:409,title:"MensajeId ya se usó con otro contenido.");
            return Ok(MedicionSalida.Desde(previous));
        }
        var measurement=new Medicion{CarrilId=lane.Id,FuenteDeteccionId=cameras[0].Id,MensajeId=message,InicioUtc=input.Inicio,FinUtc=input.Fin,
            ClaseVehiculo=input.Clase,Cantidad=input.Cantidad,ColaEstimadaMetros=0,Prueba=input.Prueba};
        await reglas.Validar(measurement,null,ct);db.Add(measurement);await db.SaveChangesAsync(ct);
        return Created("/api/mediciones/"+measurement.Id,MedicionSalida.Desde(measurement));
    }
    [HttpGet("conteos"),Authorize(Policy="Leer")]
    public async Task<IActionResult> Conteos(DateTimeOffset desde,DateTimeOffset hasta,string? interseccion=null,string? carril=null,bool? prueba=null,int limit=200,int offset=0,CancellationToken ct=default)
    {
        if(hasta<=desde || hasta-desde>TimeSpan.FromDays(31) || limit is <1 or >1000 || offset<0)return BadRequest();
        var query=from m in db.Set<Medicion>().AsNoTracking()
            join lane in db.Set<Carril>() on m.CarrilId equals lane.Id
            join access in db.Set<Acceso>() on lane.AccesoId equals access.Id
            join intersection in db.Set<Interseccion>() on access.InterseccionId equals intersection.Id
            where m.InicioUtc>=desde && m.InicioUtc<hasta && (interseccion==null || intersection.Nombre==interseccion)
                && (carril==null || lane.Numero.ToString()==carril) && (prueba==null || m.Prueba==prueba)
            orderby m.InicioUtc descending,m.Id descending
            select new{mensaje_id=m.MensajeId,interseccion=intersection.Nombre,acceso=access.Identificador,carril=lane.Numero.ToString(),clase=m.ClaseVehiculo,cantidad=m.Cantidad,inicio=m.InicioUtc,fin=m.FinUtc,prueba=m.Prueba};
        return Ok(new{items=await query.Skip(offset).Take(limit).ToListAsync(ct),limit,offset,desde,hasta});
    }
}
