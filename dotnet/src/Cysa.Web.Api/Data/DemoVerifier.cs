using System.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;

namespace Cysa.Web.Api.Data;

public sealed record ComprobacionDemo(string Codigo,string Descripcion,int Incumplimientos);
public sealed record VerificacionDemo(string BaseDatos,bool Cumple,DateTimeOffset VerificadaUtc,
    IReadOnlyDictionary<string,int> Tablas,IReadOnlyList<ComprobacionDemo> Comprobaciones);

/// <summary>Diagnóstico de solo lectura de la base sintética; nunca certifica una simulación real.</summary>
public sealed class DemoVerifier(CysaDb db,DemoDatabase demo)
{
    public async Task<VerificacionDemo> Verificar(CancellationToken ct=default)
    {
        demo.ExigirDemo();
        // Lectura consistente aun si se ejecuta desde CLI mientras otro proceso escribe.
        await using var tx=await db.Database.BeginTransactionAsync(IsolationLevel.Serializable,ct);
        var counts=await demo.Conteos(ct);
        var checks=new List<ComprobacionDemo>();
        void Agregar(string codigo,string descripcion,int errores)=>checks.Add(new(codigo,descripcion,errores));
        foreach(var (table,count) in counts)
            Agregar("cantidad-"+table,table=="Rol"?"Exactamente dos roles":"Al menos 15 registros en "+table,
                table=="Rol"?(count==2?0:1):(count>=15?0:1));
        // Los identificadores proceden del modelo EF. No se concatena texto recibido del cliente.
        static string Q(string value)=>"["+value.Replace("]","]]")+"]";
        foreach(var entity in db.Model.GetEntityTypes())
        {
            var table=entity.GetTableName()!; var store=StoreObjectIdentifier.Table(table,entity.GetSchema());
            if(entity.FindProperty("Prueba") is {} prueba)
                Agregar("sinteticos-"+table,"Todos los registros de "+table+" son de prueba",
                    await Contar($"SELECT COUNT(*) AS [Value] FROM {Q(table)} WHERE {Q(prueba.GetColumnName(store)!)} = 0",ct));
            foreach(var fk in entity.GetForeignKeys())
            {
                var parent=fk.PrincipalEntityType; var parentTable=parent.GetTableName()!;
                var parentStore=StoreObjectIdentifier.Table(parentTable,parent.GetSchema());
                var conditions=fk.Properties.Select((p,i)=>$"h.{Q(p.GetColumnName(store)!)} = p.{Q(fk.PrincipalKey.Properties[i].GetColumnName(parentStore)!)}");
                var required=string.Join(" AND ",fk.Properties.Select(p=>$"h.{Q(p.GetColumnName(store)!)} IS NOT NULL"));
                var sql=$"SELECT COUNT(*) AS [Value] FROM {Q(table)} h WHERE {required} AND NOT EXISTS (SELECT 1 FROM {Q(parentTable)} p WHERE {string.Join(" AND ",conditions)})";
                Agregar("referencia-"+table+"-"+string.Join("-",fk.Properties.Select(p=>p.Name)),"Referencias existentes a "+parentTable,await Contar(sql,ct));
            }
        }
        foreach(var (codigo,descripcion,sql) in Reglas)
            Agregar(codigo,descripcion,await Contar(sql,ct));
        await tx.CommitAsync(ct);
        return new(DemoDatabase.Name,checks.All(c=>c.Incumplimientos==0),DateTimeOffset.UtcNow,counts,checks);
    }
    Task<int> Contar(string sql,CancellationToken ct)=>db.Database.SqlQueryRaw<int>(sql).SingleAsync(ct);

    static readonly (string Codigo,string Descripcion,string Sql)[] Reglas=
    [
        ("roles","Solo administrador y operador", "SELECT COUNT(*) AS [Value] FROM Rol WHERE Nombre NOT IN ('administrador','operador')"),
        ("configuracion-plan","La configuración del plan pertenece a su intersección", "SELECT COUNT(*) AS [Value] FROM [Plan] p JOIN ConfigTecnica c ON c.Id=p.ConfigTecnicaId WHERE p.InterseccionId<>c.InterseccionId"),
        ("fase-interseccion","Cada fase habilita accesos de su intersección", "SELECT COUNT(*) AS [Value] FROM Fase f JOIN [Plan] p ON p.Id=f.PlanId JOIN Acceso a ON a.Id=f.AccesoId WHERE p.InterseccionId<>a.InterseccionId"),
        ("fase-acceso","Los accesos asociados pertenecen a la intersección del plan", "SELECT COUNT(*) AS [Value] FROM FaseAcceso fa JOIN Fase f ON f.Id=fa.FaseId JOIN [Plan] p ON p.Id=f.PlanId JOIN Acceso a ON a.Id=fa.AccesoId WHERE p.InterseccionId<>a.InterseccionId"),
        ("fase-principal","La relación principal de cada fase está presente", "SELECT COUNT(*) AS [Value] FROM Fase f WHERE NOT EXISTS (SELECT 1 FROM FaseAcceso fa WHERE fa.FaseId=f.Id AND fa.AccesoId=f.AccesoId)"),
        ("peatones","Las fases cumplen L/0.9+5 segundos sin exceder el verde", "SELECT COUNT(*) AS [Value] FROM Fase f JOIN FaseAcceso fa ON fa.FaseId=f.Id JOIN Acceso a ON a.Id=fa.AccesoId WHERE f.TiempoPeatonalSegundos<a.LongitudCrucePeatonalMetros/0.9+5 OR f.TiempoPeatonalSegundos>f.VerdeSegundos"),
        ("cobertura","Los planes evaluados cubren todos los accesos", "SELECT COUNT(*) AS [Value] FROM ValidacionSumo v JOIN [Plan] p ON p.Id=v.PlanId JOIN Acceso a ON a.InterseccionId=p.InterseccionId WHERE v.Resultado='aprobada' AND NOT EXISTS (SELECT 1 FROM Fase f JOIN FaseAcceso fa ON fa.FaseId=f.Id WHERE f.PlanId=p.Id AND fa.AccesoId=a.Id)"),
        ("estado-control","El estado conserva controlador, plan y fase compatibles", "SELECT COUNT(*) AS [Value] FROM EstadoControl e JOIN ControladorLocal c ON c.Id=e.ControladorLocalId JOIN [Plan] p ON p.Id=e.PlanId JOIN Fase f ON f.Id=e.FaseId WHERE c.InterseccionId<>p.InterseccionId OR f.PlanId<>p.Id"),
        ("medicion-fuente","La medición usa una cámara de su acceso", "SELECT COUNT(*) AS [Value] FROM Medicion m JOIN Carril c ON c.Id=m.CarrilId JOIN FuenteDeteccion f ON f.Id=m.FuenteDeteccionId WHERE c.AccesoId<>f.AccesoId"),
        ("evento-plan","La prioridad pertenece a la intersección del plan", "SELECT COUNT(*) AS [Value] FROM EventoPrioridad e JOIN [Plan] p ON p.Id=e.PlanId WHERE e.InterseccionId<>p.InterseccionId"),
        ("validacion-mediciones","Las mediciones de la validación corresponden a su intersección", "SELECT COUNT(*) AS [Value] FROM ValidacionMedicion vm JOIN ValidacionSumo v ON v.Id=vm.ValidacionSumoId JOIN [Plan] p ON p.Id=v.PlanId JOIN Medicion m ON m.Id=vm.MedicionId JOIN Carril c ON c.Id=m.CarrilId JOIN Acceso a ON a.Id=c.AccesoId WHERE a.InterseccionId<>p.InterseccionId"),
        ("validacion-eventos","Los eventos de la validación corresponden al plan", "SELECT COUNT(*) AS [Value] FROM ValidacionEvento ve JOIN ValidacionSumo v ON v.Id=ve.ValidacionSumoId JOIN EventoPrioridad e ON e.Id=ve.EventoPrioridadId WHERE v.PlanId<>e.PlanId"),
        ("validacion-peatonal","Las validaciones aprobadas respetan los mínimos peatonales", "SELECT COUNT(*) AS [Value] FROM ValidacionSumo WHERE Resultado='aprobada' AND (CumpleMinimoPeatonal=0 OR CumpleDespejePeatonal=0 OR DemoraGlobalCandidataSegundos>DemoraGlobalBaseSegundos*1.15)"),
        ("metricas-grupos","Cada acceso validado tiene total, micro y resto coherentes", "SELECT COUNT(*) AS [Value] FROM ValidacionSumo v JOIN [Plan] p ON p.Id=v.PlanId JOIN Acceso a ON a.InterseccionId=p.InterseccionId WHERE v.Resultado='aprobada' AND (3<>(SELECT COUNT(*) FROM MetricaPorAcceso m WHERE m.ValidacionSumoId=v.Id AND m.AccesoId=a.Id AND m.Grupo IN ('total','micro','resto')) OR COALESCE((SELECT SUM(CASE WHEN m.Grupo='total' THEN m.VehiculosBase ELSE -m.VehiculosBase END) FROM MetricaPorAcceso m WHERE m.ValidacionSumoId=v.Id AND m.AccesoId=a.Id),1)<>0 OR COALESCE((SELECT SUM(CASE WHEN m.Grupo='total' THEN m.VehiculosCandidatos ELSE -m.VehiculosCandidatos END) FROM MetricaPorAcceso m WHERE m.ValidacionSumoId=v.Id AND m.AccesoId=a.Id),1)<>0)"),
        ("metricas-demora","Ningún acceso aprobado empeora más del 15 %", "SELECT COUNT(*) AS [Value] FROM MetricaPorAcceso m JOIN ValidacionSumo v ON v.Id=m.ValidacionSumoId WHERE v.Resultado='aprobada' AND m.DemoraCandidataSegundos>m.DemoraBaseSegundos*1.15"),
        ("metricas-interseccion","Las métricas pertenecen al plan evaluado", "SELECT COUNT(*) AS [Value] FROM MetricaPorAcceso m JOIN ValidacionSumo v ON v.Id=m.ValidacionSumoId JOIN [Plan] p ON p.Id=v.PlanId JOIN Acceso a ON a.Id=m.AccesoId WHERE a.InterseccionId<>p.InterseccionId"),
        ("recomendaciones","Cada recomendación tiene validación aprobada", "SELECT COUNT(*) AS [Value] FROM Recomendacion r JOIN ValidacionSumo v ON v.Id=r.ValidacionSumoId WHERE v.Resultado<>'aprobada'"),
        ("modelos-futuros","Los modelos de demostración permanecen como función futura", "SELECT COUNT(*) AS [Value] FROM VersionModelo WHERE Estado<>'futuro' OR ActivadaUtc IS NOT NULL"),
        ("reportes-futuros","Los reportes son metadatos de función futura", "SELECT COUNT(*) AS [Value] FROM Reporte WHERE Estado<>'futuro'")
    ];
}
