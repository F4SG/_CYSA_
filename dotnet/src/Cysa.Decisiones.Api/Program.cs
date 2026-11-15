using Cysa.Infrastructure;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Decisiones.Api;

public partial class Program
{
    public static async Task Main(string[] args)
    {
        var builder = WebApplication.CreateBuilder(args);
        builder.AddCysaApi("CYSA Decisiones API");
        var runtime = ApiSetup.RuntimePath(builder.Configuration);
        Directory.CreateDirectory(runtime);
        builder.Services.AddDbContext<DecisionesDb>(o => o.UseSqlite(
            new Microsoft.Data.Sqlite.SqliteConnectionStringBuilder
            { DataSource = Path.Combine(runtime, "decisiones.db"), DefaultTimeout = 10 }.ToString()));
        var url = new Uri(builder.Configuration["Evaluaciones:BaseUrl"] ?? "http://localhost:5181");
        if (url.Scheme != "https" && !(builder.Environment.IsDevelopment() && url.IsLoopback && url.Scheme == "http"))
            throw new InvalidOperationException("Evaluaciones:BaseUrl requiere HTTPS fuera de la demo local.");
        builder.Services.AddHttpClient("evaluaciones", c => { c.BaseAddress = url; c.Timeout = TimeSpan.FromSeconds(5); })
            .ConfigurePrimaryHttpMessageHandler(() => new HttpClientHandler { AllowAutoRedirect = false });
        var app = builder.Build();
        using (var scope = app.Services.CreateScope())
            await scope.ServiceProvider.GetRequiredService<DecisionesDb>().Database.EnsureCreatedAsync();
        app.UseCysaApi();
        await app.RunAsync();
    }
}
