# Mejora de motos con recorte de carriles — 30/10/2026

## Alcance y tecnología

Se mantiene YOLO26s preentrenado, ByteTrack, el S10+ por nombre, las clases auto/micro/moto,
los carriles fijos de la vía inferior, los contratos y MQTT. No se entrenó un modelo, no se añadieron
sensores ni se modificaron los datos del video. El piloto con cámara IP/GPU y el objetivo RF-03 de
error ≤10 % siguen siendo la referencia del formato del proyecto.

## Cambio aplicado

Antes, la inferencia reducía toda la imagen 1280×720, incluidos los márgenes y otras vías. Las zonas
calibradas ocupan solo una fracción. Ahora se toma el rectángulo que contiene todos los polígonos,
con margen del 15 %, y YOLO recibe ese recorte a 512. El margen mantiene parte del contexto para
ver vehículos antes de cruzar la línea. La detección se convierte de nuevo a las coordenadas del
cuadro original antes de asignar carril y contar.

```yaml
crop_to_lanes: true
roi_padding: 0.15
imgsz: 512
```

El modelo y todos los umbrales se conservan. Se verificó igualdad exacta de la geometría antes/después.
El visor conserva el cuadro completo y sus líneas, y añade “ROI carriles” al indicador. El recorte se
aplica solo a zonas fijas: rechaza activarlo con carriles automáticos o líneas sin polígono. Si cambia
el encuadre, hay que recalibrar la cámara como antes; el recorte usa las zonas nuevas al reiniciar.
Para comparar con el comportamiento anterior, desactivar crop_to_lanes y usar imgsz=640.

## Evidencia experimental

Fuente externa: C:/Video/Video-Reescalado.mp4, vía inferior. Los cuadros se inspeccionaron y
procesaron en RAM; no se guardaron imágenes ni videos. Se usó además una simulación que coloca
el video vertical centrado en un cuadro 1280×720 con márgenes negros. Esta simulación reproduce
la pérdida de tamaño útil, pero no el enfoque, compresión, perspectiva ni la red del S10+ real.

En 8 muestras positivas seleccionadas visualmente (56, 57, 58, 59, 60, 61, 239 y 240 s), el perfil
completo detectó motos por encima de .15 en 4 muestras. El recorte de la vía inferior a 512 lo hizo
en 7. La inferencia tardó de media 38,0 ms y 38,7 ms respectivamente. No es una medición de precisión:
la muestra es pequeña, no cubre tráfico completo ni evalúa falsos positivos exhaustivamente.

Se probó también el bucle final de CYSA, con ByteTrack, filtros por clase, restauración de coordenadas
y dibujo, sobre la simulación de encuadre. Cada tramo comprende 60 cuadros. No se publicaron eventos
MQTT en estas pruebas: el resultado se consumió en memoria.

| Tramo | Cuadro completo | Recorte aplicado | Tiempo completo/recorte |
|---|---:|---:|---:|
| Inicio 56 s | 0/60 cuadros con moto seguida y visible | 22/60 | 2,93/2,77 s |
| Inicio 59 s | 46/60 | 60/60 | 2,66/2,71 s |

En el segundo tramo, el recorte mantuvo un ID de moto frente a dos del perfil completo. Eso no acredita
estabilidad en toda la grabación ni exactitud de aforo. Los tiempos corresponden al equipo de prueba,
no garantizan FPS del teléfono en vivo. El caso del segundo 57 aún puede perderse; hay oclusiones y
detalle insuficiente que el recorte no recupera por sí mismo.

## Verificación y pendientes

89 pruebas específicas de detección/cámara/geometría/captura pasaron, incluyendo 9 del recorte:
coordenadas restauradas, margen, límites del cuadro, configuración inválida y mismo conteo en una
trayectoria sintética con y sin recorte. Se conservan las pruebas de contrato y los resultados previos
del backend; esta corrida no incluye el fixture de inventario que usa TestClient.

Falta repetir con el celular real apuntando a la pantalla, comparar los conteos por carril y clase
contra muestra manual y medir falsos positivos. No declarar RF-03 cumplido por los recuadros o las
pruebas de software. No se tomó control del escritorio ni se reinició un proceso del usuario.
