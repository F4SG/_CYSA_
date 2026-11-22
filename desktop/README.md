# Lanzador de pruebas CYSA para Windows

`CYSA.exe` usa WinForms y .NET 10. El ZIP Windows incluye las tres APIs autocontenidas y el instalador de Python firmado por Python Software Foundation. No necesita Git, Visual Studio ni un SDK .NET en la PC de destino. Docker Desktop con WSL 2 y contenedores Linux se instala por separado para el proyecto IoT.

## Ejecutar desde Visual Studio o desde las fuentes

Al iniciar el proyecto `desktop/Cysa.Launcher`, el lanzador localiza el repositorio
desde su carpeta de compilación. Si faltan `app` y los servicios publicados, prepara
las fuentes locales y publica automáticamente la API al pulsar **Swagger (Web III)**,
**Panel Web III**, **Recrear base de pruebas** o **Probar conexión** en el diálogo SQL.
La primera compilación requiere SDK .NET 10 y acceso a NuGet si faltan dependencias.
Los siguientes arranques reutilizan la API mientras no cambien sus fuentes.

SQL Server debe estar instalado y accesible. Después de compilar la API, el lanzador
aplica las migraciones y carga la semilla si hace falta. El arranque conserva los datos.
No requiere Docker, Python, cámara ni YOLO para Web III.

Al cerrar o pulsar **Detener sistema**, se detienen los procesos locales del lanzador.
Solo se intenta detener el proyecto Docker si se intentó iniciar el flujo IoT en esa
sesión. Una configuración de una sesión anterior no obliga a consultar Docker.
Si se usó IoT y Docker dejó de estar disponible, se registra un aviso y el cierre
continúa; los datos se conservan. No se apaga Docker Desktop ni el motor SQL Server.

El archivo `CYSA.exe` copiado por separado no contiene todo el proyecto. Para usarlo
sin fuentes ni SDK, extraer completo el ZIP Windows, con `app` y `services` junto al EXE.

## Construcción

Desde PowerShell 7, con Git y SDK .NET 10:

```powershell
./desktop/Crear-Paquete.ps1
```

La salida se crea en un directorio nuevo de `artifacts/desktop/`, excluido de Git. El script publica el lanzador y las tres APIs para `win-x64`, copia únicamente fuentes rastreadas y los archivos nuevos de esta entrega, descarga Python 3.12.10 de python.org, verifica su firma y escribe manifiesto y huellas SHA-256. El ZIP contiene una carpeta `CYSA-Windows` con `CYSA.exe`, `app`, `services`, `dependencies` y `LEEME.txt`.

No se empaquetan `.git`, entornos virtuales, modelos, videos, bases, claves, tokens, `.env`, `runtime`, resultados ni respaldos. El estado del equipo que construye el ZIP no se reutiliza. El manifiesto distingue un paquete construido con cambios locales pendientes de commit.

## Instalación y aislamiento

En una PC ya configurada, abrir CYSA inicia automáticamente el monitoreo IoT,
las APIs de gestión, el banco S2 y su controlador con MMU simulado. **Iniciar
sistema** reintenta el arranque completo y **Abrir panel** también comprueba e
inicia los servicios antes de abrir el navegador. Los botones del panel reciben
las direcciones locales de Web III y S2; no es necesario iniciar Swagger aparte.
El arranque prepara las dependencias S2, la clave de despacho y MFA OTP de
Keycloak, conservando claves existentes. Cada usuario enrola su autenticador en
el siguiente ingreso si aún no tiene OTP.

El banco requiere SQL Server local y ODBC Driver 18. Si falta un servicio o
no conecta con MQTT, el lanzador informa el error y no declara el sistema listo.
La cámara y el video esperan la selección de fuente. La placa Arduino física
se inicia explícitamente; el arranque automático nunca abre un puerto serial.
**Detener sistema** y cerrar el lanzador detienen también S2 y el emulador.

El lanzador prepara las fuentes en `%LOCALAPPDATA%/CYSA/workspace`. Instala Python por usuario solo si no encuentra Python 3.12; crea un entorno virtual propio. Genera secretos mediante el configurador existente, en un directorio temporal local, y promueve el resultado de forma reanudable. No vuelve a generar credenciales al reintentar ni reiniciar.

El nombre del proyecto Compose se deriva de la carpeta de datos del usuario; `docker compose -p` separa los volúmenes y redes. En el primer arranque elige seis puertos disponibles y los guarda. El override publica solo en `127.0.0.1`; OIDC y MQTT se configuran con esos puertos. Se requiere Compose 2.24.4+ por `!override`. Otros proyectos Docker existentes no se detienen ni se eliminan.

Las APIs .NET funcionan como procesos locales con SQLite en el `runtime` del usuario y escuchan en localhost. Se usan sus perfiles de demostración existentes, con MFA simulado, sin modificar las reglas de las APIs ni conectar con controladores reales. Al cerrar, el lanzador detiene sus procesos y su proyecto Compose, conservando los volúmenes.

El botón cámara pide un índice; el de video abre un selector de archivos. Ambos usan el modo CPU o GPU elegido en la ventana y guardado por usuario, con tamaño de inferencia 640 px. Después de configurar o pulsar «Detectar y recomendar» se mide YOLO a 640 px con imágenes sintéticas: dos calentamientos y la mediana de cinco inferencias por dispositivo, sincronizando CUDA. La GPU más rápida se recomienda solo si mejora más del 10 % frente a CPU; en otro caso se recomienda CPU. La opción recomendada se marca en verde con «Recomendado», independientemente de la elección manual. La medición depende de la carga y energía actuales; se puede repetir con «Detectar y recomendar».

GPU requiere NVIDIA/CUDA y superar una inferencia real. «Preparar GPU» instala los pares oficiales de PyTorch/torchvision de [las instrucciones de PyTorch](https://pytorch.org/get-started/previous-versions/), según la versión máxima CUDA que anuncia `nvidia-smi`: 2.14.1/0.29.1 con cu130 o cu126; para controladores antiguos compatibles con 11.8, 2.7.1/0.22.1 con cu118. No instala controladores ni CUDA Toolkit. La descarga puede ocupar varios GB. Si CUDA no está disponible, se recomienda CPU y GPU queda deshabilitada hasta prepararla y comprobarla. AMD/Intel usan CPU en esta versión Windows. No se cambia silenciosamente de GPU a CPU al iniciar un conteo si el dispositivo dejó de estar disponible: se muestra el error y se pide volver a detectar o elegir CPU.

El marcado de carriles sigue siendo necesario. El primer uso descarga YOLO; las imágenes Docker y dependencias también se descargan durante la primera configuración. El paquete no es offline.

## Apariencia del centro de pruebas

El selector «Tema» permite cambiar entre Claro y Oscuro con la paleta de
`panel/tokens.css`. La elección se guarda por usuario en `appearance.json`;
los registros visibles se recolorean al cambiar de tema sin perder su contenido.
Los botones incluyen una descripción y conservan los nombres de las acciones.
La recomendación CPU/GPU mantiene su destacado verde en ambos temas.

El registro muestra hora y categoría de actividad: Docker en azul, equipo en
ámbar y SUMO en violeta. Los resultados correctos se destacan en verde, las
advertencias en ámbar y los errores en rojo, conservando también el texto del
aviso. «Seguir salida» controla el desplazamiento automático y «Limpiar vista»
vacía solo la consola de la ventana; el archivo de registro se conserva.

## Demostración SUMO

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

Este modo ejecuta la misma configuración que el botón, verifica disponibilidad de servicios y rechazo de consultas sin sesión, prueba las APIs HTTP y las pruebas Python, detiene/reinicia y comprueba que no cambian los secretos. El ingreso de ambos roles con OTP se valida desde el navegador; el diagnóstico no utiliza contraseñas guardadas para intentar omitir MFA. Al terminar detiene solo el proyecto del ensayo; conserva sus datos para diagnóstico. Requiere Docker, SQL Server, ODBC Driver 18 e internet como la primera instalación normal.

Las verificaciones añaden exclusivamente registros marcados como prueba. No demuestran precisión con tráfico real ni sustituyen la calibración de la cámara. El ejecutable aún no tiene firma comercial; el instalador Python conserva su firma oficial.
