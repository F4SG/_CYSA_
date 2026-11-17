# Lanzador de pruebas CYSA para Windows

`CYSA.exe` usa WinForms y .NET 10. El ZIP incluye dos APIs autocontenidas de Windows y el instalador de Python firmado por Python Software Foundation. No necesita Git, Visual Studio ni un SDK .NET en la PC de destino. Docker Desktop con WSL 2 y contenedores Linux se instala por separado desde el enlace de la ventana.

## Construcción

Desde PowerShell 7, con Git y SDK .NET 10:

```powershell
./desktop/Crear-Paquete.ps1
```

La salida se crea en un directorio nuevo de `artifacts/desktop/`, excluido de Git. El script publica el lanzador y ambas APIs para `win-x64`, copia únicamente fuentes rastreadas y los archivos nuevos de esta entrega, descarga Python 3.12.10 de python.org, verifica su firma y escribe manifiesto y huellas SHA-256. El ZIP contiene una carpeta `CYSA-Windows` con `CYSA.exe`, `app`, `services`, `dependencies` y `LEEME.txt`.

No se empaquetan `.git`, entornos virtuales, modelos, videos, bases, claves, tokens, `.env`, `runtime`, resultados ni respaldos. El estado del equipo que construye el ZIP no se reutiliza. El manifiesto distingue un paquete construido con cambios locales pendientes de commit.

## Instalación y aislamiento

El lanzador prepara las fuentes en `%LOCALAPPDATA%/CYSA/workspace`. Instala Python por usuario solo si no encuentra Python 3.12; crea un entorno virtual propio. Genera secretos mediante el configurador existente, en un directorio temporal local, y promueve el resultado de forma reanudable. No vuelve a generar credenciales al reintentar ni reiniciar.

El nombre del proyecto Compose se deriva de la carpeta de datos del usuario; `docker compose -p` separa los volúmenes y redes. En el primer arranque elige cinco puertos disponibles y los guarda. El override publica solo en `127.0.0.1`; OIDC y MQTT se configuran con esos puertos. Se requiere Compose 2.24.4+ por `!override`. Otros proyectos Docker existentes no se detienen ni se eliminan.

Las APIs .NET funcionan como procesos locales con SQLite en el `runtime` del usuario y escuchan en localhost. Se usan sus perfiles de demostración existentes, con MFA simulado, sin modificar las reglas de las APIs ni conectar con controladores reales. Al cerrar, el lanzador detiene sus procesos y su proyecto Compose, conservando los volúmenes.

El botón cámara pide un índice; el de video abre un selector de archivos. Ambos usan el modo CPU o GPU elegido en la ventana y guardado por usuario, con tamaño de inferencia 640 px. Después de configurar y al abrir una instalación existente se mide YOLO a 640 px con imágenes sintéticas: dos calentamientos y la mediana de cinco inferencias por dispositivo, sincronizando CUDA. La GPU más rápida se recomienda solo si mejora más del 10 % frente a CPU; en otro caso se recomienda CPU. La opción recomendada se marca en verde con «Recomendado», independientemente de la elección manual. La medición depende de la carga y energía actuales; se puede repetir con «Detectar y recomendar».

GPU requiere NVIDIA/CUDA y superar una inferencia real. «Preparar GPU» instala los pares oficiales de PyTorch/torchvision de [las instrucciones de PyTorch](https://pytorch.org/get-started/previous-versions/), según la versión máxima CUDA que anuncia `nvidia-smi`: 2.14.1/0.29.1 con cu130 o cu126; para controladores antiguos compatibles con 11.8, 2.7.1/0.22.1 con cu118. No instala controladores ni CUDA Toolkit. La descarga puede ocupar varios GB. Si CUDA no está disponible, se recomienda CPU y GPU queda deshabilitada hasta prepararla y comprobarla. AMD/Intel usan CPU en esta versión Windows. No se cambia silenciosamente de GPU a CPU al iniciar un conteo si el dispositivo dejó de estar disponible: se muestra el error y se pide volver a detectar o elegir CPU.

El marcado de carriles sigue siendo necesario. El primer uso descarga YOLO; las imágenes Docker y dependencias también se descargan durante la primera configuración. El paquete no es offline.

## Simulación visual

«Simulación SUMO (demo)» abre SUMO-GUI de la venv del usuario con una red sintética,
plan fijo y 13 vehículos. No requiere iniciar Docker. Pulsa reproducir (Ctrl+A)
en SUMO; el retardo inicial es 150 ms para observar el movimiento. Cada apertura
crea una carpeta nueva en `workspace/resultados/sumo_gui`, sin sobrescribir corridas.
Al cerrar SUMO se guarda `tripinfo.xml`; cerrar antes de finalizar deja resultados
parciales. El lanzador evita abrir dos simulaciones propias simultáneas y cierra su
ventana al detener el sistema. No calcula Webster ni aplica planes a controladores.
La interfaz usa las opciones oficiales de [SUMO-GUI](https://sumo.dlr.de/docs/sumo-gui.html).

## Comprobaciones

```powershell
dotnet build desktop/Cysa.Launcher/Cysa.Launcher.csproj
./desktop/Cysa.Launcher/bin/Debug/net10.0-windows/win-x64/CYSA.exe --self-test "$PWD/artifacts/launcher-self-test.txt"
python tools/franco/probar.py
```

La autoprueba del ejecutable verifica proyectos distintos, selección de puertos, conservación del estado privado y rechazo de un paquete con secretos. Las pruebas Python cubren configuración por usuario y recuperación de una promoción interrumpida.

Para una comprobación completa de un paquete ya generado, sin usar la instalación habitual, ejecuta desde su carpeta:

```powershell
./CYSA.exe --integration-test "$env:LOCALAPPDATA/CYSA-ensayo" "$PWD/resultado-ensayo.txt"
```

Este modo ejecuta la misma configuración que el botón, verifica login OIDC de ambos roles, publica un conteo sintético por MQTT/TLS y confirma su lectura por API, prueba ambas APIs HTTP y las pruebas Python, detiene/reinicia y comprueba que no cambian los secretos. Al terminar detiene solo el proyecto del ensayo; conserva sus datos para diagnóstico. Requiere Docker e internet como la primera instalación normal.

Las verificaciones añaden exclusivamente registros marcados como prueba. No demuestran precisión con tráfico real ni sustituyen la calibración de la cámara. El ejecutable aún no tiene firma comercial; el instalador Python conserva su firma oficial.
