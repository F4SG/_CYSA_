using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Security.Claims;
using Cysa.Infrastructure;
using Cysa.Web.Api.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;

namespace Cysa.Web.Api.Controllers;

[ApiController,Route("api/demo"),Tags("Preparar pruebas Web III")]
public sealed class DemoController(DemoDatabase demo,DemoVerifier verifier,CysaDb db,IConfiguration config,IHostEnvironment env) : ControllerBase
{
    bool Local()=>env.IsDevelopment() && config.GetValue<bool>("Demo:Enabled") &&
        HttpContext.Connection.RemoteIpAddress is { } ip && IPAddress.IsLoopback(ip);
    [HttpGet("acceso/{perfil}"),AllowAnonymous,ProducesResponseType(200),ProducesResponseType(404)]
    public IActionResult Acceso(string perfil)
    {
        if(!Local() || perfil is not ("administrador" or "operador" or "evaluador" or "operador-sin-mfa"))return NotFound();
        var now=DateTimeOffset.UtcNow;
        var role=perfil=="evaluador"?"servicio":perfil=="operador-sin-mfa"?"operador":perfil;
        var subject=perfil=="evaluador"?"servicio-evaluador-demo":role+"-demo";
        var claims=new List<Claim>{new("sub",subject),new("role",role),new("auth_time",now.ToUnixTimeSeconds().ToString(),ClaimValueTypes.Integer64)};
        if(perfil!="operador-sin-mfa" && perfil!="evaluador")claims.Add(new("amr","otp"));
        if(perfil=="evaluador")claims.Add(new("scope","evaluaciones:importar"));
        var key=Convert.FromBase64String(System.IO.File.ReadAllText(Path.Combine(ApiSetup.RuntimePath(config),"demo.key")).Trim());
        var token=new JwtSecurityTokenHandler().WriteToken(new JwtSecurityToken("cysa-demo-local","cysa-dotnet",claims,
            now.UtcDateTime,now.AddMinutes(30).UtcDateTime,new SigningCredentials(new SymmetricSecurityKey(key),SecurityAlgorithms.HmacSha256)));
        Response.Headers.CacheControl="no-store";
        return Ok(new{token,perfil,mfaSimulada=true,mfaMinutos=5,tokenMinutos=30});
    }
    [HttpGet("base"),Authorize(Policy="Leer"),ProducesResponseType(200)]
    public async Task<IActionResult> Estado(CancellationToken ct)
    {
        if(!Local())return NotFound();
        demo.ExigirDemo();
        if(!await db.Database.CanConnectAsync(ct))return Ok(new{baseDatos=DemoDatabase.Name,preparada=false});
        var pending=(await db.Database.GetPendingMigrationsAsync(ct)).ToArray();
        if(pending.Length>0)return Ok(new{baseDatos=DemoDatabase.Name,preparada=false,migracionesPendientes=pending});
        return Ok(new{baseDatos=DemoDatabase.Name,preparada=true,tablas=await demo.Conteos(ct)});
    }
    [HttpGet("verificacion"),Authorize(Policy="Leer"),ProducesResponseType<VerificacionDemo>(200),ProducesResponseType(404)]
    public async Task<IActionResult> Verificar(CancellationToken ct)
    {
        if(!Local())return NotFound();
        return Ok(await verifier.Verificar(ct));
    }
    [HttpPost("base"),Authorize(Policy="Escribir"),ProducesResponseType(200),ProducesResponseType(400)]
    public async Task<IActionResult> Recrear(CancellationToken ct)
    {
        if(!Local())return NotFound();
        if(Request.Headers["X-CYSA-Confirmar"]!=DemoDatabase.Name)return BadRequest(new{error="Debe confirmar explícitamente la base de demostración mediante X-CYSA-Confirmar."});
        await demo.Preparar(true,ct);
        return Ok(new{baseDatos=DemoDatabase.Name,recreada=true,tablas=await demo.Conteos(ct)});
    }
}
