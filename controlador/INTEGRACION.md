# Operación semafórica S2 con SQL Server

Este banco conecta **conteos MQTT → SQL Server → Webster/SUMO → decisión con MFA
real de Keycloak → MQTT/TLS → controlador PC/Arduino → confirmación y panel**.
La placa conserva `arduino/mmu_cysa/mmu_cysa.ino` y los pines D2 a D7 del montaje
documentado. No se cambian firmware, voltajes ni cableado automáticamente.

## Diferencia con Web III y con el monitoreo anterior

* **Web III:** `dotnet/CYSA.Web.sln`, SQL Server `CYSA_WebIII_Demo`, Swagger y MFA
  simulada de laboratorio. No se utiliza su token demo para enviar planes.
* **Banco S2:** servicio local Python en `http://localhost:5184`, datos operativos
  en **SQL Server `CYSA_Control_S2`**, JWT RS256 de Keycloak con OTP real y MQTT/TLS.
  Esta base separada conserva conteos, estados, planes, validaciones, decisiones,
  envíos y auditoría. Su migración idempotente es `operacion/sql/001_operacion.sql`.
* El despliegue histórico de monitoreo de Docker conserva su PostgreSQL mientras
  se migra por etapas. **El flujo nuevo del banco S2 no persiste en PostgreSQL**.
  No se modifica ni se borra la base de Web III ni los datos del monitoreo anterior.

## Preparar el entorno una vez

1. Instalar Python 3.12, SQL Server local y **ODBC Driver 18 for SQL Server**.
   El usuario Windows necesita permisos para crear la base del banco. No hay
   usuarios ni contraseñas SQL incrustados: se usa autenticación integrada.
2. Configurar e iniciar el entorno IoT siguiendo Proyecto de Sistemas I en el
   README principal: broker y Keycloak deben estar en ejecución, con sus cuentas
   y certificados locales generados. No volver a crear sus secretos.
3. Al actualizar una instalación, recargar la ACL y el consumidor del centro:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml restart mosquitto
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build consumer
```

Si la instalación usa el lanzador, aplicar las mismas operaciones al proyecto y
los archivos Compose de esa instalación; sus puertos pueden ser distintos.

4. Desde la raíz del repositorio, abrir otra PowerShell y ejecutar:

```powershell
.\iniciar_operacion.ps1
```

El script reutiliza las credenciales de esta copia o las de
`%LOCALAPPDATA%\CYSA\workspace` si corresponden al lanzador; crea solo la clave de
firmas del banco cuando falta, instala dependencias en `.venv`, configura OTP y
prepara SQL Server. No programa el Arduino. La primera descarga de SUMO puede tardar.
Mantener abierta esta terminal. Para otra instancia:

```powershell
.\iniciar_operacion.ps1 -InstanciaSQL '(localdb)\MSSQLLocalDB'
```

Con una ubicación explícita de la instalación IoT:

```powershell
.\iniciar_operacion.ps1 -Instalacion 'C:\ruta\de\la\instalacion'
```

La cadena equivalente del banco es un ejemplo sin credenciales reales:
`Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=CYSA_Control_S2;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes`.
Solo se admiten las instancias locales declaradas en `operacion/sqlserver.py`.

## Probar primero sin placa

La cámara o un publicador de pruebas debe enviar conteos `prueba=true` para
`DEMO_INT_01`, accesos N/S/E/W. Se guardan en SQL Server antes de calcular planes.
No se aceptan métricas de simulación enviadas por el navegador como evidencia.

Abrir otra terminal con el entorno de esta copia y ejecutar:

```powershell
.\iniciar_controlador.ps1 -SinPlaca -Mqtt -RecibirPlanes
```

Para usar certificados de una instalación distinta, añadir `-Instalacion
'C:\ruta\de\la\instalacion'` a ambos scripts. API y controlador deben usar la misma clave.
No copiarla a Git ni incluirla en entregas.

## Revisar desde el panel

1. Abrir **http://localhost:5184** o pulsar **Operación semafórica (S2)** en el
   panel principal. Este servicio debe estar iniciado antes de usar el botón.
2. Ingresar con Keycloak usando usuario y contraseña. Consultar no requiere OTP.
   La primera autorización o rechazo solicita configurar el autenticador con QR;
   las siguientes acciones críticas usan códigos OTP sin registrar de nuevo el dispositivo.
3. El servicio propone planes Webster cuando una ventana cerrada de cinco minutos
   tiene conteos del banco. El cálculo y SUMO se ejecutan en segundo plano.
   El administrador puede modificar una configuración aprobada de `DEMO_INT_01`
   desde `/proyecto` con MFA. La siguiente propuesta incluye su versión y límites.
4. Revisar **Evidencia**: demanda, comparación por acceso, micros/resto, reducción
   y motivos de rechazo. Un plan no aprobado no puede enviarse.
5. Como **operador**, ingresar un motivo y pulsar **Autorizar** o **Rechazar**.
   La evidencia OTP dura cinco minutos; **Renovar autenticación MFA** exige un
   ingreso nuevo. Una sesión solo con contraseña no puede decidir.
6. Observar las etapas: `pendiente`, `enviado` y `aplicado`. **Enviado no significa
   ejecutado**: solo se muestra aplicado después del recibo firmado del controlador.
7. Ver fase y plan reales reportados por el controlador. El envío se reintenta
   con el mismo UUID; no produce una segunda decisión ni reaplica el plan.

## Prioridades y límites del banco

Webster debe reducir al menos 10 % la demora global. Todos los candidatos se
simulan frente al mismo plan fijo, demanda y semilla, y se rechaza un perjuicio
superior al 15 % por acceso. Micros utiliza una extensión de hasta 10 s una vez por
ciclo; la búsqueda solo recomienda un candidato si micros mejora al menos 10 %
y el resto no empeora más de 10 %. La solicitud peatonal inicia un cruce con todos
los vehículos en rojo. Los 5 s de cruce y el despeje de L/0,9 s se completan antes
de habilitar tráfico vehicular. SUMO incluye una persona de prueba.

Para escenarios controlados de micros y emergencias, usar el módulo de consola
`python -m operacion.generar DESDE HASTA --modo micros --grupo NS`. Para emergencia
usar `--modo emergencia --grupo EO --evento HORA`. Las tres fechas son ISO 8601 con
zona horaria. Se usa el mismo entorno de Python y SQL Server que al iniciar S2.
Para solicitar un cruce en la emulación local, pasar `--solicitar-cruce-en N` al
módulo `cysa_controlador.run`. N son segundos desde el arranque del emulador.

La emergencia del banco es un **evento predefinido** con fecha/hora (hasta cuatro
minutos por delante), que permite autorizar el plan antes del evento. El plazo
de diez segundos se mide desde el evento. Si un cruce ya está activo, se mantiene
la etapa peatonal pendiente antes de cambiar a prioridad. El verde vehicular
respeta el mínimo, seguido por ámbar y todo rojo. Si el cambio no cabe en el
plazo aplicable, se rechaza. Al completar la prioridad, el secuenciador retoma
el plan anterior en la fase siguiente. Micros cede ante una emergencia.

Estos eventos controlados no acreditan detección automática de ambulancias ni
precisión YOLO de micros/emergencias: esas métricas requieren videos etiquetados
y se miden aparte. El banco solo opera DEMO_INT_01, no un cruce de vía pública.

## Prueba con Arduino

1. Revisar el montaje y resistencias de la guía del controlador. No conectar
   cargas, relés ni luces de potencia directamente a los pines. Este firmware es
   para el banco de LEDs documentado.
2. Cerrar el Monitor Serie y cualquier otro proceso que use COM3.
3. Con el firmware MMU ya cargado y comprobado, sustituir el proceso sin placa por:

```powershell
.\iniciar_controlador.ps1 -Puerto COM3 -Mqtt -RecibirPlanes
```

4. Repetir una autorización desde el panel. El cambio espera un todo rojo.
   El MMU Arduino valida las salidas vehiculares. La fase peatonal se observa
   en el estado del emulador y en SUMO.
5. Cerrar con Ctrl+C. Al cesar los mensajes, el MMU entra en rojo intermitente.
   La respuesta serial acredita las reglas del firmware; el montaje de los LEDs
   siempre se comprueba visualmente. No se flashea la placa durante estas pruebas.

## Regresión

```powershell
python tools/franco/probar.py
node --test tests/franco/oidc.test.mjs
```

Para las pruebas optativas con SQL Server real se usa exclusivamente
`CYSA_Control_S2_Pruebas`, nunca la base normal ni la de Web III:

```powershell
$env:CYSA_SQL_TESTS='1'
$env:CYSA_SQL_DATABASE='CYSA_Control_S2_Pruebas'
python tools/franco/probar.py
```

Se prueban decisiones concurrentes e idempotentes, rechazos sin envío, huellas,
recibos persistentes, caducidad, firma, pérdida de centro y transiciones seguras.
El resultado de la ejecución local, incluida la placa en COM3, está en
[VERIFICACION.md](VERIFICACION.md).
