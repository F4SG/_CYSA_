using System.Net;
using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi;

namespace Cysa.Infrastructure;

public static class ApiSetup
{
    public static string RuntimePath(IConfiguration configuration)
    {
        var configured = configuration["Storage:Directory"];
        if (!string.IsNullOrWhiteSpace(configured)) return Path.GetFullPath(configured);
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "CYSA.Web.sln")))
            directory = directory.Parent;
        if (directory is null) throw new InvalidOperationException("Configura Storage:Directory al publicar fuera de la solución.");
        return Path.Combine(directory.FullName, "runtime");
    }

    public static void AddCysaApi(this WebApplicationBuilder builder, string titulo, string? descripcion = null)
    {
        builder.Services.AddSingleton(TimeProvider.System);
        builder.Services.AddControllers().AddJsonOptions(o =>
            o.JsonSerializerOptions.UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow);
        builder.Services.AddProblemDetails();
        builder.Services.AddEndpointsApiExplorer();
        builder.Services.AddSwaggerGen(o =>
        {
            o.SwaggerDoc("v1", new() { Title = titulo, Version = "v1", Description =
                descripcion ?? "Extensión de laboratorio CYSA. Solo planes de prueba; no activa semáforos ni ejecuta SUMO." });
            o.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
                { Type = SecuritySchemeType.Http, Scheme = "bearer", BearerFormat = "JWT" });
            o.AddSecurityRequirement(document => new OpenApiSecurityRequirement
                { [new OpenApiSecuritySchemeReference("Bearer", document)] = [] });
        });

        var demo = builder.Configuration["Security:Mode"] == "Demo";
        if (demo && !builder.Environment.IsDevelopment())
            throw new InvalidOperationException("La identidad de demostración solo se permite en Development.");
        builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer(o =>
        {
            o.MapInboundClaims = false;
            o.TokenValidationParameters.ClockSkew = TimeSpan.FromSeconds(5);
            o.TokenValidationParameters.NameClaimType = "sub";
            o.TokenValidationParameters.RoleClaimType = "role";
            o.TokenValidationParameters.RequireExpirationTime = true;
            o.TokenValidationParameters.RequireSignedTokens = true;
            if (demo)
            {
                var keyPath = Path.Combine(RuntimePath(builder.Configuration), "demo.key");
                if (!File.Exists(keyPath)) throw new InvalidOperationException("Ejecuta scripts/Preparar-Demo.ps1 antes de iniciar las APIs.");
                var key = Convert.FromBase64String(File.ReadAllText(keyPath).Trim());
                if (key.Length < 32) throw new InvalidOperationException("La clave local debe tener al menos 256 bits.");
                o.TokenValidationParameters.ValidIssuer = "cysa-demo-local";
                o.TokenValidationParameters.ValidAudience = "cysa-dotnet";
                o.TokenValidationParameters.IssuerSigningKey = new SymmetricSecurityKey(key);
                o.TokenValidationParameters.ValidAlgorithms = [SecurityAlgorithms.HmacSha256];
                o.TokenValidationParameters.ValidateIssuerSigningKey = true;
            }
            else
            {
                o.Authority = builder.Configuration["Security:Authority"]
                    ?? throw new InvalidOperationException("Configura Security:Authority para OIDC.");
                o.Audience = builder.Configuration["Security:Audience"] ?? "cysa-api";
                o.RequireHttpsMetadata = !builder.Environment.IsDevelopment();
                o.TokenValidationParameters.ValidAlgorithms = [SecurityAlgorithms.RsaSha256];
            }
            o.Events = new JwtBearerEvents
            {
                OnTokenValidated = context =>
                {
                    if (demo && context.HttpContext.Connection.RemoteIpAddress is { } ip && !IPAddress.IsLoopback(ip))
                    {
                        context.Fail("La demostración solo admite conexiones locales.");
                        return Task.CompletedTask;
                    }
                    var identity = (ClaimsIdentity)context.Principal!.Identity!;
                    if (string.IsNullOrWhiteSpace(identity.FindFirst("sub")?.Value))
                    {
                        context.Fail("Falta el sujeto autenticado.");
                        return Task.CompletedTask;
                    }
                    // Keycloak firma realm_access; nunca se toman roles del cuerpo HTTP.
                    var realm = identity.FindFirst("realm_access")?.Value;
                    if (realm is not null)
                    {
                        try
                        {
                            using var json = JsonDocument.Parse(realm);
                            if (json.RootElement.TryGetProperty("roles", out var roles))
                                foreach (var role in roles.EnumerateArray())
                                    identity.AddClaim(new("role", role.GetString()!));
                        }
                        catch (Exception e) when (e is JsonException or InvalidOperationException or ArgumentException)
                        { context.Fail("Roles inválidos."); }
                    }
                    return Task.CompletedTask;
                }
            };
        });
        builder.Services.AddAuthorization(o =>
        {
            o.AddPolicy("Leer", p => p.RequireAuthenticatedUser().RequireAssertion(c =>
                c.User.IsInRole("operador") || c.User.IsInRole("administrador") || TienePermisoImportar(c.User)));
            o.AddPolicy("Importar", p => p.RequireAuthenticatedUser().RequireAssertion(c => TienePermisoImportar(c.User)));
            o.AddPolicy("Decidir", p => p.RequireAuthenticatedUser().RequireRole("operador").RequireAssertion(c =>
                MfaReciente(c.User, DateTimeOffset.UtcNow)));
        });
    }

    private static bool TienePermisoImportar(ClaimsPrincipal user) => user.FindAll("scope")
        .Any(c => c.Value.Split(' ', StringSplitOptions.RemoveEmptyEntries).Contains("evaluaciones:importar"));

    public static bool MfaReciente(ClaimsPrincipal user, DateTimeOffset ahora) =>
        user.FindAll("amr").Any(c => c.Value is "otp" or "mfa" or "hwk") &&
        long.TryParse(user.FindFirst("auth_time")?.Value, out var timestamp) &&
        timestamp <= ahora.ToUnixTimeSeconds() && ahora.ToUnixTimeSeconds() - timestamp <= 300;

    public static void UseCysaApi(this WebApplication app, bool manejarErrores = true)
    {
        if (manejarErrores) app.UseExceptionHandler();
        app.UseStatusCodePages();
        // HTTP solo para la demo local. En despliegue OIDC debe terminar TLS.
        if (!app.Environment.IsDevelopment()) app.UseHttpsRedirection();
        app.UseAuthentication();
        app.UseAuthorization();
        if (app.Environment.IsDevelopment())
        {
            app.UseSwagger();
            app.UseSwaggerUI();
        }
        app.MapGet("/health", () => Results.Ok(new { status = "ok", soloPrueba = true, activacionPlanes = false })).AllowAnonymous();
        app.MapControllers();
    }
}
