# Guía de instalación y pruebas para la PC de Franco

Esta guía acompaña la release s1-it1a8-v1 del Sprint 1 de CYSA. Permite montar las tres partes en una sola PC Windows, recorrer las ocho iteraciones y reunir evidencia sin atribuir resultados a pruebas que no se hicieron.

El resultado técnico esperado es cámara o fuente autorizada, conteos agregados, MQTT con TLS, TimescaleDB, API protegida y panel con login. SUMO se ejecuta aparte por línea de comandos con el plan fijo. Durante S1 no se activa ningún plan nuevo.

## Qué está entregado
Los tres ZIP son acumulativos de iteraciones 1 a 8 y sustituyen a los ZIP anteriores. Código, configuración, datos, informes y pruebas permanecen separados. El ensamblador crea un repositorio nuevo y rechaza mezclar releases.

## Cómo usar la guía
Lee las páginas en orden. Instala primero las herramientas; luego ensambla, configura y arranca. El recorrido sin cámara comprueba comunicaciones. El recorrido con cámara requiere recursos que no se presumen disponibles en la PC de Franco.

Franco ejecuta las tres partes en su PC para ensayar, conservando los responsables originales: Franco lleva infraestructura/backend, Cristhian detección/inventario y Leonardo panel/identidad/SUMO/reglas.

## Estado de esta versión
Hay pruebas automatizadas con datos sintéticos y una corrida SUMO DEMO. Docker, login de navegador, cámara, GPU, precisión real y aprobación docente se deben comprobar en la PC del equipo. Los informes de los ZIP distinguen lo preparado, lo probado y lo pendiente.

Las fechas del 26/10 al 06/11/2026 son planificación; no demuestran reuniones ni actividades futuras ejecutadas. La guía cubre todo S1, sin implementar Webster, prioridades, emulador efectivo ni MFA.

## Mapa de lectura
Instalación y configuración: páginas 2 a 10. Ocho iteraciones: páginas 11 a 18. Cámara y datos reales: páginas 19 a 22. Matriz: páginas 23 y 24. Respaldo y cierre: páginas 25 y 26. Problemas y referencias: páginas 27 a 30.


# Requisitos de la PC y organización

## Comprobar Windows y recursos
Abre Inicio, escribe winver y revisa edición, versión y compilación. Esta guía se centra en Windows 11 x64 y contenedores Linux. Usa una edición y compilación aún admitidas por Docker; su página oficial indica WSL 2.1.5 o posterior y referencias de Windows 11 23H2 o superior para Pro, Enterprise y Education. Comprueba la compatibilidad vigente si usas Home. ARM y Windows Server quedan fuera de este recorrido.

Docker indica 8 GB de RAM como requisito. Para este laboratorio se recomiendan 16 GB, CPU de cuatro núcleos y aproximadamente 40 GB libres; son estimaciones de trabajo, no una garantía de rendimiento. Con detección y GPU, reservar más espacio para PyTorch y pesos. Fuente: [Docker para Windows](https://docs.docker.com/desktop/setup/install/windows-install/).

En Administrador de tareas, Rendimiento, CPU, comprueba Virtualización habilitada. Si no lo está, consulta el procedimiento de BIOS o UEFI del fabricante antes de instalar WSL. No se presupone que Franco tenga GPU ni webcam.

## Qué se ejecuta en cada lugar
| Lugar | Componentes | Dirección desde allí |
| Windows de Franco | Detector, scripts Python y SUMO CLI | localhost para broker y servicios publicados |
| Docker | FastAPI, consumer, TimescaleDB, Mosquitto, Keycloak y Nginx | Nombres db, mosquitto, api y keycloak |
| Navegador | Panel y login | localhost:8088 y localhost:8080 |

No instales Mosquitto, PostgreSQL, TimescaleDB, Keycloak o Nginx por separado en Windows. El Compose los prepara. Tampoco se necesita Node.js para el panel ni OpenSSL para generar los certificados: el script usa la biblioteca Python cryptography.


# Orden de descarga e instalación

Descarga únicamente desde los enlaces oficiales siguientes. Abre los instaladores tú mismo y completa sus pasos. Las versiones de Docker Desktop, WSL y Git pueden evolucionar; registra la instalada. Consulta de fuentes realizada el 26/10/2026.

| Orden | Herramienta | Versión o criterio | Descarga oficial |
| 1 | WSL | 2.1.5 o posterior | [Microsoft WSL](https://learn.microsoft.com/en-us/windows/wsl/install) |
| 2 | Docker Desktop | Estable compatible con Windows; referencia consultada 4.97.0 | [Docker Windows](https://docs.docker.com/desktop/setup/install/windows-install/) |
| 3 | Python | Serie 3.12 x64 | [Python Windows](https://docs.python.org/3/using/windows.html) |
| 4 | Git opcional | Estable x64; referencia consultada 2.56.0 | [Git Windows](https://git-scm.com/install/windows) |
| 5 | Paquetes y SUMO | Fijados en requirements | [SUMO 1.27.0](https://pypi.org/project/eclipse-sumo/1.27.0/) |
| 6 | Detección opcional | Ultralytics 8.4.63 y build PyTorch apropiada | [Ultralytics](https://docs.ultralytics.com/quickstart/) |

Las versiones de los servicios Docker están en infra/.env.example. Se mantiene la combinación de laboratorio de los paquetes base: TimescaleDB 2.19.3 con PostgreSQL 17, Mosquitto 2.0.21, Keycloak 26.8.1 y Nginx 1.30.6. Son referencias por probar, no una certificación del conjunto.

El Perfil del Excel menciona PostgreSQL 18.6 y Mosquitto 2.1.2. La desviación está documentada: antes de adaptar S0, confirmar sus versiones y repetir las pruebas. No cambiar imágenes y migraciones sin revisar compatibilidad.

SUMO 1.27.0 se conserva para reproducir los resultados entregados aunque la página de descargas muestre 1.28.0. No hace falta instalar ambas versiones. La guía utiliza la instalación por pip de 1.27.0.


# Instalar WSL y Docker Desktop

## WSL desde PowerShell como administrador
Si WSL no está instalado, abre PowerShell con Ejecutar como administrador. La carpeta actual no importa para estos comandos.

```powershell
wsl --install
```

Reinicia Windows si se solicita. En el primer inicio de Ubuntu, crea el usuario Linux y su contraseña; no es un usuario del proyecto ni de Keycloak. Después comprueba:

```powershell
wsl --update
wsl --version
wsl --status
wsl --list --verbose
```

La distribución usada debe indicar VERSION 2. Si aparece 1, usa wsl --set-version seguido del nombre exacto que muestre tu listado y el número 2. Consulta el procedimiento oficial de Microsoft si la instalación se detiene o requiere componentes de Windows.

## Docker Desktop
Descarga el instalador x64 desde la página oficial. Elige backend WSL 2 y contenedores Linux. Completa la instalación, abre Docker Desktop y espera a que el motor esté en marcha. Si pide reiniciar, hazlo antes de continuar. Los permisos de instalación dependen del modo elegido; usa una sesión normal para trabajar en el proyecto después.

En una PowerShell nueva comprueba:

```powershell
docker version
docker compose version
docker info --format '{{.OSType}}'
```

Deben verse Client y Server en docker version; el último comando debe devolver linux. Compose viene incluido con Docker Desktop. Si no aparece Server, abre Docker Desktop y resuelve ese error antes de ejecutar preparación o arranque del proyecto.


# Instalar Python y Git

## Python 3 12
Desde python.org descarga el Python install manager para Windows o instálalo desde la Microsoft Store enlazada por la documentación oficial. Abre una PowerShell nueva y ejecuta:

```powershell
py install 3.12
py -3.12 --version
py -3.12 -m pip --version
```

Con un launcher clásico, py install puede no existir. En ese caso usa el install manager oficial; no desinstales a ciegas otras versiones. La release 3.12.10 ofrece el instalador tradicional x64, pero es la última versión de mantenimiento con ese tipo de instalador y tiene sucesoras de seguridad. Prioriza la serie 3.12 que ofrezca el gestor y registra el parche efectivo.

[Python 3.12.10 y archivos de referencia](https://www.python.org/downloads/release/python-31210/). El entorno autor usó Python 3.12.14; los paquetes apuntan a la serie 3.12. La guía no exige instalar el runtime interno de Codex.

## Git opcional
Para usar únicamente los ZIP y probar en una PC, Git no es obligatorio. Para llevar los cambios a las ramas del proyecto, descarga Git for Windows x64, conserva la integración con terminal y comprueba:

```powershell
git --version
```

No se proporcionó el repositorio S0. Este material crea una base de referencia nueva. La incorporación al repositorio del equipo requiere revisar cambios, conservar archivos existentes y acordar una rama por responsable; no se afirma que esa integración ya esté hecha.

## Preparar una carpeta propia
Usa una carpeta que puedas escribir. Esta guía usa Documents\CYSA_S1. Evita carpetas sincronizadas si provocan bloqueos; si eliges otro lugar, sustituye esa ruta en los comandos posteriores.


# Descargar los paquetes y ensamblar

Guarda los tres ZIP nuevos en una carpeta, sin mezclar versiones 1 a 4. En PowerShell normal, desde cualquier ubicación:

~~~powershell
$BASE = Join-Path $env:USERPROFILE 'Documents/CYSA_S1'
New-Item -ItemType Directory -Force $BASE | Out-Null
~~~

Abre esa carpeta en el Explorador y mueve allí los tres ZIP acumulativos 1 a 8. Después:

~~~powershell
Set-Location $BASE
Expand-Archive ./Franco_S1_Iteraciones_1_a_8.zip ./paquete_franco
$ZIP = @('./Franco_S1_Iteraciones_1_a_8.zip',
 './Cristhian_S1_Iteraciones_1_a_8.zip',
 './Leonardo_S1_Iteraciones_1_a_8.zip')
$BOOT = './paquete_franco/Franco/codigo/herramientas/ensamblar.py'
py -3.12 $BOOT --salida ./repo_s1 @ZIP
Set-Location ./repo_s1
py -3.12 -m venv .venv
~~~

Resultado esperado: repo_s1 con shared, backend, inventario, deteccion, panel, identidad, simulacion, infra, tools, tests, data, docs y reports. Cada módulo tiene un único propietario. El ensamblador rechaza destinos no vacíos y releases incompatibles.

Si repo_s1 o paquete_franco ya existen, elige nombres nuevos y ajusta los comandos. No uses sobrescritura para tapar el error. Los ZIP antiguos pueden conservarse fuera del repositorio ensamblado.

Los bloques usan PowerShell; @ZIP expande la lista de argumentos preparada arriba. Las líneas dentro de un array entre paréntesis pueden continuar en varias líneas sin caracteres especiales.


# Preparar la terminal y dependencias

## Bloque C0 para cada terminal nueva
Abre PowerShell normal y pega este bloque. Todos los comandos posteriores se ejecutan desde repo_s1 salvo que se indique otra carpeta. No hace falta activar la venv ni cambiar políticas de ejecución.

~~~powershell
Set-Location "$env:USERPROFILE/Documents/CYSA_S1/repo_s1"
$PY = (Resolve-Path .venv/Scripts/python.exe).Path
$env:PYTHONPATH = @("$PWD/shared","$PWD/backend",
 "$PWD/inventario","$PWD/deteccion") -join ';'
$DC = @('compose','--env-file','infra/.env',
 '-f','infra/compose.yaml')
~~~

Solo durante la primera instalación ejecuta también:

~~~powershell
& $PY -m pip install --upgrade pip
$REQ = @('-r','backend/requirements.txt',
 '-r','tests/requirements.txt','-r','simulacion/requirements.txt')
& $PY -m pip install @REQ
& $PY tools/franco/probar.py
~~~

Se esperan todas las pruebas correctas; esta entrega fue verificada con 34 casos. Puede aparecer un aviso de deprecación de TestClient con httpx. Un fallo requiere revisión; un aviso no equivale a fallo.

## Comprobar SUMO 1 27
Los paquetes eclipse-sumo, sumolib y sumo-data están fijados en 1.27.0:

~~~powershell
$CODE = 'import pathlib,sumo;print(pathlib.Path(sumo.__file__).parent)'
$env:SUMO_HOME = & $PY -c $CODE
& "$env:SUMO_HOME/bin/sumo.exe" --version
& "$env:SUMO_HOME/bin/netconvert.exe" --version
~~~

Repite SUMO_HOME en cada terminal de simulación. Paquetes, imágenes y pesos deben prepararse antes de trabajar sin Internet.


# Generar la configuración local

Ejecuta C0 y asegúrate de que Docker Desktop está iniciado. La preparación necesita los tres paquetes ensamblados.

~~~powershell
& $PY tools/franco/diagnostico.py --out resultados/diagnostico.json
& $PY tools/franco/preparar_local.py --repo .
docker @DC config --quiet
~~~

El generador crea contraseñas aleatorias, CA propia, certificado TLS y usuarios de laboratorio. No se envían contraseñas en argumentos de procesos. La CA privada queda fuera del montaje del broker.

| Archivo local | Uso | Tratamiento |
| infra/.env | BD, bootstrap e issuer | No publicar |
| infra/runtime/mqtt | Certificados, clave broker y usuarios hash | No compartir |
| infra/runtime/ca-private | Clave privada de CA | Mantener privada |
| infra/runtime/clientes/prueba.env | Cliente sintético MQTT | Solo pruebas |
| infra/runtime/clientes/deteccion.env | Cliente detector | Solo ejecución local |
| infra/runtime/clientes/usuarios-locales.json | Contraseñas de dos roles | No capturar |
| infra/runtime/keycloak/cysa-realm.json | Importación con usuarios | No publicar |

El script actualiza panel/config.json con URLs públicas locales. Los valores por defecto son correctos para una sola PC; no los cambies por nombres Docker que ve el backend.

La preparación rechaza runtime o .env existentes para no perder claves. Si falla a mitad, no borres esos archivos automáticamente: revisa el error y usa una copia nueva del repositorio para repetir la primera preparación. Mantén separado un runtime ya utilizado con volúmenes existentes.


# Arrancar y comprobar los servicios

Con C0 y configuración generada, desde repo_s1:

~~~powershell
docker @DC up -d --build
docker @DC ps
docker @DC logs --tail 60 api consumer mosquitto keycloak
Invoke-RestMethod http://localhost:8088/health
$OIDC = 'http://localhost:8080/realms/cysa'
Invoke-RestMethod "$OIDC/.well-known/openid-configuration"
~~~

Espera a que Keycloak termine arranque/importación antes de probar login. Repite su consulta si todavía no responde. La salud debe indicar activacion_planes false; solo comprueba el proceso API, no todo el flujo.

| Desde | Destino correcto | Motivo |
| Navegador Windows | http://localhost:8088 | Panel Nginx |
| Navegador Windows | http://localhost:8080 | Keycloak e issuer público |
| Detector Windows | localhost:8883 | Broker TLS |
| API o consumer Docker | db, mosquitto y keycloak | DNS interno |
| Login CLI | 127.0.0.1:8766/callback | Receptor temporal Windows |

No hay 1883, 5432 ni 8000 publicados al host. La API se consulta por /api en Nginx. No uses file:// para el panel. Si hay errores de arranque, revisa logs y conserva los volúmenes.

Importar al arrancar no actualiza un realm que ya existe de otra versión. Usa los volúmenes nuevos de esta base o añade cysa-cli desde identidad/realm.template.json mediante administración de Keycloak, preservando usuarios. No elimines el volumen anterior.


# Login del panel y de las herramientas

## Panel con cada rol
Abre http://localhost:8088/ y pulsa Ingresar. Consulta infra/runtime/clientes/usuarios-locales.json con tu editor para obtener las contraseñas generadas. No captures esa pantalla. Ingresa primero como administrador y luego como operador, cerrando sesión entre pruebas.

Deben aparecer Conteos, Inventario y Comunicación. PRUEBA identifica datos sintéticos. El panel ofrece búsqueda, selector de intersección y Última hora en vivo. Sin datos, indica ausencia de datos; no inventa ceros.

## Login CLI sin copiar tokens
login_local.py abre Keycloak, valida firma/issuer/audience y pasa el token solo al proceso hijo. Usa 8766 durante login. El token no se guarda en disco.

Con administrador, desde repo_s1 después de C0:

~~~powershell
$A = @('tools/franco/aceptacion_local.py',
 '--solo-roles','administrador','--out','resultados/rol_admin_01')
& $PY tools/franco/login_local.py -- $PY @A
~~~

Repite con operador y otra carpeta:

~~~powershell
$A = @('tools/franco/aceptacion_local.py',
 '--solo-roles','operador','--out','resultados/rol_operador_01')
& $PY tools/franco/login_local.py -- $PY @A
~~~

Ingresa el rol correspondiente. El operador debe obtener 403 al intentar carga. El administrador supera autorización y recibe 422 por la carga vacía deliberada, sin modificar activos. PASS_SINTETICO indica que se recibió la respuesta esperada. Se guarda resultado.json en cada carpeta.

Si caduca el token, repite login; no habilites password grant ni desactives validación. Una sesión del panel no reemplaza el token temporal de la herramienta.


# Iteración 1 del 26 de octubre

## Responsables y objetivo
Franco verifica entorno e IDs; Cristhian prepara captura e inventario; Leonardo prepara identidad, vistas y red SUMO. En la PC única, Franco reproduce las tres preparaciones usando los paquetes correspondientes.

## Acciones en orden
Completa instalación, ensamblado y dependencias de las páginas anteriores. Ejecuta C0 y el diagnóstico. Revisa estructura y contratos antes de introducir datos reales.

~~~powershell
& $PY tools/franco/diagnostico.py --out resultados/it01_diagnostico.json
Get-ChildItem shared,backend,inventario,deteccion,panel,identidad
Get-Content docs/franco/contratos.md
Get-Content deteccion/config/carriles_plantilla.yaml
~~~

Si vas a usar cámara después, confirma con Cristhian cuándo podrá conectarse su webcam a esta PC. Sin cámara, conserva el recorrido sintético. No completes inventario con dispositivos supuestos.

## Archivos y resultado esperado
Usar infra/compose.yaml, shared/cysa/contracts.py, identidad/realm.template.json y plantillas en data/cristhian. La estructura debe estar completa. El diagnóstico distingue herramientas instaladas y puertos ocupados; un puerto ocupado es normal si el servicio está en marcha.

## Evidencia y pendientes
Guarda diagnóstico sin contraseñas. Registra recursos disponibles, faltantes del corredor, geometría, plan fijo y acceso a fuentes S0-09. S0 no fue suministrado: la base ensamblada no prueba su compatibilidad hasta revisarla con el equipo.


# Iteración 2 del 27 al 28 de octubre

## Responsables y objetivo
Franco publica contratos y prepara TLS/interfaces; Cristhian prepara tracking y líneas; Leonardo prepara roles y SUMO fijo. El resultado es un formato común para avanzar sin esperar la cámara.

## Comprobar contratos y TLS
Con C0, repasa JSON Schema en data/franco/contratos y ejemplos en data/franco/ejemplos. Ejecuta la suite antes de conectar dispositivos:

~~~powershell
& $PY tools/franco/probar.py
Get-Content docs/franco/red_y_seguridad.md
~~~

Si todavía no generaste configuración, hazlo una vez siguiendo la sección correspondiente. Con Compose activo, prueba el listener:

~~~powershell
$A = @('infra/runtime/clientes/prueba.env','--',
 $PY,'tools/franco/verificar_tls.py')
& $PY tools/franco/cargar_env.py @A
~~~

Debe fallar MQTT plano y funcionar la publicación TLS autenticada con PUBACK. PUBACK confirma broker; la persistencia se comprueba en la iteración 6. No sustituye una captura de red que compruebe cifrado y aislamiento.

## Archivos y evidencia
FuenteDeteccion y Controlador están en shared/cysa/interfaces.py. El contrato de planes es solo borrador para S2, sin envío ni activación. Conserva el resultado textual sin certificados privados ni credenciales. Las líneas YAML DEMO siguen sin calibrar y no representan una intersección real.


# Iteración 3 del 29 al 30 de octubre

## Responsables y objetivo
Franco conecta recepción, validación y estados; Cristhian conecta inventario/detección; Leonardo conecta vistas y redacta reglas. En la PC de Franco se comienza con mensajes sintéticos y activos DEMO.

## Publicar datos sin cámara
Con C0 y servicios activos, publica tres ciclos. Tarda aproximadamente un minuto porque los ciclos se separan por 30 segundos.

~~~powershell
$A = @('infra/runtime/clientes/prueba.env','--',
 $PY,'tools/franco/publicar_prueba.py','--ciclos','3')
& $PY tools/franco/cargar_env.py @A
~~~

Para cargar inventario de ejemplo, usa login de administrador:

~~~powershell
$A = @('tools/cristhian/cargar_inventario.py',
 'data/cristhian/ejemplos/inventario_DEMO.csv')
& $PY tools/franco/login_local.py -- $PY @A
~~~

En el panel busca DEMO_INT_01. Revisa auto, micro y moto, activos sintéticos y comunicación PRUEBA. Si no aparecen datos, comprueba rango horario y logs del consumer; no copies números a la base para aparentar integración.

## Reglas y evidencia
Leonardo prepara reports/leonardo/propuesta_reglas_pendiente.md. Revisar con el equipo cuándo simular y qué hacer sin respuesta del operador. La propuesta mantiene el último plan válido autorizado y bloquea planes nuevos. Registrar decisiones reales en data/leonardo/plantillas/revision_reglas.csv. La reunión del 30/10 sigue siendo planificación hasta que ocurra.


# Iteración 4 del 31 de octubre al 2 de noviembre

## Responsables y objetivo
Cristhian prepara calibración/privacidad; Franco verifica consultas/TLS; Leonardo completa vistas y demora base SUMO. Ajustar la carga del fin de semana según el acuerdo del equipo.

## SUMO sintético reproducible
Con C0 y SUMO_HOME configurado, desde repo_s1:

~~~powershell
$A = @('--demo',
 '--counts','data/leonardo/ejemplos/flujos_DEMO.csv',
 '--out','resultados/sumo_it04')
& $PY simulacion/sumo_base.py @A
Get-Content resultados/sumo_it04/ejecucion.json
Get-Content resultados/sumo_it04/demora_base.csv
~~~

Elige carpeta nueva en cada corrida. Se esperan 13 vehículos completados y cero incompletos en el escenario suministrado. La red es sintética, con cuatro accesos rectos; no reproduce Santa Cruz ni valida parámetros reales.

## Datos reales pendientes
No ejecutes calibrar.py con una plantilla vacía esperando un resultado. Requiere conteo manual independiente, cantidades automáticas y ventanas/carriles/clases coincidentes. Si no hay cámara o escena vehicular, deja ese requisito pendiente y continúa la integración sintética.

## Evidencia
Guarda tripinfo.xml, demora_base.csv y ejecucion.json. La demora utilizada es timeLoss por vehículo completado, agrupado por acceso. No se incluyen resultados inventados de precisión ni se aprueba RF-03 porque SUMO funcione.


# Iteración 5 del 3 de noviembre

## Responsables y objetivo
Los tres integran sus ramas antes de la prueba completa; Franco coordina Compose/migraciones, Cristhian sus módulos y Leonardo panel/Keycloak/SUMO. El ensamblador verifica destinos de archivos de referencia; no sustituye la revisión de S0.

## Revisar la base conjunta
Desde repo_s1, con C0:

~~~powershell
& $PY tools/franco/probar.py
docker @DC config --quiet
docker @DC up -d --build
docker @DC ps
& $PY tools/franco/diagnostico.py --out resultados/it05_diagnostico.json
~~~

La base debe arrancar con el mismo Compose. No hacen falta tres PC ni acceso remoto a la webcam. El detector se conecta desde Windows al broker local y el panel consulta la misma API.

## Inspeccionar el esquema dentro del contenedor
Este comando se escribe en PowerShell, pero Python se ejecuta dentro de api con sus variables DB.

~~~powershell
docker @DC exec -T api python /workspace/tools/inspeccionar_bd.py
~~~

Esperado: hypertable_conteos true, grupos_duplicados 0 y columnas_prohibidas vacía. Revisa las columnas de conteos, estados e inventario. No demuestra por sí solo privacidad del filesystem.

## Evidencia
Conserva salida de suite, diagnóstico y revisión SQL. No publiques compose config sin --quiet porque puede imprimir contraseñas interpoladas. Marca pendiente cualquier incompatibilidad con S0 o servicio que no arranque.


# Iteración 6 del 4 de noviembre

## Responsables y objetivo
Ensayo conjunto: Cristhian origina conteos, Franco recibe/guarda y Leonardo los muestra. SUMO corre por CLI en la misma PC. Completa primero el recorrido sintético; usa cámara solo si hay fuente adecuada.

## Prueba sintética de servicios reales
Con C0 y Compose activo, usa login de administrador:

~~~powershell
$A = @('tools/franco/aceptacion_local.py',
 '--out','resultados/it06_demo')
& $PY tools/franco/login_local.py -- $PY @A
~~~

Ingresa como administrador. La prueba carga activos DEMO, publica un conteo dos veces con el mismo UUID, espera persistencia y comprueba una sola fila. Envía también un mensaje inválido y espera una barrera válida posterior para confirmar su descarte.

El ensayo de estados publica cada 25 s y consulta durante 65 s. Exige al menos tres timestamps distintos, separación de actualizaciones y antigüedad observada de hasta 30 s. El margen de 5 s permite observar latencia. Es un ensayo breve S1, no la hora continua prevista para S3.

## Completar el recorrido visible
En el panel selecciona DEMO_INT_01 y revisa Conteos, Inventario y Comunicación. Todos los datos del ejecutor llevan PRUEBA. Ejecuta SUMO DEMO con otra carpeta de salida. Consulta resultado.json y muestras_estados.json del ensayo.

Un FAIL no se sustituye por PASS manual. Revisa el detalle, corrige y repite con carpeta nueva. El ejecutor no prueba visualmente el panel ni acredita detección real; registra esas verificaciones aparte.


# Iteración 7 del 5 de noviembre

## Responsables y objetivo
Los tres ejecutan aceptación y reúnen evidencia. Franco revisa API/TLS y duplicados; Cristhian conteo/inventario/privacidad; Leonardo login/panel/SUMO/reglas.

## Comprobar ambos roles
Repite los comandos de la sección de login con nuevas carpetas, como rol_admin_02 y rol_operador_02. Deben rechazar consultas sin token, aceptar lectura autenticada y denegar escritura al operador. La prueba del administrador usa una carga vacía deliberada sin alterar activos reales.

## Privacidad y evidencia
Con cámara usa una carpeta exclusiva para CSV agregados. Inspecciónala sin borrar:

~~~powershell
$A = @('--carpeta','resultados/conteos',
 '--out','resultados/privacidad_carpetas.json')
& $PY tools/cristhian/comprobar_privacidad.py @A
docker @DC exec -T api python /workspace/tools/inspeccionar_bd.py
~~~

Indica una carpeta existente donde realmente se guardaron los CSV. El escáner no acredita carpetas no revisadas; inspecciona además logs, MQTT y almacenamiento. Las capturas de tablas numéricas para evidencia deben ir aparte de la carpeta de captura y no mostrar cámara o contraseñas.

## Completar la matriz
Usa las dos páginas de matriz y data/franco/plantillas/matriz_aceptacion.csv. Anota resultado real y referencia de evidencia. Solo marca validación real si ejecutaste medición con tráfico y conteo manual. La aprobación docente sigue pendiente hasta tener decisión registrada.


# Iteración 8 del 6 de noviembre

## Responsables y objetivo
Preparar una demostración reproducible y una entrega con límites conocidos. Franco presenta infraestructura/API; Cristhian detección/inventario; Leonardo panel/SUMO/reglas. El reparto original se conserva aunque Franco ejecute todo.

## Orden de demostración
1. Mostrar release s1-it1a8-v1 y que los paquetes se ensamblaron sin mezclar versiones.
2. Comprobar Compose y login con dos roles. Mostrar rechazo sin token y permisos según rol.
3. Mostrar un conteo por MQTT TLS consultable en panel; identificar fuente sintética o real.
4. Mostrar inventario y comunicación, con PRUEBA para estados sintéticos.
5. Ejecutar SUMO por CLI y presentar demora por acceso; identificar red DEMO si se usa.
6. Presentar calibración real si existe; de lo contrario, explicar el pendiente sin afirmar precisión.
7. Presentar reglas y revisiones/aprobación solo si existen. Confirmar ausencia de activación de planes nuevos.

## Cierre y respaldo
Conserva resultado.json, muestras de estados, calibración, CSV inventario, resultados SUMO y registro de revisiones. Haz respaldo antes de detener servicios.

No entregues infra/.env, runtime, contraseñas, tokens, claves, pesos, venv ni videos. Los ZIP distribuidos contienen código, configuración sin secretos y pruebas identificadas.

## Condición de aceptación
Una demostración sintética completa prueba integración, pero no cierra error de detección ≤10 % ni cobertura real del inventario. Déjalos pendientes si faltan recursos. Este material prepara las iteraciones finales; el acta y aceptación del equipo/docente no se inventan.


# Recorrido con cámara en la PC de Franco

## Preparar recursos opcionales
Conecta temporalmente la webcam de Cristhian a la PC de Franco o configura una fuente externa autorizada. En Configuración de Windows, Privacidad y seguridad, Cámara, permite acceso a aplicaciones de escritorio cuando corresponda. Cierra aplicaciones que ocupen la webcam.

Con C0, elige primero CPU si solo comprobarás arranque:

~~~powershell
& $PY -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
& $PY -m pip install -r deteccion/requirements.txt
& $PY -c "import torch;print(torch.__version__,torch.cuda.is_available())"
& $PY tools/cristhian/comprobar_camara.py --source 0
~~~

El último comando lee un cuadro en RAM, informa tamaño y lo descarta. No muestra ni guarda imagen y no demuestra tráfico. GPU no es necesaria para este chequeo; CPU no garantiza rendimiento para conteo.

Si hay GPU NVIDIA, revisa nvidia-smi y el [selector oficial PyTorch](https://pytorch.org/get-started/locally/). Selecciona Windows, Pip y build compatible; ejecuta el comando con el Python de la venv, no un pip global. Comprueba torch.cuda.is_available antes de indicar device 0 en YAML.

## Pesos sin registrar imágenes
Descarga YOLO26n antes de quedar sin Internet. Este comando carga el modelo, sin inferir imágenes:

~~~powershell
& $PY -c "from ultralytics import YOLO;YOLO('yolo26n.pt')"
~~~

No uses ejemplos de predict que guardan imágenes por defecto. Los pesos son software del modelo y no están incluidos en los ZIP. No se entrena un modelo nuevo.


# Configurar y ejecutar el detector

## Configuración verificable
Copia plantilla y edítala desde repo_s1:

~~~powershell
Copy-Item deteccion/config/carriles_plantilla.yaml deteccion/config/carriles_franco.yaml
notepad deteccion/config/carriles_franco.yaml
~~~

Completa el ID real acordado, acceso/carril y líneas a/b normalizadas 0..1. No copies líneas DEMO como reales. Usa source 0 para webcam o ruta externa autorizada; el índice se escribe como número en YAML. Usa device cpu o 0 solo si verificaste CUDA.

Mantén configuracion_verificada false hasta comprobar fuente, líneas y sentido. Después establece true. prueba false corresponde a captura de tráfico no sintética identificada; escenas de laboratorio o datos ficticios conservan true. Esa marca no concede aceptación ni certifica precisión.

Mapeo: car=2 a auto, motorcycle=3 a moto, bus=5 a micro como aproximación. Un bus no identifica necesariamente un micro local. Mide resultados por clase.

## Ejecutar sin guardar video

~~~powershell
New-Item -ItemType Directory -Force resultados/conteos | Out-Null
$A = @('infra/runtime/clientes/deteccion.env','--',
 $PY,'-m','cysa_detector.run',
 '--config','deteccion/config/carriles_franco.yaml',
 '--salida-conteos','resultados/conteos/camara.csv')
& $PY tools/franco/cargar_env.py @A
~~~

Detener con Ctrl+C. El último intervalo parcial puede no publicarse: excluirlo de calibración. El CSV conserva números/UUID, nunca cuadros. Si falla publicación, recupera broker y reenvía camara.csv con tools/cristhian/reenviar_conteos.py mediante cargar_env y la misma credencial. Conserva UUID para no duplicar.

La fuente externa se lee sin copiar video. El detector usa reloj de ejecución, no reloj del archivo: no utilices esas tasas como demanda real sin sincronizar reproducción y documentarlo. Una webcam sin tráfico solo prueba captura.


# Medir precisión y completar inventario real

## Calibración independiente
Copia data/cristhian/plantillas/calibracion.csv a tu carpeta de mediciones. Registra intersección, acceso, carril, clase, inicio/fin, manual, automatico y prueba. No mezcles ventanas de relojes diferentes ni muestras repetidas.

Cuenta manualmente los mismos cruces e intervalos, de forma independiente. Incluye auto, micro y moto y registra fuente en registro_fuentes.csv. Volumen representativo y criterio global se acuerdan con equipo/docente.

~~~powershell
& $PY tools/cristhian/calibrar.py mediciones/calibracion.csv resultados/calibracion_medida.csv
~~~

mediciones/calibracion.csv debe existir con tus mediciones; no es un ejemplo relleno. Error porcentual: valor absoluto de automático menos manual, dividido entre manual y multiplicado por 100. Verificar la meta ≤10 %. Con manual cero, informar falsos positivos absolutos; no hay base porcentual.

El script calcula resultados, no aprueba RF-03. No ocultes fallos de una clase con promedio global. Si no hay escenas, rendimiento suficiente o conteo manual, registrar PENDIENTE.

## Inventario real
Completa inventario.csv con activos, ubicación y protocolo reales:

~~~powershell
& $PY tools/cristhian/cargar_inventario.py mediciones/inventario.csv --validar
$A = @('tools/cristhian/cargar_inventario.py','mediciones/inventario.csv')
& $PY tools/franco/login_local.py -- $PY @A
~~~

Ingresa como administrador. Comprueba consulta en panel y cobertura de todas las cámaras/controladores reales del piloto. Inventario DEMO no demuestra esa cobertura. Conservar el denominador real y evidencia, sin credenciales.


# Simular datos del piloto desde el servidor local

La PC de Franco es el servidor de laboratorio. SUMO corre desde PowerShell por CLI, nunca desde botón del panel. Usa una intersección por corrida.

## Preparar insumos reales
Necesitas red.net.xml con geometría/plan fijo suministrados, accesos_red.csv que relacione acceso con edge entrada/salida y flujos.csv medidos. El script admite rutas de dos edges contiguos; redes más complejas requieren adaptar rutas. No se incluyen insumos reales ficticios.

Exporta conteos con token de lectura:

~~~powershell
$A = @('simulacion/exportar_conteos.py',
 '--desde','2026-10-26T12:00:00Z','--hasta','2026-10-26T13:00:00Z',
 '--interseccion','ID_REAL_ACORDADO','--out','mediciones/flujos.csv')
& $PY tools/franco/login_local.py -- $PY @A
~~~

Sustituye fechas e ID por ventana real. No uses carriles QA del ejecutor DEMO como demanda del piloto. Revisa solapamiento y origen; se rechazan duplicados del mismo carril/clase.

~~~powershell
$A = @('--network','mediciones/red.net.xml',
 '--access-map','mediciones/accesos_red.csv',
 '--counts','mediciones/flujos.csv','--out','resultados/sumo_piloto_01')
& $PY simulacion/sumo_base.py @A
~~~

No uses --demo con conteos no sintéticos. Revisa ejecucion.json, tripinfo.xml y demora_base.csv. Se usa media de timeLoss por acceso de origen de vehículos completados; departDelay queda separado. La corrida falla si no completan los esperados y desactiva teleport para no ocultarlos.

Los resultados DEMO muestran el procedimiento, no demora real. Conservar insumos/semilla 42 prepara comparación Webster de S2; aquí no se calcula ni activa un plan.


# Matriz de aceptación de comunicaciones y acceso

Las referencias apuntan a comandos de las iteraciones de esta guía. El estado corresponde a la preparación de la entrega; registra aparte la ejecución de la PC de Franco. CSV completo: data/franco/plantillas/matriz_aceptacion.csv.


| Requisito | Responsable | Prerrequisitos | Pasos | Resultado esperado | Evidencia | Estado |
|---|---|---|---|---|---|---|
| P01 Contratos | Franco | Venv instalada | C0 y probar.py; casos de contrato | Rechaza campos, tipos y tópico inválidos | Salida de suite | Sintético; vivo pendiente |
| P02 MQTT TLS | Franco | Compose y CA locales | Iteración 2 verificar_tls.py | Plano rechazado y TLS con PUBACK | Salida TLS y captura de red sin payload sensible | Pendiente en vivo |
| P03 Persistencia | Franco | Login admin y broker/BD activos | Iteración 6 aceptacion_local.py | Mismo UUID enviado dos veces produce una fila | resultado.json y revisión SQL | Lógica sintética; BD pendiente |
| P04 Inventario | Cristhian | CSV identificado y rol admin | Iteración 3 carga; iteración 6 edición | Carga/consulta/edición; cobertura real 100 % por medir | CSV y resultado.json; listado real | Sintético; piloto pendiente |
| P05 Login y roles | Leonardo y Franco | Realm, cysa-cli y dos usuarios | Sección login; solo-roles para ambos | Sin token 401; operador escritura 403; admin autorizado | JSON de roles; pantalla sin secretos | JWT sintético; login pendiente |
| P06 Estados | Franco y Leonardo | Broker/API y reloj correctos | Iteración 6 ensayo de 65 segundos | Tres actualizaciones y gap/edad <=30 s | muestras_estados.json y panel PRUEBA | Lógica sintética; vivo pendiente |


# Matriz de aceptación de detección y entrega

Los requisitos dependientes de recursos reales siguen pendientes. PRUEBA no equivale a aceptación del piloto. Anota fecha y evidencia al ejecutar cada caso.


| Requisito | Responsable | Prerrequisitos | Pasos | Resultado esperado | Evidencia | Estado |
|---|---|---|---|---|---|---|
| P07 Conteo real | Cristhian | Tráfico, líneas y control manual | Recorrido cámara y calibrar.py | Error <=10 % por muestra; todas las clases medidas | Tabla y registro de fuente; sin video | Pendiente real |
| P08 Privacidad | Cristhian y Franco | Carpetas reales de captura y BD | Iteración 7 scanner e inspeccionar_bd.py | Sin imágenes/video/placas; solo agregados | JSON scanner/SQL y revisión MQTT/logs | Revisión estática; vivo pendiente |
| P09 Panel | Leonardo | Datos y login activos | Iteraciones 3 y 6; revisión manual | Tres vistas; PRUEBA visible; búsqueda <1 min | prueba_panel.csv y captura de tablas | Pendiente visual y piloto |
| P10 SUMO fijo | Leonardo | SUMO 1.27 y demanda/red identificadas | Iteración 4 sumo_base.py; ruta real si existe | DEMO 13 completos; timeLoss por acceso | tripinfo, demora_base y ejecucion | DEMO ejecutado; real pendiente |
| P11 Sin activación | Los tres | API y panel de esta release | aceptacion_local.py POST /api/planes | 404, salud false y sin controles de planes | resultado.json y revisión de interfaz | Ausencia comprobada en API de prueba |
| P12 Reglas | Leonardo y equipo | Borrador y revisión docente | Iteración 8 registrar decisiones reales | Conservar último válido sin respuesta; aprobación registrada | revision_reglas.csv y decisión docente | Pendiente de aprobación |


# Respaldar y comprobar una restauración

## Respaldo de monitoreo
Con C0 y BD activa, desde repo_s1:

~~~powershell
& $PY tools/franco/respaldo.py --out respaldos/s1_ensayo_01.dump
~~~

Se genera dump binario PostgreSQL y JSON con SHA256. Evita redirección de binarios de PowerShell y no sobrescribe archivos existentes. Si falla, el parcial no es válido. No incluye H2 de Keycloak ni claves TLS; permanecen en volúmenes/runtime locales.

## Ensayo seguro de recuperación
Crea una base nueva cysa_restore_ sin alterar la base cysa:

~~~powershell
$A = @('--file','respaldos/s1_ensayo_01.dump',
 '--database','cysa_restore_ensayo01')
& $PY tools/franco/restaurar_copia.py @A
~~~

Falla si ya existe; no borra esa base. Usa funciones pre/post restore de TimescaleDB y consulta conteos. Tras éxito, compara cantidades e inventario con la original y documenta antes de marcar el respaldo como restaurable.

Para contrastar inventario de la base original y la restaurada, ejecuta:

~~~powershell
docker @DC exec -T db psql -U cysa -d cysa -c "SELECT count(*) FROM inventario;"
docker @DC exec -T db psql -U cysa -d cysa_restore_ensayo01 -c "SELECT count(*) FROM inventario;"
~~~

Dumps con datos reales deben mantenerse privados; no anexarlos a ZIP de código. Guarda runtime de forma privada si debes recuperar identidad/TLS, sin incluirlo en entrega compartida. No uses contraseñas recién generadas con volúmenes antiguos sin coordinar el cambio.

En caso de fallo durante restauración, la base de prueba puede quedar parcial. Consérvala para diagnóstico; el script no altera cysa. Elige otro nombre cysa_restore_ para un siguiente ensayo tras corregir la causa.


# Detener y volver a iniciar sin perder datos

## Detener
En terminal de detector/publicador pulsa Ctrl+C y espera cierre. Desde repo_s1 con C0:

~~~powershell
docker @DC stop
~~~

stop conserva contenedores y volúmenes. Puedes cerrar Docker Desktop después. No ejecutes down con opción de borrar volúmenes ni elimines volúmenes desde su interfaz para resolver errores.

## Retomar
Abre Docker Desktop y espera el motor. En PowerShell nueva pega C0:

~~~powershell
docker @DC start
docker @DC ps
Invoke-RestMethod http://localhost:8088/health
~~~

Si los contenedores no existen o cambió código, usa up -d --build en lugar de start, conservando .env y runtime. No repitas preparar_local sobre ese runtime. Migraciones iniciales solo se aplican al crear una base nueva.

## Repetir pruebas
Elige carpetas nuevas para aceptación/SUMO y nombres nuevos para respaldos. Ensayos dejan activos DEMO y conteos sintéticos con prueba true. Para datos reales usa IDs acordados distintos de DEMO y registra fuente.

Conserva configuración y issuer localhost:8080. Si cambias puertos/PC, revisa Compose, SAN, realm, redirectUris, post logout, CSP y config.json de manera coordinada. No desactives TLS/OIDC.


# Resolver problemas de instalación y arranque

| Síntoma | Comprobar | Acción |
| WSL no instala | winver, virtualización, permisos | PowerShell admin para WSL; diagnóstico oficial y reinicio |
| Docker solo Client | Desktop/backend detenido | Abrir Desktop y repetir docker version |
| Contenedores Windows | docker info OSType | Cambiar a contenedores Linux |
| py incorrecto o Store | Gestor/launcher y terminal | Terminal nueva, py -3.12 y Python de venv |
| Activate.ps1 bloqueado | Política PowerShell | No activarlo; usar ruta absoluta & $PY |
| Puerto ocupado | Diagnóstico y proceso anterior | Detener servicio propio anterior; no cambiar un puerto aislado |
| Rutas con espacios | Comillas y carpeta | C0 y rutas entre comillas |
| Ensamblador no encontrado | Extracción y CWD | Revisar paquete_franco/Franco |

Si falla pip, comprueba conexión y venv. Conserva el error concreto; no instales globalmente ni cambies todas las versiones. SUMO se instala en la misma venv que ejecuta su script.

Si una imagen no descarga, revisa etiqueta en .env.example y registro oficial. Su disponibilidad se comprueba en la PC del equipo. Si cambias versión, repite configuración/migración/integración y registra decisión.

Los ZIP no instalan servicios por sí solos. Completa descarga y configuración antes de interpretar un error del entorno como fallo de código.


# Resolver problemas de datos y autenticación

| Síntoma | Comprobación y solución |
| TLS rechaza certificado | CA del mismo runtime, SAN localhost y reloj. No desactivar validación |
| MQTT no autorizado | cargar_env con credencial prueba o deteccion según tarea; revisar ACL |
| PUBACK sin conteos | Logs consumer/DB, contrato y rango UTC; PUBACK no confirma BD |
| API 401 | Repetir login, revisar issuer/audience/fecha; no usar ID token como access token |
| API 403 | Administrador para escribir inventario; operador solo lectura |
| invalid_redirect_uri | Realm y URL exacta. Importar no actualiza realm existente |
| CLI no abre 8766 | Terminar login anterior propio y repetir; no exponer a red |
| Cámara sin cuadros | Permisos, conexión, índice y otra app. Usar comprobar_camara |
| CUDA no disponible | Hardware/driver/build PyTorch; CPU solo para arranque |
| SUMO no encuentra binario | SUMO_HOME y ejecutables de esa venv |
| SUMO rechaza demanda | Duplicados/solapamiento/clases/zona; cero vehículos no da demora |

Panel vacío: confirmar login, intersección, rango y datos. Desactiva Última hora en vivo para consultar historia. No rellenes datos manualmente para aparentar cámara.

Error SQL de tabla/extensión: revisar logs db. Una base existente no repite initdb. No borrar volúmenes: requiere migración revisada o nueva base de laboratorio separada.


# Resultados de referencia y evidencia

## Verificado al preparar la entrega
Pasaron 34 pruebas sintéticas: contratos, API con repositorio en memoria, JWT/permisos, inventario, líneas, calibración numérica, certificados con Docker sustituido, login CLI, límites de estados y rechazo de releases antiguas.

SUMO 1.27.0 ejecutó red DEMO con semilla 42 y completó 13 vehículos. Los datos están en data/leonardo/resultados_sinteticos. No son mediciones del piloto ni un plan vigente real.

## Pendiente de ejecutar en la PC de Franco
Docker/Mosquitto/TimescaleDB/Keycloak/Nginx en vivo, panel visual, login de navegador, cámara/GPU, precisión de tráfico, inventario real y aprobación docente. Pruebas en memoria no acreditan SQL real. El ensayo breve no sustituye la hora continua de S3.

## Registro recomendado
Guardar fecha, responsable, release, origen, comando, resultado y referencia de evidencia. Separar PASS_SINTETICO, validación real y PENDIENTE. Un FAIL sigue visible hasta corregirse y repetirse.

Las capturas pueden mostrar tablas numéricas; nunca cámara, contraseñas o tokens. Usa prueba_panel.csv para tiempos de búsqueda y revision_reglas.csv para decisiones. Las reglas permanecen borrador hasta decisión registrada.

Esta guía corresponde a los ZIP acumulativos s1-it1a8-v1. No modifica HTML ni Excel. El detalle de correcciones/límites está en informes de cada paquete.


# Referencias oficiales

Descargas e instalación:

- [Microsoft WSL](https://learn.microsoft.com/en-us/windows/wsl/install)
- [Docker Desktop Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
- [Notas de versión Docker](https://docs.docker.com/desktop/release-notes/)
- [Python en Windows y gestor](https://docs.python.org/3/using/windows.html)
- [Python 3.12.10 como referencia tradicional](https://www.python.org/downloads/release/python-31210/)
- [Git para Windows](https://git-scm.com/install/windows)
- [SUMO 1.27.0 PyPI](https://pypi.org/project/eclipse-sumo/1.27.0/)
- [Descargas SUMO](https://sumo.dlr.de/docs/Downloads.php)
- [Instalación Ultralytics](https://docs.ultralytics.com/quickstart/)
- [Selector PyTorch](https://pytorch.org/get-started/locally/)

Comportamiento de las herramientas:

- [Paho MQTT Python](https://eclipse.dev/paho/clients/python/docs/)
- [Configuración Mosquitto](https://mosquitto.org/man/mosquitto-conf-5.html)
- [Administración Keycloak](https://www.keycloak.org/docs/latest/server_admin/index.html)
- [Timescale hypertable](https://docs.timescale.com/api/latest/hypertable/create_hypertable/)
- [SUMO TripInfo y timeLoss](https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html)

Fuentes del proyecto: Excel Formato_Proyecto_Gestión__Semaforica, texto del Sprint 1 y HTML sprint_1_equipo con ocho iteraciones. Los paquetes conservan huellas de fuentes y checksums propios.

Consulta: 26/10/2026. Versiones de pruebas registradas en reports. Una descarga puede ofrecer versiones posteriores a requirements; no cambiarlas sin repetir pruebas.
