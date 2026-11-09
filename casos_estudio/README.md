# Patrones creacionales en CYSA

Los patrones se usan desde el detector, la herramienta de simulación y el comando de entornos. El piloto trabaja en modo sombra.

## Clonar y calibrar un perfil

Desde la raíz, usa el mismo Python que utilizas para iniciar el detector. La carpeta de destino debe existir y el nombre del archivo debe ser nuevo.

```powershell
python tools/cristhian/detector.py clonar-perfil --config deteccion/config/camara_usb.yaml --interseccion INT_02 --fuente "camara:Nombre USB" --salida deteccion/config/camara_int_02.yaml
python tools/cristhian/detector.py iniciar --config deteccion/config/camara_int_02.yaml --marcar zona
```

Usa el ID de la intersección registrado en el inventario. También puedes indicar un índice de cámara o un archivo de video con `--fuente`. El perfil queda pendiente de calibración. En el editor, guarda los carriles de la escena nueva antes de contar.

## Ejecutar el detector y preparar SUMO

El comando habitual del detector selecciona el creador de cámara o video según el YAML. Ambos usan el mismo procesamiento y cierran los recursos si falla la publicación. El Singleton permite una sesión por proceso. Cada sesión crea su cámara, modelo y contador.

El comando habitual de SUMO prepara y valida el escenario antes de ejecutar la simulación. Para preparar solo los archivos, agrega `--prepare-only`.

```powershell
python simulacion/sumo_base.py --demo --counts data/leonardo/ejemplos/flujos_DEMO.csv --seed 42 --out resultados/escenario_preparado --prepare-only
```

Usa `--network` y `--access-map` en lugar de `--demo` para suministrar una red con plan fijo y su mapa de accesos. El resultado preparado contiene red, rutas y configuración. Ejecuta SUMO por separado con el archivo `base.sumocfg` y la semilla indicada.

## Ejecutar un entorno

Desde la raíz, usa el Python del detector y configura las rutas de importación.

```powershell
$env:PYTHONPATH = "$PWD/shared;$PWD/deteccion"
python -m cysa_detector.entorno laboratorio --conteo data/franco/ejemplos/conteo_DEMO.json --plan data/franco/ejemplos/plan_borrador_DEMO.json --salida laboratorio.jsonl
python -m cysa_detector.entorno sombra --config perfil_calibrado.yaml --estado estado_observado.json --salida sombra.jsonl
```

Laboratorio reproduce mensajes `Conteo` marcados como prueba. El plan opcional cambia el estado del emulador en memoria. Sombra usa el detector del perfil y lee una instantánea del mensaje `Estado` de la misma intersección, con la misma marca de prueba. En sombra el controlador bloquea el envío de planes. Ambos comandos generan JSONL local con el estado y los conteos.

Las pruebas de integración de los patrones están en `tests/test_patrones_creacionales.py` y se ejecutan con la suite de CYSA.
