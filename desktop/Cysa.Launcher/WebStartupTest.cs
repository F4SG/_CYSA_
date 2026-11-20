using System.Text.Json;

namespace Cysa.Launcher;

internal static class WebStartupTest
{
    public static async Task Run(string root,string package,string report)
    {
        var instance=new Instance(root,package);
        var messages=new List<string>();instance.Log=message=>{lock(messages)messages.Add(message);};
        var packaged=File.Exists(Path.Combine(package,"services","Cysa.Web.Api","Cysa.Web.Api.exe"));
        if(!packaged&&instance.SourceRoot is null)throw new Exception("No se detectó el repositorio desde el directorio de compilación.");
        try
        {
            instance.Seed();
            if(!File.Exists(Path.Combine(instance.Repo,"infra","compose.yaml")))throw new Exception("No se prepararon las fuentes de la aplicación.");
            if(Directory.Exists(Path.Combine(instance.Repo,".git"))||Directory.Exists(Path.Combine(instance.Repo,"dotnet","runtime")))throw new Exception("Se copiaron datos privados o de ejecución.");
            var executable=await instance.EnsureWebExecutable();var modified=File.GetLastWriteTimeUtc(executable);
            var again=await instance.EnsureWebExecutable();
            if(executable!=again||File.GetLastWriteTimeUtc(again)!=modified)throw new Exception("La versión compilada no se reutilizó.");
            await instance.StartWebIII();
            using var client=new HttpClient();
            using var swagger=await client.GetAsync(instance.WebUrl+"/swagger/index.html");swagger.EnsureSuccessStatusCode();
            if(!(await swagger.Content.ReadAsStringAsync()).Contains("Swagger UI"))throw new Exception("Swagger no cargó.");
            using var schema=await client.GetAsync(instance.WebUrl+"/swagger/v1/swagger.json");schema.EnsureSuccessStatusCode();
            using var model=JsonDocument.Parse(await schema.Content.ReadAsStringAsync());
            if(!model.RootElement.GetProperty("paths").TryGetProperty("/api/intersecciones",out _))throw new Exception("Faltan los endpoints.");
            using var access=await client.GetAsync(instance.WebUrl+"/api/demo/acceso/administrador");access.EnsureSuccessStatusCode();
            using var token=JsonDocument.Parse(await access.Content.ReadAsStringAsync());
            client.DefaultRequestHeaders.Authorization=new("Bearer",token.RootElement.GetProperty("token").GetString());
            using var response=await client.GetAsync(instance.WebUrl+"/api/demo/base");response.EnsureSuccessStatusCode();
            using var database=JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            if(!database.RootElement.GetProperty("preparada").GetBoolean())throw new Exception("No se aplicaron las migraciones.");
            foreach(var table in database.RootElement.GetProperty("tablas").EnumerateObject())
                if(table.Name=="Rol"?table.Value.GetInt32()!=2:table.Value.GetInt32()<15)throw new Exception("Datos de prueba incompletos.");
            var compilations=messages.Count(m=>m.Contains("Preparando automáticamente la API"));
            if(compilations!=(packaged?0:1))throw new Exception("Número inesperado de preparaciones de la API.");
            await File.WriteAllTextAsync(report,JsonSerializer.Serialize(new{resultado="PASS",fuentesDetectadas=instance.SourceRoot is not null,
                copiaSinEstadoPrivado=true,compilacionAutomatica=!packaged,cacheReutilizada=true,swagger=200,
                migracionesYSemilla=true,serviciosIncluidos=packaged}));
        }
        finally{await instance.StopWebIII();}
    }
}
