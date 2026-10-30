# Referencia del proyecto y perfil de prueba en vivo

Referencia indicada por el usuario: Formato_Proyecto_Gestión__Semaforica.xlsx.
Revisión de solo lectura del 30/10/2026. No se modificó la hoja de cálculo.
SHA256 de la fuente: e8b999681d2a40196a35c7ab73626dff9717ee6e5bcd99559cd91e6c39ce451f

## Requisitos que gobiernan los ajustes

- Perfil!E29, E40 y C84:R90: cámara IA como única fuente, YOLO26, PC con GPU para el piloto,
  red local MQTT con TLS, FastAPI, PostgreSQL/TimescaleDB, Docker Compose, SUMO y panel.
- Requerimientos!I91:Q91 (RF-03, Sprint 1): YOLO preentrenado y configuración reutilizable por carril;
  no entrenar un modelo nuevo. Conservar auto, micro y moto. Diferencia de conteo ≤10 % frente a control manual.
- Requerimientos!I92:Q94: cámara→MQTT→plataforma→panel; datos de prueba identificados.
- Requerimientos!I97:Q98: TLS 1.2+ y privacidad; guardar conteos agregados sin imágenes, video ni placas.
- Requerimientos!I101:Q101: adaptar los dispositivos sin alterar los contratos ni el núcleo del sistema.
- Perfil!E40: piloto en modo sombra. No emitir órdenes a semáforos reales.

El S10+ apuntando a un video es un sustituto de laboratorio para ensayar la captura. No equivale al
piloto con cámara IP y GPU ni acredita por sí solo RF-03. No cambiar tecnologías, añadir sensores,
entrenar nuevos modelos ni modificar el alcance de los sprints para resolver un problema de fluidez.

## Ajuste aplicado a la prueba con celular

El perfil principal usa YOLO26s preentrenado a 640, cámara S10+ por nombre, solicitud de 1280×720
con 15 FPS y capture_latest=true. Se conservan los umbrales por clase y el seguimiento ByteTrack.
El perfil mediano anterior se conserva en deteccion/config/carriles_motos_modelo_mediano.yaml.
Los pesos locales no se suben a Git.

Se compararon modelos pequeños y medianos en muestras del video externo. YOLO26s a 640 procesó
aproximadamente 25–27 FPS de inferencia en esas muestras. Es una medición de inferencia sobre archivo,
no FPS garantizados del sistema completo ni latencia del enlace del teléfono. La captura y el procesamiento
reales se muestran en la ventana, y la resolución/FPS del controlador pueden diferir de lo solicitado.

Para cámaras, un hilo de captura conserva solo el cuadro reciente en RAM. Mientras el modelo está ocupado,
los cuadros pendientes se reemplazan; no se repite un cuadro ni crece una cola de video. La edad mostrada
se mide desde que OpenCV entrega el cuadro en la PC; no mide el transporte previo desde el S10+.
El hilo lector libera la cámara. Si el controlador se bloquea, no se fuerza un release concurrente.

Para archivos externos se conserva lectura secuencial; capture_latest no se aplica. No se cambian el reloj
del video, los contratos de MQTT ni la lógica central de conteo. No se guarda video ni imágenes nuevas.

## Límites y validación necesaria

El descarte de cuadros reduce el atraso pero puede perder motos pequeñas, recorridos rápidos o continuidad
de IDs. El perfil rápido es de laboratorio y no acredita la meta de ≤10 %. Si los errores superan esa meta,
no declarar RF-03 cumplido: revisar geometría, mejorar el encuadre y validar el hardware GPU previsto.
No usar el perfil de prueba rápida como sustituto de la calibración formal por carril y clase.

Al usar el celular, llenar el encuadre con el video y evitar escritorio, marcos y reflejos. Mantenerlo fijo.
Cerrar la prueba anterior antes de iniciar otra. No se reiniciaron procesos del usuario ni se controló su escritorio.

## Verificación de esta adaptación

68 pruebas específicas de detección, cámara, seguimiento, geometría, tiempo y captura reciente aprobadas.
La regresión general se interrumpió al bloquearse el TestClient del backend en su inicialización de
AnyIO dentro del entorno restringido; no se declara un pase completo de esa corrida.
No se cambió el backend ni se reinició el detector del usuario. Sigue pendiente verificar fluidez y
conteo por clase/carril con el S10+ real, comparando contra conteo manual según RF-03.

## Perfil vigente tras la verificación de motos

Se mantiene YOLO26s y la captura reciente. Con los carriles fijos ya revisados se activa recorte por
polígonos con margen .15 e inferencia 512. Ver `mejora_motos_roi.md` para evidencia, tiempos y límites.
El recorte no cambia las coordenadas ni el conteo central y no acredita la meta de RF-03.
