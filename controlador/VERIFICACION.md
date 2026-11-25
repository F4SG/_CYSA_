# Verificación del banco S2 — 20 de noviembre de 2026

Pruebas realizadas en Windows, sobre servicios locales aislados del entorno de
trabajo y la base **SQL Server `CYSA_Control_S2_Pruebas`**. No se borró ni migró la
base de Web III ni el almacenamiento anterior de monitoreo.

| Comprobación | Resultado |
| --- | --- |
| Regresión Python, incluyendo SUMO real y transacciones SQL Server | 310 pruebas aprobadas |
| Sesión OIDC: renovación concurrente, error y cierre de sesión | 3 pruebas aprobadas |
| Sintaxis de JavaScript y de los dos scripts PowerShell | Correcta |
| API local y panel S2 | HTTP 200; salud informa SQL Server y conexión MQTT |
| Flujo sin placa | Plan calculado y validado, autorizado, enviado y confirmado |
| Arduino conectado | COM3, plan `OP_c9f2134dfcfb49928977784a6d0d0bfb` aplicado |
| Demanda de la prueba física | 80 mensajes MQTT, 240 vehículos sintéticos |
| Comparación SUMO de ese caso | Reducción de demora global de 23,18 % |
| Autorización | Keycloak real, Authorization Code + PKCE y OTP; `amr=otp` y `auth_time` firmados |
| Permisos | Sin sesión: 401; operador no genera: 403; administrador no decide: 403 |
| Reintento de autorización | Misma decisión y UUID, sin duplicar el envío |
| Persistencia | Nueva conexión SQL consulta la decisión, el recibo y la auditoría |
| Cambio de plan físico | Esperó ámbar y todo rojo; recibió confirmación sin falla MMU reportada |

La prueba física utilizó el protocolo serial del firmware existente, con su
watchdog activo. No se flasheó la placa ni se modificaron pines, voltajes o
cableado. Al detener el controlador se deja actuar al watchdog del MMU. La
confirmación serial no certifica visualmente el montaje de cada LED.

La suite también cubre firmas alteradas, órdenes vencidas, espera del primer
latido, pérdida de centro y retorno a local seguro, la ejecución de escenarios simulados de emergencia.

Este informe conserva los resultados del 20 de noviembre. El piloto vigente
autoriza y despacha Webster, y evalúa la emergencia en SUMO.

Las emergencias son eventos definidos del banco; esta verificación no acredita
reconocimiento automático de ambulancias ni precisión YOLO. Para ello hacen falta
videos etiquetados y mediciones específicas. No se conectan semáforos reales.

Hay una advertencia de deprecación del cliente HTTP de pruebas de Starlette;
no hubo pruebas fallidas en la ejecución final.

Para reproducir los pasos de operación, consultar [INTEGRACION.md](INTEGRACION.md).
