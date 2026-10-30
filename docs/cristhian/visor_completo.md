# Visor completo con carriles y controles

El detector muestra el cuadro completo de la cámara, sin recortarlo para la visualización.
La mejora de motos usa el recorte de carriles únicamente dentro de la inferencia.
Se restauran las coordenadas antes de dibujar y contar; los polígonos guardados no se modifican.

El panel inferior incluye la fuente, el estado, la resolución recibida, tamaño de inferencia,
FPS procesados, antigüedad del cuadro en PC cuando está disponible y acumulados por carril
para auto/micro/moto. Los acumulados son de la ejecución: CSV y MQTT siguen por intervalos.

Botones y teclas:
- Carriles / L: mostrar u ocultar polígonos, líneas y sus etiquetas, sin cambiar el conteo.
- Datos / D: mostrar u ocultar la tabla, sin borrar acumulados.
- Detener / Q / Esc: finalizar la prueba con su cierre habitual.
- Recalibrar / R: disponible únicamente en modo de carriles automáticos.

En esta prueba permanecen los carriles fijos de la vía inferior. Para cambiar su geometría,
se conserva tools/cristhian/calibrar_via.py --iniciar, con ESPACIO, cuatro esquinas,
1–8, U, +/−, S y Q. No es necesario recalibrar por el cambio visual.

Inicio en PowerShell desde la carpeta del repositorio:

```powershell
.\.venv\Scripts\python.exe tools/cristhian/detector.py iniciar
```

Los botones actúan dentro de la ventana OpenCV. El panel se agrega debajo del video, con texto suavizado y más grande; no se guarda
ningún cuadro ni se controla el escritorio. Si ya existe una prueba abierta, cerrarla con Q
y volver a iniciar para cargar el visor actualizado.

La ventana se dimensiona al recibir el primer cuadro según el área de trabajo de Windows
(formato vertical, ancho menor a media pantalla y máximo 720×900, reservando espacio para título y bordes). El video completo se adapta
con su proporción original al espacio superior. Esta escala afecta solo a la visualización.
Los datos se organizan en columnas por carril y los botones en una fila inferior.

En el formato vertical, los conteos se muestran en una tabla compacta de carril, auto,
micro, moto y total. Los botones se distribuyen en dos columnas debajo de los datos.
La vista completa se conserva con su proporción original; no cambia el recorte interno de inferencia.

## Edición y fluidez

Desde detector.py iniciar, el botón Editar carriles o la tecla E cierra ordenadamente
la captura y la publicación de la ejecución actual antes de abrir calibrar_via.py.
El editor también usa formato vertical de media pantalla, con botones debajo.
ESPACIO fija la imagen; marcar las cuatro esquinas en el orden mostrado; 1–8 cambia
la cantidad; U deshace; +/− mueve la línea; S guarda y Q cancela.
Guardar y cancelar vuelven automáticamente al detector usando el mismo YAML y CSV.
Cancelar no cambia las zonas anteriores. La nueva ejecución inicia sus acumulados de
pantalla desde cero; el historial de CSV y backend se conserva.
El retorno interno 20 del detector indica edición, no un error de cámara. El gestor
lo maneja; al ejecutar directamente python -m cysa_detector.run no se abre el editor.

Se solicita captura a 30 FPS en el perfil del S10+ (antes 15). El controlador y el enlace
pueden negociar otro valor. capture_latest sigue activo y conserva un único cuadro
pendiente, por lo que no crea una cola de video cuando la inferencia va más despacio.

La publicación MQTT ahora usa un solo trabajador para mantener orden y una cola acotada
a 64 eventos. El CSV se escribe antes de encolar; un fallo de PUBACK o cola llena se
propaga y deja el registro local para reenvío. La consola distingue registrado/encolado
de una entrega confirmada. El cierre espera las publicaciones pendientes antes de
liberar MQTT. Esto elimina la espera de red del hilo de video durante los intervalos.

Verificación: 103 pruebas específicas de detección/cámara/interfaz, incluidas edición,
retorno del gestor, mapeo de clics, publicación lenta sin bloquear, orden y errores.
En una muestra de 20 cuadros externos procesados en RAM, la inferencia tras calentamiento
promedió 39,0 ms con la configuración inicial de hilos, 130,1 ms con un hilo, 77,1 ms con
dos y 47,8 ms con cuatro. No se redujeron hilos por resultar más lento. Se conservan
YOLO26s, imgsz 512, umbrales de motos, geometría existente y ROI interno. La muestra
es de archivo y no mide la latencia óptica/red del S10+ ni demuestra precisión formal.
Falta verificar la fluidez real al reiniciar la prueba del teléfono.

## Vista en vivo separada de la inferencia

El perfil del S10+ activa async_inference: true. Solo para cámara con capture_latest:
un trabajador procesa YOLO/ByteTrack de forma secuencial mientras el hilo de ventana
atiende la captura más reciente y los controles. Existe un único cuadro pendiente que se
sustituye por el más reciente, sin cola acumulativa. Al terminar una inferencia el
trabajador toma ese cuadro directamente, sin esperar otro ciclo del visor.

Los resultados se consumen una sola vez para contar. Los recuadros pueden corresponder a
una captura ligeramente anterior al fondo en vivo; se ocultan si su captura supera 180 ms,
aunque el resultado siga siendo válido para procesar su trayectoria. Un aumento de FPS del
visor no significa más inferencias ni demuestra precisión de conteo. Se conservan modelo,
resolución de inferencia, umbrales, zonas y contratos. La indicación IA muestra el tiempo de
una inferencia; la edad de cuadro sigue siendo desde su recepción en PC, no latencia óptica.

La espera de captura usa poll de 15 ms para atender botones incluso si el teléfono deja de
enviar temporalmente. La cámara y el visor se liberan antes de esperar al trabajador de IA
al cerrar o entrar al editor. Archivos de video conservan procesamiento secuencial.

Comparación controlada con 60 cuadros externos procesados en RAM, captura simulada a 30 FPS,
1280×720, modelo calentado y composición completa del visor, sin abrir ventana nativa ni
publicar MQTT: modo síncrono 4,33 s / 13,9 FPS de visor; separado 2,05 s / 30,0 FPS.
Pausa máxima entre presentaciones simuladas: 94 ms y 63 ms respectivamente. Esta comparación
no mide Windows HighGUI ni la latencia del enlace real del S10+. No se guardaron cuadros.
Pruebas nuevas verifican no acumular trabajos, metadatos correctos, errores, respuesta de
edición mientras IA está ocupada, actualización de video y un cruce contado una sola vez.
