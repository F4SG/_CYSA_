using System.Security.Cryptography;
using System.Text;

namespace Cysa.Launcher;

internal static class SourceLayout
{
    static readonly HashSet<string> ExcludedDirectories=new(StringComparer.OrdinalIgnoreCase)
    {
        ".git",".vs",".idea",".venv",".review-venv","bin","obj","runtime","resultados","respaldos",
        "artifacts","mediciones","node_modules","__pycache__",".pytest_cache",".launcher-setup",
        ".aws",".codex",".agents","entrega-webiii"
    };
    static readonly HashSet<string> ExcludedExtensions=new(StringComparer.OrdinalIgnoreCase)
        {".key",".pem",".pfx",".p12",".db",".sqlite",".sqlite3",".pdb",".pyc",".pt",".mp4",".avi",".mov",".exe",".zip"};
    public static string? FindRoot(string directory)
    {
        for(var current=new DirectoryInfo(Path.GetFullPath(directory));current is not null;current=current.Parent)
            if(File.Exists(Path.Combine(current.FullName,"desktop","Cysa.Launcher","Cysa.Launcher.csproj")) &&
               File.Exists(Path.Combine(current.FullName,"dotnet","src","Cysa.Web.Api","Cysa.Web.Api.csproj")) &&
               File.Exists(Path.Combine(current.FullName,"infra","compose.yaml")))return current.FullName;
        return null;
    }
    public static IEnumerable<string> Files(string directory)
    {
        foreach(var file in Directory.EnumerateFiles(directory))
        {
            var name=Path.GetFileName(file);
            if((File.GetAttributes(file)&FileAttributes.ReparsePoint)!=0 || ExcludedExtensions.Contains(Path.GetExtension(file)))continue;
            if((name.Equals(".env",StringComparison.OrdinalIgnoreCase)||name.StartsWith(".env.",StringComparison.OrdinalIgnoreCase)) && name!=".env.example")continue;
            if(name.Equals("gcm-diagnose.log",StringComparison.OrdinalIgnoreCase))continue;
            yield return file;
        }
        foreach(var child in Directory.EnumerateDirectories(directory))
        {
            if(ExcludedDirectories.Contains(Path.GetFileName(child)) || (File.GetAttributes(child)&FileAttributes.ReparsePoint)!=0)continue;
            foreach(var file in Files(child))yield return file;
        }
    }
    public static string WebFingerprint(string source)
    {
        var dotnet=Path.Combine(source,"dotnet");
        var files=Files(Path.Combine(dotnet,"src")).Concat(Directory.EnumerateFiles(dotnet).Where(f=>Path.GetExtension(f) is ".props" or ".targets"));
        using var hash=IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        foreach(var file in files.OrderBy(f=>Path.GetRelativePath(dotnet,f),StringComparer.Ordinal))
        {
            hash.AppendData(Encoding.UTF8.GetBytes(Path.GetRelativePath(dotnet,file).Replace('\\','/')+"\0"));
            hash.AppendData(File.ReadAllBytes(file));hash.AppendData([0]);
        }
        return Convert.ToHexString(hash.GetHashAndReset()).ToLowerInvariant();
    }
}
