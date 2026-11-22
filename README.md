# CYSA

[Casos de uso: ubicación y acceso](#casos-de-uso-ubicación-y-acceso) · [Web III: API, entrega y pruebas](#web-iii) · [Proyecto de Sistemas I: monitoreo IoT](#proyecto-de-sistemas-i)

## Casos de uso: ubicación y acceso

Los botones conservan exactamente los nombres del diagrama de casos de uso.
En el **panel IoT** (`http://localhost:8088/`), inicia sesión con Keycloak para
ver el menú lateral. El **panel Web III** está en `/demo` de la API local:
abre **Swagger (Web III)** desde el centro de pruebas y cambia `/swagger` por
`/demo` en esa misma dirección; el puerto depende de la instalación. Si usas
la alternativa por consola de esta guía, la dirección es
`http://localhost:5183/demo`.

| Caso de uso / nombre exacto del botón | Dónde se encuentra | Cómo se accede y qué permite |
| --- | --- | --- |
| Iniciar sesión | Barra superior de ambos paneles; también en la bienvenida del panel IoT. | En IoT, pulsa el botón e ingresa con tu cuenta de Keycloak. En Web III, selecciona el perfil de demostración y pulsa el botón; la MFA de esa sesión es simulada. |
| Administrar usuario y roles | Menú lateral del panel IoT, visible para el administrador; menú **CASOS DE USO** de Web III. | En IoT, entra como administrador para gestionar cuentas y asignar los dos roles existentes. En Web III, selecciona el botón y el recurso **Usuarios** o **Roles**; las escrituras requieren el perfil administrador y el catálogo de roles es de consulta. |
| Gestionar configuraciones del corredor | Menú lateral del panel IoT y menú **CASOS DE USO** de Web III. | El botón de IoT abre el módulo de Web III en otra pestaña. En Web III, selecciona **Configuraciones técnicas**; el administrador puede gestionar los registros de laboratorio. Esto no modifica por sí solo los parámetros del banco S2. |
| Gestionar infraestructura | Menú lateral del panel IoT y menú **CASOS DE USO** de Web III. | En IoT, consulta los activos registrados. En Web III, elige el recurso: corredores, intersecciones, accesos, carriles, fuentes de detección o controladores; el administrador dispone de las operaciones de gestión. |
| Gestionar planes semafóricos | Menú lateral del panel IoT y menú **CASOS DE USO** de Web III; sección del mismo nombre en el banco S2. | El botón lateral de IoT abre Web III. Allí se consultan y gestionan datos de laboratorio; el operador puede decidir sobre planes validados con MFA simulada. Para ejecutar el flujo con SUMO y controlador emulado, usa el botón superior **Operación semafórica (S2)** de IoT, o abre `http://localhost:5184` tras iniciar el banco: el administrador genera y el operador autoriza o rechaza con MFA real reciente. |
| Monitorear operación semafórica | Menú lateral del panel IoT, menú **CASOS DE USO** de Web III y sección del mismo nombre en el banco S2. | En IoT, consulta conteos por intersección, acceso y carril; la vista adicional **Comunicación** muestra fase, plan y último estado. En Web III se consultan recursos de laboratorio. En S2 se muestran los estados reportados por el controlador emulado. |
| Consultar reportes de desempeño | Menú lateral del panel IoT y menú **CASOS DE USO** de Web III. | El botón de IoT abre Web III. Selecciona **Reportes** para consultar metadatos sintéticos. La generación de reportes de desempeño sigue siendo una función futura. |
| Cerrar sesión | Barra superior de ambos paneles, después de iniciar sesión; también en el banco S2. | Pulsa el botón en el panel utilizado. En IoT y S2 se utiliza la sesión de Keycloak; Web III cierra su sesión independiente de demostración. |

Los accesos desde IoT a Web III usan la dirección `webApiBase` de la
configuración local del panel; la API Web III debe estar iniciada y esa dirección
debe coincidir con su puerto. El banco S2 requiere la preparación descrita en
[la guía de integración](controlador/INTEGRACION.md). Los nombres coincidentes
identifican el caso de uso, pero cada entorno conserva el alcance indicado en
la tabla.

## Web III

Entrega de la Web API con SQL Server.

**Proyecto:** CYSA — Web API para gestión semafórica. Desarrollado en **C# y
ASP.NET Core sobre .NET 10**, con **Entity Framework Core 10 y SQL Server**.
Repositorio: [F4SG/_CYSA_](https://github.com/F4SG/_CYSA_), rama [main](https://github.com/F4SG/_CYSA_/tree/main).

| Integrante | Usuario GitHub |
|---|---|
| Franco Andres Salas Gutierrez | [F4SG](https://github.com/F4SG) |
| Leonardo Ariel Albornos Millares | [LeonardoAlbornos-dev](https://github.com/LeonardoAlbornos-dev) |
| Cristhian Arispe Vargas | [Cristhian123987](https://github.com/Cristhian123987) |
| Fabrizio Dominguez Mogrovejo | [FabrizioDominguez](https://github.com/FabrizioDominguez) |

### Qué se entrega para Web III

El ZIP **CYSA_WebAPI.zip** contiene el proyecto completo desde fuentes, sus tres
migraciones EF Core, este contenido de configuración en su README y el
**PDF de evidencias**. Excluye `bin`, `obj` y `.vs`. La solución está en
[dotnet/CYSA.Web.sln](dotnet/CYSA.Web.sln) y la API principal es
[Cysa.Web.Api](dotnet/src/Cysa.Web.Api/Cysa.Web.Api.csproj).

El PDF se entrega dentro del ZIP como **Evidencias_WebIII.pdf**; los archivos de
entrega se distribuyen por Teams y no se alojan en el historial Git. Su contenido incluye:

| Evidencia | Operación y código HTTP identificados |
|---|---|
| Captura de Swagger UI con endpoints | Rutas, parámetros, esquemas y operaciones de la API |
| Operaciones exitosas | GET 200; POST 201 con Location; PUT 204; DELETE 204 |
| Validación y recurso inexistente | Solicitud inválida 400 y consulta de ID inexistente 404 |
| Persistencia después de reiniciar | GET por ID 200 antes y después de detener e iniciar la API, con el mismo contenido y sin recrear la base |

El ZIP incluye también **Resultados_pruebas_WebIII.json**, con el registro de
151 comprobaciones HTTP sobre SQL Server, las operaciones y sus códigos.

### Inicio rápido paso a paso para el docente

**Requisitos antes de comenzar:** Windows, **SDK .NET 10** y **SQL Server local**
instalado y en ejecución. Se necesita internet para restaurar las dependencias
la primera vez. No se requieren Docker, Python, cámara, YOLO ni SUMO para Web III.

**1. Descargar y extraer todo el ZIP.** Descarga **CYSA_WebAPI.zip** de la entrega
en Teams. También puedes descargar las fuentes desde GitHub: rama **main** →
**Code** → **Download ZIP**. Haz clic derecho en el ZIP → **Extraer todo**.
No abras el proyecto desde la vista del archivo comprimido.

**2. Identificar la carpeta raíz.** Entra en las carpetas extraídas hasta ver
**desktop**, **dotnet** y **README.md** en el mismo nivel. Esa es la carpeta desde
la que debes ejecutar los comandos. En el ZIP de Teams se llama **CYSA-WebIII**;
en la descarga de GitHub el nombre puede ser diferente.

**3. Abrir PowerShell y entrar a esa carpeta con `cd`.** Por ejemplo, si guardaste
el ZIP de Teams en Descargas y usaste la carpeta de extracción predeterminada,
ejecuta esta línea y pulsa **Enter**:

```powershell
cd "$env:USERPROFILE\Downloads\CYSA_WebAPI\CYSA-WebIII"
```

La ruta es un ejemplo: si extrajiste el ZIP en otra ubicación, copia la ruta de
la carpeta raíz desde la barra de direcciones del Explorador y úsala entre
comillas después de `cd`. No copies literalmente una ruta que no exista en tu PC.

**4. Comprobar la ubicación.** Ejecuta esta línea y pulsa **Enter**:

```powershell
dir
```

La lista debe mostrar **desktop** y **dotnet**. Si no aparecen, vuelve al paso 2;
no continúes desde una carpeta superior ni desde `dotnet`.

**5. Comprobar el SDK.** Ejecuta esta línea y pulsa **Enter**:

```powershell
dotnet --list-sdks
```

Debe aparecer una versión **10.x**. Si el comando no existe o no aparece ese SDK,
instala SDK .NET 10 y abre una nueva PowerShell antes de continuar.

**6. Restaurar las dependencias del centro de pruebas.** Ejecuta únicamente esta
línea y espera a que termine antes de escribir la siguiente:

```powershell
dotnet restore .\desktop\Cysa.Launcher\Cysa.Launcher.csproj
```

**7. Abrir el centro de pruebas.** Ejecuta esta línea y pulsa **Enter**:

```powershell
dotnet run --project .\desktop\Cysa.Launcher\Cysa.Launcher.csproj --no-restore
```

Espera la compilación. Aparecerá la ventana **CYSA / Centro de pruebas**, con los
botones del sistema. Mantén abierta PowerShell y esa ventana durante la revisión.
**Ejecuta cada línea anterior por separado; no hace falta ejecutar los comandos
de la alternativa por consola que aparece más abajo.**

**8. Elegir SQL Server en el centro de pruebas.** Pulsa **SQL Server (Web III)**.
Selecciona una instancia que esté instalada en tu equipo: **localhost**, una
instancia **SQLEXPRESS** de la lista o **(localdb)\MSSQLLocalDB**. Pulsa
**Probar conexión**, espera el resultado **Conexión correcta** y pulsa
**Guardar configuración**. La primera comprobación puede compilar y descargar
dependencias de la API. Este paso no borra ni crea la base y no instala SQL Server.
Si falla, comprueba el servicio y los permisos de Windows antes de continuar.

**9. Abrir Swagger.** En el centro de pruebas pulsa **Swagger (Web III)**.
Espera a que termine la preparación: el lanzador inicia la API, aplica las
migraciones pendientes, crea la base si falta y carga los datos de prueba si
corresponde. Se abrirá Swagger UI en el navegador con los endpoints disponibles.
El puerto se asigna a esta instalación; usa la dirección que abre el botón.

**10. Revisar como administrador.** Al cargar Swagger se selecciona automáticamente
el **administrador de demostración**. Espera a ver **Perfil activo: administrador**.
No necesitas iniciar sesión con GitHub ni copiar un token en Authorize.
El perfil se renueva durante la revisión. Los botones de operador y evaluador
siguen disponibles para las operaciones específicas y las pruebas de permisos;
la MFA de este laboratorio es simulada.

**11. Probar los endpoints de Administrar usuario y roles.** Las operaciones
están agrupadas por función; los nombres de grupo no son las rutas de la API.
Busca y despliega el grupo **Administrar usuario y roles**. Puedes usar **Ctrl+F**
y escribir `Administrar usuario y roles` o `/api/roles` si no lo ves.

**Ejemplo inicial: listar los roles (200).**

1. Dentro de **Administrar usuario y roles**, pulsa la fila azul **GET /api/roles**,
   la que no lleva `{id}` al final.
2. Pulsa **Try it out**.
3. Deja **Pagina** en `1` y **Tamano** en `50`; deja vacíos los demás filtros.
4. Pulsa **Execute**.
5. Baja hasta **Server response**. En **Code** debe aparecer **200** y en
   **Response body** una lista con los roles `administrador` y `operador`,
   incluyendo sus campos `id`, `nombre`, `descripcion` y `prueba`.
   La tabla **Responses** situada más abajo documenta los códigos posibles;
   el resultado real de tu solicitud está en **Server response**.
6. Anota el `id` del rol `operador`: se utiliza en el ejemplo de creación siguiente.

En ese mismo grupo puedes probar estas operaciones sin buscar otros apartados:

| Qué probar | Fila y valores en Swagger | Resultado esperado |
|---|---|---|
| Listar usuarios de prueba | **GET /api/usuarios**, **Try it out**, **Pagina** `1`, **Tamano** `50`, filtros vacíos, **Execute** | **200** y al menos 15 registros de la semilla |
| Consultar un rol por ID | **GET /api/roles/{id}**, introducir un `id` devuelto por el listado y pulsar **Execute** | **200** y ese rol |
| Validación de parámetros | **GET /api/roles**, **Pagina** `0`, **Tamano** `50`, **Execute** | **400** porque la página debe ser como mínimo 1 |
| Recurso inexistente | **GET /api/roles/{id}**, **id** `999999`, **Execute** | **404** en la base de demostración |

Después del error 400, vuelve a poner **Pagina** en `1` para continuar.
`GET /api/intersecciones` también está disponible, dentro de **Gestionar
infraestructura**; no es necesario buscarlo para realizar estos primeros ejemplos.

**12. Crear un registro, comprobar persistencia y cerrar.** Continúa en el grupo
**Administrar usuario y roles**:

1. Despliega **POST /api/usuarios**, pulsa **Try it out** y reemplaza el cuerpo
   del formulario por este JSON. En `rolId` usa el ID del rol `operador` que
   anotaste en el paso 11; en una semilla nueva suele ser `2`:

```json
{
  "prueba": true,
  "rolId": 2,
  "identificadorIdp": "docente-prueba-001",
  "nombre": "Revisión del docente",
  "activo": true,
  "mfaHabilitado": false
}
```

2. Pulsa **Execute**. Debes recibir **201**. Anota el `id` del **Response body**
   y la cabecera **Location**. El identificador es único: si repites la prueba,
   cambia `docente-prueba-001` por otro valor, por ejemplo `docente-prueba-002`.
   Este registro es sintético; no crea una cuenta de GitHub ni de Keycloak.
3. Despliega **GET /api/usuarios/{id}**, pulsa **Try it out**, escribe el `id`
   recibido y pulsa **Execute**. Debe devolver **200** y el mismo usuario.
4. Cierra el centro de pruebas. Vuelve a ejecutar la línea del paso 7, abre
   **Swagger (Web III)** y espera **Perfil activo: administrador**.
5. Regresa a **Administrar usuario y roles → GET /api/usuarios/{id}**, introduce
   el mismo `id` y pulsa **Execute**. Debe devolver **200** con los mismos datos:
   esa es la comprobación de persistencia después del reinicio.
6. Si deseas limpiar solo ese registro temporal, usa **DELETE /api/usuarios/{id}**
   con el `id` que acabas de crear; debe responder **204**.

**No pulses Recrear base de pruebas entre las dos consultas**, porque ese botón
borra deliberadamente CYSA_WebIII_Demo y vuelve a cargar la semilla. Al terminar,
cierra el centro de pruebas: detiene sus procesos locales y conserva los datos.

### Alternativa por consola: SQL Server, migraciones y Swagger

Descarga y extrae todo el repositorio o el ZIP. Requisitos: **SDK .NET 10**,
acceso a NuGet para restaurar dependencias y **SQL Server local** instalado y
en ejecución. La cuenta Windows debe poder crear y administrar la base de prueba.
Desde la raíz del proyecto, en PowerShell:

```powershell
Set-Location dotnet
dotnet restore
dotnet tool restore

# Ejemplo con autenticación integrada de Windows, sin credenciales reales.
$env:ConnectionStrings__Cysa = 'Server=localhost;Database=CYSA_WebIII_Demo;Integrated Security=True;TrustServerCertificate=True;Connect Timeout=10'
$env:ASPNETCORE_ENVIRONMENT = 'Development'
$env:Security__Mode = 'Demo'
$env:Demo__Enabled = 'true'
$env:Evaluaciones__BaseUrl = 'http://localhost:5183'

# Crea la base si no existe y aplica las migraciones pendientes.
dotnet ef database update --project src/Cysa.Web.Api --context CysaDb

# Prepara los datos sintéticos si faltan, conservando los datos existentes.
dotnet run --project src/Cysa.Web.Api --no-launch-profile -- --preparar-demo

# Inicia la API; mantener esta terminal abierta.
dotnet run --project src/Cysa.Web.Api --no-launch-profile -- --urls http://localhost:5183
```

Para SQL Server Express, cambia `Server=localhost` por `Server=localhost\SQLEXPRESS`;
para LocalDB, por `Server=(localdb)\MSSQLLocalDB`. Usa una instancia disponible en
tu equipo. La base de demostración es **CYSA_WebIII_Demo**.

Abre **http://localhost:5183/swagger** o el panel **http://localhost:5183/demo**.
Swagger selecciona automáticamente el administrador de laboratorio y renueva ese
perfil. La MFA es simulada; los botones conservan los perfiles de evaluador y
operador para sus operaciones específicas y las pruebas de permisos.

La semilla contiene al menos 15 registros por tabla de aplicación, salvo los dos
roles del modelo. Para demostrar persistencia, crea un registro, consulta su ID,
detén la API con Ctrl+C, vuelve a ejecutar únicamente el último comando y repite
el GET. No uses recreación entre lecturas: borra deliberadamente los datos.

Web III se prueba sin Docker, Python, cámara, YOLO ni SUMO. La
[guía técnica de Web III](dotnet/README-WebIII.md) detalla DTO, recursos, reglas,
pruebas reproducibles e integración gradual con el resto del sistema.

## Proyecto de Sistemas I

Monitoreo IoT y conteo vehicular.

Desde aquí se documenta el proyecto de **Sistemas I**: cámara o video, detección,
MQTT, FastAPI, identidad, panel y simulación. Sus requisitos e instrucciones
corresponden a ese flujo; para revisar la entrega de **Web III**, usa la sección
anterior. Para estos comandos, abre una terminal en la raíz del repositorio, no
en la carpeta `dotnet`. El despliegue IoT conserva su persistencia PostgreSQL/SQLite mientras
se completa la integración gradual documentada.

Sistema de monitoreo de tránsito: detecta y cuenta vehículos, guarda los resultados y los muestra en un panel web con acceso por roles.

**Esta entrega incluye el conteo con cámara o video y el asistente para elegir la fuente y marcar carriles.** El monitoreo de vías trabaja en modo sombra. El [banco S2 de integración](controlador/INTEGRACION.md) permite enviar planes únicamente al controlador emulado/Arduino de laboratorio; no actúa sobre semáforos de la vía pública. FastAPI atiende el monitoreo; `dotnet/` incorpora la Web API de Web III con SQL Server y conserva los dos servicios históricos de evaluación y decisiones para compatibilidad.

### Sprint 1 — implementado y revisado

Su alcance es detectar, contar y consultar el flujo vehicular en modo sombra,
sin enviar órdenes a semáforos. La revisión del Sprint 1 ya fue realizada.

- Detectar y contar autos, motos y micros por carril.
- Elegir una cámara o un archivo de video desde el asistente.
- Marcar la vía y el sentido de conteo antes de empezar.
- Consultar conteos, inventario y estados reportados desde el navegador.
- Ingresar como operador o administrador; gestionar usuarios con el segundo rol.
- Guardar conteos agregados en CSV y enviarlos al panel mediante MQTT.

Para reproducirlo, seguir las secciones **1 a 4** y el guion de **5. Probar el
Sprint 1** de esta misma guía. La evidencia de conteo y sus límites se conservan
en esa sección.

### Sprint 2 — controlador e integración del banco

El código está implementado y se probó con SQL Server, SUMO, MQTT y el Arduino
conectado por COM3.

| Parte | Qué incluye |
| --- | --- |
| Controlador y MMU | Fases de verde, ámbar y todo rojo; comprobación de conflictos en Arduino; watchdog y modo local seguro ante pérdida del centro. |
| Cálculo y simulación | Conteos de prueba → SQL Server → propuesta Webster → comparación con el plan fijo usando SUMO real. |
| Decisión y envío | El administrador calcula; el operador autoriza con MFA reciente. La orden viaja firmada por MQTT/TLS y cambia de plan al terminar un todo rojo. |
| Confirmación y consulta | Panel **Operación semafórica (S2)** con planes, evidencia, fase y estado reportados; recibo de aplicación y auditoría guardados en SQL Server. |
| Prioridades del banco | Comparación de prioridad para micros y eventos de emergencia definidos por fecha/hora, conservando los tiempos de seguridad. |

Los [pendientes del Sprint 2](#pendientes-del-sprint-2) están al final de este README.

Consultar la [guía base del controlador](controlador/README.md), la
[integración paso a paso](controlador/INTEGRACION.md) y los
[resultados de verificación](controlador/VERIFICACION.md).

Para esa integración, inicia primero el entorno IoT de las secciones siguientes. Después,
desde la raíz del repositorio, ejecuta cada línea en una PowerShell distinta y deja ambas abiertas:

```powershell
.\iniciar_operacion.ps1
```

```powershell
.\iniciar_controlador.ps1 -Puerto COM3 -Mqtt -RecibirPlanes
```

Abre `http://localhost:5184` o **Operación semafórica (S2)** en el panel. SQL Server local
y ODBC Driver 18 deben estar instalados. El administrador calcula; el operador autoriza
con OTP real de Keycloak. El primer acceso permite registrar su autenticador. La base
operativa es `CYSA_Control_S2`, independiente de `CYSA_WebIII_Demo`. El monitoreo IoT
anterior conserva su almacén histórico; los nuevos planes, decisiones, envíos, conteos
y estados S2 se guardan en SQL Server. Consulta los pasos y límites en la guía enlazada.

[Uso de los patrones creacionales y de los entornos de prueba](casos_estudio/README.md).

### 1. Antes de instalar

Esta guía usa **Windows y PowerShell**. Ejecuta los comandos desde la carpeta del repositorio.

| Necesitas | Para qué |
| --- | --- |
| Git | Descargar y actualizar el código |
| Python 3.12 de 64 bits | Ejecutar el detector y las herramientas |
| Docker Desktop abierto, con contenedores Linux/WSL 2 | Ejecutar base, API, identidad, broker y panel |
| Internet durante la instalación | Descargar paquetes, imágenes y pesos YOLO |
| Video local o cámara con permisos de Windows | Probar el conteo |
| Node.js, opcional | Ejecutar las pruebas JavaScript |

Antes de continuar, comprueba:

```powershell
git --version
py -3.12 --version
docker info
```

Si `docker info` falla, abre Docker Desktop y espera a que termine de iniciar. Deja libres los puertos **8088**, **8080** y **8883**. Para probar sin GPU usa el perfil CPU indicado en la sección 4; será más lento. El perfil de video a 960 px usa una GPU NVIDIA y necesita PyTorch con CUDA compatible.

### 2. Instalar por primera vez

#### Descargar y crear el entorno

```powershell
git clone https://github.com/F4SG/_CYSA_.git CYSA
Set-Location CYSA
py -3.12 -m venv .venv
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $py -m pip install -r backend/requirements.txt -r deteccion/requirements.txt -r simulacion/requirements.txt -r controlador/requirements.txt -r tests/requirements.txt
```

Usar `$py` evita tener que activar el entorno virtual. En cada PowerShell nueva, entra a `CYSA` y vuelve a definir `$py` con el comando anterior.

#### Generar la configuración local

Con Docker Desktop funcionando:

```powershell
& $py tools/franco/preparar_local.py --repo .
```

Este paso genera automáticamente las contraseñas, certificados MQTT, configuración del panel y archivos de entorno. **Se ejecuta una sola vez**: si ya tienes `infra/.env` o `infra/runtime`, sigue la sección 7 para actualizar.

No copies `.env.example` sobre el `.env` generado. No subas `infra/runtime`, contraseñas ni certificados privados a GitHub.

#### Levantar los servicios

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build
docker compose --env-file infra/.env -f infra/compose.yaml ps
```

El primer arranque puede tardar varios minutos por las descargas. Comprueba que Keycloak haya iniciado:

```powershell
Invoke-RestMethod http://localhost:8080/realms/cysa
```

Si todavía no responde, espera y repite esa consulta. Cuando responda, termina de configurar los usuarios y la interfaz:

```powershell
& $py tools/franco/configurar_usuarios_local.py
& $py tools/franco/configurar_interfaz_local.py
& $py tools/franco/endurecer_identidad_local.py
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build --no-deps api
Invoke-RestMethod http://localhost:8088/health
```

**Resultado esperado:** `status` igual a `ok` y `activacion_planes` igual a `false`. Esto comprueba que la API responde; la prueba de conteo de la sección 5 comprueba el recorrido de los datos.

### 3. Entrar al panel

Abre **http://localhost:8088/** y pulsa **Ingresar**.

Consulta las credenciales generadas en tu equipo abriendo este archivo con un editor:

```powershell
notepad infra/runtime/clientes/usuarios-locales.json
```

| Cuenta inicial | Qué permite |
| --- | --- |
| `operador` | Consultar flujo vehicular, inventario y comunicación |
| `administrador` | Lo anterior, más gestionar usuarios y escribir inventario mediante la API |

Las contraseñas son diferentes en cada instalación. No muestres este archivo durante la presentación. Las cuentas adicionales de otra máquina no se descargan al clonar el proyecto.

Para cambiar entre roles, cierra sesión antes de ingresar con la otra cuenta.

### 4. Configurar y ejecutar el conteo

Primero levanta Docker y entra al panel. El detector se ejecuta en Windows; Docker no abre la cámara.

#### Si tienes GPU NVIDIA configurada

Haz doble clic en **`iniciar_conteo.bat`**, o ejecuta desde PowerShell:

```powershell
.\iniciar_conteo.ps1
```

Usa `deteccion/config/video_santa_cruz.yaml`, con GPU `device: 0` y tamaño de inferencia 960. Antes puedes comprobar si tu instalación de PyTorch reconoce CUDA:

```powershell
& $py -c "import torch; print(torch.cuda.is_available())"
```

Si devuelve `False`, usa la opción CPU para esta prueba.

#### Si usarás CPU

```powershell
.\iniciar_conteo.ps1 -Perfil deteccion/config/carriles_cristhian.yaml
```

Si PowerShell bloquea los scripts, usa esta alternativa directa con Python:

```powershell
& $py tools/cristhian/detector.py iniciar --config deteccion/config/carriles_cristhian.yaml --fuente --marcar zona --salida resultados/conteos_demo.csv
```

#### Pasos del asistente

1. Elige **1: cámara** o **2: archivo de video**. El video de la evidencia no está incluido; prepara tu propio archivo antes de presentar.
2. Selecciona la cámara por nombre o elige el archivo en la ventana.
3. En el editor, marca las **cuatro esquinas de la vía** que quieres contar; excluye acera, puente y otros flujos.
4. Ajusta la cantidad de carriles con las teclas **1 a 8**. Revisa la flecha roja del sentido; **D** la invierte.
5. Pulsa **S** para guardar e iniciar el conteo. **U** deshace un punto; **Q/Esc** sale del editor. Confirma que guardaste antes de continuar.
6. Deja correr el detector. **Q** termina el conteo.

Para marcar únicamente una línea de dos puntos por carril, agrega `-Linea` al comando de PowerShell. La línea no debe atravesar otros flujos.

Los pesos YOLO `.pt` no vienen en Git. Prepara `deteccion/modelos/yolo26s.pt` antes de la presentación; Ultralytics puede descargarlo al primer uso con internet. Si la descarga automática falla, coloca el peso en esa ruta y vuelve a iniciar.

#### Dónde queda cada resultado

| Resultado | Dónde verlo |
| --- | --- |
| Video con detecciones y totales de la ejecución | Ventana del detector |
| Conteos agregados de cada intervalo | Panel → Flujo vehicular |
| Copia local de los conteos | `resultados/conteos_<fecha>.csv`, al usar el asistente |
| Fuente y carriles elegidos en el asistente | `resultados/detector/sesion_<perfil>.yaml` |

Los perfiles de demostración usan **`prueba: true`** e intersección **`DEMO_INT_01`**. En el panel consulta ese contexto de validación y la última hora. Cada intervalo dura unos **30 segundos** y el panel consulta cada **15 segundos**: los resultados no aparecen cuadro a cuadro.

### 5. Probar el Sprint 1

Haz este ensayo completo antes de presentar. Usa un video con vehículos visibles y deja al menos un minuto para observar publicaciones.

| Paso | Acción | Resultado esperado |
| --- | --- | --- |
| 1 | Ejecutar `docker compose --env-file infra/.env -f infra/compose.yaml ps` | Los seis servicios están en ejecución; la base pasa su healthcheck |
| 2 | Consultar `/health` con el comando de instalación | `ok`; activación de planes deshabilitada |
| 3 | Entrar como operador | Acceso a flujo, inventario y comunicación; sin gestión de usuarios |
| 4 | Abrir el asistente, elegir video/cámara, marcar vía y guardar | Se abre el detector y muestra la fuente seleccionada |
| 5 | Dejar que vehículos crucen la línea en el sentido indicado | Los totales del visor cambian; detectar un vehículo sin cruce no equivale a contarlo |
| 6 | Revisar Flujo vehicular tras uno o dos intervalos | Aparecen registros de la prueba para la intersección elegida |
| 7 | Cerrar con Q y revisar el CSV generado | Existen conteos agregados; no se guarda el video |
| 8 | Cerrar sesión y entrar como administrador | Aparece Usuarios; puedes consultar las cuentas |

Un inventario vacío en una instalación nueva es posible: se carga por separado. La vista Comunicación necesita un publicador de estados; ejecutar solo el detector no genera estados de un controlador. El [controlador emulado](controlador/README.md) iniciado con `-Mqtt` publica esos estados.

#### Pruebas automáticas

Desde la raíz, con las dependencias instaladas:

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $py tools/franco/probar.py
node --test tests/franco/oidc.test.mjs
```

El segundo comando requiere Node.js. Estas pruebas validan el software; no sustituyen el ensayo con Docker, cámara y panel ni la medición de precisión en campo.

#### Guion breve de presentación

1. Explica el objetivo: monitorear y contar vehículos sin intervenir los semáforos.
2. Muestra el ingreso como operador y las vistas principales.
3. Elige una fuente, marca los carriles y explica el sentido de cruce.
4. Muestra un cruce contado y luego su intervalo en el panel y el CSV.
5. Cambia al administrador y muestra la gestión de usuarios.
6. Presenta la evidencia medida y sus límites.

**Evidencia disponible:** en un video de 10:49 min se reportaron 197 vehículos frente a 194 manuales con marcado por línea (diferencia total de +1,5 %). La clase micro tuvo 57,1 % de error en esa corrida. Es una prueba ajustada sobre un solo video: no demuestra cumplimiento general de RF-03. Consulta la [evidencia completa](docs/cristhian/evidencia_conteo_video.md), incluida la corrida con marcado por zona.

### 6. Encender y apagar otro día

En PowerShell, dentro de la carpeta `CYSA`:

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
docker compose --env-file infra/.env -f infra/compose.yaml up -d
```

Abre el panel e inicia el asistente de conteo de la sección 4. Al terminar, cierra el detector con Q y detén los servicios:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml stop
```

Esto conserva los datos. **No uses `down -v`: elimina los volúmenes.** No vuelvas a generar secretos para encender el sistema.

### 7. Actualizar una instalación existente

Guarda tus cambios locales y respalda los datos antes de actualizar. Conserva `infra/.env`, `infra/runtime` y los volúmenes. La rama principal actual se llama **`main`**.

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $py -m pip install -r backend/requirements.txt -r deteccion/requirements.txt -r simulacion/requirements.txt -r controlador/requirements.txt -r tests/requirements.txt
& $py tools/franco/configurar_usuarios_local.py --solo-archivos
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build
```

Cuando Keycloak responda, ejecuta los tres configuradores y recrea `api`, como al final de la sección 2. No ejecutes `preparar_local.py` otra vez. Antes de actualizar Keycloak, consulta el respaldo de identidad en la guía técnica: el respaldo de PostgreSQL no incluye sus cuentas.

### 8. Problemas frecuentes

| Problema | Qué hacer |
| --- | --- |
| Docker no responde | Abrir Docker Desktop, esperar y verificar `docker info` |
| No encuentra Python o `.venv` | Instalar Python 3.12 y ejecutar los comandos desde la raíz del repositorio |
| Falta `usuarios-api.env` | Ejecutar `configurar_usuarios_local.py --solo-archivos` antes de Compose |
| Keycloak aún no responde | Esperar y consultar `docker compose --env-file infra/.env -f infra/compose.yaml logs --tail 50 keycloak` |
| Login falla o la API devuelve 503 | Verificar Keycloak, ejecutar los configuradores y recrear `api`; no regenerar secretos |
| API devuelve 401 | Cerrar sesión y volver a ingresar; comprobar el reloj del equipo |
| API devuelve 403 | Revisar el rol y que la cuenta esté habilitada |
| Error de CUDA | Usar el comando CPU de la sección 4 |
| Cámara ocupada o imagen negra | Cerrar otras aplicaciones de cámara y revisar permisos de Windows |
| El detector cuenta pero el panel no cambia | Esperar intervalos, revisar contexto de prueba, intersección y rango de fechas; consultar logs de `consumer` y `mosquitto` |
| El panel muestra el diseño anterior | Recargar con Ctrl+F5 y volver a ingresar |

Para revisar el recorrido de datos:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml logs --tail 50 consumer mosquitto api
```

### Arquitectura y documentación

**Cámara/video → YOLO + ByteTrack → conteos → MQTT/TLS → consumidor → PostgreSQL/TimescaleDB → FastAPI → panel web.** Keycloak controla acceso y roles. SUMO se ejecuta aparte mediante herramientas de consola o desde «Simulación SUMO (demo)» del lanzador Windows, que abre su interfaz gráfica con un escenario sintético de plan fijo. El panel de monitoreo IoT no ejecuta automáticamente evaluaciones SUMO. El panel de laboratorio Web III permite registrar métricas suministradas y evaluar planes con sus reglas, sin ejecutar el simulador ni activar semáforos.

- [Guía técnica completa](docs/guia_tecnica_s1.md): arquitectura, endpoints, contratos, simulación, seguridad y respaldos.
- [Gestión de usuarios](docs/franco/gestion_usuarios_local.md).
- [Visor y controles](docs/cristhian/visor_completo.md).
- [Calibración de la vía](docs/cristhian/calibrar_solo_via_inferior.md).
- [Evidencia de conteo con video](docs/cristhian/evidencia_conteo_video.md).
- [Controlador emulado y placa MMU (Sprint 2)](controlador/README.md).

Esta configuración IoT es de laboratorio local. La validación en campo, MFA real, auditoría integral del corredor y activación física de planes corresponden a etapas posteriores. La MFA simulada y la auditoría de operaciones del laboratorio Web III se describen en su guía.

Equipo: **Franco, Cristhian, Leonardo y Fabrizio**.

### Patrones de diseño implementados

| Patrón | Tipo | Cómo se usa en CYSA |
| --- | --- | --- |
| Prototype | Creacional de objeto | `clonar-perfil` copia un perfil YAML y sus carriles para otra fuente y deja la copia pendiente de calibración. |
| Factory Method | Creacional de clase | Los creadores del detector construyen una fuente de cámara o video según el perfil. Ambas usan el mismo flujo de conteo. |
| Builder | Creacional de objeto | `EscenarioSUMOBuilder` valida y prepara la red, las rutas y la configuración del escenario. |
| Abstract Factory | Creacional de objeto | Cada fábrica crea una fuente de conteos y un controlador compatibles con su entorno, laboratorio o sombra. |
| Facade (Fachada) | Estructural de objeto | [`FachadaConteo`](tools/cristhian/detector.py#L268) coordina la fuente, el perfil y la calibración antes de arrancar el detector desde «Iniciar conteo». |
| Strategy | Comportamiento | `AsignadorCarril` elige al iniciar cómo asignar un vehículo a un carril: por zonas, solo líneas o automático. El bucle del detector ya no decide por modo. |
| Template Method | Comportamiento | `CreadorDetector.ejecutar()` fija los pasos (crear fuente, publicar, cerrar) y cada creador redefine `crear_fuente()`. |
| Iterator | Comportamiento | `FuenteDeteccion.eventos()` entrega los conteos uno a uno con un generador que libera la cámara al terminar. |
| Observer | Comportamiento | El detector publica por MQTT y el consumidor se suscribe a los tópicos de conteos y estado. |
| State | Comportamiento | El [controlador emulado](controlador/README.md) cambia entre `CENTRO`, `LOCAL_SEGURO` (RF-06) e `INTERMITENTE`; cada modo decide qué hacer con los latidos y las fallas del MMU. |

Además usamos **Publish–Subscribe mediante MQTT** para distribuir eventos; está relacionado con Observer, pero no es un Observer local clásico. Command tiene una prueba de concepto para RF-02 y RF-16 en [`casos_comportamiento`](casos_comportamiento/README.md).

### Pendientes del Sprint 2

- **Configurar OTP en cada instalación:** habilitar y enrolar el autenticador del
  operador antes de autorizar planes. La prueba integrada con OTP real ya se
  realizó en el entorno aislado.
- **Validar la detección automática:** los eventos de emergencia del banco son
  predefinidos. La detección automática de ambulancias y la precisión por clase
  requieren validación con videos etiquetados.
- **Preparar el equipo para las pruebas:** descargar el ZIP no instala los
  servicios, no configura las cuentas ni programa la placa automáticamente.
  Seguir la [guía de integración](controlador/INTEGRACION.md).
