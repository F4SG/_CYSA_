# Interfaz de CYSA

El panel y el acceso de Keycloak comparten identidad, paleta y temas claro/oscuro.
Se utilizan blanco, gris, negro y verde para la navegación, acciones y estados. Las
vistas de flujo vehicular, inventario, comunicación y usuarios conservan sus permisos
y contratos. La interfaz presenta las funciones disponibles de Sprint 1, sin mostrar
etiquetas de desarrollo ni anunciar funciones futuras. No se activan planes semafóricos.

## Uso

- El selector Apariencia está en el encabezado del panel y en el acceso.
- La elección se conserva entre sesiones de navegador y entre los puertos del acceso y
  el panel usando una cookie de preferencia del mismo host. Solo la preferencia visual
  se almacena también en localStorage; los tokens siguen exclusivamente en memoria.
- Usuarios abre la lista del equipo. Crear usuario abre un formulario modal. Cancelar
  o Escape cierran el formulario; mientras se envía, se impide cerrarlo para no confundir
  cancelación con una petición que ya está en curso.
- Altas de administradores y cambios de acceso piden confirmación en un diálogo del mismo estilo.
- Guardar se habilita cuando cambian el rol o el estado, salvo en la propia cuenta protegida.
- Las tablas se desplazan horizontalmente en pantallas pequeñas y los formularios se adaptan.
- Se distinguen errores, estados vacíos y confirmaciones sin convertir mensajes de éxito en alertas.
- El campo Contexto conserva la distinción entre registros marcados para validación y operación.
  No se alteró el indicador prueba del contrato ni se presentan registros de validación como operativos.

## Tema de acceso

La carpeta identidad/themes/cysa/login extiende el tema nativo keycloak. Conserva sus formularios,
validaciones, acciones de contraseña y mecanismos OIDC; se personalizan estilos, composición,
idioma y mensajes. Los archivos compartidos de tokens y preferencia deben permanecer idénticos
a sus equivalentes del panel. Las pruebas verifican esa coherencia y el montaje de Docker.

Para una instalación existente, desde la raíz:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up -d --no-deps keycloak
# Esperar a que Keycloak responda en localhost:8080.
.\.venv\Scripts\python.exe tools/franco/configurar_interfaz_local.py
```

El configurador actualiza solo tema, nombre público e idioma; no reemplaza cuentas, roles,
clientes ni secretos. El realm.template.json ya incluye el tema para instalaciones nuevas.
En este entorno local de desarrollo se desactiva la caché de temas de Keycloak para permitir
actualizar los recursos montados; habilitarla antes de un despliegue de producción.
El panel carga los archivos montados sin reconstruir la API. Recargar con Ctrl+F5.

## Verificación

Se revisaron visualmente acceso y panel en ambos temas, en escritorio y móvil. La prueba
con navegador aislado sin ventana verificó persistencia de preferencia entre puertos y
recargas, login, formulario modal, cancelación de alta administrativa, alta real de operador,
cambio obligatorio de contraseña con el tema personalizado, permisos, y ausencia de errores
JavaScript/desbordamiento de página en móvil. La cuenta desechable creada por esta verificación
se eliminó al terminar; se conservaron todas las cuentas anteriores.

Guía oficial de temas: https://www.keycloak.org/ui-customization/themes
