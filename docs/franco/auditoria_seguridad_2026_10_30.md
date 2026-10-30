# Revisión local de cuentas, código y seguridad — 30/10/2026

## Cambios y evidencia

| Hallazgo | Corrección | Verificación |
| --- | --- | --- |
| Perfiles de laboratorio visibles y nombres poco presentables | Normalización de las cuatro cuentas conocidas: administrador, admin.accesos, operador y operador.transito. Perfiles funcionales; correos reservados cysa.example. Sin cambiar IDs, roles ni contraseñas | Login real con las contraseñas anteriores y lista de Keycloak sin los textos de laboratorio |
| Comprobación de rol vigente omitida si faltaba KC_USERS_CLIENT_SECRET | Eliminado el bypass y el directorio global duplicado. Cada app recibe una única instancia explícita de identidad y verifica todas las lecturas/escrituras | Sin configuración, las escrituras dan 503; no autorizan. Operador bloqueado. Cuenta desactivada y token anterior bloqueados también en monitoreo |
| Carreras entre renovaciones concurrentes de OIDC | Una única renovación en vuelo, invalidación al fallar y generación de sesión que impide restaurar tokens tras logout | Tres pruebas JavaScript: renovación única, fallo y logout durante renovación |
| Recorte inadvertido de contraseñas por str_strip_whitespace global | Solo se recortan campos de perfil; la clave conserva exactamente sus caracteres | Prueba de API y alta/login/cambio de contraseña reales con espacios al principio y al final |
| Sin protección ante intentos repetidos ni política mínima en Keycloak | Bloqueo temporal, 5 fallos, espera incremental; política de 12–128 caracteres. Aplicado en cysa y master sin cambiar las claves actuales | Configuración leída desde Keycloak y login real; plantilla de nuevas instalaciones actualizada |
| Cliente de identidad podía seguir redirecciones | Redirecciones prohibidas; cierre de errores HTTP y límite de respuesta de 2 MiB | Pruebas de redirección y tamaño; flujos reales de Keycloak continúan funcionando |
| Componentes con avisos publicados | Keycloak 26.7.0 → 26.8.1, Nginx 1.28.0 → 1.30.6, PyJWT 2.10.1 → 2.15.1 y pip del contenedor → 26.2.2 | Imágenes y versiones verificadas; login y permisos reales después de actualizar |
| Cabeceras incompletas | CSP con object-src none, X-Frame-Options DENY, Permissions-Policy y ocultación de versión; Nginx validado y recargado | Comprobación de cabeceras HTTP reales |
| Imports y superficie sin uso | Retirados imports no referenciados de backend/herramientas/detección, dos exports de tema y selector CSS sin consumidor | Revisión AST y referencias; se conservan puntos de entrada CLI y callbacks usados dinámicamente |

Se realizaron 166 pruebas Python y 3 pruebas JavaScript, todas aprobadas. La suite mantiene
una advertencia preexistente de deprecación del TestClient (no es un fallo de ejecución).
También se probó el panel real con Edge aislado sin ventana, sin controlar el escritorio:
roles, token alterado, revocación, cambio de rol mediante diálogo, restauración de estado,
temas, alta temporal y cambio de contraseña. Las cuentas desechables de verificación se
eliminaron; permanecen las cuatro cuentas funcionales locales.

## Dependencias y secretos

Se consultó OSV con nombres y versiones de las 21 dependencias Python instaladas en la API.
La primera consulta detectó avisos de pip y PyJWT. Después de actualizar, la misma consulta
no devolvió vulnerabilidades conocidas para ese conjunto y esa fecha. El resultado no
incluye paquetes del sistema operativo, el host Windows ni todas las imágenes de Docker.
El consumidor existente no se reinició: no expone API JWT. Usará las dependencias corregidas
en su siguiente reconstrucción desde el Dockerfile compartido.

Se compararon las credenciales locales generadas con los archivos versionables y no se
hallaron coincidencias. infra/.env, infra/runtime y respaldos permanecen ignorados por Git
y excluidos del contexto de construcción. No se mostraron claves ni tokens en resultados.
Las pruebas que tienen claves literales utilizan valores sintéticos independientes.

## Respaldo y conservación

Antes de actualizar Keycloak se detuvo únicamente ese servicio y se copió su directorio de
datos a respaldos/seguridad-2026-10-30/keycloak-data, junto con la configuración anterior.
Los perfiles anteriores se guardaron en perfiles-anteriores.json, dentro del mismo respaldo.
No se eliminaron volúmenes ni datos de conteos/inventario. Keycloak conserva el volumen existente.
El script endurecer_identidad_local.py limita los cambios de nombre a las cuentas conocidas
por los archivos locales, comprueba colisiones y restaura editUsernameAllowed en finally.
Las credenciales actualizadas están en infra/runtime/clientes/cuentas-locales.json.

## Límites y pendientes

Esta revisión encuentra y corrige problemas concretos; no certifica ausencia absoluta de
bugs, código muerto o vulnerabilidades. No reemplaza una prueba de penetración ni una auditoría
completa de dependencias del sistema, cámaras, red, host o imágenes restantes.

El servicio está enlazado a localhost y conserva start-dev/HTTP para desarrollo. HTTPS de
producción, MFA y trazabilidad persistente RF-02 siguen pendientes según la planificación.
Las cuentas funcionales y correos reservados son locales; un despliegue real requiere cuentas
personales, contactos reales y un tratamiento de secretos adecuado al entorno. La cuenta técnica
usa gestión de usuarios del realm: ese secreto solo debe estar en la API. Para múltiples
trabajadores/instancias se necesita coordinación distribuida de mutaciones, además del lock
actual de la única instancia. No se alteraron detección, MQTT, contratos ni activación de planes.

## Referencias verificadas

- Keycloak 26.8.1 y sus correcciones: https://www.keycloak.org/2026/10/keycloak-2681-released
- Avisos de Nginx: https://nginx.org/en/security_advisories.html
- Cambios de seguridad de PyJWT: https://pyjwt.readthedocs.io/en/stable/changelog.html
- Consulta de vulnerabilidades: https://osv.dev/
