using System.Security.Cryptography;
using System.Text.Json;

namespace Cysa.Core;

public sealed class EvaluadorPlanes(TimeProvider reloj)
{
    // Las fronteras se comparan sin redondear: exactamente 15 % está permitido.
    public ResultadoEvaluacion Evaluar(SolicitudEvaluacion plan, string usuario)
    {
        var motivos = new List<string>();
        var metricas = plan.Accesos.Select(a => new MetricaAcceso(a.Id,
            (a.DemoraCandidataSegundos - a.DemoraBaseSegundos) / a.DemoraBaseSegundos * 100m,
            a.LongitudCruceMetros / 0.9m + 5m)).ToList();
        foreach (var acceso in metricas.Where(a => a.VariacionPorcentaje > 15m))
            motivos.Add($"El acceso {acceso.AccesoId} supera el aumento máximo de demora del 15 %.");
        foreach (var fase in plan.Fases)
        {
            var minimo = metricas.Where(a => fase.Accesos.Contains(a.AccesoId)).Max(a => a.MinimoPeatonalSegundos);
            if (fase.TiempoPeatonalSegundos < minimo)
                motivos.Add($"La fase {fase.Id} no cubre el mínimo peatonal de todos sus accesos.");
        }
        var ahora = reloj.GetUtcNow();
        var huella = Convert.ToHexString(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(plan)));
        return new(Guid.NewGuid(), plan, huella, motivos.Count == 0, motivos, metricas,
            ahora, ahora.AddHours(24), usuario);
    }
}
