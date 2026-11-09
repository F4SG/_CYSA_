# Patrones creacionales en CYSA

En Sprint 1, Prototype está disponible en el gestor del detector. Los otros patrones se estudian por separado. El piloto trabaja en modo sombra.

## Clonar y calibrar un perfil

Desde la raíz, usa el mismo Python que utilizas para iniciar el detector. La carpeta de destino debe existir y el nombre del archivo debe ser nuevo.

```powershell
python tools/cristhian/detector.py clonar-perfil --config deteccion/config/camara_usb.yaml --interseccion INT_02 --fuente "camara:Nombre USB" --salida deteccion/config/camara_int_02.yaml
python tools/cristhian/detector.py iniciar --config deteccion/config/camara_int_02.yaml --marcar zona
```

Usa el ID de la intersección registrado en el inventario. También puedes indicar un índice de cámara o un archivo de video con `--fuente`. El perfil queda pendiente de calibración. En el editor, guarda los carriles de la escena nueva antes de contar.

## Casos de estudio

| Patrón | Comportamiento del caso |
| --- | --- |
| Factory Method | `fuentes.py` crea fuentes de cámara y video que comparten el procesamiento. La operación común cierra el generador si falla el consumidor. |
| Builder | `escenario_sumo.py` valida una red con plan fijo, demanda de prueba y correspondencias. Prepara una carpeta nueva con red, rutas y configuración para SUMO. |
| Abstract Factory | `entorno.py` compone una fuente de prueba y un emulador en memoria. Ambos verifican la marca de prueba y la intersección. |
| Singleton | Las pruebas muestran cómo un contador por cámara aísla los conteos, incluso cuando dos cámaras asignan el mismo ID de seguimiento. |

Para preparar un escenario sin ejecutar SUMO:

```python
from casos_estudio.escenario_sumo import EscenarioSUMOBuilder

escenario = (
    EscenarioSUMOBuilder()
    .con_red_demo()
    .con_demanda("data/leonardo/ejemplos/flujos_DEMO.csv")
    .con_semilla(42)
    .con_salida("escenario_demo")
    .construir()
)
```

Las pruebas de estos casos están en `tests/test_patrones_creacionales.py` y se ejecutan con el resto de la suite de Sprint 1.
