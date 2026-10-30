# RF-12: gestión local de usuarios (Sprint 1)

## Alcance aplicado

El panel incorpora Usuarios solo para el rol administrador. Permite listar/buscar/paginar,
crear cuentas de operador o administrador, cambiar rol y activar/desactivar cuentas.
No se crean cuentas directamente en PostgreSQL ni se implementa otra autenticación:
Keycloak mantiene usuarios, contraseñas, roles y sesiones. El login sigue con Authorization
Code + PKCE y tokens en memoria. Las contraseñas nuevas son temporales (mínimo 12 caracteres)
y Keycloak exige cambiarlas al primer ingreso. No hay registro público ni eliminación desde
el panel; se conservan identificadores e historial al desactivar.

El propio administrador no puede cambiar su rol ni desactivarse. Cada escritura administrativa
comprueba el rol vigente y el estado de la cuenta en Keycloak, además del JWT, incluyendo
las escrituras de inventario. Así, un JWT antiguo no mantiene permisos de escritura tras
quitar el rol. La lectura también comprueba el estado y el rol vigentes en cada petición; al desactivar/cambiar rol también se cierran las sesiones y refresh tokens.
Las cuentas técnicas están excluidas y solo se admiten los dos roles de CYSA.
Los roles heredados por grupos deben resolverse en Keycloak antes de cambiar esa cuenta.

La API usa una cuenta técnica confidencial cysa-user-admin, solo en el backend, con
query-users/view-users/manage-users/view-realm del cliente realm-management. No se dan
privilegios de la consola maestra de Keycloak a los usuarios de CYSA. Su secreto está en
infra/runtime/clientes/usuarios-api.env, excluido de Git y cargado solamente por el servicio
api. El cliente no admite login interactivo ni password grant. El bootstrap de instalación
se usa solo en la herramienta local de configuración, nunca desde el panel.

La creación asigna el rol antes de habilitar la cuenta; ante fallos se intenta desactivar y
limpiar la cuenta incompleta. Un fallo de comunicación deja un resultado incierto que debe
verificarse en Keycloak; no se informa éxito. Los cambios se serializan en la única instancia
actual de API. Antes de desplegar múltiples trabajadores/instancias se requiere coordinación
distribuida. Las respuestas no exponen credenciales, secretos ni cuerpos de validación con claves.

Se habilitan eventos administrativos de Keycloak sin guardar representaciones (pueden contener
secretos); los logs de API registran ID del actor real, cuenta, rol y resultado sin contraseñas.
La trazabilidad común persistente RF-02 sigue planificada en S2/S3. El MFA también conserva
su implementación/pruebas previstas para S2/S3. La autorización de planes permanece deshabilitada.
No se afirma el cierre completo de RF-12 o de los requisitos de auditoría/MFA.

## Instalar en una copia existente

Desde la raíz del repositorio, con Keycloak local funcionando y las credenciales existentes
en infra/.env (no volver a generar todos los secretos):

```powershell
.\.venv\Scripts\python.exe tools/franco/configurar_usuarios_local.py
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build --no-deps api
```

La herramienta crea una sola vez usuarios-api.env y configura/actualiza únicamente su cliente
técnico en el realm existente. No recrea realms, volúmenes, usuarios ni los datos de monitoreo.
Puede repetirse: reutiliza el secreto ya generado. Nunca imprime contraseñas ni tokens.
En una instalación nueva, preparar_local.py crea también el archivo de entorno necesario;
levantar los servicios, esperar que Keycloak responda y ejecutar configurar_usuarios_local.py.

## Probar desde el panel

1. Abrir http://localhost:8088/ y recargar con Ctrl+F5 si había una versión anterior.
2. Ingresar con una cuenta administradora y abrir Usuarios.
3. Completar usuario, nombre, apellido, correo, rol y contraseña temporal. Crear usuario.
4. Abrir otra sesión (por ejemplo privada), ingresar con la cuenta nueva y cambiar la clave.
5. Como operador, no se ve Usuarios y GET/POST/PATCH /api/usuarios devuelve 403 incluso
   enviando la petición directamente. Como administrador, sí permite gestionar cuentas.
6. Cambiar el rol o estado de otra cuenta y verificar su siguiente ingreso. La propia cuenta
   aparece protegida. Una cuenta con rol revocado tampoco puede cargar inventario con su JWT anterior.

Se dejaron dos cuentas reales de prueba locales (una por rol), con contraseñas ya cambiadas
mediante el flujo de Keycloak. Sus credenciales están únicamente en
infra/runtime/clientes/cuentas-locales.json. No compartir ni versionar ese archivo.

## API

- GET /api/usuarios?search=&offset=0&limit=25: consulta solo administradores; máximo 50 por página.
- POST /api/usuarios: username, first_name, last_name, email, role y password. Responde 201.
- PATCH /api/usuarios/{uuid}: role y enabled booleano. Sin borrado de cuentas ni cambio de clave desde aquí.
- 401 sin sesión; 403 sin permiso; 409 duplicado/autoprotección/roles heredados; 422 datos inválidos;
  503 identidad no disponible o integración pendiente. Sin caché de respuestas de usuarios.

## Evidencia local del 30/10/2026

156 pruebas automatizadas aprobaron (una advertencia preexistente del TestClient).
Además se probó panel + FastAPI + Keycloak reales en un navegador sin ventana visible y con
perfil aislado: alta de ambos roles desde el formulario, cambio obligatorio de contraseña,
login del nuevo operador y administrador, operador bloqueado por API, autoprotección,
activación/desactivación desde la tabla, cambio de rol y rechazo de un JWT antiguo tanto
en gestión de usuarios como en carga de inventario. Se revisó diseño de escritorio y móvil.
Los servicios conservan los datos existentes y /health responde status=ok, activacion_planes=false.
No se tomó control del escritorio. Los cambios de esta función permanecen locales.

## Documentación de referencia

- API oficial de Keycloak: https://www.keycloak.org/docs-api/latest/rest-api/index.html
- Administración y cuentas de servicio: https://www.keycloak.org/docs/latest/server_admin/index.html

## Revisión posterior de seguridad

La revisión del 30/10 normalizó las cuatro cuentas conocidas a administrador, admin.accesos,
operador y operador.transito, con perfiles funcionales y direcciones reservadas cysa.example
para este entorno local. Se conservaron IDs, roles y contraseñas. No representan identidades
personales de funcionarios: las cuentas nominativas reales deben crearse con sus datos.
Se añadió protección temporal ante intentos fallidos, política de clave entre 12 y 128
caracteres y comprobación obligatoria de identidad vigente para lectura y escritura.
El control no se omite por falta de un secreto: responde indisponibilidad y deniega acceso.
La migración mantiene deshabilitada la edición propia de nombres tras terminar.
Ver auditoria_seguridad_2026_10_30.md para alcance, evidencia y límites.
