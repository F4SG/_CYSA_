using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;

namespace Cysa.Web.Api.Data;

public sealed class DemoDatabase(CysaDb db,IConfiguration config,IHostEnvironment environment)
{
    public const string Name="CYSA_WebIII_Demo";
    public async Task<object> ProbarConexion(CancellationToken ct=default)
    {
        ExigirDemo();
        var connection=new SqlConnectionStringBuilder(db.Database.GetConnectionString())
        {
            InitialCatalog="master",ConnectTimeout=5,PersistSecurityInfo=false
        };
        await using var sql=new SqlConnection(connection.ConnectionString);
        using var timeout=CancellationTokenSource.CreateLinkedTokenSource(ct);timeout.CancelAfter(TimeSpan.FromSeconds(10));
        await sql.OpenAsync(timeout.Token);
        await using var command=sql.CreateCommand();
        command.CommandText="SELECT DB_ID(@nombre)";command.Parameters.AddWithValue("@nombre",Name);command.CommandTimeout=5;
        var id=await command.ExecuteScalarAsync(timeout.Token);
        return new{Conectada=true,Instancia=connection.DataSource,BaseDatos=Name,BaseExiste=id is not null && id!=DBNull.Value};
    }
    public void ExigirDemo()
    {
        var connection=new SqlConnectionStringBuilder(db.Database.GetConnectionString());
        if(!environment.IsDevelopment() || !config.GetValue<bool>("Demo:Enabled") || connection.InitialCatalog!=Name)
            throw new InvalidOperationException("La recreación solo está habilitada en Development para la base CYSA_WebIII_Demo.");
        if(connection.DataSource is not ("localhost" or "." or "(localdb)\\MSSQLLocalDB" or "localhost\\SQLEXPRESS" or ".\\SQLEXPRESS"))
            throw new InvalidOperationException("La preparación de demostración solo admite una instancia local de SQL Server.");
    }
    public async Task Preparar(bool recrear,CancellationToken ct=default)
    {
        ExigirDemo();
        if(recrear)await db.Database.EnsureDeletedAsync(ct);
        await db.Database.MigrateAsync(ct);
        await DemoSeeder.Cargar(db,ct);
    }
    public async Task PrepararPractica(CancellationToken ct = default)
    {
        ExigirDemo();
        await DemoSeeder.PrepararBanco(db, ct);
    }
    public async Task<Dictionary<string,int>> Conteos(CancellationToken ct=default)
    {
        var result=new Dictionary<string,int>();
        foreach(var entity in db.Model.GetEntityTypes().OrderBy(e=>e.GetTableName()))
        {
            var table=entity.GetTableName()!;
            // Los identificadores provienen exclusivamente del modelo EF, nunca de una solicitud.
            var sql="SELECT COUNT(*) AS [Value] FROM ["+table.Replace("]", "]]")+ "]";
            result[table]=await db.Database.SqlQueryRaw<int>(sql).SingleAsync(ct);
        }
        return result;
    }
}
