namespace Cysa.Launcher;

internal sealed record SqlServerOptions(string Instancia)
{
    public static readonly string[] Instancias=["localhost",".",@"localhost\SQLEXPRESS",@".\SQLEXPRESS",@"(localdb)\MSSQLLocalDB"];
    public static string Validar(string instancia)=>Instancias.Contains(instancia,StringComparer.Ordinal)
        ? instancia : throw new InvalidOperationException("Selecciona una instancia local de SQL Server de la lista.");
    public string Cadena()=>"Server="+Validar(Instancia)+";Database=CYSA_WebIII_Demo;Integrated Security=True;TrustServerCertificate=True;Connect Timeout=10";
}

internal sealed class SqlServerDialog : Form
{
    readonly ComboBox server=new(){DropDownStyle=ComboBoxStyle.DropDownList,Dock=DockStyle.Fill,AccessibleName="Instancia local de SQL Server"};
    readonly Label result=new(){AutoSize=false,Dock=DockStyle.Fill,Text="Primero prueba la conexión. No se crea ni se borra la base.",AccessibleName="Resultado de conexión"};
    readonly Button test=new(){Text="Probar conexión",AutoSize=true};
    readonly Button save=new(){Text="Guardar configuración",AutoSize=true,Enabled=false};
    readonly Button cancel=new(){Text="Cancelar",AutoSize=true,DialogResult=DialogResult.Cancel};
    bool testing;
    public string Instancia=>SqlServerOptions.Validar(server.SelectedItem?.ToString()??"");

    public SqlServerDialog(string actual,bool externa,Func<string,Task> probar)
    {
        Text="SQL Server (Web III)";StartPosition=FormStartPosition.CenterParent;
        ClientSize=new Size(600,380);MinimumSize=new Size(590,410);Font=new Font("Segoe UI",10);
        FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;MinimizeBox=false;
        var layout=new TableLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(20),ColumnCount=1,RowCount=6};
        foreach(var height in new[]{30,44,90,76,44,42})layout.RowStyles.Add(new(SizeType.Absolute,height));
        Controls.Add(layout);
        layout.Controls.Add(new Label{Text="Instancia local de SQL Server",AutoSize=true});
        server.Items.AddRange(SqlServerOptions.Instancias);server.SelectedItem=actual;layout.Controls.Add(server);
        layout.Controls.Add(new Label{Text="Base: CYSA_WebIII_Demo\nAutenticación de Windows del usuario actual. SQL Server debe estar instalado y en ejecución.",Dock=DockStyle.Fill});
        layout.Controls.Add(result);
        var actions=new FlowLayoutPanel{Dock=DockStyle.Fill};actions.Controls.AddRange([test,save,cancel]);layout.Controls.Add(actions);
        layout.Controls.Add(new Label{Text="Guardar detiene solo la API Web III de esta instalación. Vuelve a abrirla desde Swagger o Panel Web III.",Dock=DockStyle.Fill,Font=new Font(Font.FontFamily,8)});
        CancelButton=cancel;
        if(externa)
        {
            server.Enabled=test.Enabled=false;
            result.Text="CYSA_WEBIII_CONNECTION define la conexión y tiene prioridad. Para usar este diálogo, retira esa variable y vuelve a abrir CYSA.";
        }
        server.SelectedIndexChanged+=(_,_)=>{save.Enabled=false;result.Text="Prueba esta instancia antes de guardar.";};
        test.Click+=async(_,_)=>
        {
            testing=true;server.Enabled=test.Enabled=save.Enabled=cancel.Enabled=false;
            result.Text="Probando conexión local…";
            try{await probar(Instancia);result.Text="Conexión correcta. Puedes guardar. La base no fue modificada.";save.Enabled=true;}
            catch(Exception){result.Text="No se pudo conectar. Revisa el registro, el servicio SQL Server y los permisos de Windows. No se guardaron cambios.";}
            finally{testing=false;server.Enabled=test.Enabled=cancel.Enabled=true;}
        };
        save.Click+=(_,_)=>{DialogResult=DialogResult.OK;Close();};
        FormClosing+=(_,e)=>{if(testing)e.Cancel=true;};
    }
}
