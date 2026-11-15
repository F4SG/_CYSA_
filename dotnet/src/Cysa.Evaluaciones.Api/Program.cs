using Cysa.Core;
using Cysa.Infrastructure;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Evaluaciones.Api;

public partial class Program
{
    public static async Task Main(string[] args)
    {
        var builder = WebApplication.CreateBuilder(args);
        builder.AddCysaApi("CYSA Evaluaciones API");
        var runtime = ApiSetup.RuntimePath(builder.Configuration);
        Directory.CreateDirectory(runtime);
        builder.Services.AddDbContext<EvaluacionesDb>(o => o.UseSqlite(
            new Microsoft.Data.Sqlite.SqliteConnectionStringBuilder
            { DataSource = Path.Combine(runtime, "evaluaciones.db"), DefaultTimeout = 10 }.ToString()));
        builder.Services.AddScoped<EvaluadorPlanes>();
        var app = builder.Build();
        using (var scope = app.Services.CreateScope())
            await scope.ServiceProvider.GetRequiredService<EvaluacionesDb>().Database.EnsureCreatedAsync();
        app.UseCysaApi();
        await app.RunAsync();
    }
}
