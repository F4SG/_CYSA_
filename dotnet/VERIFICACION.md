# Verificación de las APIs de CYSA

Revisión local del 15 de noviembre de 2026 sobre la base `294096a7df12a6ac5cf11c7a097a781d938d6718`, rama de trabajo `feature/apis-dotnet`.

| Comprobación | Resultado |
| --- | --- |
| Compilación .NET 10 de la solución, advertencias tratadas como errores | Correcta. |
| Pruebas automatizadas .NET | 31 correctas, 0 fallidas. |
| Dos procesos Kestrel y peticiones HTTP reales | Correcto: Swagger, evaluación aprobada/rechazada, permisos y MFA de demo. |
| Reintento de decisión y reinicio de Decisiones | Sin duplicación; historial conservado en SQLite. |
| Suite Python preexistente `tools/franco/probar.py` | 206 correctas; una advertencia de deprecación de Starlette/httpx. |
| Suite JavaScript preexistente `node --test tests/franco/oidc.test.mjs` | 3 correctas. |
| Comparación de código anterior con el commit base | Sin cambios de código fuera de la carpeta nueva `dotnet/`; README principal actualizado para documentar la extensión. |
| Exclusión de tokens, claves, bases y binarios de Git | Verificada con `git check-ignore`. |

Las dependencias de regresión Python se instalaron en `dotnet/runtime/regression`, sin modificar el entorno del proyecto ni sus requirements. La primera ejecución restringida se bloqueó al iniciar TestClient; la ejecución fuera de esa restricción terminó correctamente.

No se probaron cámara/GPU, una instalación Docker en funcionamiento, SUMO real, MFA real de Keycloak ni actuación sobre semáforos. Las pruebas no constituyen una certificación de esos componentes. El módulo está preparado como demostración aislada, con métricas suministradas y tokens de prueba. La solución y perfiles se prepararon para Visual Studio Community 2026; la compilación y ejecución se verificaron con la CLI .NET y procesos HTTP.
