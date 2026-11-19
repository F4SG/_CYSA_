# Reglas de validación y conservación de evidencia

Esta mejora concreta RF-02, RF-05 y RF-10 del proyecto, sin añadir roles ni control manual de semáforos.

* Una versión de plan que ya tiene una validación SUMO conserva sus datos, fases y accesos habilitados, incluso mientras todavía figure como borrador antes de emitir la recomendación. Cualquier modificación requiere una nueva versión.
* Antes de aprobar una validación o emitir una recomendación, la intersección debe tener accesos y fases. Cada acceso necesita cobertura, y cada fase debe respetar el mayor mínimo peatonal de sus accesos: longitud / 0,9 + 5 segundos.
* La recepción de conteos acepta exactamente la versión `1.0`, UUID no vacío e intervalo positivo de hasta 30,5 segundos, conforme al contrato existente de Python/MQTT. Los conteos siguen siendo agregados; no se almacena video.
* Los errores de entrada responden 400. Los intentos de editar o eliminar una versión evaluada responden 409. La autorización de planes conserva el operador y MFA exigidos; no se altera la separación de los dos roles.

`scripts/Probar-WebIII.py` comprueba estas reglas con SQL Server real, incluidos intervalos nulos o excesivos, versión de mensaje inválida, accesos sin fase, mínimo peatonal y protección del plan entre evaluación y recomendación. Las pruebas usan únicamente CYSA_WebIII_Demo y mantienen el carácter sintético de los datos.
