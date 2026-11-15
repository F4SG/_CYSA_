using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Security.Cryptography;
using Cysa.Core;
using Cysa.Infrastructure;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.IdentityModel.Tokens;
using Xunit;

namespace Cysa.Api.Tests;

public sealed class RelojPrueba : TimeProvider
{
    public DateTimeOffset Ahora { get; set; } = DateTimeOffset.UtcNow;
    public override DateTimeOffset GetUtcNow() => Ahora;
}

public sealed class ApiTests : IDisposable
{
    private readonly byte[] key = RandomNumberGenerator.GetBytes(32);
    private readonly WebApplicationFactory<Evaluaciones.Api.Program> evaluaciones;
    private readonly WebApplicationFactory<Decisiones.Api.Program> decisiones;
    private readonly RelojPrueba reloj = new();
    private readonly string storage;

    public ApiTests()
    {
        storage = Path.Combine(ApiSetup.RuntimePath(new ConfigurationBuilder().Build()), "tests", Guid.NewGuid().ToString());
        Directory.CreateDirectory(storage);
        File.WriteAllText(Path.Combine(storage, "demo.key"), Convert.ToBase64String(key));
        evaluaciones = new WebApplicationFactory<Evaluaciones.Api.Program>().WithWebHostBuilder(b =>
        {
            Configurar(b);
            b.ConfigureTestServices(s => { s.RemoveAll<TimeProvider>(); s.AddSingleton<TimeProvider>(reloj); });
        });
        decisiones = new WebApplicationFactory<Decisiones.Api.Program>().WithWebHostBuilder(b =>
        {
            Configurar(b);
            b.ConfigureTestServices(s =>
            {
                s.RemoveAll<TimeProvider>(); s.AddSingleton<TimeProvider>(reloj);
                s.AddHttpClient("evaluaciones").ConfigurePrimaryHttpMessageHandler(() => evaluaciones.Server.CreateHandler());
            });
        });
    }

    private void Configurar(IWebHostBuilder b)
    {
        b.UseEnvironment("Development");
        b.UseSetting("Security:Mode", "Demo");
        b.UseSetting("Storage:Directory", storage);
        b.UseSetting("Evaluaciones:BaseUrl", "http://localhost:5181");
    }

    private string Token(string role = "operador", bool mfa = true, bool importar = false,
        byte[]? signingKey = null, string audience = "cysa-dotnet", int authAge = 0, int expires = 1800)
    {
        var now = DateTimeOffset.UtcNow;
        var claims = new List<Claim> { new("sub", "prueba-" + role), new("role", role),
            new("auth_time", (now.ToUnixTimeSeconds() - authAge).ToString(), ClaimValueTypes.Integer64) };
        if (mfa) claims.Add(new("amr", "otp"));
        if (importar) claims.Add(new("scope", "evaluaciones:importar"));
        return new JwtSecurityTokenHandler().WriteToken(new JwtSecurityToken("cysa-demo-local", audience, claims,
            now.AddHours(-1).UtcDateTime, now.AddSeconds(expires).UtcDateTime,
            new SigningCredentials(new SymmetricSecurityKey(signingKey ?? key), SecurityAlgorithms.HmacSha256)));
    }

    private static HttpClient Cliente<T>(WebApplicationFactory<T> factory, string? token) where T : class
    {
        var client = factory.CreateClient();
        if (token is not null) client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        return client;
    }

    private static SolicitudEvaluacion Plan(decimal candidata = 42, decimal peatonal = 25) => new()
    {
        PlanId = "PLAN_DEMO", Version = 1, InterseccionId = "DEMO_INT_01", PlanBaseId = "FIJO",
        Escenario = "Escenario sintético para pruebas", Origen = "demo",
        Accesos = [new() { Id = "N", DemoraBaseSegundos = 40, DemoraCandidataSegundos = candidata, LongitudCruceMetros = 18 }],
        Fases = [new() { Id = "P1", Accesos = ["N"], TiempoPeatonalSegundos = peatonal }]
    };

    private async Task<ResultadoEvaluacion> Crear(SolicitudEvaluacion? plan = null)
    {
        using var client = Cliente(evaluaciones, Token("servicio", false, true));
        var response = await client.PostAsJsonAsync("/api/evaluaciones", plan ?? Plan());
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        return (await response.Content.ReadFromJsonAsync<ResultadoEvaluacion>())!;
    }

    private static SolicitudDecision Decidir(ResultadoEvaluacion e, string accion = "autorizar") => new()
        { SolicitudId = Guid.NewGuid(), EvaluacionId = e.Id, Version = e.Plan.Version, Accion = accion, Motivo = "Revisión del escenario de prueba" };

    [Theory]
    [InlineData(46, 25, true)]
    [InlineData(46.0001, 25, false)]
    [InlineData(40, 24.999, false)]
    [InlineData(48, 20, false)]
    public async Task Evalua_fronteras_sin_redondear(decimal candidata, decimal peatonal, bool aprobada)
    {
        var result = await Crear(Plan(candidata, peatonal));
        Assert.Equal(aprobada, result.Aprobada);
        Assert.Equal(25m, result.Metricas.Single().MinimoPeatonalSegundos);
        Assert.Equal(aprobada, result.Motivos.Count == 0);
        Assert.Equal(64, result.HuellaSha256.Length);
    }

    [Fact]
    public async Task Fase_con_varios_cruces_cubre_el_mayor_minimo()
    {
        var plan = Plan();
        plan.Accesos.Add(new() { Id = "S", DemoraBaseSegundos = 20, DemoraCandidataSegundos = 20, LongitudCruceMetros = 27 });
        plan.Fases[0].Accesos.Add("S");
        Assert.False((await Crear(plan)).Aprobada); // S necesita 35 s aunque N necesita 25.
    }

    [Theory]
    [InlineData("base-cero")]
    [InlineData("negativa")]
    [InlineData("sin-fase")]
    [InlineData("acceso-ajeno")]
    [InlineData("duplicado")]
    [InlineData("elemento-nulo")]
    public async Task Rechaza_entradas_inconsistentes(string caso)
    {
        var plan = Plan();
        switch (caso)
        {
            case "base-cero": plan.Accesos[0] = plan.Accesos[0] with { DemoraBaseSegundos = 0 }; break;
            case "negativa": plan.Accesos[0] = plan.Accesos[0] with { DemoraCandidataSegundos = -1 }; break;
            case "sin-fase": plan.Fases.Clear(); break;
            case "acceso-ajeno": plan.Fases[0].Accesos.Add("X"); break;
            case "duplicado": plan.Accesos.Add(plan.Accesos[0]); break;
            case "elemento-nulo": plan.Accesos.Add(null!); break;
        }
        using var client = Cliente(evaluaciones, Token("servicio", false, true));
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync("/api/evaluaciones", plan)).StatusCode);
    }

    [Fact]
    public async Task Version_evaluada_no_se_sobrescribe()
    {
        var first = await Crear();
        using var client = Cliente(evaluaciones, Token("servicio", false, true));
        Assert.Equal(HttpStatusCode.Conflict, (await client.PostAsJsonAsync("/api/evaluaciones", Plan(48))).StatusCode);
        var stored = await client.GetFromJsonAsync<ResultadoEvaluacion>($"/api/evaluaciones/{first.Id}");
        Assert.True(stored!.Aprobada);
    }

    [Theory]
    [InlineData("sin-token", 401)]
    [InlineData("firma", 401)]
    [InlineData("audiencia", 401)]
    [InlineData("expirado", 401)]
    [InlineData("operador", 403)]
    [InlineData("administrador", 403)]
    public async Task Importacion_exige_identidad_y_permiso(string caso, int status)
    {
        var token = caso switch
        {
            "sin-token" => null,
            "firma" => Token("servicio", importar: true, signingKey: RandomNumberGenerator.GetBytes(32)),
            "audiencia" => Token("servicio", importar: true, audience: "otra-api"),
            "expirado" => Token("servicio", importar: true, expires: -60),
            _ => Token(caso)
        };
        using var client = Cliente(evaluaciones, token);
        Assert.Equal(status, (int)(await client.PostAsJsonAsync("/api/evaluaciones", Plan())).StatusCode);
    }

    [Theory]
    [InlineData("operador", false, 0)]
    [InlineData("administrador", true, 0)]
    [InlineData("operador", true, 301)]
    public async Task Decision_exige_operador_y_mfa_reciente(string role, bool mfa, int authAge)
    {
        var result = await Crear();
        using var client = Cliente(decisiones, Token(role, mfa, authAge: authAge));
        Assert.Equal(HttpStatusCode.Forbidden, (await client.PostAsJsonAsync("/api/planes/PLAN_DEMO/decisiones", Decidir(result))).StatusCode);
    }

    [Theory]
    [InlineData("autorizar", "autorizado")]
    [InlineData("rechazar", "rechazado")]
    public async Task Flujo_completo_persiste_y_reintento_no_duplica(string accion, string estado)
    {
        var evaluation = await Crear();
        using var client = Cliente(decisiones, Token());
        var request = Decidir(evaluation, accion);
        var response = await client.PostAsJsonAsync("/api/planes/PLAN_DEMO/decisiones", request);
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        var result = (await response.Content.ReadFromJsonAsync<ResultadoDecision>())!;
        Assert.Equal(estado, result.EstadoPosterior);
        Assert.Equal("prueba-operador", result.UsuarioId);
        Assert.True(result.MfaVerificado);
        Assert.Equal(evaluation.HuellaSha256, result.HuellaSha256);
        Assert.Equal(HttpStatusCode.OK, (await client.PostAsJsonAsync("/api/planes/PLAN_DEMO/decisiones", request)).StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, (await client.PostAsJsonAsync("/api/planes/PLAN_DEMO/decisiones", request with { Motivo = "Intento de alterar la decisión" })).StatusCode);
        var history = await client.GetFromJsonAsync<List<ResultadoDecision>>("/api/planes/PLAN_DEMO/historial");
        Assert.Single(history!);
        using var scope = decisiones.Services.CreateScope();
        var saved = scope.ServiceProvider.GetRequiredService<DecisionesDb>().Decisiones.Single();
        Assert.Contains(evaluation.HuellaSha256, saved.EvaluacionJson);
    }

    [Fact]
    public async Task Dos_decisiones_concurrentes_no_autorizan_dos_veces()
    {
        var evaluation = await Crear();
        using var client = Cliente(decisiones, Token());
        var results = await Task.WhenAll(
            client.PostAsJsonAsync("/api/planes/PLAN_DEMO/decisiones", Decidir(evaluation)),
            client.PostAsJsonAsync("/api/planes/PLAN_DEMO/decisiones", Decidir(evaluation, "rechazar")));
        Assert.Single(results, r => r.StatusCode == HttpStatusCode.Created);
        Assert.Single(results, r => r.StatusCode == HttpStatusCode.Conflict);
    }

    [Theory]
    [InlineData("rechazada")]
    [InlineData("vencida")]
    [InlineData("version")]
    [InlineData("otro-plan")]
    public async Task No_decide_sobre_evaluacion_invalida(string caso)
    {
        var e = await Crear(Plan(caso == "rechazada" ? 48 : 40));
        if (caso == "vencida") reloj.Ahora = reloj.Ahora.AddHours(25);
        var request = Decidir(e);
        if (caso == "version") request = request with { Version = 2 };
        using var client = Cliente(decisiones, Token());
        var planId = caso == "otro-plan" ? "OTRO" : "PLAN_DEMO";
        Assert.Equal(HttpStatusCode.Conflict, (await client.PostAsJsonAsync($"/api/planes/{planId}/decisiones", request)).StatusCode);
        Assert.Empty((await client.GetFromJsonAsync<List<ResultadoDecision>>($"/api/planes/{planId}/historial"))!);
    }

    [Fact]
    public async Task Propiedades_desconocidas_no_permiten_suplantar_usuario_ni_mfa()
    {
        using var client = Cliente(decisiones, Token());
        var body = new { solicitudId = Guid.NewGuid(), evaluacionId = Guid.NewGuid(), version = 1,
            accion = "autorizar", motivo = "Una prueba", usuarioId = "administrador", mfa = true };
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync("/api/planes/PLAN_DEMO/decisiones", body)).StatusCode);
    }

    [Fact]
    public async Task Caida_de_evaluaciones_no_genera_decision()
    {
        using var fallida = decisiones.WithWebHostBuilder(b => b.ConfigureTestServices(s =>
            s.AddHttpClient("evaluaciones").ConfigurePrimaryHttpMessageHandler(() => new FalloRed())));
        using var client = Cliente(fallida, Token());
        var request = new SolicitudDecision { SolicitudId = Guid.NewGuid(), EvaluacionId = Guid.NewGuid(),
            Version = 1, Accion = "autorizar", Motivo = "Prueba de desconexión" };
        Assert.Equal(HttpStatusCode.ServiceUnavailable, (await client.PostAsJsonAsync("/api/planes/PLAN_DEMO/decisiones", request)).StatusCode);
        Assert.Empty((await client.GetFromJsonAsync<List<ResultadoDecision>>("/api/planes/PLAN_DEMO/historial"))!);
    }

    [Fact]
    public async Task Documentacion_y_health_estan_disponibles()
    {
        using var client = Cliente(evaluaciones, null);
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/health")).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/swagger/v1/swagger.json")).StatusCode);
    }

    public void Dispose() { decisiones.Dispose(); evaluaciones.Dispose(); }

    private sealed class FalloRed : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct) =>
            throw new HttpRequestException("Desconexión simulada");
    }
}
