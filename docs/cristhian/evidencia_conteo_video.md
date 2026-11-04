# Evidencia de conteo con video real (RF-03, Sprint 1)

Fecha: 03/11/2026. Responsable: Cristhian. Perfil: `deteccion/config/video_santa_cruz.yaml`.

## Qué se midió

- Video de una calle de Santa Cruz grabado desde la vereda, 928×1664, 30 FPS, 10:49 min, con algo de
  movimiento de cámara. El video no se versiona.
- Una línea sobre la **vía inferior** (vehículos que bajan hacia la cámara). La otra vía no se cuenta.
- Conteo manual del video completo hecho por una persona: 132 autos, 22 camiones, 33 motos y 7 micros
  (194 vehículos). En S1 los camiones se cuentan como `auto` (contrato de 3 clases), así que el manual
  comparable es auto 154, micro 7 y moto 33.
- Comparación con las herramientas del repositorio: `preparar_calibracion.py` y `calibrar.py`, con
  `--inicio-video` para que los intervalos sigan el reloj del video.

## Resultado

| Clase | Manual | Detector | Error | Resultado |
| --- | --- | --- | --- | --- |
| auto (incluye camiones) | 154 | 154 | 0,0 % | CUMPLE |
| moto | 33 | 32 | 3,0 % | CUMPLE |
| micro | 7 | 11 | 57,1 % | NO CUMPLE (se mide en S1; clasificación en S2) |
| **Total** | **194** | **197** | **+1,5 %** | **CUMPLE (≤10 %)** |

Equipo de prueba: laptop con RTX 3070 Ti, YOLO26s a 960 px, Ultralytics 8.4.63.

## Cómo se llegó al perfil

Cada paso se probó con el mismo video y la misma línea; los números son del video completo.

| Paso | Total | Motos | Qué mostró |
| --- | --- | --- | --- |
| YOLO26n 640, línea larga | 200 | 1 | El total parecía bien solo porque faltaban motos y camiones |
| YOLO26s 640 / 960 / 1088 / 1280 | 227–237 | 27–38 | 960 px fue el mejor tamaño para motos; los autos sobraban en todos |
| + camiones (COCO 7) y trayectorias guardadas | 257 | 34 | Los ~56 autos de más cruzaban el **extremo derecho** de la línea, otro flujo (sobre todo min 6–10, cuando la cámara se movió) |
| Línea acortada al tramo de la vía inferior | 189 | 26 | Total −2,6 %; acortar entre 65 % y 80 % da lo mismo, no es un ajuste fino |
| `iou: 0.7` | 192 | 28 | Con 0,5 el NMS descartaba motos superpuestas con autos |
| + reenlace (1 s / 0,25) | **197** | **32** | Motos tapadas por un auto justo en la línea y retomadas con otro ID |

Se probaron y **descartaron**: YOLOv8s Open Images V7 (119 en total, 0 motos), YOLOE con clases de
texto (separa camiones, pero confunde autos con "van"), YOLO26m 640 (no mejoró a 26s 960), NMS por
clase (sin mejora) y filtros contra conteo doble (no cambiaron el resultado: el exceso no era doble conteo).

## Cambios de código

- `counter.py`: reenlace opcional (`conteo_reenlace_s`, `conteo_reenlace_distancia`). Si un ID
  desaparece del lado de origen y en ese tiempo aparece otro de la misma clase pasada la línea, a esa
  distancia o menos, se cuenta ese cruce una vez. Apagado por defecto. Pruebas: `test_conteo_doble.py`.
- `preparar_calibracion.py`: cada intervalo de 30 s pertenece a la ventana manual donde cae su punto
  medio (los intervalos duran 30 s más un cuadro y antes se rechazaban bloques de 5 min).
- `run.py`: `ritmo_real` reproduce un archivo a sus FPS para demostrar el conteo en vivo en el panel.
- `detector.py iniciar --marcar`: abre el editor de carriles sobre la fuente antes de contar.

## Limitaciones

- **Un solo video**, y la línea y el reenlace se ajustaron con ese mismo video. Falta repetir la
  medición con otro video o en campo, con su conteo manual, para declarar RF-03 cumplido.
- Cámara a la altura de la vereda: las oclusiones son mayores que con la cámara en el poste.
  Unas pocas motos quedan tapadas por completo y no se detectan en ningún cuadro.
- **Micro** sigue sobrecontando (camiones grandes como bus). Se resuelve en S2 con reentrenamiento
  local (auto, micro, moto, camión, emergencia).
- 960 px necesita GPU (PC con GPU o Jetson). En CPU usar el perfil del celular (512 px).
