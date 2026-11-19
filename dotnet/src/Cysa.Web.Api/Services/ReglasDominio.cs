using Cysa.Web.Api.Data;
using Cysa.Web.Api.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;

namespace Cysa.Web.Api.Services;

public sealed class ReglasDominio(CysaDb db)
{
    public async Task Validar(Entidad e,PropertyValues? anterior,CancellationToken ct)
    {
        var metadata=db.Model.FindEntityType(e.GetType())!;
        foreach(var fk in metadata.GetForeignKeys())
        {
            var p=fk.Properties.Single(); var value=p.PropertyInfo!.GetValue(e);
            if(anterior is not null && !Equals(anterior[p.Name],value))
                throw new ReglaException("No se cambia la pertenencia de un registro existente. Cree otro recurso para conservar su historial.");
            var parent=await db.FindAsync(fk.PrincipalEntityType.ClrType,[value],ct);
            if(parent is null)throw new ReglaException($"La referencia {p.Name} no existe.");
            if(parent is Entidad linked && linked is not Rol && linked.Prueba!=e.Prueba)
                throw new ReglaException("No se mezclan registros de prueba con registros operativos.");
        }
        foreach(var p in e.GetType().GetProperties().Where(p=>p.PropertyType==typeof(DateTimeOffset)))
            if((DateTimeOffset)p.GetValue(e)! < new DateTimeOffset(2000,1,1,0,0,0,TimeSpan.Zero))
                throw new ReglaException($"{p.Name} debe contener una fecha válida desde el año 2000.");
        switch(e)
        {
            case Acceso a when anterior is not null:
                if(await db.Set<Fase>().AnyAsync(f=>f.AccesoId==a.Id && f.TiempoPeatonalSegundos<a.LongitudCrucePeatonalMetros/0.9m+5m,ct))
                    throw new ReglaException("El cambio dejaría fases existentes por debajo del mínimo peatonal.",409);
                if(await (from link in db.Set<FaseAcceso>() join f in db.Set<Fase>() on link.FaseId equals f.Id
                    where link.AccesoId==a.Id && f.TiempoPeatonalSegundos<a.LongitudCrucePeatonalMetros/0.9m+5m select f.Id).AnyAsync(ct))
                    throw new ReglaException("El cambio incumple el mínimo de una fase vinculada.",409);
                break;
            case ConfigTecnica c when anterior is not null && await db.Set<Plan>().AnyAsync(p=>p.ConfigTecnicaId==c.Id,ct):
                throw new ReglaException("Una configuración utilizada por planes se conserva. Registre una nueva versión.",409);
            case ConfigTecnica c when c.VerdeMaxSegundos<c.VerdeMinSegundos:
                throw new ReglaException("El verde máximo no puede ser menor al mínimo.");
            case Plan p:
                var config=await db.Set<ConfigTecnica>().FindAsync([p.ConfigTecnicaId],ct);
                if(config!.InterseccionId!=p.InterseccionId || config.Estado!="aprobada")throw new ReglaException("La configuración debe estar aprobada y pertenecer a la misma intersección.");
                if(p.Estado!="borrador" || anterior is not null && (string)anterior[nameof(Plan.Estado)]! != "borrador")
                    throw new ReglaException("Solo se crean o editan borradores. Validación y autorización usan sus operaciones específicas.",409);
                if(anterior is not null)await ExigirBorradorSinEvaluacion(p,ct);
                break;
            case Fase f:
                var plan=await db.Set<Plan>().FindAsync([f.PlanId],ct);
                var acceso=await db.Set<Acceso>().FindAsync([f.AccesoId],ct);
                var limits=await db.Set<ConfigTecnica>().FindAsync([plan!.ConfigTecnicaId],ct);
                if(plan.InterseccionId!=acceso!.InterseccionId)throw new ReglaException("La fase y el acceso deben pertenecer a la misma intersección.");
                await ExigirBorradorSinEvaluacion(plan,ct);
                if(f.TiempoPeatonalSegundos<acceso.LongitudCrucePeatonalMetros/0.9m+5m)throw new ReglaException("La fase no cumple el mínimo peatonal L/0,9 + 5 segundos.");
                var linkedLengths=await (from link in db.Set<FaseAcceso>() join a in db.Set<Acceso>() on link.AccesoId equals a.Id where link.FaseId==f.Id select a.LongitudCrucePeatonalMetros).ToListAsync(ct);
                if(linkedLengths.Any(length=>f.TiempoPeatonalSegundos<length/0.9m+5m))throw new ReglaException("La fase no cubre el mínimo peatonal de todos sus accesos habilitados.");
                if(f.VerdeSegundos<limits!.VerdeMinSegundos || f.VerdeSegundos>limits.VerdeMaxSegundos || f.AmbarSegundos<limits.AmbarSegundos || f.TodoRojoSegundos<limits.TodoRojoSegundos)
                    throw new ReglaException("La fase incumple los límites técnicos aprobados.");
                if(f.VerdeSegundos+f.AmbarSegundos+f.TodoRojoSegundos>plan.CicloSegundos)throw new ReglaException("La fase excede el ciclo del plan.");
                break;
            case Medicion m:
                if(m.FinUtc<=m.InicioUtc || m.FinUtc-m.InicioUtc>TimeSpan.FromHours(24))throw new ReglaException("El intervalo debe ser positivo y de hasta 24 horas.");
                var lane=await db.Set<Carril>().FindAsync([m.CarrilId],ct);
                var camera=await db.Set<FuenteDeteccion>().FindAsync([m.FuenteDeteccionId],ct);
                if(lane!.AccesoId!=camera!.AccesoId)throw new ReglaException("El carril y la cámara deben corresponder al mismo acceso.");
                break;
            case EstadoControl s:
                var controller=await db.Set<ControladorLocal>().FindAsync([s.ControladorLocalId],ct);
                var active=await db.Set<Plan>().FindAsync([s.PlanId],ct);
                var phase=await db.Set<Fase>().FindAsync([s.FaseId],ct);
                if(controller!.InterseccionId!=active!.InterseccionId || phase!.PlanId!=active.Id)throw new ReglaException("Controlador, plan y fase no corresponden a la misma operación.");
                break;
            case EventoPrioridad p:
                var eventPlan=await db.Set<Plan>().FindAsync([p.PlanId],ct);
                if(p.InterseccionId!=eventPlan!.InterseccionId)throw new ReglaException("El evento y el plan deben pertenecer a la misma intersección.");
                if(p.AtendidoUtc<p.DetectadoUtc)throw new ReglaException("La atención no puede preceder a la detección.");
                if(p.Tipo=="emergencia" && p.Resultado=="atendido" && p.AtendidoUtc-p.DetectadoUtc>TimeSpan.FromSeconds(10))throw new ReglaException("Una emergencia atendida debe respetar el máximo de 10 s; registre un conflicto si no se cumple.");
                break;
            case ValidacionSumo v:
                if(v.Resultado=="aprobada" && (!v.CumpleMinimoPeatonal || !v.CumpleDespejePeatonal || v.DemoraGlobalCandidataSegundos>v.DemoraGlobalBaseSegundos*1.15m))
                    throw new ReglaException("No se aprueba una validación que incumple peatones o el umbral de demora.");
                if(v.Resultado=="aprobada")await VerificarCoberturaPeatonal(v.PlanId,ct);
                break;
            case MetricaPorAcceso m:
                var validation=await db.Set<ValidacionSumo>().FindAsync([m.ValidacionSumoId],ct);
                var testedPlan=await db.Set<Plan>().FindAsync([validation!.PlanId],ct);
                var approach=await db.Set<Acceso>().FindAsync([m.AccesoId],ct);
                if(testedPlan!.InterseccionId!=approach!.InterseccionId)throw new ReglaException("La métrica debe corresponder a un acceso de la intersección evaluada.");
                if(validation.Resultado=="aprobada" && m.DemoraCandidataSegundos>m.DemoraBaseSegundos*1.15m)throw new ReglaException("Una validación aprobada no admite un acceso con aumento de demora mayor al 15 %.");
                break;
            case Recomendacion r:
                var approved=await db.Set<ValidacionSumo>().FindAsync([r.ValidacionSumoId],ct);
                if(approved!.Resultado!="aprobada")throw new ReglaException("Solo se recomienda un plan con validación aprobada.");
                var relatedPlan=await db.Set<Plan>().FindAsync([approved.PlanId],ct);
                var accessIds=await db.Set<Acceso>().Where(a=>a.InterseccionId==relatedPlan!.InterseccionId).Select(a=>a.Id).ToListAsync(ct);
                await VerificarCoberturaPeatonal(approved.PlanId,ct);
                var metrics=await db.Set<MetricaPorAcceso>().Where(m=>m.ValidacionSumoId==approved.Id).ToListAsync(ct);
                foreach(var accessId in accessIds)
                {
                    var groups=metrics.Where(m=>m.AccesoId==accessId).ToList();
                    if(groups.Count!=3 || groups.Select(m=>m.Grupo).Distinct().Count()!=3)throw new ReglaException("Cada acceso requiere métricas total, micro y resto antes de recomendar.");
                    if(groups.Single(m=>m.Grupo=="total").VehiculosBase!=groups.Where(m=>m.Grupo!="total").Sum(m=>m.VehiculosBase)
                        || groups.Single(m=>m.Grupo=="total").VehiculosCandidatos!=groups.Where(m=>m.Grupo!="total").Sum(m=>m.VehiculosCandidatos))
                        throw new ReglaException("Los vehículos del grupo total deben coincidir con micro más resto.");
                }
                if(relatedPlan!.Estado=="borrador")relatedPlan.Estado="validado";
                break;
            case Usuario u:
                if(u.IdentificadorIdp=="administrador-demo" && (!u.Activo || u.RolId!=1 || !u.MfaHabilitado))throw new ReglaException("La cuenta administradora de la demostración debe conservar acceso.");
                break;
            case FaseAcceso link:
                var linkedPhase=await db.Set<Fase>().FindAsync([link.FaseId],ct);
                var linkedAccess=await db.Set<Acceso>().FindAsync([link.AccesoId],ct);
                var linkedPlan=await db.Set<Plan>().FindAsync([linkedPhase!.PlanId],ct);
                await ExigirBorradorSinEvaluacion(linkedPlan!,ct);
                if(linkedPlan!.InterseccionId!=linkedAccess!.InterseccionId || linkedPhase.TiempoPeatonalSegundos<linkedAccess.LongitudCrucePeatonalMetros/0.9m+5m)
                    throw new ReglaException("El acceso debe corresponder a la misma intersección y su mínimo peatonal debe estar cubierto.");
                break;
            case ValidacionMedicion link:
                var count=await db.Set<Medicion>().FindAsync([link.MedicionId],ct);
                var countedLane=await db.Set<Carril>().FindAsync([count!.CarrilId],ct);
                var countedAccess=await db.Set<Acceso>().FindAsync([countedLane!.AccesoId],ct);
                var countValidation=await db.Set<ValidacionSumo>().FindAsync([link.ValidacionSumoId],ct);
                var countPlan=await db.Set<Plan>().FindAsync([countValidation!.PlanId],ct);
                if(countedAccess!.InterseccionId!=countPlan!.InterseccionId)throw new ReglaException("La medición no corresponde a la intersección evaluada.");
                break;
            case ValidacionEvento link:
                var testedEvent=await db.Set<EventoPrioridad>().FindAsync([link.EventoPrioridadId],ct);
                var eventValidation=await db.Set<ValidacionSumo>().FindAsync([link.ValidacionSumoId],ct);
                if(testedEvent!.PlanId!=eventValidation!.PlanId)throw new ReglaException("El evento no corresponde al plan evaluado.");
                break;
        }
    }
    public async Task PuedeEliminar(Entidad e,CancellationToken ct)
    {
        if(e is Plan removedPlan)await ExigirBorradorSinEvaluacion(removedPlan,ct);
        if(e is ConfigTecnica c && await db.Set<Plan>().AnyAsync(p=>p.ConfigTecnicaId==c.Id,ct))throw new ReglaException("La configuración tiene planes asociados.",409);
        if(e is Fase f)await ExigirBorradorSinEvaluacion((await db.Set<Plan>().FindAsync([f.PlanId],ct))!,ct);
        if(e is Usuario {IdentificadorIdp:"administrador-demo"})throw new ReglaException("No se elimina la cuenta administradora de demostración.",409);
        if(e is FaseAcceso link)
        {
            var phase=await db.Set<Fase>().FindAsync([link.FaseId],ct);
            var plan=await db.Set<Plan>().FindAsync([phase!.PlanId],ct);
            await ExigirBorradorSinEvaluacion(plan!,ct);
            if(plan!.Estado!="borrador" || phase.AccesoId==link.AccesoId)throw new ReglaException("Se conserva el acceso principal y las relaciones de planes evaluados.",409);
        }
    }

    async Task ExigirBorradorSinEvaluacion(Plan plan,CancellationToken ct)
    {
        if(plan.Estado!="borrador" || await db.Set<ValidacionSumo>().AnyAsync(v=>v.PlanId==plan.Id,ct))
            throw new ReglaException("La versión ya fue evaluada o decidida. Cree una nueva versión; se conserva el plan y sus fases.",409);
    }

    async Task VerificarCoberturaPeatonal(int planId,CancellationToken ct)
    {
        var plan=await db.Set<Plan>().FindAsync([planId],ct);
        var accesses=await db.Set<Acceso>().Where(a=>a.InterseccionId==plan!.InterseccionId).ToListAsync(ct);
        var phases=await db.Set<Fase>().Where(f=>f.PlanId==planId).ToListAsync(ct);
        if(accesses.Count==0 || phases.Count==0)throw new ReglaException("El plan requiere accesos y fases peatonales antes de aprobarse o recomendarse.");
        var phaseIds=phases.Select(f=>f.Id).ToList();
        var links=await db.Set<FaseAcceso>().Where(l=>phaseIds.Contains(l.FaseId)).ToListAsync(ct);
        var covered=new HashSet<int>();
        foreach(var phase in phases)
        {
            var ids=links.Where(l=>l.FaseId==phase.Id).Select(l=>l.AccesoId).Append(phase.AccesoId).ToHashSet();
            foreach(var id in ids)
            {
                var access=accesses.SingleOrDefault(a=>a.Id==id);
                if(access is null || phase.TiempoPeatonalSegundos<access.LongitudCrucePeatonalMetros/0.9m+5m)
                    throw new ReglaException("Cada fase debe cubrir el mínimo peatonal de todos sus accesos de la misma intersección.");
                covered.Add(id);
            }
        }
        if(accesses.Any(a=>!covered.Contains(a.Id)))throw new ReglaException("Todos los accesos de la intersección requieren una fase que cubra su mínimo peatonal.");
    }
}
