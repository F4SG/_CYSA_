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
            foreach(var name in new[]{"Cysa.Evaluaciones.Api","Cysa.Decisiones.Api","Cysa.Web.Api","Operacion S2","Controlador S2"})
                if(!first.ContainsKey(name))throw new Exception("Servicio no iniciado: "+name);
            using var client=new HttpClient(new HttpClientHandler{AllowAutoRedirect=false});
            var panel=await client.GetStringAsync(instance.PanelUrl);
            if(!panel.Contains("data-tab=\"configuraciones\"") || !panel.Contains("data-tab=\"planes\"") || panel.Contains("Swagger (Web III)"))
                throw new Exception("El panel de Proyecto de Sistemas no integra sus módulos.");
            if(!(await client.GetStringAsync(instance.WebUrl+"/demo")).Contains("Laboratorio Web III"))
                throw new Exception("Falta la interfaz separada de Web III.");
            foreach(var (url,module) in new[]{(instance.WebUrl+"/proyecto","configuraciones"),(instance.OperationUrl+"/","planes")})
            {
                using var response=await client.GetAsync(url);
                if((int)response.StatusCode is <300 or >=400 || response.Headers.Location?.AbsoluteUri!=instance.PanelUrl+"/?modulo="+module+"&volver=1")
                    throw new Exception("La entrada anterior no dirige a su módulo del panel: "+url);
            }
            using var config=JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(instance.Repo,"panel/config.json")));
            if(config.RootElement.GetProperty("webApiBase").GetString()!=instance.WebUrl || config.RootElement.GetProperty("operacionBase").GetString()!=instance.OperationUrl)
                throw new Exception("Los botones no apuntan a los servicios iniciados");
            foreach(var (url,method) in new[]{(instance.WebUrl+"/api/proyecto/configuraciones","POST"),(instance.OperationUrl+"/api/operacion/planes","GET")})
            {
                using var request=new HttpRequestMessage(HttpMethod.Options,url);
                request.Headers.Add("Origin",instance.PanelUrl);
                request.Headers.Add("Access-Control-Request-Method",method);
                request.Headers.Add("Access-Control-Request-Headers","authorization");
                using var response=await client.SendAsync(request);
                if(!response.IsSuccessStatusCode || !response.Headers.TryGetValues("Access-Control-Allow-Origin",out var origins)
                    || !origins.Contains(instance.PanelUrl))
                    throw new Exception("El navegador no puede acceder al módulo desde el panel: "+url);
            }
            using var swagger=await client.GetAsync(instance.WebUrl+"/swagger/index.html");
            swagger.EnsureSuccessStatusCode();
            await instance.StartAll();
            var second=instance.RunningServices();
            if(first.Count!=second.Count || first.Any(p=>!second.TryGetValue(p.Key,out var id) || id!=p.Value))
                throw new Exception("El segundo arranque duplicó procesos");
            if(!secrets.SequenceEqual(SHA256.HashData(File.ReadAllBytes(Path.Combine(instance.Repo,"infra/.env")))))
                throw new Exception("Cambió la configuración privada");
            await instance.StopAll();
            if(instance.RunningServices().Count!=0 || new[]{instance.Ports.Evaluation,instance.Ports.Decision,instance.Ports.Web,instance.Ports.Operation}
                    .Any(port=>!Instance.IsFree(port)))
                throw new Exception("No se cerraron los servicios propios");
            await File.WriteAllTextAsync(report,"PASS: arranque completo, enlaces correctos, segundo arranque sin duplicados, configuración privada conservada y cierre conjunto sin procesos propios restantes.");
        }
        catch(Exception error){await File.WriteAllTextAsync(report,"FAIL: "+error);Environment.ExitCode=1;}
        finally{await instance.StopAll();}
    }
}
