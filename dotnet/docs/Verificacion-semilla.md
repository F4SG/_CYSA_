# Verificar datos sintéticos

Después de preparar la base, `GET /api/demo/verificacion` devuelve `cumple`, los
conteos por tabla y cada comprobación con su cantidad de incumplimientos.
Requiere sesión con permiso de lectura, conexión local, Development y Demo habilitado.
HTTP 200 indica que se realizó el diagnóstico: revisar también `cumple`.
No aplica migraciones, borra ni modifica registros.

Desde `dotnet/src/Cysa.Web.Api`, con la conexión local configurada y el entorno
Development: `dotnet run --no-launch-profile -- --verificar-demo`.
El código de salida es 0 si cumple y 1 si detecta incumplimientos. La base debe
estar preparada previamente; este comando no la crea.

La lectura transaccional comprueba mínimos por tabla (Rol=2; las demás >=15),
marcas de prueba, referencias, correspondencia de intersecciones, cobertura de
accesos, tiempos peatonales, métricas total/micro/resto y el límite del 15 %.
También confirma que las funciones futuras siguen identificadas como tales.
El diagnóstico describe el estado actual: operaciones de laboratorio pueden
dejar datos adicionales o una validación pendiente de completar sus métricas.
Recrear la base restaura la semilla de referencia.

Esto verifica coherencia de registros sintéticos; no demuestra una ejecución de
SUMO ni certifica resultados de tránsito real.

`python scripts/Verificar-Semilla.py` comprueba el diagnóstico por CLI y HTTP,
su ausencia de mutaciones, permisos y bloqueo en Production. Introduce una marca
de prueba incorrecta, verifica que se detecte y finalmente recrea la semilla.
Usarlo solo con datos desechables de CYSA_WebIII_Demo.
