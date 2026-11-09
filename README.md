# CYSA — Sprint 1

Sistema de monitoreo de tránsito: detecta y cuenta vehículos, guarda los resultados y los muestra en un panel web con acceso por roles.

**Esta entrega incluye el conteo con cámara o video y el asistente para elegir la fuente y marcar carriles.** Trabaja en modo sombra: no cambia semáforos ni activa planes. La API actual es FastAPI; el servicio de análisis en .NET es una propuesta futura y no forma parte de esta entrega.

## Qué puedes demostrar

- Detectar y contar autos, motos y micros por carril.
- Elegir una cámara o un archivo de video desde el asistente.
- Marcar la vía y el sentido de conteo antes de empezar.
- Consultar conteos, inventario y estados reportados desde el navegador.
- Ingresar como operador o administrador; gestionar usuarios con el segundo rol.
- Guardar conteos agregados en CSV y enviarlos al panel mediante MQTT.

[Uso de los patrones creacionales y de los entornos de prueba](casos_estudio/README.md).

## 1. Antes de instalar

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

## 2. Instalar por primera vez

### Descargar y crear el entorno

```powershell
git clone https://github.com/F4SG/_CYSA_.git CYSA
Set-Location CYSA
py -3.12 -m venv .venv
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $py -m pip install -r backend/requirements.txt -r deteccion/requirements.txt -r simulacion/requirements.txt -r tests/requirements.txt
```

Usar `$py` evita tener que activar el entorno virtual. En cada PowerShell nueva, entra a `CYSA` y vuelve a definir `$py` con el comando anterior.

### Generar la configuración local

Con Docker Desktop funcionando:

```powershell
& $py tools/franco/preparar_local.py --repo .
```

Este paso genera automáticamente las contraseñas, certificados MQTT, configuración del panel y archivos de entorno. **Se ejecuta una sola vez**: si ya tienes `infra/.env` o `infra/runtime`, sigue la sección 7 para actualizar.

No copies `.env.example` sobre el `.env` generado. No subas `infra/runtime`, contraseñas ni certificados privados a GitHub.

### Levantar los servicios

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

## 3. Entrar al panel

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

## 4. Configurar y ejecutar el conteo

Primero levanta Docker y entra al panel. El detector se ejecuta en Windows; Docker no abre la cámara.

### Si tienes GPU NVIDIA configurada

Haz doble clic en **`iniciar_conteo.bat`**, o ejecuta desde PowerShell:

```powershell
.\iniciar_conteo.ps1
```

Usa `deteccion/config/video_santa_cruz.yaml`, con GPU `device: 0` y tamaño de inferencia 960. Antes puedes comprobar si tu instalación de PyTorch reconoce CUDA:

```powershell
& $py -c "import torch; print(torch.cuda.is_available())"
```

Si devuelve `False`, usa la opción CPU para esta prueba.

### Si usarás CPU

```powershell
.\iniciar_conteo.ps1 -Perfil deteccion/config/carriles_cristhian.yaml
```

Si PowerShell bloquea los scripts, usa esta alternativa directa con Python:

```powershell
& $py tools/cristhian/detector.py iniciar --config deteccion/config/carriles_cristhian.yaml --fuente --marcar zona --salida resultados/conteos_demo.csv
```

### Pasos del asistente

1. Elige **1: cámara** o **2: archivo de video**. El video de la evidencia no está incluido; prepara tu propio archivo antes de presentar.
2. Selecciona la cámara por nombre o elige el archivo en la ventana.
3. En el editor, marca las **cuatro esquinas de la vía** que quieres contar; excluye acera, puente y otros flujos.
4. Ajusta la cantidad de carriles con las teclas **1 a 8**. Revisa la flecha roja del sentido; **D** la invierte.
5. Pulsa **S** para guardar e iniciar el conteo. **U** deshace un punto; **Q/Esc** sale del editor. Confirma que guardaste antes de continuar.
6. Deja correr el detector. **Q** termina el conteo.

Para marcar únicamente una línea de dos puntos por carril, agrega `-Linea` al comando de PowerShell. La línea no debe atravesar otros flujos.

Los pesos YOLO `.pt` no vienen en Git. Prepara `deteccion/modelos/yolo26s.pt` antes de la presentación; Ultralytics puede descargarlo al primer uso con internet. Si la descarga automática falla, coloca el peso en esa ruta y vuelve a iniciar.

### Dónde queda cada resultado

| Resultado | Dónde verlo |
| --- | --- |
| Video con detecciones y totales de la ejecución | Ventana del detector |
| Conteos agregados de cada intervalo | Panel → Flujo vehicular |
| Copia local de los conteos | `resultados/conteos_<fecha>.csv`, al usar el asistente |
| Fuente y carriles elegidos en el asistente | `resultados/detector/sesion_<perfil>.yaml` |

Los perfiles de demostración usan **`prueba: true`** e intersección **`DEMO_INT_01`**. En el panel consulta ese contexto de validación y la última hora. Cada intervalo dura unos **30 segundos** y el panel consulta cada **15 segundos**: los resultados no aparecen cuadro a cuadro.

## 5. Probar el software para el sprint

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

Un inventario vacío en una instalación nueva es posible: se carga por separado. La vista Comunicación necesita un publicador de estados; ejecutar solo el detector no genera estados de un controlador.

### Pruebas automáticas

Desde la raíz, con las dependencias instaladas:

```powershell
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $py tools/franco/probar.py
node --test tests/franco/oidc.test.mjs
```

El segundo comando requiere Node.js. Estas pruebas validan el software; no sustituyen el ensayo con Docker, cámara y panel ni la medición de precisión en campo.

### Guion breve de presentación

1. Explica el objetivo: monitorear y contar vehículos sin intervenir los semáforos.
2. Muestra el ingreso como operador y las vistas principales.
3. Elige una fuente, marca los carriles y explica el sentido de cruce.
4. Muestra un cruce contado y luego su intervalo en el panel y el CSV.
5. Cambia al administrador y muestra la gestión de usuarios.
6. Presenta la evidencia medida y sus límites.

**Evidencia disponible:** en un video de 10:49 min se reportaron 197 vehículos frente a 194 manuales con marcado por línea (diferencia total de +1,5 %). La clase micro tuvo 57,1 % de error en esa corrida. Es una prueba ajustada sobre un solo video: no demuestra cumplimiento general de RF-03. Consulta la [evidencia completa](docs/cristhian/evidencia_conteo_video.md), incluida la corrida con marcado por zona.

## 6. Encender y apagar otro día

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

## 7. Actualizar una instalación existente

Guarda tus cambios locales y respalda los datos antes de actualizar. Conserva `infra/.env`, `infra/runtime` y los volúmenes. La rama principal actual se llama **`master`**.

```powershell
git switch master
git pull --ff-only origin master
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $py -m pip install -r backend/requirements.txt -r deteccion/requirements.txt -r simulacion/requirements.txt -r tests/requirements.txt
& $py tools/franco/configurar_usuarios_local.py --solo-archivos
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build
```

Cuando Keycloak responda, ejecuta los tres configuradores y recrea `api`, como al final de la sección 2. No ejecutes `preparar_local.py` otra vez. Antes de actualizar Keycloak, consulta el respaldo de identidad en la guía técnica: el respaldo de PostgreSQL no incluye sus cuentas.

## 8. Problemas frecuentes

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

## Arquitectura y documentación

**Cámara/video → YOLO + ByteTrack → conteos → MQTT/TLS → consumidor → PostgreSQL/TimescaleDB → FastAPI → panel web.** Keycloak controla acceso y roles. SUMO se ejecuta aparte mediante herramientas de consola.

- [Guía técnica completa](docs/guia_tecnica_s1.md): arquitectura, endpoints, contratos, simulación, seguridad y respaldos.
- [Gestión de usuarios](docs/franco/gestion_usuarios_local.md).
- [Visor y controles](docs/cristhian/visor_completo.md).
- [Calibración de la vía](docs/cristhian/calibrar_solo_via_inferior.md).
- [Evidencia de conteo con video](docs/cristhian/evidencia_conteo_video.md).

Esta configuración es de laboratorio local. La validación en campo, MFA, auditoría integral y activación de planes corresponden a etapas posteriores.

Equipo: **Franco, Cristhian, Leonardo y Fabrizio**.

## Patrones de diseño implementados

| Patrón | Tipo | Cómo se usa en CYSA |
| --- | --- | --- |
| Prototype | Creacional de objeto | `clonar-perfil` copia un perfil YAML y sus carriles para otra fuente y deja la copia pendiente de calibración. |
| Factory Method | Creacional de clase | Los creadores del detector construyen una fuente de cámara o video según el perfil. Ambas usan el mismo flujo de conteo. |
| Builder | Creacional de objeto | `EscenarioSUMOBuilder` valida y prepara la red, las rutas y la configuración del escenario. |
| Abstract Factory | Creacional de objeto | Cada fábrica crea una fuente de conteos y un controlador compatibles con su entorno, laboratorio o sombra. |
| Singleton | Creacional de objeto | `CoordinadorDetector` mantiene una instancia por proceso y permite una sola sesión de detección activa a la vez. |
