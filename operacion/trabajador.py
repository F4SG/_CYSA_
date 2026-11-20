"""Conteos y estados MQTT → SQL Server; outbox SQL Server → MQTT autenticado."""
import logging,time
from queue import Queue,Empty
from cysa.mqtt import client
from cysa.contracts import decode_message
from .despacho import iniciar
log=logging.getLogger('cysa.operacion')
def ejecutar(store,stop):
    import os
    c=client('cysa-control-'+os.environ.get('CYSA_SQL_DATABASE','CYSA_Control_S2'),manual_ack=True,persistent=True);despacho=None
    queue=Queue(maxsize=1000)
    import threading
    store.mqtt_ready=threading.Event()
    def connected(c,u,f,reason,properties):
        if not reason.is_failure:
            c.subscribe([('corredor/+/+/conteos',1),('corredor/+/estado',1),('corredor/DEMO_INT_01/confirmacion',1)])
            store.mqtt_ready.set()
    def message(c,u,msg):
        if len(msg.payload)>32768:
            if msg.qos:c.ack(msg.mid,msg.qos)
            return
        try:queue.put_nowait(msg)
        except __import__('queue').Full:log.warning('Cola llena; mensaje queda sin confirmar en el broker')
    def procesar(msg):
        try:
            if msg.topic=='corredor/DEMO_INT_01/confirmacion':despacho[1](msg.payload)
            else:store.save(decode_message(msg.topic,msg.payload))
        except (ValueError,KeyError,TypeError):log.warning('Contrato o firma no válidos; mensaje descartado')
        if msg.qos:c.ack(msg.mid,msg.qos)
    c.on_connect=connected;c.on_message=message
    c.on_disconnect=lambda *args:store.mqtt_ready.clear()
    try:
        despacho=iniciar(c,store)
        c.connect_async(__import__('os').environ.get('MQTT_HOST','localhost'),int(__import__('os').environ.get('MQTT_PORT','8883')),60)
        c.loop_start()
        pending=None
        while not stop.is_set():
            if pending is None:
                try:pending=queue.get(timeout=1)
                except Empty:continue
            try:procesar(pending);pending=None
            except Exception:
                log.warning('SQL no disponible; se conserva el mensaje sin confirmar y se reintenta')
                stop.wait(1)
    except Exception:log.exception('Trabajador SQL/MQTT detenido; no se despachan planes')
    finally:
        if despacho:despacho[0].set()
        c.disconnect();c.loop_stop()
