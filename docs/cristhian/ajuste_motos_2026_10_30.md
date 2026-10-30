# Ajuste de detección de motos — 30/10/2026

Se analizó el archivo externo `C:/Video/Video-Reescalado.mp4`: 928×1664, aproximadamente 649,42 s,
30,014 FPS. El archivo no se modificó ni se copió al repositorio. La inspección de cuadros se hizo en RAM.

## Diagnóstico

El perfil anterior usaba YOLO26n y tamaño de inferencia predeterminado 640. En la muestra de 15 s
no devolvía la moto visible, incluso aumentando solamente el tamaño. A 60 s devolvía algunas motos
por debajo del umbral .25. ByteTrack también excluía objetos antes de tener un ID y CYSA ocultaba
los vehículos fuera de los carriles calibrados. Por eso la ausencia de recuadro no equivalía siempre
a ausencia de detección en el modelo.

Se compararon YOLO26n, YOLO26s, YOLO11s y YOLO26m, resoluciones 640/960/1280 y seguimiento
por secuencias. Se eligió YOLO26m a 960 con la cabeza de inferencia sin end-to-end y NMS agnóstico
para reducir recuadros duplicados. Estas opciones están soportadas por Ultralytics 8.4.63 instalado.

## Perfil aplicado al S10+

```yaml
model: deteccion/modelos/yolo26m.pt
imgsz: 960
confidence: 0.25
class_confidence:
  3: 0.15
track_confidence: 0.10
end2end: false
agnostic_nms: true
iou: 0.5
show_outside_lanes: true
```

Se conserva ByteTrack original (inicio/alta .25, baja .10). `track_confidence` deja llegar detecciones
más débiles al tracker; la aceptación posterior conserva .25 para autos/micros y usa .15 para motos.
No se cambia el umbral de autos al de motos. Los objetos sin ID siguen sin contarse. Un vehículo
fuera del carril se dibuja gris y se etiqueta “Fuera de zona - no cuenta”; no incrementa el aforo.
Se conserva la cámara por nombre y la geometría/configuración restante. Los pesos están instalados
localmente bajo `deteccion/modelos/` y excluidos por `*.pt` en Git. No se entrenó un modelo nuevo.

## Resultado y límites

En secuencias de 60 cuadros iniciadas a 14 y 59 s, el perfil anterior mostró motos seguidas en 0 y 17
cuadros. La prueba directa de modelo/tracker candidato produjo 38 y 57; ejecutando el bucle final
completo de CYSA, incluyendo filtros por clase, produjo **35 y 57**. Las comparaciones son de
presencia de recuadro sobre esas muestras, no recall ni precisión frente a anotaciones de referencia.

El segundo 15 se inspeccionó visualmente y se confirmó un recuadro sobre la moto visible. El bucle
final también mostró motos fuera de la zona de conteo en gris. Se mantuvieron la cámara, el video y
MQTT sin cambios durante la validación; esta prueba de archivo no publicó eventos en la base.

En CPU el procesamiento de 60 cuadros tardó aproximadamente 10,6–11,5 s en la prueba completa,
más lento que los 2 s originales del video. No prometer tiempo real ni conteo correcto de todas las
motos en una cámara en vivo. Aumenta la sensibilidad y puede haber falsos positivos/cambios de ID.
El reescalado previo y filmar una pantalla no recuperan detalle perdido. La precisión formal de conteo
sigue requiriendo anotación manual, verificación de carriles y medición de errores.

Suite de software: **89 pruebas aprobadas**, con la advertencia ya existente de Starlette/httpx.
Pruebas nuevas: parámetros, validación, umbrales por clase y conteo de moto débil ya seguida sin
aceptar un auto de igual confianza baja. Los scripts de diagnóstico no guardan cuadros ni videos.

## Probar directamente el archivo

Cerrar la prueba anterior con Q y ejecutar desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe tools/cristhian/probar_motos_video.py --video "C:\Video\Video-Reescalado.mp4" --desde 14
```

El visor muestra clases, IDs, puntajes y tiempo del archivo; no cuenta ni publica MQTT. Q/Esc termina.
Para volver a la cámara con el sistema, cerrar el visor y ejecutar `tools/cristhian/detector.py iniciar`.
Una ejecución antigua debe cerrarse/reiniciarse para cargar el perfil nuevo. No se reinició ningún
proceso del usuario ni se controló su escritorio para esta actualización.
