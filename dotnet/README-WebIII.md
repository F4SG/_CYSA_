# CYSA - Web API para Web III

ASP.NET Core sobre **.NET 10**, Entity Framework Core 10 y SQL Server. La instancia comprobada en el equipo de desarrollo es SQL Server 2025 Developer, versión 17.0.1155.3. La conexión utiliza autenticación integrada de Windows; el ZIP no incluye contraseñas, tokens ni bases locales.

Repositorio: https://github.com/F4SG/_CYSA_.git. Rama principal actual: [`main`](https://github.com/F4SG/_CYSA_/tree/main). La integración SQL Server y el lanzador actualizado están publicados en esta rama.

| Integrante | Usuario GitHub |
|---|---|
| Franco Andres Salas Gutierrez | F4SG |
| Leonardo Ariel Albornos Millares | LeonardoAlbornos-dev |
| Cristhian Arispe Vargas | Cristhian123987 |
| Fabrizio Dominguez Mogrovejo | FabrizioDominguez |

La participación individual se acredita con aportes y commits reales de cada integrante. La sesión del navegador no selecciona el autor Git. La planificación de responsables no constituye evidencia de participación realizada.

## Abrir desde el ejecutable

Extraer todo el paquete antes de abrir `CYSA.exe`. SQL Server debe estar instalado y su instancia debe aceptar la conexión del usuario Windows, con permiso para crear y administrar la base de demostración.

Si se ejecuta el proyecto del lanzador desde Visual Studio o desde este ZIP de fuentes,
detecta el repositorio y compila la API automáticamente al pulsar Swagger, Panel Web III
o Probar conexión. Ese modo requiere SDK .NET 10; la primera compilación puede restaurar
dependencias de NuGet. No hace falta preparar manualmente carpetas `app` o `services`.
El paquete Windows completo ya incluye los servicios compilados y no necesita el SDK.

* **Swagger (Web III)** aplica las migraciones pendientes, carga la semilla si falta y abre Swagger. El arranque conserva los datos que ya existan.
* **Panel Web III** abre las pantallas y formularios de laboratorio.
* **Recrear base de pruebas** borra exclusivamente `CYSA_WebIII_Demo`, la crea mediante migraciones y vuelve a cargar los datos. En el panel web también está el botón **Crear o recrear base y datos de prueba**, con la misma advertencia visible.

No se necesita ejecutar Configurar esta PC, Docker, cámara, YOLO, MQTT, SUMO ni el controlador para probar Web III. Los otros botones conservan el flujo del proyecto IoT. El primer arranque requiere conexión válida a SQL Server; no instala el motor automáticamente.

En Swagger, los botones de perfil locales permiten probar administrador, operador, evaluador y operador sin MFA. Son identidades sintéticas disponibles solo en Development, con Demo:Enabled y desde loopback; no son las cuentas GitHub ni cuentas reales de Keycloak. La MFA de laboratorio es simulada y dura cinco minutos. El administrador se renueva automáticamente cada cuatro minutos; en los otros perfiles se puede renovar pulsando otra vez su botón. Los tokens duran treinta minutos y no se incluyen en la entrega.

Swagger activa automáticamente **administrador** al cargar su esquema y renueva ese
perfil cada cuatro minutos mientras permanezca seleccionado. El docente puede
consultar todos los recursos y probar el CRUD sin copiar tokens. Los botones
conservan el cambio manual de perfil para comprobar permisos y errores: usar
**evaluador** para importar evaluaciones y **operador** para registrar decisiones,
según las reglas del dominio. Si se selecciona otro perfil, no se sustituye por
administrador durante la revisión. El acceso automático solo funciona cuando
el servidor permite la demostración local; no concede permisos en modo OIDC.

## Ejecutar desde el código

Requisitos: SDK .NET 10 y SQL Server local. Desde la carpeta `dotnet`, en PowerShell:

```powershell
dotnet restore
dotnet tool restore
$env:ConnectionStrings__Cysa = 'Server=localhost;Database=CYSA_WebIII_Demo;Integrated Security=True;TrustServerCertificate=True;Connect Timeout=10'
$env:ASPNETCORE_ENVIRONMENT = 'Development'
$env:Security__Mode = 'Demo'
$env:Demo__Enabled = 'true'
$env:Evaluaciones__BaseUrl = 'http://localhost:5183'
dotnet run --project src/Cysa.Web.Api --no-launch-profile -- --preparar-demo
dotnet run --project src/Cysa.Web.Api --no-launch-profile -- --urls http://localhost:5183
```

Abrir http://localhost:5183/demo o http://localhost:5183/swagger. Mantener el proceso de la terminal abierto. La clave de demostración se genera localmente en `dotnet/runtime`, excluido de Git y del ZIP.

La cadena anterior es un ejemplo sin credenciales. Para una instancia Express, adaptar `Server=localhost\SQLEXPRESS`. El botón de recreación admite únicamente los nombres de instancia locales listados en `DemoDatabase.cs` y el nombre exacto `CYSA_WebIII_Demo`; rechaza otras bases. El lanzador admite una cadena local mediante la variable `CYSA_WEBIII_CONNECTION`. Para LocalDB, usar `Server=(localdb)\MSSQLLocalDB`.

Aplicar únicamente las migraciones, sin cargar la semilla:

```powershell
dotnet ef database update --project src/Cysa.Web.Api --context CysaDb
```

Preparar sin borrar (`--preparar-demo`) y recrear deliberadamente (`--recrear-demo`) son operaciones distintas:

```powershell
dotnet run --project src/Cysa.Web.Api --no-launch-profile -- --recrear-demo
```

El arranque nunca usa EnsureCreated para el modelo nuevo: utiliza las migraciones incluidas. Las APIs SQLite históricas se conservan como programas de compatibilidad y para sus pruebas; el host unificado `Cysa.Web.Api` registra sus contextos con SQL Server.

## Modelo, operaciones y nombres

Hay 21 entidades del dominio, tres tablas intermedias y dos tablas de compatibilidad, Evaluaciones y Decisiones: 26 tablas de aplicación. FaseAcceso permite habilitar varios accesos en una fase; ValidacionMedicion y ValidacionEvento identifican las mediciones y eventos utilizados por cada validación. AccesoId en Fase identifica su cruce principal, que también queda incluido en FaseAcceso. Los accesos adicionales deben pertenecer a la misma intersección y respetar el mínimo peatonal. La tabla técnica `__EFMigrationsHistory` refleja las tres migraciones realmente aplicadas. La semilla contiene 15 registros por tabla, salvo Rol (administrador y operador) y MetricaPorAcceso (45: total, micro y resto por cada acceso evaluado). Todos los datos de la semilla son sintéticos y llevan `Prueba=true`.

El código se separa en Models, Dto, Controllers, Data y Services. Los DTO de entrada no admiten IDs generados por el servidor ni propiedades desconocidas. Las consultas están paginadas, admiten cancelación y usan EF Core asíncrono. Las restricciones protegen claves, referencias, valores únicos, intervalos, cantidades y los dos roles. Las reglas comprueban pertenencia de recursos, límites técnicos y mínimo peatonal L/0,9 + 5 s. No hay borrado en cascada de historial operativo.

Inventario y perfiles admiten CRUD según permisos y dependencias. Mediciones, estados, eventos y validaciones se registran y consultan; no exponen PUT ni DELETE. Bitácoras y roles se consultan. Los planes solo se editan como borradores; una recomendación requiere las métricas coherentes de sus accesos y permite pasar a validado. El operador decide con MFA mediante `/api/planes/{id}/decisiones-control`, proporcionando la validación exacta, un UUID de solicitud y un motivo. La misma solicitud se puede reintentar; una decisión distinta posterior se rechaza. Solo se actúa sobre planes de prueba; ninguna ruta activa semáforos reales.

| Acceso visible, óvalo y título | Contenido |
|---|---|
| Iniciar sesión | Perfil local de laboratorio |
| Administrar usuarios y roles | Perfiles y dos roles; no crea contraseñas ni cuentas GitHub/Keycloak |
| Gestionar configuraciones del corredor | Parámetros, bitácora y versiones de modelo futuras |
| Gestionar infraestructura | Corredores, intersecciones, accesos, carriles, cámaras y controladores |
| Gestionar planes semafóricos | Planes, fases, validaciones, métricas, recomendaciones y decisiones |
| Monitorear operación semafórica | Estados, mediciones, eventos y alertas |
| Consultar reportes de desempeño | Metadatos futuros; no presenta informes calculados |
| Cerrar sesión | Finalizar el acceso local |

Los nombres de acceso y título coinciden literalmente con el MDJ. Las subacciones tienen nombres específicos, como Crear registro o Autorizar plan. Las funciones Reporte y VersionModelo conservan su estado futuro; quince filas de ejemplo no equivalen a implementar generación de reportes o gobernanza de modelos. Las validaciones de la semilla explicitan que no provienen de ejecutar SUMO.

## Pruebas reproducibles

Desde el ejecutable, **SQL Server (Web III)** permite elegir la instancia local,
probarla y guardar la configuración con autenticación de Windows. La base es
siempre `CYSA_WebIII_Demo`. Probar no crea ni borra bases ni aplica migraciones.
Guardar detiene la API Web III de esta instalación; volver a abrir **Swagger
(Web III)** o **Panel Web III** aplica la configuración conservando los datos.
El motor SQL Server debe estar instalado y en ejecución. La configuración queda
en `%LOCALAPPDATA%\CYSA\webiii-sql.json` (o la carpeta `--data-dir` elegida), fuera
del repositorio. Si existe `CYSA_WEBIII_CONNECTION`, tiene prioridad y el diálogo
informa que se está usando una configuración externa.
Abrir el lanzador permite entrar a Web III sin ejecutar la medición YOLO de
CPU/GPU; la detección de hardware queda en su botón específico.

En el proyecto API, con `ASPNETCORE_ENVIRONMENT=Development`,
`dotnet run --no-launch-profile -- --probar-conexion` comprueba la conexión local
sin preparar la base. Devuelve si la base existe; puede conectar correctamente
aunque aún no exista. El código de salida es 0 si conecta y 1 si falla.

La búsqueda y los filtros se describen en [Consultas de infraestructura](docs/Consultas-infraestructura.md).
La comprobación de coherencia se ejecuta con `--verificar-demo` o
`GET /api/demo/verificacion`; ver [Verificación de semilla](docs/Verificacion-semilla.md).
Las reglas adicionales se detallan en [Validaciones](docs/Reglas-validacion.md).
`python scripts/Probar-ConexionSQL.py` verifica la conexión, el rechazo de otra base
o un servidor remoto, los errores sin credenciales y la conservación de los datos.

```powershell
dotnet build CYSA.Web.sln
dotnet test tests/Cysa.Api.Tests/Cysa.Api.Tests.csproj
python scripts/Probar-WebIII.py
```

El script Python usa solo biblioteca estándar, arranca la API en un puerto de pruebas y utiliza SQL Server real. Recrea **CYSA_WebIII_Demo** y prueba recursos, CRUD, 201/Location, PUT/DELETE, referencias inválidas, 400/404, 401/403, mínimo peatonal, auditoría protegida, decisiones con MFA, reintentos y persistencia después de reiniciar. Genera `runtime/webiii-integration/evidencias.json` sin tokens. No ejecutarlo contra una sesión de demostración cuyos datos se quieran conservar.

Para la prueba manual de persistencia: crear una intersección en Swagger y anotar el ID/Location; consultar GET por ID; detener la API y volverla a iniciar sin pulsar Recrear base; repetir el mismo GET y comprobar el contenido. El botón de recreación borra deliberadamente esos datos y, por tanto, no forma parte del reinicio usado para demostrar persistencia.

El PDF de entrega identifica las operaciones y códigos de las pruebas reales, e incluye una captura de Swagger. El ZIP de fuentes excluye bin, obj, .vs, runtime y secretos.

## Integración gradual con el proyecto IoT

`/api/integracion/conteos` recibe el contrato agregado de Python/MQTT, resuelve la infraestructura ya registrada y persiste en SQL Server; el mismo mensaje se reintenta sin duplicarse. `/api/integracion/conteos` por GET permite consultar esos datos con los nombres del contrato existente. `backend/app/http_repository.py` ofrece un adaptador explícito para probar ese contrato con una URL y una credencial de servicio. Debe conectarse al consumidor/configuración del despliegue antes de retirar su repositorio PostgreSQL.

El despliegue IoT actual conserva PostgreSQL/TimescaleDB para sus servicios de monitoreo y SQLite en los ejecutables API históricos. No se borran ni migran silenciosamente sus bases existentes. La API Web III funciona enteramente sobre SQL Server e integra los controladores de evaluación y decisión; el traslado completo de los estados/inventario del despliegue Docker requiere mapear identificadores, configurar OIDC de servicio y verificar sus datos. La entrega incluye la ruta de integración y pruebas, sin afirmar que el corredor real ya fue migrado.

Fuera del laboratorio: desactivar Demo:Enabled y configurar Security:Mode=Oidc, Security:Authority y Security:Audience; usar TLS y una cuenta SQL con permisos ajustados al despliegue. La API de demostración no certifica la procedencia de SUMO ni sustituye las pruebas de cámara/controlador.
