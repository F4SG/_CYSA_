using System.Text.Json;

namespace Cysa.Launcher;

internal sealed partial class Instance
{
    public string OperationUrl=>$"http://localhost:{Ports.Operation}";

    Dictionary<string,string> OperationEnvironment()=>new()
    {
        ["PYTHONPATH"]=string.Join(Path.PathSeparator,new[]{"","shared","backend","inventario","simulacion","controlador"}.Select(p=>Path.Combine(Repo,p))),
        ["CYSA_INSTALACION_DIR"]=Repo,
        ["CYSA_SQL_SERVER"]=SqlServerActual(),
        ["CYSA_SQL_DATABASE"]="CYSA_Control_S2",
        ["CYSA_OPERACION_PORT"]=Ports.Operation.ToString(),
        ["CYSA_OPERACION_URL"]=OperationUrl,
        ["CYSA_WEB_URL"]=WebUrl,
        ["CYSA_PANEL_URL"]=PanelUrl+"/"
    };

    async Task<bool> PrepararEjemplos()
    {
        Write("Validando cinco propuestas de práctica en SUMO…");
        try
        {
            var code = await Run(Venv, ["tools/franco/preparar_planes_demo.py", "--instalacion", Root],
                environment: OperationEnvironment(), check: false, timeoutMinutes: 3);
            if (code == 0) return true;
        }
        catch (InvalidOperationException error)
        {
            Write(error.Message);
        }
        Write("No se pudo renovar el lote de práctica. Se conserva el lote anterior.");
        return false;
    }

    async Task StartOperation()
    {
        var environment=OperationEnvironment();
        if(!apis.TryGetValue("Operacion S2",out var server) || server.HasExited)
        {
            if(!IsFree(Ports.Operation))throw new InvalidOperationException($"El puerto del banco S2 ({Ports.Operation}) está ocupado por otro proceso.");
            var requirements=new[]{"backend/requirements.txt","simulacion/requirements.txt","controlador/requirements.txt","operacion/requirements.txt"};
            var fingerprint=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(string.Join("\n",requirements.Select(p=>File.ReadAllText(Path.Combine(Repo,p)))))));
            var marker=Path.Combine(Root,"s2-requisitos.sha256");
            if(!File.Exists(marker) || File.ReadAllText(marker)!=fingerprint)
            {
                Write("Preparando dependencias del banco S2; se reutiliza el entorno Python de esta PC.");
                await Run(Venv,new[]{"-m","pip","install","--disable-pip-version-check"}.Concat(requirements.SelectMany(p=>new[]{"-r",p})),environment:environment,timeoutMinutes:15);
                await File.WriteAllTextAsync(marker,fingerprint);
            }
            await Run(Venv,["tools/franco/preparar_control.py","--repo",Repo],environment:environment);
            await Run(Venv,["tools/franco/configurar_mfa_control.py","--repo",Repo],environment:environment);
            apis["Operacion S2"]=Start(Venv,["-m","operacion.servidor"],environment:environment);
        }
        await WaitOperationReady();
        if(!apis.TryGetValue("Controlador S2",out var controller) || controller.HasExited)
        {
            // El arranque general usa software. Nunca elige ni abre un puerto serial.
            apis["Controlador S2"]=Start(Venv,["-m","cysa_controlador.run","--config","controlador/config/demo_int_01.yaml",
                "--sin-placa","--mqtt","--credenciales",Path.Combine(Repo,"infra/runtime/clientes/emulador.env"),
                "--clave-planes",Path.Combine(Repo,"infra/runtime/control/clave.key")],environment:environment);
            await Task.Delay(1000);
            if(apis["Controlador S2"].HasExited)throw new InvalidOperationException("El controlador S2 no pudo iniciar. Revisa el registro.");
        }
        var path=Path.Combine(Repo,"panel/config.json");
        var config=JsonSerializer.Deserialize<Dictionary<string,JsonElement>>(await File.ReadAllTextAsync(path))!;
        config["operacionBase"]=JsonSerializer.SerializeToElement(OperationUrl);
        await File.WriteAllTextAsync(path,JsonSerializer.Serialize(config));
        Write("Banco S2 listo con SQL Server, MQTT y MMU simulado. La placa física y la fuente de cámara se seleccionan aparte.");
    }

    async Task WaitOperationReady()
    {
        for(var attempt=0;attempt<60;attempt++)
        {
            if(apis.TryGetValue("Operacion S2",out var process) && process.HasExited)
                throw new InvalidOperationException("El banco S2 terminó durante el arranque. Revisa SQL Server y el registro.");
            try
            {
                using var response=await http.GetAsync(OperationUrl+"/health");
                if(response.IsSuccessStatusCode)
                {
                    using var data=JsonDocument.Parse(await response.Content.ReadAsStringAsync());
                    if(data.RootElement.TryGetProperty("mqtt_conectado",out var mqtt) && mqtt.GetBoolean())return;
                }
            }
            catch(HttpRequestException){} catch(TaskCanceledException){}
            await Task.Delay(1000);
        }
        throw new InvalidOperationException("El banco S2 no está listo: SQL Server y MQTT deben estar disponibles. Revisa el registro.");
    }
}
