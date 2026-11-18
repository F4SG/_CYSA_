using System.Security.Claims;
using System.Text.Json;
using Cysa.Infrastructure;
using Cysa.Web.Api.Data;
using Cysa.Web.Api.Dto;
using Cysa.Web.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Web.Api.Services;

public sealed class ReglaException(string message,int status=400) : Exception(message) { public int Status { get; }=status; }

public sealed class RecursoService<T,TEntrada,TSalida>(CysaDb db, ReglasDominio reglas,IHttpContextAccessor accessor)
    where T:Entidad,new() where TEntrada:IEntrada<T> where TSalida:ISalida<T,TSalida>
{
    public async Task<List<TSalida>> Listar(int pagina,int tamano,CancellationToken ct)
    {
        if(pagina<1 || pagina>10000 || tamano<1 || tamano>200) throw new ReglaException("Página 1..10000 y tamaño 1..200.");
        return (await db.Set<T>().AsNoTracking().OrderBy(e=>e.Id).Skip((pagina-1)*tamano).Take(tamano).ToListAsync(ct)).Select(TSalida.Desde).ToList();
    }
    public async Task<TSalida?> Obtener(int id,CancellationToken ct)
    {
        var e=await db.Set<T>().AsNoTracking().SingleOrDefaultAsync(e=>e.Id==id,ct);
        return e is null ? default : TSalida.Desde(e);
    }
    public async Task<TSalida> Crear(TEntrada input,CancellationToken ct)
    {
        var e=new T(); input.Aplicar(e); await reglas.Validar(e,null,ct);
        db.Add(e); await Guardar("crear",e,"Sin valor anterior",ct); return TSalida.Desde(e);
    }
    public async Task<bool> Actualizar(int id,TEntrada input,CancellationToken ct)
    {
        var e=await db.Set<T>().SingleOrDefaultAsync(e=>e.Id==id,ct); if(e is null)return false;
        var before=JsonSerializer.Serialize(e);
        var previous=db.Entry(e).CurrentValues.Clone();
        input.Aplicar(e); await reglas.Validar(e,previous,ct);
        await Guardar("actualizar",e,before,ct); return true;
    }
    public async Task<bool> Eliminar(int id,CancellationToken ct)
    {
        var e=await db.Set<T>().SingleOrDefaultAsync(e=>e.Id==id,ct); if(e is null)return false;
        await reglas.PuedeEliminar(e,ct);
        var before=JsonSerializer.Serialize(e); db.Remove(e);
        await Guardar("eliminar",e,before,ct); return true;
    }
    async Task Guardar(string operation,T e,string before,CancellationToken ct)
    {
        // Datos de dominio y auditoría comparten una transacción; los IDs no salen del cliente.
        await using var tx=await db.Database.BeginTransactionAsync(ct);
        if(operation=="eliminar" && e is Fase removed)
            db.RemoveRange(await db.Set<FaseAcceso>().Where(a=>a.FaseId==removed.Id).ToListAsync(ct));
        await db.SaveChangesAsync(ct);
        if(operation=="crear" && e is Fase created)
        {
            db.Add(new FaseAcceso{FaseId=created.Id,AccesoId=created.AccesoId,Prueba=created.Prueba});
            await db.SaveChangesAsync(ct);
        }
        var principal=accessor.HttpContext?.User;
        var subject=principal?.FindFirstValue("sub");
        var actor=await db.Set<Usuario>().FirstOrDefaultAsync(u=>u.IdentificadorIdp==subject,ct);
        if(actor is null)throw new ReglaException("El usuario autenticado debe tener un perfil local registrado para conservar la auditoría.",403);
        if(actor is not null)
        {
            db.Add(new Bitacora{UsuarioId=actor.Id,Operacion=operation,FechaUtc=DateTimeOffset.UtcNow,
                Motivo="Operación realizada mediante la API",ObjetoTipo=typeof(T).Name,ObjetoId=e.Id.ToString(),
                ValorAnterior=before,ValorPosterior=operation=="eliminar" ? "Eliminado" : JsonSerializer.Serialize(e),
                MfaVerificado=principal is not null && ApiSetup.MfaReciente(principal,DateTimeOffset.UtcNow),Prueba=e.Prueba});
            await db.SaveChangesAsync(ct);
        }
        await tx.CommitAsync(ct);
    }
}
