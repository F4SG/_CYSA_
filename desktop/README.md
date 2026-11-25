# Lanzador de pruebas CYSA para Windows

`CYSA.exe` usa WinForms y .NET 10. El ZIP Windows incluye las tres APIs autocontenidas y el instalador de Python firmado por Python Software Foundation. No necesita Git, Visual Studio ni un SDK .NET en la PC de destino. Docker Desktop con WSL 2 y contenedores Linux se instala por separado para el proyecto IoT.

## Ejecutar desde Visual Studio o desde las fuentes

Al iniciar el proyecto `desktop/Cysa.Launcher`, el lanzador localiza el repositorio
desde su carpeta de compilación. Si faltan los servicios publicados, prepara las
fuentes locales y publica automáticamente las APIs de Evaluaciones, Decisiones y
Web III al pulsar **Iniciar sistema** o **Abrir panel**. Las acciones exclusivas de
Web III solo preparan su propia API.
La primera compilación requiere SDK .NET 10 y acceso a NuGet si faltan dependencias.
Los siguientes arranques reutilizan las APIs mientras no cambien sus fuentes.

## Datos de práctica de Proyecto de Sistemas

En **2. Pruebas y práctica**, elige el conjunto de la demostración:

- **Cargar datos de práctica** repone las últimas 24 horas de muestras sintéticas,
  con tres carriles en el acceso norte, cambios de demanda por hora y tres clases.
  Las cinco propuestas de práctica usan autos, motos y micros y se evalúan en SUMO.
  Busca `DEMO_INT_01` y el contexto **Validación** en los reportes.
- **Cargar datos con video** abre el archivo que elijas. Marca tres carriles y pulsa
  **S**. Cuando termine el video, o al pulsar **Q**, el lanzador reemplaza la última
  importación con los intervalos procesados. Busca `DEMO_VIDEO` y **Validación**.
  Usa solo conteos agregados, con el ritmo de los intervalos del archivo. Para
  demostrar la recepción en vivo por MQTT/TLS, usa **Contar con video**. Los
  dos botones identifican sus conteos como `DEMO_VIDEO`.
- **Eliminar datos** permite quitar los conteos de video en vivo e importados o
  los datos sintéticos de práctica. Para una corrida anterior que aparece en
  `DEMO_INT_01`, elige **Video anterior (buscar por intervalo)** y copia la
  fecha, la hora de inicio y la de fin del período mostrado. Conserva
  el archivo de video, los registros ajenos al lanzador, la configuración del banco
  y las decisiones ya auditadas. Si queda un envío de práctica pendiente, espera
  su resultado antes de retirar los datos sintéticos.

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

## Prueba Arduino, MFA y operación física

Con la instalación preparada, pulsa **Probar Arduino** y elige el puerto USB de
tu equipo. La placa debe tener cargado el firmware `controlador/arduino/mmu_cysa`.
Comprueba los LEDs durante la prueba y, al finalizar en **TODO CORRECTO**, acepta
continuar con la integración MFA. El lanzador cierra la prueba serial, sustituye
el MMU simulado por esa placa y abre **Gestionar planes semafóricos**.

La tarjeta **Luces del Arduino** también aparece al abrir **Gestionar planes
semafóricos** desde el menú. Sus indicadores se encienden al recibir telemetría
reciente de la placa. Si no hay propuestas disponibles, usa **Cargar datos de
práctica** en el lanzador.

Ingresa como operador, autoriza una propuesta validada, completa el segundo
factor y confirma la decisión al volver. El panel distingue autorización, envío
y aplicación: solo muestra el éxito cuando coinciden el recibo y el plan activo
de la sesión física. Las luces mostradas son órdenes del controlador, no una
lectura óptica. Al confirmar que los LEDs coinciden, aparecen el cierre de la
prueba y **Volver al panel**, sin detener la operación.

**Detener Arduino** y **Reanudar Arduino** están en el bloque Arduino del
lanzador. Detener deja la placa en rojo intermitente y conserva el plan
confirmado. Reanudar reinicia el enlace y consulta en SQL Server su validación,
autorización MFA y aplicación anterior; recupera ese plan después de ámbar y
todo rojo. No activa propuestas sin confirmar ni emergencias temporales. Los
botones se habilitan según el estado; el panel permanece disponible al detener.
Tras cerrar y volver a abrir el lanzador, la placa espera un clic en Reanudar.

El puerto y el plan seleccionado se guardan en `arduino-control.json`, dentro
de la carpeta de datos de cada usuario. La telemetría se genera en
`workspace/infra/runtime/control/arduino-estado.json` y su consulta requiere
sesión. Ambos son datos de ejecución de esa instalación: no se descargan del
repositorio ni deben copiarse entre equipos. Otra PC genera sus propias cuentas,
certificados y claves con **Configurar esta PC**, selecciona su propia instancia
SQL y su puerto USB, y autoriza sus propios planes. Se requieren SQL Server,
ODBC Driver 18 y Docker Desktop/WSL 2 además del SDK .NET 10 si se usan fuentes.

## Construcción del paquete Windows

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
Keycloak, conservando claves existentes. El ingreso y las consultas usan usuario
y contraseña. El usuario enrola su autenticador con el QR en su primera acción
crítica; después utiliza códigos OTP, sin volver a escanear el QR.

El banco requiere SQL Server local y ODBC Driver 18. Si falta un servicio o
no conecta con MQTT, el lanzador informa el error y no declara el sistema listo.
La cámara y el video esperan la selección de fuente. La placa Arduino física
se inicia explícitamente; el arranque automático nunca abre un puerto serial.
**Detener sistema** y cerrar el lanzador detienen también S2 y el emulador.

Los accesos a módulos consultan la configuración de la instalación al pulsarlos;
no utilizan un puerto alternativo fijo si falta información. Antes de levantar
los servicios se publican sus direcciones en `panel/config.json`. Los módulos
se abren en la misma pestaña y disponen de **Volver al panel general**, también
en Swagger. El regreso recupera la sesión mediante Keycloak. Las páginas y la
configuración local se sirven sin caché para evitar enlaces de una versión anterior.

**Consultar reportes de desempeño** permanece dentro del panel general como
función futura, sin entrar a `/demo`. Los módulos de configuraciones y S2
recuperan automáticamente la sesión de Keycloak; no requieren otro clic en
**Iniciar sesión**. Si la sesión venció, Keycloak vuelve a pedir las credenciales.
El perfil de demostración y la sesión de `/demo` corresponden exclusivamente a
Web III, no al recorrido de Proyecto de Sistemas.

El lanzador prepara las fuentes en `%LOCALAPPDATA%/CYSA/workspace`. Instala Python por usuario solo si no encuentra Python 3.12; crea un entorno virtual propio. Genera secretos mediante el configurador existente, en un directorio temporal local, y promueve el resultado de forma reanudable. No vuelve a generar credenciales al reintentar ni reiniciar.

El nombre del proyecto Compose se deriva de la carpeta de datos del usuario; `docker compose -p` separa los volúmenes y redes. En el primer arranque elige seis puertos disponibles y los guarda. El override publica solo en `127.0.0.1`; OIDC y MQTT se configuran con esos puertos. Se requiere Compose 2.24.4+ por `!override`. Otros proyectos Docker existentes no se detienen ni se eliminan.

Las APIs .NET funcionan como procesos locales con SQLite en el `runtime` del usuario y escuchan en localhost. Se usan sus perfiles de demostración existentes, con MFA simulado, sin modificar las reglas de las APIs ni conectar con controladores reales. Al cerrar, el lanzador detiene sus procesos y su proyecto Compose, conservando los volúmenes.

El acceso **Gestionar configuraciones del corredor** del panel IoT abre
`/proyecto` con Keycloak real. Consultar no exige OTP; crear, modificar o eliminar
configuraciones exige administrador con MFA reciente en el servidor. Los datos
siguen perteneciendo a la base de laboratorio SQL Server, sin cambiar por sí
solos los parámetros del controlador S2. La demostración `/demo` de Web III
conserva su acceso independiente y sus tokens simulados no acceden a las rutas
`/api/proyecto`. **Gestionar planes semafóricos** abre S2, donde el operador
necesita MFA reciente para autorizar o rechazar. Tras completar MFA se recupera
el borrador y se solicita confirmar de nuevo; nunca se aplica una decisión
automáticamente al regresar de Keycloak.

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

«Simulación SUMO (demo)» abre un corredor sintético con los cruces A y B,
19 vehículos y un cruce peatonal. Pulsa reproducir (Ctrl+A). Ambos cruces parten
del plan fijo y la ambulancia naranja activa un evento predefinido al acercarse a A.
A avisa a B, que espera el despeje peatonal. Cada cruce pasa por ámbar y todo rojo
para dar prioridad y repite la transición al volver al plan fijo.

Los marcadores pasan de gris a ámbar durante el aviso y a verde durante la prioridad.
Cada apertura crea una carpeta en `workspace/resultados/sumo_gui` con
`eventos_corredor.csv`, `semaforos.xml` y `tripinfo.xml`. Una corrida completa registra
`corrida_completada`. Acepta cerrar los archivos al finalizar para guardar los XML.
El lanzador evita abrir dos simulaciones propias simultáneas.
La demo corre en SUMO sin Docker, cámara ni conexión con el controlador.
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

## Prueba automática del Arduino

El botón **Probar Arduino** detecta los puertos serie disponibles y permite elegir el de la placa.
Cierra antes el Monitor Serie de Arduino y cualquier controlador que use ese puerto. La placa debe
tener cargado `controlador/arduino/mmu_cysa/mmu_cysa.ino`. Esta prueba es para el banco de LEDs.
No necesita iniciar Docker, SQL Server, cámara ni los servicios del sistema.

Al pulsar **Probar** ejecuta la prueba existente de conexión, ciclo seguro, pérdida de señal,
conflicto de verdes y ámbar corto. Los pasos y el resultado aparecen en el registro de actividad.
La prueba cambia físicamente las luces; el cableado y los LEDs se comprueban mirando la placa.
Si hace falta RESET manual, termina con un aviso en lugar de bloquearse esperando una tecla.
Al terminar, el puerto se cierra y la placa puede quedar en rojo intermitente hasta reiniciar el controlador.

La parte superior del lanzador muestra la secuencia completa y explica el paso actual mientras
se ejecuta la prueba Arduino. Durante el ciclo normal indica las luces ordenadas para NS
(norte-sur) y EO (este-oeste). El resultado indica qué verificó el programa y recuerda observar
los LEDs. La ventana permite desplazamiento vertical para conservar visibles los textos de los botones.
