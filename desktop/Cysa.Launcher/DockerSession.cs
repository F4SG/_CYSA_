namespace Cysa.Launcher;

internal sealed class DockerSession
{
    bool used;
    public void MarkUsed() => used = true;

    public async Task Stop(Func<Task<bool>> available, Func<Task> stop, Action<string> log)
    {
        if (!used) return;
        if (!await available())
        {
            log("Docker no está disponible; no se pudo detener su proyecto. Los procesos locales ya se detuvieron y los datos se conservan.");
            return;
        }
        await stop();
        used = false;
    }
}

internal static class ShutdownTest
{
    public static async Task Run()
    {
        var session = new DockerSession();
        var probes = 0; var stops = 0; var warnings = 0;
        Task<bool> Available() { probes++; return Task.FromResult(true); }
        Task Stop() { stops++; return Task.CompletedTask; }
        void Warn(string _) => warnings++;
        await session.Stop(Available, Stop, Warn);
        if (probes != 0 || stops != 0) throw new Exception("Un cierre sin IoT consultó Docker.");
        session.MarkUsed();
        await session.Stop(() => { probes++; return Task.FromResult(false); }, Stop, Warn);
        if (stops != 0 || warnings != 1) throw new Exception("Docker no disponible no se trató como aviso.");
        await session.Stop(Available, Stop, Warn);
        await session.Stop(Available, Stop, Warn);
        if (probes != 2 || stops != 1) throw new Exception("El cierre no detuvo Docker una sola vez o no permitió reintentar.");
        session.MarkUsed();
        var failed = false;
        try { await session.Stop(Available, () => throw new IOException("Fallo real al detener"), Warn); }
        catch (IOException) { failed = true; }
        if (!failed) throw new Exception("Se ocultó un error real al detener contenedores.");
        await session.Stop(Available, Stop, Warn);
        if (stops != 2) throw new Exception("No se pudo reintentar tras un fallo de detención.");
    }
}
