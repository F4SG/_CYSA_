# Detección, selección de cámara y privacidad

La guía de operación vigente está en la [sección F del README](../../README.md#f-cómo-funciona-la-detección-y-cómo-reproducir-las-pruebas).
Los documentos de iteraciones anteriores describen la base Sprint 1; no sustituyen los comandos actuales.

## Fuentes y captura

Se admiten cámaras por índice, nombre de dispositivo y archivos/URL externos. En Windows,
`camera_name` tiene prioridad sobre el índice y se resuelve con el mismo backend de OpenCV.
Una coincidencia ausente o ambigua detiene el arranque, sin recurrir a otra cámara.
La configuración del Galaxy S10+ usa su nombre de cámara virtual; la plantilla USB exige completar el nombre.
Para un archivo o URL se debe eliminar `camera_name`. Los archivos no reciben propiedades de captura de la webcam.

La resolución/FPS solicitados son propuestas al controlador. Ancho y alto reales se leen de los cuadros;
ni resolución pedida ni FPS declarado equivalen a rendimiento de inferencia o calidad óptica demostrada.
No se aplica escalado para aparentar Full HD. En la sesión hubo una captura 1920×1080 identificada después
como la laptop: no se atribuye esa resolución al S10+.

## Modelo, trayectorias y geometría

YOLO26n preentrenado, sin entrenamiento adicional, con ByteTrack persistente.
COCO: 2→auto, 3→moto, 5→micro; bus→micro es una aproximación local no validada.
El punto de referencia es el centro inferior del recuadro. Solo cuenta un cruce del segmento finito,
en el sentido válido y dentro del polígono del carril asignado. El flujo evita sumar un ID ya contado en otro carril.
La memoria de trayectorias persiste entre intervalos y se poda tras 120 s sin observación.
Reasignaciones de ID, oclusiones y reinicios pueden causar duplicados o pérdidas y requieren contraste manual.

El modo automático agrupa trayectorias y espera evidencia estable después de un tiempo mínimo de observación.
No cuenta durante esa calibración. No es segmentación de marcas viales ni demuestra carriles vacíos;
se congela la geometría al activarse. Recalibrar al mover la cámara. Los polígonos manuales se pueden
marcar sobre un cuadro retenido únicamente en RAM, con la misma fuente y resolución del detector.

## Tiempo, publicación y parada

Intervalos configurables de 1 a 30 s, máximo contractual 30,5 s. En vivo se usa UTC de la PC.
Para un archivo, `--inicio-video` con zona habilita cuadros/FPS como reloj original;
no interpretar el tiempo de procesamiento como tiempo de tráfico. No publicar ceros si no hubo cuadros.
Al EOF o parada cooperativa se publica el último tramo efectivamente observado si cabe en el contrato.
Ctrl+C puede interrumpir antes de emitir el último tramo; excluir ventanas incompletas de la calibración.

CSV conserva UUID antes de MQTT TLS/QoS 1 y permite reenviar eventos con los mismos identificadores.
Un CSV no acredita PUBACK ni persistencia en BD. El consumer valida y aplica idempotencia.
El gestor local puede iniciar sin ventana, consultar estado y solicitar parada mediante un marcador;
no fuerza la terminación de procesos ajenos ni administra lanzadores antiguos de fuera del repositorio.

## Privacidad y alcance de validación

Los cuadros se leen y procesan en RAM. YOLO usa save/save_txt/save_crop/save_frames/show=false;
la vista de CYSA se dibuja aparte en memoria. No se invocan imwrite ni VideoWriter para persistir cuadros.
Solo se guardan CSV agregados, configuración de zonas, logs y control de proceso.
No almacenar imágenes, videos, placas, credenciales ni URLs con contraseñas en el repositorio.

Una prueba filmando una pantalla es de laboratorio, no una medición de calle. La validación con el
video externo de unos 20 s produjo cuatro carriles estimados y cuatro cruces tras calibración, sin
acreditar el número total de carriles ni un porcentaje de precisión. La meta de error ≤10 % requiere
conteos manuales alineados y cobertura completa.

El escáner de privacidad solo cubre las carpetas indicadas: complementar con revisión de MQTT, SQL,
logs y destinos de ejecución. Los informes históricos siguen siendo evidencia de su fecha y alcance.
