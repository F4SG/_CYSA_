# Prueba completa del controlador con la placa

Guía para probar el banco base del Sprint 2 en Windows: placa MMU, controlador, modo local
seguro (RF-06) y comunicación con Docker y el panel. Tiempo aproximado: 30 minutos.
El envío de planes Webster, SQL Server y la emergencia simulada en SUMO se prueban con [INTEGRACION.md](INTEGRACION.md).

## 0. Antes de empezar

Necesitas:

- La copia del proyecto que ya tienes instalada con Docker (la de la sección 2 del README), en `main`.
- La placa Arduino (Uno o Nano), un cable USB de datos, 6 LEDs (2 rojos, 2 ámbar, 2 verdes) y 6
  resistencias de 220 Ω.
- Arduino IDE.

En PowerShell, desde la raíz del proyecto:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
$py = (Resolve-Path .\.venv\Scripts\python.exe).Path
& $py -m pip install -r controlador/requirements.txt
```

Si Docker ya estaba instalado, recarga el broker y el consumidor para que tomen la ACL y el latido nuevos:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up -d
docker compose --env-file infra/.env -f infra/compose.yaml restart mosquitto
docker compose --env-file infra/.env -f infra/compose.yaml up -d --build consumer
```

## 1. Armar y programar la placa

| Grupo | Rojo | Ámbar | Verde |
| --- | --- | --- | --- |
| NS | D2 | D3 | D4 |
| EO | D5 | D6 | D7 |

Cada LED: pin → resistencia de 220 Ω → pata larga del LED; pata corta → GND.

1. Abrir `controlador/arduino/mmu_cysa/mmu_cysa.ino` en Arduino IDE.
2. Elegir la placa (Herramientas → Placa) y el puerto (Herramientas → Puerto). Anotar el puerto, por ejemplo `COM3`.
3. Pulsar **Subir**.
4. Abrir el Monitor Serie a **115200 baudios**. Debe aparecer `LISTO:2` y los dos rojos encendidos.
5. **Cerrar el Monitor Serie.** Si queda abierto, el controlador no puede usar el puerto.

## 2. Prueba A: la placa sola (2 minutos)

```powershell
.\iniciar_controlador.ps1 -ProbarPlaca -Puerto COM3
```

El programa enciende un ciclo seguro (mirar que los LEDs coincidan con lo que muestra la consola) y luego
provoca tres fallas a propósito. En cada una, todos los rojos deben parpadear y la placa se reinicia sola.

**Resultado esperado:** 8 líneas `OK` y `Resultado: TODO CORRECTO`.

Si un LED no coincide con la consola, revisa el cableado. Si `La placa responde LISTO` falla, revisa el
puerto y que el Monitor Serie esté cerrado.

## 3. Prueba B: modo local seguro sin Docker (4 minutos)

```powershell
.\iniciar_controlador.ps1 -Puerto COM3 -SimularCorte 30:120
```

El centro simulado late hasta los 30 s, se corta y vuelve a los 120 s. La consola y los LEDs deben seguir
esta línea de tiempo (±1 s):

| Tiempo | Consola | LEDs |
| --- | --- | --- |
| 0 s | `CENTRO | plan LOCAL_SEGURO` (pasa a DEMO_FIJO al terminar el todo rojo) | NS verde |
| 25–31 s | ámbar NS, todo rojo y luego `plan DEMO_FIJO` | NS ámbar, todo rojo, NS verde |
| 66 s | `F2_EO_VERDE` | EO verde |
| **≈85 s** | **`LOCAL_SEGURO`** (último latido a los 25 s + 60 s) | sin cambio: termina la fase en curso |
| 96–101 s | ámbar EO, todo rojo y luego `plan LOCAL_SEGURO` | EO ámbar, todo rojo, NS verde |
| **120 s** | **`CENTRO`** | sin cambio hasta el próximo todo rojo |
| ≈132 s | `plan DEMO_FIJO` | NS verde |

Ctrl+C para terminar. Al segundo, todos los rojos parpadean: la placa detectó que la PC dejó de enviar.

## 4. Prueba C: sistema completo con Docker y el panel (10 minutos)

1. Con Docker en marcha, abre el panel en http://localhost:8088, ingresa y abre **Comunicación**.
2. Inicia el controlador con el broker:

   ```powershell
   .\iniciar_controlador.ps1 -Puerto COM3 -Mqtt
   ```

   En unos 5 s la consola pasa a `CENTRO`. En el panel aparece **DEMO_INT_01** con la fase actual,
   `plan_activo` y `conectado`; se actualiza al cambiar de fase y cada 10 s (activar **En vivo**).
3. **Corte del centro (RF-06).** En otra PowerShell:

   ```powershell
   docker compose --env-file infra/.env -f infra/compose.yaml stop consumer
   ```

   A los 60 s la consola muestra `LOCAL_SEGURO` y, tras el próximo todo rojo, los LEDs siguen el plan local.
   El panel marca la intersección **Sin actualización**, porque el consumidor que guarda los estados está detenido.
4. **Vuelta del centro.**

   ```powershell
   docker compose --env-file infra/.env -f infra/compose.yaml start consumer
   ```

   En unos 5 s la consola vuelve a `CENTRO` y el panel muestra `conectado` otra vez.
5. Opcional: en otra PowerShell ejecuta `.\iniciar_conteo.ps1` para tener conteo y controlador a la vez
   (Flujo vehicular y Comunicación con datos en vivo).

## 5. Prueba D: seguridad en vivo (2 minutos)

Con el controlador en marcha (`-Mqtt` o `-SimularCorte`):

1. **Desconectar el cable USB.** La consola muestra `INTERMITENTE | FALLA:SIN_ENLACE` y, en 1 s, la placa
   pone todos los rojos en intermitente. Ctrl+C, conectar el cable e iniciar otra vez.
2. **Detener con Ctrl+C.** La placa pasa a rojo intermitente en 1 s.

En ambos casos la placa no vuelve a obedecer hasta reiniciarse: al iniciar el controlador se reinicia sola.

## 6. Pruebas automáticas

```powershell
& $py tools/franco/probar.py
```

Resultado esperado: todas las pruebas aprobadas (279 en esta versión).

## Evidencias para el informe del sprint

- Captura de la prueba A con `TODO CORRECTO`.
- Video corto de la prueba B entre los 80 y 105 s (paso a local seguro y cambio en el todo rojo).
- Capturas del panel en **Comunicación**: `conectado`, `Sin actualización` durante el corte y `conectado` al volver.
- Foto de la placa en rojo intermitente (prueba D).
- Resultado de `probar.py`.

## Problemas frecuentes

| Problema | Solución |
| --- | --- |
| `No se pudo abrir COM3` / `Acceso denegado` | Cerrar el Monitor Serie de Arduino u otro programa que use el puerto |
| `La placa tiene 4 grupos y la configuración 2` | El `.ino` y el YAML no coinciden: ajustar `N_GRUPOS` y los pines |
| La consola nunca pasa a `CENTRO` con `-Mqtt` | Revisar que Docker esté en marcha y que se hayan recargado `mosquitto` y `consumer` (paso 0) |
| `No existe infra/runtime/clientes/emulador.env` | La instalación no generó las credenciales: seguir la sección 2 del README |
| La placa parpadea apenas arranca el controlador | Ver el motivo en la consola (`FALLA:...`). Con el cableado correcto, una falla indica un error del controlador: informar el motivo |
