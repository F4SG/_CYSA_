using System.Security.Cryptography;
using System.Text.Json;

namespace Cysa.Launcher;

internal static class SystemStartupTest
{
    public static async Task Run(string root,string package,string report)
    {
        var instance=new Instance(root,package);
        instance.Log=Console.WriteLine;
        var secrets=SHA256.HashData(File.ReadAllBytes(Path.Combine(instance.Repo,"infra/.env")));
        try
        {
            instance.Seed();
            await instance.StartAll();
            await instance.Verify();
            var first=instance.RunningServices();
            foreach(var name in new[]{"Cysa.Web.Api","Operacion S2","Controlador S2"})
                if(!first.ContainsKey(name))throw new Exception("Servicio no iniciado: "+name);
            using var client=new HttpClient();
            foreach(var url in new[]{instance.WebUrl+"/demo",instance.OperationUrl+"/",instance.PanelUrl})
            {
                using var response=await client.GetAsync(url);
                response.EnsureSuccessStatusCode();
            }
            using var config=JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(instance.Repo,"panel/config.json")));
            if(config.RootElement.GetProperty("webApiBase").GetString()!=instance.WebUrl || config.RootElement.GetProperty("operacionBase").GetString()!=instance.OperationUrl)
                throw new Exception("Los botones no apuntan a los servicios iniciados");
            await instance.StartAll();
            var second=instance.RunningServices();
            if(first.Count!=second.Count || first.Any(p=>!second.TryGetValue(p.Key,out var id) || id!=p.Value))
                throw new Exception("El segundo arranque duplicó procesos");
            if(!secrets.SequenceEqual(SHA256.HashData(File.ReadAllBytes(Path.Combine(instance.Repo,"infra/.env")))))
                throw new Exception("Cambió la configuración privada");
            await instance.StopAll();
            if(instance.RunningServices().Count!=0 || !Instance.IsFree(instance.Ports.Web) || !Instance.IsFree(instance.Ports.Operation))
                throw new Exception("No se cerraron los servicios propios");
            await File.WriteAllTextAsync(report,"PASS: arranque completo, enlaces correctos, segundo arranque sin duplicados, configuración privada conservada y cierre conjunto sin procesos propios restantes.");
        }
        catch(Exception error){await File.WriteAllTextAsync(report,"FAIL: "+error);Environment.ExitCode=1;}
        finally{await instance.StopAll();}
    }
}
