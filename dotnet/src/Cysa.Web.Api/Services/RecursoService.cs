using System.Security.Claims;
using System.Text.Json;
using Cysa.Infrastructure;
using Cysa.Web.Api.Data;
using Cysa.Web.Api.Dto;
using Cysa.Web.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Web.Api.Services;

public sealed class ReglaException(string message,int status=400) : Exception(message) { public int Status { get; }=status; }

public sealed class RecursoService<T,TEntrada,TSalida>(CysaDb db, ReglasDominio reglas,IHttpContextAccessor accessor,IConfiguration configuration)
    where T:Entidad,new() where TEntrada:IEntrada<T> where TSalida:ISalida<T,TSalida>
{
    public async Task<List<TSalida>> Listar(ConsultaRecursos consulta,CancellationToken ct)
    {
        var pagina=consulta.Pagina; var tamano=consulta.Tamano;
        if(pagina<1 || pagina>10000 || tamano<1 || tamano>200) throw new ReglaException("Página 1..10000 y tamaño 1..200.");
        var query=Filtrar(consulta);
        return (await query.AsNoTracking().OrderBy(e=>e.Id).Skip((pagina-1)*tamano).Take(tamano).ToListAsync(ct)).Select(TSalida.Desde).ToList();
    }
    IQueryable<T> Filtrar(ConsultaRecursos c)
    {
        var tipo=typeof(T); var texto=c.Buscar?.Trim();
        var inventario=tipo==typeof(Corredor)||tipo==typeof(Interseccion)||tipo==typeof(Acceso)||tipo==typeof(Carril)||tipo==typeof(FuenteDeteccion)||tipo==typeof(ControladorLocal);
        var filtra=!string.IsNullOrEmpty(texto)||c.CorredorId.HasValue||c.InterseccionId.HasValue||c.AccesoId.HasValue||c.Activa.HasValue;
        if(!filtra)return db.Set<T>();
        if(!inventario)throw new ReglaException("Los filtros de infraestructura solo se aplican al inventario.");
        if(c.InterseccionId.HasValue && tipo==typeof(Corredor) || c.AccesoId.HasValue && tipo!=typeof(Acceso)&&tipo!=typeof(Carril)&&tipo!=typeof(FuenteDeteccion) || c.Activa.HasValue && tipo!=typeof(FuenteDeteccion))
            throw new ReglaException("Un filtro no corresponde al recurso seleccionado.");
        var intersecciones=db.Set<Interseccion>().Where(i=>(!c.CorredorId.HasValue||i.CorredorId==c.CorredorId)&&(!c.InterseccionId.HasValue||i.Id==c.InterseccionId)).Select(i=>i.Id);
        var accesos=db.Set<Acceso>().Where(a=>intersecciones.Contains(a.InterseccionId)&&(!c.AccesoId.HasValue||a.Id==c.AccesoId)).Select(a=>a.Id);
        if(tipo==typeof(Corredor))return Convertir(db.Set<Corredor>().Where(e=>(!c.CorredorId.HasValue||e.Id==c.CorredorId)&&(string.IsNullOrEmpty(texto)||e.Nombre.Contains(texto)||e.Descripcion.Contains(texto))));
        if(tipo==typeof(Interseccion))return Convertir(db.Set<Interseccion>().Where(e=>intersecciones.Contains(e.Id)&&(string.IsNullOrEmpty(texto)||e.Nombre.Contains(texto)||e.EstadoOperativo.Contains(texto))));
        if(tipo==typeof(Acceso))return Convertir(db.Set<Acceso>().Where(e=>accesos.Contains(e.Id)&&(string.IsNullOrEmpty(texto)||e.Identificador.Contains(texto)||e.Aproximacion.Contains(texto))));
        if(tipo==typeof(Carril))return Convertir(db.Set<Carril>().Where(e=>accesos.Contains(e.AccesoId)&&(string.IsNullOrEmpty(texto)||e.Sentido.Contains(texto))));
        if(tipo==typeof(FuenteDeteccion))return Convertir(db.Set<FuenteDeteccion>().Where(e=>accesos.Contains(e.AccesoId)&&(!c.Activa.HasValue||e.Activa==c.Activa)&&(string.IsNullOrEmpty(texto)||e.Ubicacion.Contains(texto)||e.ModeloIa.Contains(texto)||e.TipoCamara.Contains(texto))));
        return Convertir(db.Set<ControladorLocal>().Where(e=>intersecciones.Contains(e.InterseccionId)&&(string.IsNullOrEmpty(texto)||e.Tipo.Contains(texto)||e.Protocolo.Contains(texto)||e.Ubicacion.Contains(texto))));
    }
    static IQueryable<T> Convertir<TRecurso>(IQueryable<TRecurso> query) => (IQueryable<T>)(object)query;
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
        var authority=configuration["Security:ProjectAuthority"];
        var projectIdentity=!string.IsNullOrEmpty(authority) && principal?.FindFirstValue("iss")==authority;
        if(actor is null && subject is not null && principal is not null && projectIdentity)
        {
            var role=principal.IsInRole("administrador")?"administrador":"operador";
            var roleId=await db.Set<Rol>().Where(r=>r.Nombre==role).Select(r=>r.Id).SingleAsync(ct);
            actor=new Usuario{IdentificadorIdp=subject,Nombre=principal.FindFirstValue("preferred_username")??subject,RolId=roleId,Activo=true,MfaHabilitado=true,Prueba=true};
            db.Add(actor);await db.SaveChangesAsync(ct);
        }
        if(actor is not null && !actor.Activo)throw new ReglaException("El perfil local está desactivado.",403);
        if(actor is null)throw new ReglaException("El usuario autenticado debe tener un perfil local registrado para conservar la auditoría.",403);
        if(actor is not null)
        {
            db.Add(new Bitacora{UsuarioId=actor.Id,Operacion=operation,FechaUtc=DateTimeOffset.UtcNow,
                Motivo=projectIdentity && e is ConfigTecnica ? "Configuración registrada mediante la API de Proyecto"
                    : "Operación realizada mediante la API",ObjetoTipo=typeof(T).Name,ObjetoId=e.Id.ToString(),
                ValorAnterior=before,ValorPosterior=operation=="eliminar" ? "Eliminado" : JsonSerializer.Serialize(e),
                MfaVerificado=principal is not null && ApiSetup.MfaReciente(principal,DateTimeOffset.UtcNow),Prueba=e.Prueba});
            await db.SaveChangesAsync(ct);
        }
        await tx.CommitAsync(ct);
    }
}
