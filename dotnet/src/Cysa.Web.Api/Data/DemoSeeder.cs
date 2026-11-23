using System.Data;
using System.Text.Json;
using Cysa.Core;
using Cysa.Infrastructure;
using Cysa.Web.Api.Models;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Web.Api.Data;

public static class DemoSeeder
{
    public static async Task PrepararBanco(CysaDb db, CancellationToken ct = default)
    {
        await using var tx = await db.Database.BeginTransactionAsync(IsolationLevel.Serializable, ct);
        var intersection = await db.Set<Interseccion>().Where(i => i.Nombre == "DEMO_INT_01" && i.Prueba)
            .OrderBy(i => i.Id).FirstOrDefaultAsync(ct);
        if (intersection is null)
        {
            const string name = "Corredor de práctica CYSA";
            var corridor = await db.Set<Corredor>().SingleOrDefaultAsync(c => c.Nombre == name, ct);
            if (corridor is { Prueba: false })
                throw new InvalidOperationException("El nombre del corredor de práctica pertenece a un corredor operativo.");
            if (corridor is null)
            {
                corridor = new Corredor { Nombre = name, Descripcion = "Corredor sintético de Proyecto de Sistemas" };
                db.Add(corridor);
                await db.SaveChangesAsync(ct);
            }
            if (await db.Set<Interseccion>().AnyAsync(i => i.CorredorId == corridor.Id && i.Nombre == "DEMO_INT_01", ct))
                throw new InvalidOperationException("DEMO_INT_01 pertenece a una intersección operativa en este corredor.");
            intersection = new Interseccion { CorredorId = corridor.Id, Nombre = "DEMO_INT_01", EstadoOperativo = "activo" };
            db.Add(intersection);
            await db.SaveChangesAsync(ct);
        }

        var accesses = await db.Set<Acceso>().Where(a => a.InterseccionId == intersection.Id)
            .ToDictionaryAsync(a => a.Identificador, StringComparer.OrdinalIgnoreCase, ct);
        foreach (var (id, direction) in new[] { ("N", "Norte"), ("S", "Sur"), ("E", "Este"), ("W", "Oeste") })
        {
            if (!accesses.TryGetValue(id, out var access))
            {
                access = new Acceso { InterseccionId = intersection.Id, Identificador = id, Aproximacion = direction,
                    LongitudCrucePeatonalMetros = 6 };
                db.Add(access);
                await db.SaveChangesAsync(ct);
            }
            if (access.Prueba && !await db.Set<Carril>().AnyAsync(c => c.AccesoId == access.Id && c.Numero == 1, ct))
                db.Add(new Carril { AccesoId = access.Id, Numero = 1, Sentido = "entrada" });
        }

        var configurations = db.Set<ConfigTecnica>().Where(c => c.InterseccionId == intersection.Id);
        if (!await configurations.AnyAsync(c => c.Prueba, ct))
        {
            var lastVersion = await configurations.MaxAsync(c => (int?)c.Version, ct) ?? 0;
            db.Add(new ConfigTecnica { InterseccionId = intersection.Id, Version = lastVersion + 1,
                VerdeMinSegundos = 10, VerdeMaxSegundos = 90, AmbarSegundos = 3, TodoRojoSegundos = 2,
                ExtensionPrioridadSegundos = 10, ResponsableTecnico = "Configuración base de laboratorio",
                AprobadaUtc = DateTimeOffset.UtcNow, Estado = "aprobada" });
        }
        await db.SaveChangesAsync(ct);
        await tx.CommitAsync(ct);
    }

    public static async Task Cargar(CysaDb db,CancellationToken ct=default)
    {
        // La semilla pertenece exclusivamente a la base de demostración, no a una base operativa.
        if(await db.Set<Corredor>().AnyAsync(ct))return;
        await using var tx=await db.Database.BeginTransactionAsync(ct);
        var now=DateTimeOffset.UtcNow;
        var roles=new[]{new Rol{Nombre="administrador",Descripcion="Gestión de infraestructura, cuentas y configuraciones"},new Rol{Nombre="operador",Descripcion="Monitoreo y autorización de planes con MFA"}};
        db.AddRange(roles); await db.SaveChangesAsync(ct);
        var users=Enumerable.Range(1,15).Select(i=>new Usuario{RolId=roles[i==1?0:1].Id,Nombre=$"Usuario de prueba {i:00}",
            IdentificadorIdp=i==1?"administrador-demo":i==2?"operador-demo":$"usuario-demo-{i:00}",Activo=true,MfaHabilitado=true}).ToArray();
        db.AddRange(users); await db.SaveChangesAsync(ct);
        for(var i=1;i<=15;i++)
        {
            var corridor=new Corredor{Nombre=$"Corredor de prueba {i:00}",Descripcion="Red sintética para pruebas Web III; no representa infraestructura municipal certificada"};
            db.Add(corridor); await db.SaveChangesAsync(ct);
            var intersection=new Interseccion{CorredorId=corridor.Id,Nombre=$"DEMO_INT_{i:00}",Latitud=-17.78m+i*0.001m,Longitud=-63.18m+i*0.001m,EstadoOperativo="activo"};
            db.Add(intersection); await db.SaveChangesAsync(ct);
            var access=new Acceso{InterseccionId=intersection.Id,Identificador="N",Aproximacion="Norte",LongitudCrucePeatonalMetros=18};
            var controller=new ControladorLocal{InterseccionId=intersection.Id,Tipo="PC y MMU emulado",Protocolo="MQTT/TLS",Ubicacion=$"Gabinete de prueba {i:00}",Emulado=true};
            var config=new ConfigTecnica{InterseccionId=intersection.Id,Version=1,VerdeMinSegundos=10,VerdeMaxSegundos=60,AmbarSegundos=3,TodoRojoSegundos=2,
                ExtensionPrioridadSegundos=10,ResponsableTecnico="Responsable técnico de prueba",AprobadaUtc=now.AddDays(-1),Estado="aprobada"};
            db.AddRange(access,controller,config); await db.SaveChangesAsync(ct);
            var lane=new Carril{AccesoId=access.Id,Numero=1,Sentido="entrada"};
            var camera=new FuenteDeteccion{AccesoId=access.Id,TipoCamara="IP de prueba",Ubicacion=$"Acceso norte de {intersection.Nombre}",Protocolo="RTSP",Activa=true,ModeloIa="modelo-demo",UmbralConfianza=0.5m};
            var plan=new Plan{InterseccionId=intersection.Id,ConfigTecnicaId=config.Id,Version=1,Tipo="optimizado",MetodoCalculo="Datos sintéticos de laboratorio",CicloSegundos=60,CalculadoUtc=now.AddHours(-2),Estado="validado"};
            db.AddRange(lane,camera,plan); await db.SaveChangesAsync(ct);
            var phase=new Fase{PlanId=plan.Id,AccesoId=access.Id,Orden=1,Tipo="peatonal",VerdeSegundos=30,AmbarSegundos=3,TodoRojoSegundos=2,TiempoPeatonalSegundos=25};
            var validation=new ValidacionSumo{PlanId=plan.Id,Escenario=$"Escenario sintético {i:00}; no ejecutado en SUMO",Semilla=100+i,EjecutadaUtc=now.AddHours(-1),
                Resultado="aprobada",Motivo="Datos de demostración; 20 % de mejora y mínimo peatonal de 25 s",DemoraGlobalBaseSegundos=40,DemoraGlobalCandidataSegundos=32,CumpleMinimoPeatonal=true,CumpleDespejePeatonal=true};
            db.AddRange(phase,validation); await db.SaveChangesAsync(ct);
            db.Add(new EstadoControl{ControladorLocalId=controller.Id,PlanId=plan.Id,FaseId=phase.Id,FechaUtc=now,ComunicacionDisponible=true,Modo="central"});
            db.Add(new Medicion{CarrilId=lane.Id,FuenteDeteccionId=camera.Id,MensajeId=$"semilla-{i:00}",InicioUtc=now.AddMinutes(-1),FinUtc=now,
                ClaseVehiculo=i%3==0?"micro":i%3==1?"auto":"moto",Cantidad=15+i,ColaEstimadaMetros=3+i});
            db.Add(new EventoPrioridad{InterseccionId=intersection.Id,PlanId=plan.Id,Tipo=i%2==0?"micro":"emergencia",Origen="emulador",DetectadoUtc=now.AddMinutes(-5),
                AtendidoUtc=now.AddMinutes(-5).AddSeconds(8),Resultado="atendido",Accion="extension",ExtensionSegundos=8,Ciclo=1});
            db.Add(new Alerta{InterseccionId=intersection.Id,Tipo="comunicacion",FechaUtc=now.AddMinutes(-10),Severidad="informativa",Descripcion="Prueba de comunicación recuperada",Estado="cerrada"});
            db.Add(new Recomendacion{ValidacionSumoId=validation.Id,EmitidaUtc=now,JustificacionTecnica="Ejemplo sintético: demora 40 a 32 s y cruce peatonal de 25 s"});
            foreach(var (group,vehicles) in new[]{("total",100),("micro",20),("resto",80)})
                db.Add(new MetricaPorAcceso{ValidacionSumoId=validation.Id,AccesoId=access.Id,Grupo=group,VehiculosBase=vehicles,VehiculosCandidatos=vehicles,DemoraBaseSegundos=40,DemoraCandidataSegundos=32});
            db.Add(new Bitacora{UsuarioId=users[(i-1)%users.Length].Id,Operacion="cargar-demostracion",FechaUtc=now,Motivo="Preparación de datos sintéticos Web III",
                ObjetoTipo="Interseccion",ObjetoId=intersection.Id.ToString(),ValorAnterior="Sin registro",ValorPosterior=$"Creada {intersection.Nombre}",MfaVerificado=false});
            db.Add(new VersionModelo{Tipo="deteccion",Identificador=$"modelo-futuro-{i:00}",Descripcion="Registro de ejemplo; gobernanza no implementada",Estado="futuro",ActivadaUtc=null});
            db.Add(new Reporte{CorredorId=corridor.Id,Tipo="ejemplo de metadatos; sin informe calculado",DesdeUtc=now.AddDays(-1),HastaUtc=now,GeneradoUtc=now,Modo="auto",Estado="futuro"});
            var request=new SolicitudEvaluacion{PlanId=$"PLAN_DEMO_{i:00}",Version=1,InterseccionId=intersection.Nombre,PlanBaseId=$"FIJO_{i:00}",Escenario="Semilla sintética Web III",Origen="demo",
                Accesos=[new(){Id="N",DemoraBaseSegundos=40,DemoraCandidataSegundos=32,LongitudCruceMetros=18}],Fases=[new(){Id="PEATONAL_N",Accesos=["N"],TiempoPeatonalSegundos=25}]};
            var evaluation=new EvaluadorPlanes(TimeProvider.System).Evaluar(request,"servicio-evaluador-demo");
            db.Add(new EvaluacionGuardada{Id=evaluation.Id,PlanId=request.PlanId,Version=1,Json=JsonSerializer.Serialize(evaluation)});
            var decisionRequest=new SolicitudDecision{SolicitudId=Guid.NewGuid(),EvaluacionId=evaluation.Id,Version=1,Accion="rechazar",Motivo="Decisión sintética de demostración; no activa planes"};
            var decision=new ResultadoDecision(Guid.NewGuid(),decisionRequest.SolicitudId,request.PlanId,1,evaluation.Id,evaluation.HuellaSha256,"validado","rechazado",decisionRequest.Motivo,"operador-demo",false,now);
            db.Add(new DecisionGuardada{Id=decision.Id,SolicitudId=decision.SolicitudId,PlanId=request.PlanId,Version=1,UsuarioId="operador-demo",SolicitudJson=JsonSerializer.Serialize(decisionRequest),
                ResultadoJson=JsonSerializer.Serialize(decision),EvaluacionJson=JsonSerializer.Serialize(evaluation)});
            await db.SaveChangesAsync(ct);
            var measurement=await db.Set<Medicion>().SingleAsync(m=>m.CarrilId==lane.Id,ct);
            var priority=await db.Set<EventoPrioridad>().SingleAsync(e=>e.PlanId==plan.Id,ct);
            db.Add(new FaseAcceso{FaseId=phase.Id,AccesoId=access.Id});
            db.Add(new ValidacionMedicion{ValidacionSumoId=validation.Id,MedicionId=measurement.Id});
            db.Add(new ValidacionEvento{ValidacionSumoId=validation.Id,EventoPrioridadId=priority.Id});
            await db.SaveChangesAsync(ct);
        }
        await tx.CommitAsync(ct);
    }
}
