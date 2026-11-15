"""Enlace con el centro de control por MQTT (TLS y usuario del broker).

Recibe los latidos del centro y publica el Estado del controlador. Nunca bloquea
el ciclo de control: paho trabaja en su propio hilo y la publicación no espera PUBACK.
"""
import os
import threading
import time

from cysa.contracts import Latido, TOPICO_LATIDO

INTERVALO_LATIDO_S = 5.0


class CentroMQTT:
    def __init__(self, client_id='cysa-controlador'):
        from cysa.mqtt import client
        self._ultimo = None
        self._lock = threading.Lock()
        self.conectado = threading.Event()
        self.c = client(client_id)

        def conectar(c, u, f, reason, properties):
            if reason.is_failure:
                return
            self.conectado.set()
            c.subscribe(TOPICO_LATIDO, qos=1)

        def mensaje(c, u, msg):
            try:
                Latido.model_validate_json(msg.payload)
            except ValueError:
                return                      # latido inválido: no cuenta como comunicación
            with self._lock:
                self._ultimo = time.monotonic()

        self.c.on_connect = conectar
        self.c.on_disconnect = lambda *args: self.conectado.clear()
        self.c.on_message = mensaje
        self.c.connect_async(os.environ.get('MQTT_HOST', 'localhost'), int(os.environ.get('MQTT_PORT', '8883')), 60)
        self.c.loop_start()

    def ultimo_latido(self, ahora=None):
        with self._lock:
            return self._ultimo

    def publicar_estado(self, estado):
        if self.conectado.is_set():
            self.c.publish(f'corredor/{estado.interseccion}/estado', estado.model_dump_json(), qos=1)

    def cerrar(self):
        self.c.loop_stop()
        self.c.disconnect()


class CentroSimulado:
    """Centro de prueba sin broker. corte=(inicio_s, fin_s) simula una caída de la comunicación;
    fin_s=None significa que no vuelve. Sin corte, el centro late siempre."""
    def __init__(self, inicio, corte=None, intervalo_s=INTERVALO_LATIDO_S):
        self.inicio, self.corte, self.intervalo = inicio, corte, intervalo_s
        self._ultimo = None

    def _activo(self, t):
        if self.corte is None:
            return True
        desde, hasta = self.corte
        return t < desde or (hasta is not None and t >= hasta)

    def ultimo_latido(self, ahora=None):
        ahora = time.monotonic() if ahora is None else ahora
        t = ahora - self.inicio
        if self._activo(t) and (self._ultimo is None or ahora - self._ultimo >= self.intervalo):
            self._ultimo = ahora
        return self._ultimo

    def publicar_estado(self, estado):
        pass

    def cerrar(self):
        pass


class SinCentro:
    """Sin enlace: el controlador queda en su plan local seguro."""
    def ultimo_latido(self, ahora=None):
        return None

    def publicar_estado(self, estado):
        pass

    def cerrar(self):
        pass
