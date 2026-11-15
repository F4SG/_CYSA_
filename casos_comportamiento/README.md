# Patrones de comportamiento

Proyecto Gestión Inteligente de Semáforos — Sistema IoT de Gestión Semafórica Adaptativa (equipo CYSA).

| Patrón | Dónde | Estado |
| --- | --- | --- |
| Strategy | `deteccion/cysa_detector/asignacion.py`, usado por `CameraSource._loop` | Integrado en el detector |
| State | `casos_comportamiento/state.py` | Prueba de concepto para el controlador emulado del Sprint 2 (RF-06, RF-08, RF-09) |
| Command | `casos_comportamiento/command.py` | Prueba de concepto para RF-02 (trazabilidad) y RF-16 (reversión) |
| Template Method | `CreadorDetector.ejecutar()` en `run.py` | Ya existía |
| Iterator | `FuenteDeteccion.eventos()` | Ya existía |
| Observer | Publicación y suscripción MQTT (`shared/cysa/mqtt.py`, `backend/app/consumer.py`) | Ya existía |

Chain of Responsibility, Mediator y Memento no se aplican: las validaciones son funciones y contratos
Pydantic, la coordinación ya la hacen `FachadaConteo` y el broker, y Command guarda el valor anterior de cada cambio.

## Strategy en el detector

La forma de asignar un vehículo a un carril se elige una vez al iniciar (o al recalibrar):

- `AsignacionPorZonas`: el carril es la zona dibujada que contiene al vehículo; fuera de las zonas no cuenta.
- `AsignacionPorLineas`: sin zonas, cada línea decide su propio cruce.
- `AsignacionAutomatica`: usa los carriles aprendidos por `AutoLanes`.

`_loop` solo llama a `asignador.asignar(track_id, punto)`, sin condiciones por modo.

## State y Command

Son pruebas de concepto que no se conectan todavía al sistema. Supuestos de State: ámbar 3 s y todo
rojo 2 s, como el plan DEMO; en modo local seguro no se atienden prioridades. Se integran cuando se
implementen el controlador emulado y la trazabilidad.

Las pruebas están en `tests/test_patrones_comportamiento.py` y se ejecutan con la suite de CYSA.
