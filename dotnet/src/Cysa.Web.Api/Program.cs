using System.Security.Cryptography;
using Cysa.Core;
using Cysa.Infrastructure;
using Cysa.Web.Api.Data;
using Cysa.Web.Api.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.OpenApi;

namespace Cysa.Web.Api;

public partial class Program
{
    public static async Task Main(string[] args)
    {
        var prepare=args.Contains("--preparar-demo"); var reset=args.Contains("--recrear-demo"); var verify=args.Contains("--verificar-demo");
        if(verify&&(prepare||reset))throw new ArgumentException("La verificación no se combina con preparación o recreación.");
        var builder=WebApplication.CreateBuilder(args.Where(a=>a is not ("--preparar-demo" or "--recrear-demo" or "--verificar-demo")).ToArray());
        if(prepare || reset || verify)
        {
            builder.Configuration["Demo:Enabled"]="true";
            builder.Configuration["Security:Mode"]="Demo";
        }
        if(builder.Configuration["Security:Mode"]=="Demo")
        {
            var runtime=ApiSetup.RuntimePath(builder.Configuration); Directory.CreateDirectory(runtime);
            var key=Path.Combine(runtime,"demo.key");
            if(!File.Exists(key))await File.WriteAllTextAsync(key,Convert.ToBase64String(RandomNumberGenerator.GetBytes(32)));
        }
        builder.AddCysaApi("CYSA · Web API · Web III", "API modular con SQL Server. Datos sintéticos de demostración, sin cámara ni SUMO. Los recursos futuros solo exponen metadatos. Acceso de laboratorio y migraciones en /demo. Los registros históricos no admiten edición ni eliminación.");
        builder.Services.AddControllers()
            .AddApplicationPart(typeof(Cysa.Evaluaciones.Api.Controllers.EvaluacionesController).Assembly)
            .AddApplicationPart(typeof(Cysa.Decisiones.Api.Controllers.DecisionesController).Assembly);
        builder.Services.AddSwaggerGen(o=>
        {
            o.CustomOperationIds(a=>(a.RelativePath??"root").Replace("/","_").Replace("{","").Replace("}","")+"_"+a.HttpMethod);
        });
        builder.Services.AddHttpContextAccessor();
        builder.Services.AddSingleton<SemaphoreSlim>(_=>new(1,1));
        builder.Services.AddDbContext<CysaDb>(o=>o.UseSqlServer(builder.Configuration.GetConnectionString("Cysa")));
        builder.Services.AddDbContext<EvaluacionesDb>(o=>o.UseSqlServer(builder.Configuration.GetConnectionString("Cysa")));
        builder.Services.AddDbContext<DecisionesDb>(o=>o.UseSqlServer(builder.Configuration.GetConnectionString("Cysa")));
        builder.Services.AddScoped<DemoDatabase>(); builder.Services.AddScoped<DemoVerifier>(); builder.Services.AddScoped<ReglasDominio>();
        builder.Services.AddScoped(typeof(RecursoService<,,>)); builder.Services.AddScoped<EvaluadorPlanes>();
        // Las decisiones leen la evaluación del mismo host por HTTP; no adquieren dos veces el bloqueo de datos.
        builder.Services.AddHttpClient("evaluaciones",c=>
        {
            c.BaseAddress=new Uri(builder.Configuration["Evaluaciones:BaseUrl"]??"http://localhost:5183");
            c.Timeout=TimeSpan.FromSeconds(10);
        }).ConfigurePrimaryHttpMessageHandler(()=>new HttpClientHandler{AllowAutoRedirect=false});
        builder.Services.AddAuthorization(o=>o.AddPolicy("Escribir",p=>p.RequireAuthenticatedUser().RequireRole("administrador")
            .RequireAssertion(c=>ApiSetup.MfaReciente(c.User,DateTimeOffset.UtcNow))));
        var app=builder.Build();
        if(verify)
        {
            await using var scope=app.Services.CreateAsyncScope();
            var result=await scope.ServiceProvider.GetRequiredService<DemoVerifier>().Verificar();
            Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(result)); Environment.ExitCode=result.Cumple?0:1; return;
        }
        if(prepare || reset)
        {
            await using var scope=app.Services.CreateAsyncScope();
            var demo=scope.ServiceProvider.GetRequiredService<DemoDatabase>(); await demo.Preparar(reset);
            Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(await demo.Conteos())); return;
        }
        app.UseExceptionHandler();
        app.Use(async(context,next)=>
        {
            // El reinicio espera operaciones activas. Las lecturas internas de evaluaciones no entran al semáforo.
            var gated=context.Request.Path.StartsWithSegments("/api") && !(context.Request.Method=="GET" && context.Request.Path.StartsWithSegments("/api/evaluaciones"));
            var gate=context.RequestServices.GetRequiredService<SemaphoreSlim>();
            if(gated)await gate.WaitAsync(context.RequestAborted);
            try{await next(context);}
            catch(ReglaException e){await Results.Problem(statusCode:e.Status,title:e.Message).ExecuteAsync(context);}
            catch(DbUpdateException e) when(e.InnerException is SqlException {Number:2601 or 2627 or 547})
            {await Results.Problem(statusCode:context.Request.Method=="DELETE"?409:400,title:"La operación viola una referencia, una restricción o un valor único. No se guardaron los cambios.").ExecuteAsync(context);}
            catch(SqlException){await Results.Problem(statusCode:503,title:"SQL Server no está disponible o la base no está preparada. Revise la conexión y las migraciones.").ExecuteAsync(context);}
            finally{if(gated)gate.Release();}
        });
        app.UseStaticFiles();
        if(app.Environment.IsDevelopment())app.UseSwaggerUI(o=>o.InjectJavascript("/swagger-demo.js"));
        app.UseCysaApi(manejarErrores:false);
        app.MapGet("/",()=>Results.Redirect("/demo"));
        app.MapGet("/demo",()=>Results.File(Path.Combine(app.Environment.WebRootPath,"demo.html"),"text/html"));
        await app.RunAsync();
    }
}
