@echo off
setlocal
pushd "%~dp0"
dotnet build "desktop\Cysa.Launcher\Cysa.Launcher.csproj" --configuration Release --nologo
if errorlevel 1 (
  echo No se pudo compilar CYSA. Comprueba que el SDK .NET 10 este instalado y cierra CYSA si esta abierto.
  pause
  popd
  exit /b 1
)
start "" "%~dp0desktop\Cysa.Launcher\bin\Release\net10.0-windows\win-x64\CYSA.exe"
popd
