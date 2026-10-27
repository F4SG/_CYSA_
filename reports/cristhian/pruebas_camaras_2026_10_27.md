# Actualización de pruebas de cámaras — 27/10/2026

## Cambios incorporados

- Ventana de detección persistente; YOLO no crea/cierra una ventana por cuadro.
- Zonas manuales por carril, línea finita, sentido de cruce y contador visible.
- Estimación automática de carriles basada en trayectorias con fase de calibración estable.
- ID, clase y carril asignado por vehículo; exclusión de cruces fuera de zona y de recuentos en otro carril.
- Solicitud de resolución/FPS y presentación de dimensiones reales del cuadro.
- Selección por nombre con Media Foundation en Windows: no sustituir el S10+ ausente por la laptop.
- Gestor portable de primer plano/segundo plano, consulta y parada cooperativa con control de PID reutilizado.
- Documentación de preparación, pruebas ópticas con pantalla y lectura directa de archivos externos.

## Verificación automatizada de esta actualización

Suite completa: **75 pruebas aprobadas**. Incluye backend, contratos, autenticación, inventario,
SUMO y pruebas de cámara/geometría/tiempo/ventana/gestor. Las pruebas de selección y proceso usan
simulaciones controladas; no implican que se haya abierto una cámara física desde el entorno restringido.
Se mantiene una advertencia de deprecación de Starlette/httpx en TestClient; no hubo fallos.

Comando habitual desde la raíz:

```powershell
.\.venv\Scripts\python.exe tools/franco/probar.py
```

La ejecución de publicación usó un directorio temporal y límites de descubrimiento explícitos por
las restricciones del entorno, con `--basetemp`, `--confcutdir=.` y `--rootdir=.`.

`git diff --check`: sin errores. Comandos de ayuda del gestor y enumerador: ejecutados correctamente.
Escáner de privacidad sobre `deteccion/` y `resultados/`: sin archivos multimedia encontrados.
No cubre otras carpetas, logs externos, MQTT, SQL ni archivos borrados anteriormente.

## Validación con video externo

Se volvió a procesar el archivo de tráfico de unos 20 s con el código final y reloj de video.
La hora inicial fue de ejemplo, no un dato acreditado de la grabación. No se publicó esta prueba en MQTT.

| Dato | Resultado |
|---|---|
| Cuadro recibido del archivo | 1080×1920 |
| Carriles estimados con evidencia | 4 |
| Eventos agregados producidos | 12: un tramo por cuatro carriles y tres clases |
| Cruces después de calibrar | 4 |
| Duración contractual de eventos | Todos positivos y ≤30,5 s |
| Archivos de imagen/video generados por el detector | Ninguno |

Esto acredita que el flujo del archivo se ejecuta, no el número total real de carriles ni exactitud de conteo.
No hay conteo manual de referencia que demuestre la meta ≤10 %. La calibración excluye sus primeros vehículos.

## Pruebas físicas observadas durante la sesión

- Se realizaron comprobaciones locales de webcam y cámara móvil. Las fuentes por índice devolvieron
  640×480 y 1280×720; esos resultados no acreditan por sí solos la identidad del dispositivo.
- Windows mostró el Galaxy S10+ vinculado, con cámara conectada activa y vista en vivo.
- Se probó el enfoque de filmar un video de tráfico en una pantalla, además de leer ese video directamente.
- Hubo una ventana negra al usar una comprobación de un solo cuadro. La herramienta nueva mantiene el
  flujo abierto y muestra resolución real para comprobar el inicio de la cámara.
- Un inicio informó 1920×1080, pero se observó después que estaba usando la laptop al seleccionar `0`.
  No se atribuye Full HD al S10+ a partir de ese registro.
- La selección por nombre y el gestor portable son la corrección de software de esta actualización.
  Repetir la prueba física desde la sesión de Windows del usuario para verificar el dispositivo y la calidad finales.
- La API local respondió `status: ok` durante las comprobaciones previas. Ese health no prueba por sí solo
  captura, calibración, PUBACK ni persistencia de cada evento en el panel.
- Se vinculó también un iPhone 15 Pro, sin validarlo como webcam del detector; la prueba nativa se retomó con Android.

## Pendientes de validación

Comprobar captura del S10+ por nombre con el nuevo código, resolución efectiva y enfoque; contrastar
conteos con una muestra manual alineada; probar en campo con geometría revisada y cubrir el camino
cámara→MQTT→consumer→BD→panel con evidencia numérica. No se modifican los pendientes de aprobación docente
ni se declara validación de aforos reales en calle.
