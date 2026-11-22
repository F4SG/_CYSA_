using System.Text.Json;

namespace Cysa.Launcher;

internal sealed partial class Instance
{
    string SqlSettingsPath=>Path.Combine(Root,"webiii-sql.json");
    public bool SqlConnectionExterna=>!string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable("CYSA_WEBIII_CONNECTION"));
    public string SqlServerActual()
    {
        if(!File.Exists(SqlSettingsPath))return "localhost";
        try{return SqlServerOptions.Validar(JsonSerializer.Deserialize<SqlServerOptions>(File.ReadAllText(SqlSettingsPath))?.Instancia??"");}
        catch(JsonException){throw new InvalidOperationException("La configuración webiii-sql.json no es válida. Revisa el archivo de esta instalación.");}
    }
    public async Task ProbarSqlServer(string instancia)
    {
        var exe=await EnsureWebExecutable();var env=WebEnvironment();
        env["ConnectionStrings__Cysa"]=new SqlServerOptions(SqlServerOptions.Validar(instancia)).Cadena();
        Write("Probando SQL Server local con autenticación de Windows. No se aplican migraciones.");
        await Run(exe,["--probar-conexion"],Path.GetDirectoryName(exe),env,timeoutMinutes:1);
    }
    public async Task GuardarSqlServer(string instancia)
    {
        if(SqlConnectionExterna)throw new InvalidOperationException("CYSA_WEBIII_CONNECTION tiene prioridad sobre la configuración local.");
        var options=new SqlServerOptions(SqlServerOptions.Validar(instancia));
        await StopWebIII();
        if(!IsFree(Ports.Web))throw new InvalidOperationException("Otro proceso usa el puerto Web III. Detén esa instancia antes de cambiar la conexión.");
        var temporary=SqlSettingsPath+".tmp";
        await File.WriteAllTextAsync(temporary,JsonSerializer.Serialize(options));File.Move(temporary,SqlSettingsPath,true);
        Write("Configuración local SQL Server guardada. Abre Swagger (Web III) o Panel Web III para iniciar la API.");
    }
    internal async Task StopWebIII()
    {
        if(apis.TryGetValue("Cysa.Web.Api",out var process))
        {
            if(!process.HasExited){process.Kill(true);await process.WaitForExitAsync();}
            process.Dispose();apis.Remove("Cysa.Web.Api");
        }
    }
    internal Task<string> EnsureWebExecutable() => EnsureApiExecutable("Cysa.Web.Api");

    async Task<string> EnsureApiExecutable(string service)
    {
        var exe=Path.Combine(Package,"services",service,service+".exe");
        if(File.Exists(exe))return exe;
        var source=SourceRoot??throw new InvalidOperationException($"No se encontró {service}. Extrae el ZIP Windows completo, incluidas app y services, o utiliza el ZIP de fuentes.");
        var project=Path.Combine(source,"dotnet","src",service,service+".csproj");
        if(!File.Exists(project))
            throw new InvalidOperationException($"Faltan las fuentes de {service}. Comprueba que el árbol de fuentes esté completo.");
        var web=service=="Cysa.Web.Api";
        var cache=web ? Path.Combine(Root,"webiii-services") : Path.Combine(Root,"api-services",service);
        var output=Path.Combine(cache,SourceLayout.WebFingerprint(source));
        exe=Path.Combine(output,service+".exe");
        var ready=Path.Combine(output,"preparado.txt");
        bool Published() => File.Exists(exe) && (!web || File.Exists(Path.Combine(output,"wwwroot","demo.html")));
        if(Published() && File.Exists(ready))return exe;
        // Si hay que reparar una publicación incompleta, el marcador solo vuelve tras el éxito.
        if(File.Exists(ready))File.Delete(ready);
        var label=web ? "API Web III" : service;
        Write($"Ejecución desde fuentes detectada. Preparando automáticamente la {label} con el SDK .NET.");
        try
        {
            if(await Run("dotnet",["--version"],source,check:false,output:false,timeoutMinutes:1)!=0)
                throw new InvalidOperationException("Para ejecutar desde Visual Studio o las fuentes necesitas el SDK .NET 10. El ZIP Windows completo funciona sin instalar el SDK.");
        }
        catch(System.ComponentModel.Win32Exception)
        {throw new InvalidOperationException("No se encontró el SDK .NET. Instala el SDK .NET 10 para ejecutar las fuentes o utiliza el ZIP Windows completo.");}
        Directory.CreateDirectory(output);
        await Run("dotnet",["publish",project,
            "-c","Release","-r","win-x64","--self-contained","true","-p:PublishSingleFile=true","-p:IncludeNativeLibrariesForSelfExtract=true","--disable-build-servers","-o",output,"--nologo"],source,timeoutMinutes:10);
        if(!Published())throw new InvalidOperationException($"No se completó la preparación de {label}. Revisa el registro de compilación.");
        await File.WriteAllTextAsync(ready,service+" preparada desde las fuentes.");
        Write($"{label} preparada. Los siguientes arranques reutilizan esta versión mientras no cambien sus fuentes.");
        return exe;
    }
    public string WebUrl => $"http://localhost:{Ports.Web}";
    Dictionary<string,string> WebEnvironment() => new()
    {
        ["ASPNETCORE_ENVIRONMENT"]="Development", ["Security__Mode"]="Demo", ["Demo__Enabled"]="true",
        ["Storage__Directory"]=Path.Combine(Root,"webiii-runtime"),
        ["Security__ProjectAuthority"]=IdentityUrl+"/realms/cysa",
        ["Security__ProjectSource"]=Repo,
        ["Security__PanelUrl"]=PanelUrl+"/",
        ["Evaluaciones__BaseUrl"]=WebUrl,
        ["ConnectionStrings__Cysa"]=SqlConnectionExterna ? Environment.GetEnvironmentVariable("CYSA_WEBIII_CONNECTION")! : new SqlServerOptions(SqlServerActual()).Cadena(),
        ["Logging__LogLevel__Default"]="Warning"
    };
    public async Task StartWebIII()
    {
        const string name="Cysa.Web.Api";
        if(apis.TryGetValue(name,out var process) && !process.HasExited)return;
        if(!IsFree(Ports.Web))throw new InvalidOperationException("El puerto de Web III está ocupado. Cierra la otra instancia o revisa puertos.json.");
        var exe=await EnsureWebExecutable();
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
