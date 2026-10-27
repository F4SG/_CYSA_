# CYSA — Sistema de Monitoreo Semaforico (Sprint 1)

> Gestion Semaforica - Sprint 1
> Sistema de conteo vehicular, monitoreo de estados, inventario de activos e infraestructura segura.

## A. Descripcion general

### Objetivo
- Recibir y persistir conteos vehiculares y estados de semaforo.
- Gestionar inventario de activos por rol.
- Visualizar datos en tiempo real en el Panel de Monitoreo web.
- Simular demandas base con SUMO para calibracion futura.

### Tecnologias y herramientas

| Capa | Tecnologia | Version |
|---|---|---|
| Lenguaje backend | Python | 3.12.10 |
| API REST | FastAPI + Uvicorn | 0.136.0 / 0.34.2 |
| Contratos de datos | Pydantic v2 | 2.11.4 |
| Base de datos | TimescaleDB (PostgreSQL 17) | 2.19.3-pg17 |
| Broker MQTT | Eclipse Mosquitto (TLS) | 2.0.21 |
| Cliente MQTT | Paho-MQTT | 2.1.0 |
| Autenticacion | Keycloak (OIDC + PKCE) | 26.7.0 |
| Panel web | HTML + JS + CSS vanilla | - |
| Proxy web | Nginx | 1.28.0-alpine |
| Orquestacion | Docker Compose v2 | v5.6.1 |
| Simulacion vehicular | Eclipse SUMO | 1.27.0 |
| Deteccion (S2) | Ultralytics YOLO26n, OpenCV | 8.4.63 / 4.11.0.86 |
| Autenticacion JWT | PyJWT + cryptography | 2.10.1 / 50.0.2 |
| Tests | pytest | 8.3.5 |

### Requisitos minimos

| Requisito | Minimo |
|---|---|
| OS | Windows 10/11 64-bit con WSL 2 |
| RAM | 8 GB (recomendado 16 GB) |
| Disco | 20 GB libres |
| Python | 3.12.x 64-bit |
| Docker Desktop | 4.x con backend WSL 2 |
| Git | 2.40 o superior |

---

## B. Arquitectura del proyecto

### Redes Docker
- `operacional` (internal: true): DB <-> Mosquitto <-> Consumer <-> API
- `panel`: API <-> Keycloak <-> Nginx (accesible desde localhost)

### Puertos expuestos en localhost

| Puerto | Servicio |
|---|---|
| 8088 | Panel web (Nginx) |
| 8080 | Keycloak |
| 8883 | Broker MQTT TLS |

### Estructura de carpetas

```
repo_s1/
├── backend/           # API REST FastAPI (Franco)
├── shared/            # Contratos compartidos Pydantic (Franco)
├── inventario/        # Modulo de inventario (Cristhian)
├── deteccion/         # Detector vehicular YOLO (Cristhian) - S2
├── simulacion/        # SUMO + exportacion (Leonardo)
├── panel/             # Interfaz web HTML/JS/CSS (Leonardo)
├── identidad/         # Configuracion Keycloak + Nginx (Franco)
├── infra/             # Docker Compose + Dockerfiles (Franco)
├── data/              # Plantillas y datos por integrante
├── tools/             # Herramientas de prueba y operacion
├── tests/             # Suite pytest 34 casos
├── docs/              # Documentacion por integrante
├── .gitignore
├── .dockerignore
└── README.md
```

---

## C. Distribucion del trabajo

| Integrante | Responsabilidad | Modulos |
|---|---|---|
| Franco (F4SG) | Infraestructura, contratos, backend API, MQTT/TLS, Keycloak | backend/, shared/, infra/, identidad/, tools/franco/, tests/franco/, docs/franco/ |
| Cristhian | Inventario, deteccion YOLO (S2), privacidad | inventario/, deteccion/, tools/cristhian/, tests/cristhian/, docs/cristhian/ |
| Leonardo | Panel web, SUMO, reglas semaforicas | panel/, simulacion/, tests/leonardo/, docs/leonardo/ |

---

## D. Instalacion desde cero

### 1. Requisitos previos

Instalar Git (https://git-scm.com/download/win), Python 3.12 64-bit
(https://www.python.org/downloads/) y Docker Desktop (https://www.docker.com/products/docker-desktop/).

Para WSL 2 (si no esta instalado):
```powershell
wsl --install
wsl --set-default-version 2
```

### 2. Clonar el repositorio

```powershell
git clone https://github.com/F4SG/CYSA.git
Set-Location CYSA
```

### 3. Crear entorno virtual e instalar dependencias

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
pip install -r deteccion/requirements.txt
pip install -r simulacion/requirements.txt
pip install -r tests/requirements.txt
```

### 4. Generar configuracion local (TLS + credenciales)

Ejecutar una sola vez. Requiere Docker Desktop activo.

```powershell
$env:PYTHONPATH = @("$PWD/shared","$PWD/backend","$PWD/inventario","$PWD/deteccion") -join ';'
python tools/franco/preparar_local.py --repo .
```

Genera en infra/runtime/ (excluida del repositorio):
- infra/.env con credenciales de BD, MQTT y Keycloak
- infra/runtime/mqtt/ con CA y certificados TLS del broker
- infra/runtime/keycloak/cysa-realm.json importado al inicio
- infra/runtime/clientes/ con credenciales locales de prueba

### 5. Verificar la instalacion

```powershell
$env:PYTHONPATH = @("$PWD/shared","$PWD/backend","$PWD/inventario","$PWD/deteccion") -join ';'
python tools/franco/diagnostico.py --out resultados/diagnostico.json
python tools/franco/probar.py
```

---

## E. Encendido, apagado y operacion

IMPORTANTE: Ejecutar todos los comandos docker compose desde la carpeta raiz del proyecto.
Si aparece `couldn't find env file`, primero ejecutar Set-Location hacia la carpeta del proyecto.

### ENCENDER los servicios

```powershell
Set-Location "$env:USERPROFILE\Documents\CYSA_S1\repo_s1"

# Uso habitual (contenedores ya existen)
docker compose --env-file infra/.env -f infra/compose.yaml start

# Primera vez o despues de un 'down'
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build
```

### APAGAR los servicios (datos conservados)

```powershell
Set-Location "$env:USERPROFILE\Documents\CYSA_S1\repo_s1"
docker compose --env-file infra/.env -f infra/compose.yaml stop
```

NUNCA usar `down -v` - borra los volumenes y pierde la base de datos.

### Verificar estado

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml ps
Invoke-RestMethod http://localhost:8088/health
```

### Panel web

Abrir: http://localhost:8088
Credenciales locales en: infra/runtime/clientes/usuarios-locales.json

### Reiniciar un servicio especifico

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml restart keycloak
docker compose --env-file infra/.env -f infra/compose.yaml restart api
```

### Errores comunes

| Error | Causa | Solucion |
|---|---|---|
| couldn't find env file | PowerShell fuera de la carpeta del proyecto | Set-Location a la raiz del proyecto |
| ERR_CONNECTION_REFUSED en panel | Keycloak no corre | restart keycloak + ver logs |
| API 401 sesion invalida | Scope basic sin claim sub | Regenerar con preparar_local.py |
| ConnectionRefusedError en verificar_tls | Mosquitto sin puerto expuesto | Verificar ports 8883 en compose.yaml |
| docker compose start falla | Contenedores no existen | Usar up -d --build la primera vez |
| ModuleNotFoundError en pytest | PYTHONPATH no configurado | Configurar PYTHONPATH con shared, backend, inventario, deteccion |
| Keycloak Exited 1 inmediato | JSON invalido en cysa-realm.json | python -c "import json; json.load(open(...))" - regenerar si falla |

---

## F. Flujo de deteccion con Webcam (Guia paso a paso para Cristhian)

Esta seccion documenta el procedimiento paso a paso para que Cristhian (o cualquier integrante del equipo) configure, pruebe y opere la webcam fisica en el flujo de deteccion vehicular YOLO26, publicando aforos agregados en tiempo real hacia el broker MQTT y la base de datos central sin comprometer la privacidad.

### 1. Requisitos previos de hardware y librerias

- **Hardware**: Camara web integrada o externa USB (o en su defecto stream RTSP / DroidCam). Para arranque rapido basta CPU; para rendimiento optimo en tiempo real se recomienda GPU NVIDIA CUDA (`device: 0`).
- **Entorno virtual activo**:
  ```powershell
  Set-Location "$env:USERPROFILE\Documents\CYSA_S1\repo_s1"
  .venv\Scripts\Activate.ps1
  pip install -r deteccion/requirements.txt
  ```
- **Configurar PYTHONPATH**:
  ```powershell
  $env:PYTHONPATH = @("$PWD/shared", "$PWD/deteccion") -join ';'
  ```

### 2. Comprobar la disponibilidad de la camara

Verificar que OpenCV reconozca la camara antes de lanzar el modelo, garantizando que ningun fotograma se almacene en disco:

```powershell
# Probar webcam por defecto (indice 0)
python tools/cristhian/comprobar_camara.py --source 0

# Si se cuenta con camara secundaria o externa USB, probar con indice 1:
python tools/cristhian/comprobar_camara.py --source 1
```

*Salida esperada:*
```text
Fuente disponible: 640 x 480. Cuadro descartado; no acredita escena de trafico ni precision.
```
*(El script captura un unico frame en RAM, valida la resolucion y lo destruye de inmediato).*

### 3. Crear el archivo de calibracion de carriles (YAML)

Copiar la plantilla de configuracion:
```powershell
Copy-Item deteccion/config/carriles_plantilla.yaml deteccion/config/carriles_cristhian.yaml
```

Para obtener las coordenadas de cada carril sin guardar imagenes, marcar las lineas con clics sobre la vista en vivo (dos clics por carril, `q` para terminar); el script imprime el bloque `lanes:` listo para pegar e indica el sentido que cuenta `negative_to_positive`:
```powershell
python tools/cristhian/marcar_lineas.py --source 0 --acceso N
```

Editar `deteccion/config/carriles_cristhian.yaml` con los datos del escenario:

```yaml
# OBLIGATORIO: Cambiar a true (si permanece en false, run.py se niega a iniciar)
configuracion_verificada: true

# Identificador de la interseccion (p. ej. DEMO_INT_01 o la asignada en inventario)
interseccion: DEMO_INT_01

# Indice de la camara verificado en el paso anterior (0, 1) o URL del stream
source: 0

# Modelo YOLO (descarga automatica de yolo26n.pt si no existe localmente)
model: yolo26n.pt

# Dispositivo de procesamiento: 'cpu' para laptop o '0' para GPU NVIDIA
device: cpu

# Bandera de prueba: true para laboratorio/sprint; false para mediciones reales en campo
prueba: true

# Intervalo de agregacion en segundos (valor entre 1 y 30)
intervalo_s: 30

# Umbral de confianza minima para deteccion
confidence: 0.3

# Mapeo de clases del dataset COCO a tipos vehiculares CYSA
class_map:
  2: auto
  5: micro
  3: moto

# Lineas virtuales de conteo (coordenadas normalizadas 0.0 a 1.0, origen superior-izq)
# a: [x, y] inicio del segmento | b: [x, y] fin del segmento
# direction: 'negative_to_positive', 'positive_to_negative' o 'both'
lanes:
  - acceso: N
    carril: N_0
    a: [0.1, 0.6]
    b: [0.8, 0.6]
    direction: negative_to_positive
```

> **Regla de orientacion:** La direccion de cruce se evalua mediante el producto vectorial respecto al segmento dirigido de `a` hacia `b`. Si los vehiculos circulan en sentido contrario al conteo, cambiar a `direction: positive_to_negative` o usar `both` si el carril es bidireccional.

### 4. Ejecutar el flujo de deteccion y publicacion en tiempo real

Para que los eventos se transmitan al backend y se visualicen en el panel, el entorno debe tener cargadas las credenciales MQTT TLS. Las credenciales del cliente `deteccion` (usuario, contrasena y CA) las genera `preparar_local.py` en `infra/runtime/clientes/deteccion.env`; `infra/.env` no las contiene. Se cargan con `cargar_env.py`:

```powershell
# Ejecutar cargando las credenciales MQTT del cliente deteccion
python tools/franco/cargar_env.py infra/runtime/clientes/deteccion.env -- python -m cysa_detector.run --config deteccion/config/carriles_cristhian.yaml --salida-conteos resultados/conteos_cristhian.csv
```

**Con un archivo de video** (por ejemplo, una grabacion del corredor guardada fuera del repositorio), poner su ruta en `source` y agregar la hora real de inicio de la grabacion. Asi los intervalos siguen el tiempo del video y no el de la PC (con GPU el video se procesa mas rapido que su duracion) y coinciden con un conteo manual del mismo video:

```powershell
python tools/franco/cargar_env.py infra/runtime/clientes/deteccion.env -- python -m cysa_detector.run --config deteccion/config/carriles_cristhian.yaml --salida-conteos resultados/conteos_cristhian.csv --inicio-video 2026-10-31T07:00:00-04:00
```

**Comportamiento durante la ejecucion:**
1. Lee los fotogramas secuencialmente en RAM sin generar archivos temporales de video ni imagenes.
2. Aplica deteccion YOLO26 y seguimiento persistente con ByteTrack (mantiene identificadores de trayectorias hasta 120 s).
3. Incrementa el aforo cuando la base inferior del vehiculo cruza el segmento del carril configurado.
4. Al cumplirse la ventana (ej. cada 30 segundos), emite el evento estructurado `Conteo` con UUID unico.
5. Publica via MQTT con TLS cifrado al topic `corredor/{interseccion}/{acceso}/conteos` (puerto 8883, QoS 1).
6. Registra el respaldo incremental en `resultados/conteos_cristhian.csv`.
7. Si el procesamiento por fotograma es demasiado lento (>30.5 s por intervalo), el sistema se detiene automaticamente para evitar violar los contratos temporales.

Para finalizar la captura con la camara, presionar `Ctrl + C`.

### 5. Verificacion estricta de privacidad (Cero imagenes en disco)

El sistema CYSA prohibe el guardado de fotografias, videos o placas en almacenamiento secundario. Cristhian puede auditar el cumplimiento en cualquier momento ejecutando:

```powershell
python tools/cristhian/comprobar_privacidad.py --carpeta resultados --carpeta deteccion --out resultados/privacidad.json
```
*Salida esperada:*
```text
No se encontraron imágenes/videos en las carpetas indicadas; completar revisión SQL y MQTT.
```

### 6. Recuperacion y reenvio de eventos pendientes

Si la red o el broker MQTT se desconectaron durante la captura de la camara, los conteos permanecen respaldados en el archivo CSV local. Cristhian puede reenviarlos al restablecerse la conexion sin temor a duplicados (la base de datos descarta duplicados por `mensaje_id`):

```powershell
python tools/franco/cargar_env.py infra/runtime/clientes/deteccion.env -- python tools/cristhian/reenviar_conteos.py resultados/conteos_cristhian.csv
```

### 7. Calibracion de precision vehicular (RF-03)

Para evaluar el margen de error entre el conteo por camara y una muestra tomada manualmente:

1. Registrar los aforos manuales en una copia de `data/cristhian/plantillas/conteo_manual.csv`, en ventanas que coincidan con intervalos completos del detector (por ejemplo 5 min = 10 intervalos de 30 s).
2. Unir el conteo manual con el CSV del detector (suma los intervalos de 30 s de cada ventana y rechaza ventanas sin cobertura completa):
   ```powershell
   python tools/cristhian/preparar_calibracion.py resultados/conteo_manual.csv resultados/conteos_cristhian.csv resultados/calibracion.csv
   ```
3. Ejecutar la herramienta de evaluacion:
   ```powershell
   python tools/cristhian/calibrar.py resultados/calibracion.csv resultados/calibracion_evaluada.csv
   ```
4. El reporte desglosara el porcentaje de discrepancia por carril y categoria vehicular, validando la meta de tolerancia `<= 10%`.


---

## G. Linea de tiempo del Sprint 1

| Fecha | Iteracion | Hito | Estado |
|---|---|---|---|
| 26/10/2026 | It 1 | Entorno: diagnostico 100%, 34 pruebas | OK |
| 26/10/2026 | It 2 | TLS MQTT verificado: plano rechazado, PUBACK confirmado | OK |
| 26/10/2026 | It 3 | 9 conteos + 4 activos DEMO en panel y BD | OK |
| 26/10/2026 | It 4 | Simulacion SUMO: 13/13 vehiculos, demora_base.csv | OK |
| 26/10/2026 | It 5 | Inspeccion BD: hypertable activa, 0 duplicados | OK |
| 26/10/2026 | It 6 | Ensayo conjunto: 8/8 casos PASS_SINTETICO | OK |
| 26/10/2026 | It 7 | Roles (403/422) + privacidad: 0 multimedia en disco | OK |
| 26/10/2026 | It 8 | Respaldo + restauracion: paridad exacta verificada | OK |

---

## H. Matriz de requisitos Sprint 1

| N | Requisito | Estado | Implementacion | Como verificar |
|---|---|---|---|---|
| R01 | Contratos estrictos Pydantic extra=forbid | OK | shared/cysa/contracts.py | python tools/franco/probar.py |
| R02 | MQTT exclusivamente TLS en puerto 8883 | OK | infra/mosquitto/, shared/cysa/mqtt.py | python tools/franco/verificar_tls.py |
| R03 | Sin listener MQTT plano (1883 cerrado) | OK | infra/mosquitto/mosquitto.conf | aceptacion_local.py |
| R04 | Idempotencia QoS 1 sin duplicados en BD | OK | backend/app/consumer.py | aceptacion_local.py |
| R05 | Mensajes fuera de contrato descartados | OK | backend/app/consumer.py | aceptacion_local.py campo imagen rechazado |
| R06 | Autenticacion OIDC PKCE S256 | OK | panel/oidc.js, identidad/realm.template.json | http://localhost:8088 iniciar sesion |
| R07 | JWT RS256 validado via JWKS en cada request | OK | backend/app/auth.py | curl sin token -> 401 |
| R08 | Rol operador sin escritura en inventario | OK | backend/app/auth.py require_roles | aceptacion_local.py -> 403 |
| R09 | Rol administrador con escritura en inventario | OK | inventario/cysa_inventory/router.py | aceptacion_local.py -> 422 en payload vacio |
| R10 | API REST: /api/conteos, /inventario, /estados, /health | OK | backend/app/main.py | Invoke-RestMethod http://localhost:8088/health |
| R11 | Panel con 3 vistas y etiqueta PRUEBA visible | OK | panel/index.html, panel/app.js | http://localhost:8088 |
| R12 | Hypertable TimescaleDB activa | OK | infra/sql/001_core.sql | inspeccionar_bd.py |
| R13 | POST /planes devuelve 404 (sin activacion S1) | OK | backend/app/main.py | aceptacion_local.py |
| R14 | Simulacion SUMO base con red sintetica | OK | simulacion/sumo_base.py | python simulacion/sumo_base.py --demo |
| R15 | Respaldo y restauracion verificados | OK | tools/franco/respaldo.py, restaurar_copia.py | respaldos/s1_ensayo_01.dump |
| R16 | Sin imagenes/videos en disco privacidad | OK | tools/cristhian/comprobar_privacidad.py | 0 archivos multimedia en resultados/ |
| R17 | Conteo real con camara fisica | PENDIENTE | deteccion/cysa_detector/ | Piloto en campo S2 |
| R18 | Aprobacion docente del Sprint | PENDIENTE | Reunion de cierre requerida | Acta formal pendiente |

---

## Creditos

Proyecto academico Sprint 1
CYSA Sistema de Gestion Semaforica
Integrantes: Franco (F4SG), Cristhian, Leonardo
Fecha de verificacion local: 26 de octubre de 2026
