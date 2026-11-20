"""Monitor de conflictos (MMU).

MMUSerial habla con la placa Arduino (controlador/arduino/mmu_cysa). MMUSimulada
aplica las mismas reglas en Python para probar sin la placa.

Protocolo por USB-serial, 115200 baudios, una línea por mensaje:
  PC -> placa   L:<luces>   una letra por grupo (G verde, Y ámbar, R rojo), p. ej. L:GR
  placa -> PC   LISTO:<n>   al encender, con el número de grupos
                FALLA:<motivo>  CONFLICTO, SIN_AMBAR, AMBAR_CORTO, AMBAR_A_VERDE, FORMATO o SIN_SENAL
La PC agrega FALLA:SIN_ENLACE si se pierde el puerto (cable desconectado).
Ante una falla la placa pone todo en rojo intermitente y no vuelve a obedecer hasta reiniciarla.
"""
import time

TOLERANCIA_AMBAR_S = 0.2     # margen por el retardo del enlace serial
WATCHDOG_S = 1.0             # sin mensajes de la PC por más de 1 s -> falla
INTERVALO_ENVIO_S = 0.2      # la PC repite las luces cada 0,2 s aunque no cambien


class ReglasMMU:
    """Reglas comunes a la placa y al simulador."""
    def __init__(self, cruce):
        self.cruce = cruce
        self.actual = ('R',) * len(cruce.grupos)
        self.desde_ambar = [None] * len(cruce.grupos)
        self.ultimo = None
        self.falla = None

    def recibir(self, luces, ahora):
        if self.falla:
            return self.falla
        if len(luces) != len(self.actual) or any(l not in 'GYR' for l in luces):
            return self._fallar('FORMATO')
        if self.cruce.en_conflicto(luces):
            return self._fallar('CONFLICTO')
        for g, (antes, despues) in enumerate(zip(self.actual, luces)):
            if antes == 'G' and despues == 'R':
                return self._fallar('SIN_AMBAR')
            if antes == 'Y' and despues == 'G':
                return self._fallar('AMBAR_A_VERDE')
            if antes == 'Y' and despues == 'R' and ahora - self.desde_ambar[g] < self.cruce.ambar_min_s - TOLERANCIA_AMBAR_S:
                return self._fallar('AMBAR_CORTO')
        for g, (antes, despues) in enumerate(zip(self.actual, luces)):
            if despues == 'Y' and antes != 'Y':
                self.desde_ambar[g] = ahora
        self.actual = tuple(luces)
        self.ultimo = ahora
        return None

    def vigilar(self, ahora):
        if not self.falla and self.ultimo is not None and ahora - self.ultimo > WATCHDOG_S:
            return self._fallar('SIN_SENAL')
        return None

    def _fallar(self, motivo):
        self.falla = f'FALLA:{motivo}'
        return self.falla


class MMUSimulada:
    """Misma conducta que la placa, sin hardware."""
    def __init__(self, cruce):
        self.reglas = ReglasMMU(cruce)
        self._salida = [f'LISTO:{len(cruce.grupos)}']

    def enviar(self, luces, ahora):
        respuesta = self.reglas.recibir(tuple(luces), ahora)
        if respuesta:
            self._salida.append(respuesta)

    def mensajes(self, ahora):
        falla = self.reglas.vigilar(ahora)
        if falla:
            self._salida.append(falla)
        salida, self._salida = self._salida, []
        return salida

    def cerrar(self):
        pass


class MMUSerial:
    """Placa Arduino conectada por USB."""
    def __init__(self, puerto, cruce, espera_s=6.0, serial_factory=None):
        if serial_factory is None:
            import serial
            serial_factory = serial.Serial
        self.n = len(cruce.grupos)
        self.puerto = serial_factory(puerto, 115200, timeout=0)
        self._buffer = ''
        self._pendientes = []
        # Abrir el puerto reinicia la placa (Uno/Nano): esperar su LISTO.
        limite = time.monotonic() + espera_s
        while time.monotonic() < limite:
            lineas = self._leer()
            for i, linea in enumerate(lineas):
                if linea.startswith('LISTO:'):
                    if int(linea.split(':', 1)[1]) != self.n:
                        raise RuntimeError(f'La placa tiene {linea.split(":", 1)[1]} grupos y la configuración {self.n}')
                    self._pendientes = lineas[i + 1:]     # no perder mensajes que llegaron juntos
                    return
            time.sleep(0.05)
        raise TimeoutError(f'La placa en {puerto} no respondió LISTO. Revisar el puerto y el programa cargado.')

    def _leer(self):
        datos = self.puerto.read(256)
        if datos is None:
            datos = b''
        if datos:
            self._buffer += datos.decode('ascii', errors='replace')
        *lineas, self._buffer = self._buffer.split('\n')
        return [l.strip() for l in lineas if l.strip()]

    def enviar(self, luces, ahora):
        try:
            self.puerto.write(f'L:{"".join(luces)}\n'.encode('ascii'))
        except OSError:                       # SerialException hereda de OSError
            self._pendientes.append('FALLA:SIN_ENLACE')

    def mensajes(self, ahora):
        try:
            nuevos = self._leer()
        except OSError:                       # cable desconectado: la placa se apaga sola en 1 s
            nuevos = ['FALLA:SIN_ENLACE']
        salida, self._pendientes = self._pendientes + nuevos, []
        return salida

    def cerrar(self):
        self.puerto.close()
