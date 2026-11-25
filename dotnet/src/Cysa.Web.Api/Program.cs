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
        var prepare=args.Contains("--preparar-demo"); var reset=args.Contains("--recrear-demo"); var verify=args.Contains("--verificar-demo"); var probe=args.Contains("--probar-conexion");
        var practice = args.Contains("--preparar-practica");
        var projectSchema = args.Contains("--preparar-proyecto-esquema");
        var clearProject = args.Contains("--vaciar-proyecto");
        if(new[]{prepare,reset,verify,probe,practice,projectSchema,clearProject}.Count(a=>a)>1)throw new ArgumentException("Usa solo una operación de preparación, recreación, verificación o prueba de conexión.");
        var builder=WebApplication.CreateBuilder(args.Where(a=>a is not ("--preparar-demo" or "--recrear-demo" or "--verificar-demo" or "--probar-conexion" or "--preparar-practica" or "--preparar-proyecto-esquema" or "--vaciar-proyecto")).ToArray());
        var projectSettings = builder.Configuration.GetConnectionString("Proyecto");
        var projectConnection = string.IsNullOrWhiteSpace(projectSettings) ? null : ProyectoDatabase.ConnectionString(projectSettings);
        if (projectSchema || clearProject || (practice && projectConnection is not null))
        {
            if (!builder.Environment.IsDevelopment() || projectConnection is null)
                throw new InvalidOperationException("El mantenimiento de Proyecto de Sistemas requiere la base local CYSA_Proyecto.");
            await ProyectoDatabase.Prepare(projectConnection, clearProject, practice);
            Console.WriteLine(clearProject ? "Base de Proyecto de Sistemas vacía." : "Base de Proyecto de Sistemas preparada.");
            return;
        }
        if(prepare || reset || verify || probe || practice)
        {
            builder.Configuration["Demo:Enabled"]="true";
            builder.Configuration["Security:Mode"]="Demo";
        }
        if(probe)
        {
            // No se inicia HTTP, se generan credenciales ni se aplican migraciones.
            try
            {
                await using var db=new CysaDb(new DbContextOptionsBuilder<CysaDb>().UseSqlServer(builder.Configuration.GetConnectionString("Cysa")).Options);
                var result=await new DemoDatabase(db,builder.Configuration,builder.Environment).ProbarConexion();
                Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(result));
            }
            catch(Exception e) when(e is SqlException or InvalidOperationException or ArgumentException or OperationCanceledException)
            {
                Console.WriteLine(System.Text.Json.JsonSerializer.Serialize(new{Conectada=false,Error="No se pudo conectar a la instancia local de demostración. Revisa entorno Development, instancia, servicio y permisos SQL Server."}));
                Environment.ExitCode=1;
            }
            return;
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
        var panelUrl = builder.Configuration["Security:PanelUrl"];
        var panelOrigin = Uri.TryCreate(panelUrl, UriKind.Absolute, out var panelUri)
            && panelUri.IsLoopback && panelUri.Scheme is "http" or "https" && string.IsNullOrEmpty(panelUri.UserInfo)
            ? panelUri.GetLeftPart(UriPartial.Authority) : null;
        builder.Services.AddCors(options => options.AddPolicy("PanelProyecto", policy =>
        {
            if (panelOrigin is not null)
                policy.WithOrigins(panelOrigin).WithMethods("GET", "POST", "PUT", "DELETE")
                    .WithHeaders("Authorization", "Content-Type", "X-CYSA-Motivo");
        }));
        builder.Services.AddSingleton<SemaphoreSlim>(_=>new(1,1));
        var webConnection = builder.Configuration.GetConnectionString("Cysa");
        builder.Services.AddDbContext<CysaDb>((services, options) =>
        {
            var request = services.GetRequiredService<IHttpContextAccessor>().HttpContext?.Request;
            var esProyecto = request?.Path.StartsWithSegments("/api/proyecto") == true;
            options.UseSqlServer(esProyecto && projectConnection is not null ? projectConnection : webConnection);
        });
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
        if (practice)
        {
            await using var scope = app.Services.CreateAsyncScope();
            await scope.ServiceProvider.GetRequiredService<DemoDatabase>().PrepararPractica();
            Console.WriteLine("Configuración y carriles de práctica disponibles para DEMO_INT_01.");
            return;
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
        app.Use(async(context,next)=>{context.Response.Headers.CacheControl="no-store";await next();});
        app.UseStaticFiles();
        app.UseCors();
        if(app.Environment.IsDevelopment())app.UseSwaggerUI(o=>o.InjectJavascript("/swagger-demo.js"));
        app.UseCysaApi(manejarErrores:false);
        app.MapGet("/",()=>Results.Redirect("/demo")).ExcludeFromDescription();
        app.MapGet("/demo",()=>Results.File(Path.Combine(app.Environment.WebRootPath,"demo.html"),"text/html")).ExcludeFromDescription();
        app.MapGet("/proyecto",()=>panelOrigin is null ? Results.NotFound() :
            Results.Redirect(panelOrigin + "/?modulo=configuraciones&volver=1")).ExcludeFromDescription();
        await app.RunAsync();
    }
}
