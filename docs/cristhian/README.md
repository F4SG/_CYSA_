> Actualización 27/10/2026: para ejecutar el repositorio actual consultar la [guía principal](../../README.md#f-cómo-funciona-la-detección-y-cómo-reproducir-las-pruebas) y [detección y privacidad](deteccion_y_privacidad.md). El texto siguiente conserva el contexto del paquete histórico de Sprint 1.

# Cristhian Sprint 1 completo de iteraciones 1 a 8
Responsabilidad: detección, inventario y privacidad. Release s1-it1a8-v1.
Este ZIP es acumulativo y sustituye al anterior de iteraciones 1 a 4. No mezclar releases.
Las fechas 26/10–06/11/2026 son hitos planificados; no se presume haber ejecutado reuniones, calibración o aprobación.

## Inicio
1. Leer la guía Guia_Completa_Pruebas_PC_Franco.docx o PDF entregada por separado.
2. Colocar los tres ZIP 1 a 8 en la misma carpeta y extraer solo Franco para ejecutar su ensamblador.
3. Ensamblar a una carpeta nueva, crear venv e instalar dependencias como indica la guía.
4. Usar `documentacion/integracion_comun.md` para los comandos de laboratorio.

## Organización
`codigo`: módulos ejecutables. `configuracion`: Compose, identidades y opciones según propietario.
`datos`: plantillas, ejemplos y resultados sintéticos separados. `documentacion`: instrucciones y contratos.
`informes`: resultados y pendientes. `pruebas`: tests automatizados. `manifiesto.json`: destinos sin colisiones.

## Iteraciones
1. 26/10: preparación del entorno y los insumos de cada responsable.
2. 27–28/10: contratos, TLS, líneas de conteo, identidad y red SUMO base.
3. 29–30/10: conexión de módulos y borrador de reglas.
4. 31/10–02/11: herramientas de calibración y funciones base; datos reales pendientes.
5. 03/11: ensamblador acumulativo, diagnóstico y compatibilidad del repositorio de referencia.
6. 04/11: procedimiento y ejecutor del ensayo sintético en una PC; recorrido con cámara condicionado a recursos.
7. 05/11: matriz de aceptación, evidencia, pruebas de permisos/duplicados/estados y revisión de privacidad.
8. 06/11: documentación, demostración, respaldo y control de pendientes para la entrega.

## Estado
Ver `informes/verificacion_1_a_8.md`. Preparado no significa aceptado. No hay medidas reales de cámara,
GPU ni corredor ni aprobación docente. Docker/Keycloak/MQTT reales requieren ejecución en la PC del equipo.
No hay Webster, prioridades, activación de planes, emulador efectivo ni MFA en S1.
