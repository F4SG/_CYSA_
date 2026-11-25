# Controlador semafórico emulado (Sprint 2)

Banco de pruebas del Sistema IoT de Gestión Semafórica Adaptativa. Reemplaza al controlador ATC + MMU del
laboratorio:

- **La PC** corre el controlador (`cysa_controlador`): recorre las fases del plan, cambia de modo y publica
  su `Estado` por MQTT.
- **La placa Arduino** (`arduino/mmu_cysa`) enciende los LEDs y actúa como **monitor de conflictos (MMU)**:
  si recibe una combinación insegura, o deja de recibir órdenes por más de 1 s, pone todo en **rojo
  intermitente** y no vuelve a obedecer hasta presionar RESET.

Incluye plan fijo, MMU y **modo local seguro (RF-06)**. Para calcular planes con conteos,
validar Webster en SUMO, autorizarlo con MFA y enviarlo al banco, sigue [INTEGRACION.md](INTEGRACION.md). Ese flujo guarda sus datos en
**SQL Server** y requiere iniciar también `iniciar_operacion.ps1`.

**Para probarlo todo con la placa, seguir [PRUEBA_COMPLETA.md](PRUEBA_COMPLETA.md).**

## Modos (patrón State)

| Modo | Cuándo | Plan |
| --- | --- | --- |
| `LOCAL_SEGURO` | Al arrancar, y si no llegan latidos del centro por más de 60 s (RF-06) | `plan_local` |
| `CENTRO` | Mientras llegan latidos del centro | `plan_centro` |
| `INTERMITENTE` | La placa informó una falla | Ninguno: rojo intermitente hasta reiniciar |

El cambio de plan nunca corta una fase: se aplica al terminar el próximo **todo rojo**.

## Reglas de seguridad

El controlador rechaza al cargar cualquier plan que rompa estas reglas, y la placa las vuelve a verificar
con cada mensaje:

- dos grupos en conflicto nunca tienen verde o ámbar a la vez;
- de verde se pasa siempre por ámbar (mínimo 3 s) antes de rojo, y de ámbar nunca a verde;
- todo plan tiene al menos una fase de todo rojo y respeta los mínimos de `tiempos_min`.

## Montaje de la placa

Valores por defecto (Uno, Nano o Mega); se cambian en la sección CONFIGURACIÓN de `mmu_cysa.ino`:

| Grupo | Rojo | Ámbar | Verde |
| --- | --- | --- | --- |
| NS (grupo 0) | D2 | D3 | D4 |
| EO (grupo 1) | D5 | D6 | D7 |

Cada LED va del pin a una resistencia de 220 Ω y luego a GND. El LED de la placa (D13) se enciende
cuando hay una falla. El orden de los grupos del `.ino` debe ser el mismo que `grupos` en el YAML.

**Cargar el programa:** abrir `arduino/mmu_cysa/mmu_cysa.ino` en Arduino IDE, elegir la placa y el puerto
y pulsar Subir. En el Monitor Serie (115200 baudios) debe aparecer `LISTO:2`; cerrar el monitor antes de
iniciar el controlador.

## Ejecutar

Desde la raíz del repositorio, en Windows: doble clic en `iniciar_controlador.bat`. Muestra los puertos
disponibles y pide el de la placa (Enter usa el MMU simulado). Otras formas:

```powershell
.\iniciar_controlador.ps1 -Puerto COM3                       # placa en COM3, centro simulado
.\iniciar_controlador.ps1 -Puerto COM3 -SimularCorte 30:120  # prueba de RF-06 sin broker
.\iniciar_controlador.ps1 -Puerto COM3 -Mqtt                 # con el stack Docker en marcha
.\iniciar_controlador.ps1 -SinPlaca                          # sin hardware
.\iniciar_controlador.ps1 -ProbarPlaca -Puerto COM3          # prueba automática de la placa
```

**Prueba de RF-06 sin broker** (`-SimularCorte 30:120`): el centro simulado deja de latir a los 30 s.
Alrededor de los 90 s el controlador pasa a `LOCAL_SEGURO` y, al volver los latidos a los 120 s, regresa a
`CENTRO`. Cada cambio de plan espera el todo rojo.

## Comunicación con el centro (MQTT)

| Tópico | Publica | Lee | Contenido |
| --- | --- | --- | --- |
| `centro/latido` | plataforma (consumidor, cada 5 s) | emulador | contrato `Latido` |
| `corredor/<intersección>/estado` | emulador (al cambiar de fase y cada 10 s) | plataforma | contrato `Estado` |

Con `-Mqtt`, el controlador usa el usuario `emulador` de `infra/runtime/clientes/emulador.env`, que ya genera
la instalación. Después de actualizar el repositorio hay que recargar el broker y el consumidor para que
tomen la ACL y el latido nuevos:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml restart mosquitto
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build consumer
```

El estado del controlador se ve en el panel, en **Comunicación**.

## Protocolo con la placa

USB-serial a 115200 baudios, una línea por mensaje:

- PC → placa: `L:<luces>`, una letra por grupo (`G` verde, `Y` ámbar, `R` rojo), cada 0,2 s. Ejemplo: `L:GR`.
- placa → PC: `LISTO:<n>` al encender; `FALLA:<motivo>` con `CONFLICTO`, `SIN_AMBAR`, `AMBAR_CORTO`,
  `AMBAR_A_VERDE`, `FORMATO` o `SIN_SENAL`. Si se pierde el puerto (cable desconectado), la PC registra
  `FALLA:SIN_ENLACE` y el controlador pasa a `INTERMITENTE`.

## Pruebas

`tests/controlador/test_controlador.py` cubre la validación de planes, el secuenciador, los modos, las reglas
del MMU, el enlace serial (con un puerto falso) y un ciclo completo de 400 s con corte de comunicación,
sin fallas del MMU. Se ejecutan con la suite de CYSA.
