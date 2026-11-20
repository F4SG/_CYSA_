# APIs históricas de evaluación y decisiones de CYSA

Esta guía describe los dos servicios independientes con SQLite que se conservan para compatibilidad. Para la entrega actual de **Web III**, utiliza **Cysa.Web.Api con SQL Server** y sigue la [guía de ejecución, migraciones y pruebas de Web III](README-WebIII.md). El perfil **CYSA dos APIs** de esta guía corresponde al modo histórico.

Solución para Visual Studio Community 2026 y .NET 10. Incluye **dos APIs ejecutables independientes**, controladores escritos manualmente, reglas en C#, autenticación JWT, documentación Swagger y persistencia con EF Core y SQLite. Es una extensión de laboratorio: no modifica el detector, FastAPI, el panel, MQTT, Docker Compose ni la base de datos de Sprint 1.

## Abrir y ejecutar en Visual Studio Community

1. Abre `CYSA.Web.sln`. Se necesita la carga de trabajo **Desarrollo de ASP.NET y web** y el SDK .NET 10.
2. En la terminal de Visual Studio, entra en la carpeta `dotnet` y ejecuta:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Preparar-Demo.ps1
   ```

   Genera una clave aleatoria y tokens exclusivamente locales en `runtime/`. No modifica Keycloak ni crea usuarios reales. La configuración de ejecución Bypass afecta solo ese proceso.
3. Selecciona **CYSA dos APIs** en el selector de inicio. Si no aparece, clic derecho en la solución → **Configurar proyectos de inicio** → **Varios proyectos de inicio**. Configura ambas APIs como **Iniciar**, con destino **Demo local**, y deja las bibliotecas y pruebas en **Ninguno**.
4. Pulsa F5. Evaluaciones abre `http://localhost:5181/swagger`; Decisiones abre `http://localhost:5182/swagger`.
5. Abre `runtime/Demo.http` y ejecuta las peticiones en orden. Después del POST de evaluación, reemplaza `REEMPLAZAR_UUID` por el `id` recibido. Alternativamente copia el token apropiado de `runtime/tokens.json` en **Authorize** de Swagger, sin agregar la palabra Bearer.
6. Para otra evaluación del mismo plan, incrementa `version`. Para repetir la misma decisión, conserva `solicitudId`; para una nueva operación, usa otro UUID.

Los tokens duran 30 minutos; las decisiones exigen evidencia MFA de los últimos **5 minutos**. Vuelve a ejecutar `Preparar-Demo.ps1` y vuelve a copiar los tokens cuando venza esa ventana. No reinicies las APIs para renovar tokens. La MFA del modo demo es **simulada por el script**, no un segundo factor real.

## Organización

| Proyecto | Responsabilidad |
| --- | --- |
| `Cysa.Evaluaciones.Api` | Servicio HTTP en 5181; valida e importa resultados de escenarios y guarda evaluaciones inmutables. |
| `Cysa.Decisiones.Api` | Servicio HTTP en 5182; consulta Evaluaciones por HTTP, registra una decisión por versión y expone historial. |
| `Cysa.Core` | Contratos, validaciones y cálculo del 15 % y mínimo peatonal. |
| `Cysa.Infrastructure` | Autenticación, configuración común y contextos EF Core. |
| `Cysa.Api.Tests` | Pruebas HTTP con JWT firmados y bases SQLite aisladas, incluidas concurrencia y fallos de red. |

Son dos procesos y dos bases: `runtime/evaluaciones.db` y `runtime/decisiones.db`. Decisiones no abre la base de Evaluaciones: utiliza un cliente HTTP con espera máxima de cinco segundos y sin seguir redirecciones. Ambas comparten contratos y bibliotecas de infraestructura, no el almacenamiento.

## Endpoints

| API | Método y ruta | Permiso | Resultado |
| --- | --- | --- | --- |
| Evaluaciones | `POST /api/evaluaciones` | Scope `evaluaciones:importar` | Evalúa, guarda y devuelve 201, aunque el resultado técnico sea rechazado. |
| Evaluaciones | `GET /api/evaluaciones/{id}` | Lectura | Evaluación completa, versión, huella, métricas y motivos. |
| Evaluaciones | `GET /api/evaluaciones?planId=PLAN_DEMO&pagina=1` | Lectura | Hasta 50 evaluaciones por página, versiones descendentes. |
| Decisiones | `POST /api/planes/{planId}/decisiones` | Operador y MFA reciente | Autoriza o rechaza una versión con evaluación aprobada y vigente. |
| Decisiones | `GET /api/planes/{planId}/decisiones/{id}` | Lectura | Decisión registrada. |
| Decisiones | `GET /api/planes/{planId}/historial?pagina=1` | Lectura | Hasta 50 decisiones por página, versiones descendentes. |
| Ambas | `GET /health` | Público | Identifica que solo opera con pruebas y no activa planes. |

Lectura permite `operador`, `administrador` o el scope de importación. El importador representa una **cuenta de servicio**, no un tercer rol humano. El administrador no autoriza planes; el operador no importa métricas por defecto.

Se devuelven errores ProblemDetails: 400 datos inválidos, 401 JWT ausente/inválido, 403 permiso o MFA insuficientes, 404 recurso inexistente, 409 conflicto de versión/decisión o evaluación no apta, 503 servicio de evaluaciones inaccesible. No se aceptan propiedades adicionales como `usuarioId` o `mfa` enviadas por el cliente.

## Reglas y alcance

- **RF-05 parcial:** compara cada demora candidata con la referencia. Rechaza aumentos estrictamente mayores del 15 %; exactamente 15 % está permitido. No redondea antes de decidir. Una demora base cero no permite el cálculo relativo: devuelve 400 para que se revise ese escenario.
- **RF-10 parcial:** mínimo peatonal `longitud / 0.9 + 5`. Si una fase habilita varios cruces, exige el mayor mínimo. Todos los accesos declarados deben estar cubiertos; se rechazan duplicados y referencias inexistentes. No verifica conflictos entre verdes, ámbar, todo rojo ni controladores reales.
- **RF-02 parcial:** guarda usuario autenticado, fecha UTC, motivo, estado anterior y posterior, UUID de solicitud, evaluación y huella SHA-256. La decisión y su evidencia se escriben juntas. No hay endpoints para editar o borrar el historial. Esto no convierte un archivo SQLite en una bitácora a prueba de alteraciones por un administrador del equipo (RNF-09 queda pendiente).
- **RF-12 parcial:** exige JWT válido, rol operador y evidencia MFA reciente para decidir. La demostración genera esa evidencia de forma ficticia; el perfil OIDC necesita una configuración real del proveedor antes de afirmar cumplimiento completo.
- Cada par `planId/version` tiene una evaluación inmutable y como máximo una decisión definitiva, protegidas por índices únicos incluso con peticiones simultáneas. Las revisiones utilizan otra versión y conservan el historial.
- Las evaluaciones caducan a las 24 horas, una política de esta demo, no un plazo exigido por los requerimientos. Las decisiones ya guardadas se pueden consultar y sus reintentos idénticos no crean duplicados aunque después venza la evaluación.
- `origen: sumo-importado` declara que las métricas vienen de una exportación; **no certifica su procedencia**. El importador debe suministrar todos los accesos del cruce y métricas comparables del mismo escenario. Esta versión no consulta el inventario para comprobar esa exhaustividad.
- No ejecuta SUMO, no calcula Webster, no publica órdenes MQTT y no controla semáforos. Todas las respuestas incluyen `soloPrueba: true`. No sustituye ni modifica los contratos Python de Sprint 1.

## Autenticación OIDC futura

El perfil normal usa JWT RS256 de `Security:Authority` y la audiencia `Security:Audience`; los valores iniciales apuntan al Keycloak local existente. Lee roles firmados de `realm_access.roles` y requiere `sub`, vigencia y firma. Para importaciones, configura una cuenta de servicio con scope `evaluaciones:importar`. Para decisiones, el proveedor debe emitir `amr` con `otp`, `mfa` o `hwk`, más `auth_time` correspondiente a una autenticación multifactor de hace como máximo cinco minutos. Tener MFA habilitado en la cuenta no basta.

Esta configuración no se aplica automáticamente al realm de Sprint 1. El sistema antiguo no garantiza esos claims; no debe suponerse que sus tokens actuales permiten decisiones. Antes de despliegue real se requieren validación con el IdP, política de revocación/cuentas deshabilitadas, TLS, autorización vigente para cada acción y pruebas de integración. Esta extensión valida el JWT hasta su expiración y no consulta el estado actual de la cuenta en cada petición.

Fuera de Development se bloquea el modo Demo y se exige HTTPS hacia Evaluaciones y para los metadatos OIDC. Al publicar, configura `Storage__Directory`, `Evaluaciones__BaseUrl`, `Security__Authority`, `Security__Audience` y `AllowedHosts`; usa almacenamiento nuevo o migraciones versionadas. `EnsureCreated` inicializa la demo vacía, no migra bases existentes.

## Compilar y verificar

Desde `dotnet`:

```powershell
dotnet restore CYSA.Web.sln
dotnet build CYSA.Web.sln --no-restore
dotnet test CYSA.Web.sln --no-restore
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Probar-Integracion.ps1
```

La última prueba abre ambos servicios con puertos libres y bases nuevas, hace peticiones HTTP reales, comprueba persistencia después de reiniciar Decisiones y cierra los procesos creados. No requiere Docker, cámara ni Keycloak. Sus archivos quedan bajo `runtime/smoke/`, excluidos de Git.

También pueden arrancarse desde dos terminales:

```powershell
dotnet run --project src/Cysa.Evaluaciones.Api --launch-profile "Demo local"
dotnet run --project src/Cysa.Decisiones.Api --launch-profile "Demo local"
```

## Guion para la presentación

1. Mostrar en Visual Studio los dos controladores, el servicio de cálculo y las dos bases.
2. Evaluar un plan con demora 40 → 48 segundos: rechazo por aumento del 20 %.
3. Evaluar otro con cruce de 18 m y tiempo peatonal de 20 s: rechazo porque necesita 25 s.
4. Evaluar uno con 40 → 42 segundos y 25 s peatonales: aprobado.
5. Intentar decidir con el token de administrador o de operador sin MFA: 403.
6. Autorizar con el operador de demo; repetir la misma petición y mostrar que no duplica el historial.
7. Consultar la bitácora y explicar que la autorización queda registrada como prueba, sin actuación física.

Referencias de herramientas: [APIs con controladores](https://learn.microsoft.com/en-us/aspnet/core/tutorials/first-web-api?view=aspnetcore-10.0), [varios proyectos de inicio en Visual Studio](https://learn.microsoft.com/en-us/visualstudio/ide/how-to-set-multiple-startup-projects?view=visualstudio).
