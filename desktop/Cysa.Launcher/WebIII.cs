using System.Text.Json;

namespace Cysa.Launcher;

internal sealed partial class Instance
{
    public string WebUrl => $"http://localhost:{Ports.Web}";
    Dictionary<string,string> WebEnvironment() => new()
    {
        ["ASPNETCORE_ENVIRONMENT"]="Development", ["Security__Mode"]="Demo", ["Demo__Enabled"]="true",
        ["Storage__Directory"]=Path.Combine(Root,"webiii-runtime"),
        ["Evaluaciones__BaseUrl"]=WebUrl,
        ["ConnectionStrings__Cysa"]=Environment.GetEnvironmentVariable("CYSA_WEBIII_CONNECTION") ??
            "Server=localhost;Database=CYSA_WebIII_Demo;Integrated Security=True;TrustServerCertificate=True;Connect Timeout=10",
        ["Logging__LogLevel__Default"]="Warning"
    };
    public async Task StartWebIII()
    {
        const string name="Cysa.Web.Api";
        if(apis.TryGetValue(name,out var process) && !process.HasExited)return;
        if(!IsFree(Ports.Web))throw new InvalidOperationException("El puerto de Web III está ocupado. Cierra la otra instancia o revisa puertos.json.");
        var exe=Path.Combine(Package,"services",name,name+".exe");
        if(!File.Exists(exe))throw new InvalidOperationException("Falta el servicio Web III. Extrae el paquete actualizado completo.");
        var env=WebEnvironment();
        Write("Preparando SQL Server: CYSA_WebIII_Demo. El arranque conserva los datos existentes.");
        // No configura Docker, cámara, Python, YOLO, SUMO ni cuentas del sistema principal.
        await Run(exe,["--preparar-demo"],Path.GetDirectoryName(exe),env,timeoutMinutes:5);
        apis[name]=Start(exe,["--urls",WebUrl],Path.GetDirectoryName(exe),env);
        await WaitUrl(WebUrl+"/health",60);
        var panelConfig=Path.Combine(Repo,"panel","config.json");
        if(File.Exists(panelConfig))
        {
            var data=JsonSerializer.Deserialize<Dictionary<string,JsonElement>>(File.ReadAllText(panelConfig))!;
            data["webApiBase"]=JsonSerializer.SerializeToElement(WebUrl);
            File.WriteAllText(panelConfig,JsonSerializer.Serialize(data));
        }
        Write("Web III listo: SQL Server y API independientes. Cámara y simulación no son necesarias.");
    }
    public async Task OpenSwaggerWebIII(){await StartWebIII();Open(WebUrl+"/swagger");}
    public async Task OpenDatabaseWebIII(){await StartWebIII();Open(WebUrl+"/demo");}
    public async Task ResetDatabaseWebIII()
    {
        await StartWebIII();
        using var access=await http.GetAsync(WebUrl+"/api/demo/acceso/administrador"); access.EnsureSuccessStatusCode();
        using var json=JsonDocument.Parse(await access.Content.ReadAsStringAsync());
        using var request=new HttpRequestMessage(HttpMethod.Post,WebUrl+"/api/demo/base");
        request.Headers.Authorization=new("Bearer",json.RootElement.GetProperty("token").GetString());
        request.Headers.Add("X-CYSA-Confirmar","CYSA_WebIII_Demo");
        using var setup=new HttpClient{Timeout=TimeSpan.FromMinutes(5)};
        using var result=await setup.SendAsync(request);
        if(!result.IsSuccessStatusCode)throw new InvalidOperationException("No se pudo recrear la base de demostración. Revisa el panel Web III y la conexión SQL Server.");
        Write("CYSA_WebIII_Demo recreada: migraciones y semilla cargadas. Dos roles y al menos 15 registros por las demás tablas.");
        Open(WebUrl+"/demo");
    }
}
