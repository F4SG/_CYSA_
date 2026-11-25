using Cysa.Web.Api.Models;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Web.Api.Data;

internal static class ProyectoDatabase
{
    const string Name = "CYSA_Proyecto";

    public static string ConnectionString(string value)
    {
        var connection = new SqlConnectionStringBuilder(value);
        if (connection.DataSource is not ("localhost" or "." or "(localdb)\\MSSQLLocalDB" or "localhost\\SQLEXPRESS" or ".\\SQLEXPRESS"))
            throw new InvalidOperationException("Proyecto de Sistemas requiere una instancia SQL Server local.");
        connection.InitialCatalog = Name;
        return connection.ConnectionString;
    }

    public static async Task Prepare(string connection, bool clear, bool practice)
    {
        var options = new DbContextOptionsBuilder<CysaDb>().UseSqlServer(ConnectionString(connection)).Options;
        await using var db = new CysaDb(options);
        if (clear) await db.Database.EnsureDeletedAsync();
        await db.Database.MigrateAsync();
        if (!practice) return;

        var roles = await db.Set<Rol>().Select(role => role.Nombre).ToListAsync();
        foreach (var name in new[] { "administrador", "operador" })
            if (!roles.Contains(name))
                db.Add(new Rol { Nombre = name, Descripcion = "Rol de acceso de Proyecto de Sistemas" });
        await db.SaveChangesAsync();
        await DemoSeeder.PrepararBanco(db);
    }
}
