"""Proceso separado de FastAPI: un suscriptor, confirmación después de persistir."""
import logging,os,threading,time
from datetime import datetime,timezone
from cysa.mqtt import client
from cysa.contracts import decode_message,Latido,TOPICO_LATIDO
from app.repository import Repository
log=logging.getLogger('cysa.consumer')
def iniciar_latido(c,intervalo_s=5.0,detener=None):
    """Publica el latido del centro de control. Si deja de llegar por más de 60 s, cada
    controlador pasa a su plan local seguro (RF-06)."""
    detener=detener or threading.Event()
    def latir():
        while not detener.wait(intervalo_s):
            if c.is_connected():
                c.publish(TOPICO_LATIDO,Latido(timestamp=datetime.now(timezone.utc)).model_dump_json(),qos=1)
    hilo=threading.Thread(target=latir,name='cysa-latido',daemon=True);hilo.start()
    return detener
def main():
    logging.basicConfig(level=logging.INFO)
    repo=Repository();repo.ready()
    c=client('cysa-plataforma',manual_ack=True)
    def connected(client,userdata,flags,reason,properties):
        if reason.is_failure:log.error('MQTT rechazó autenticación');return
        client.subscribe([('corredor/+/+/conteos',1),('corredor/+/estado',1)])
    def message(client,userdata,msg):
        try:event=decode_message(msg.topic,msg.payload)
        except ValueError:
            log.warning('Mensaje descartado: contrato o tópico inválido')
            if msg.qos:client.ack(msg.mid,msg.qos)
            return
        # No confirmar hasta escribir. El reintento mantiene el mismo evento, sin perderlo en reconexión.
        delay=1
        while True:
            try:repo.save(event);break
            except Exception:
                log.error('Persistencia no disponible; se reintenta sin registrar el payload')
                time.sleep(delay);delay=min(30,delay*2)
        if msg.qos:client.ack(msg.mid,msg.qos)
    c.on_connect=connected;c.on_message=message
    iniciar_latido(c,float(os.environ.get('LATIDO_S','5')))
    c.connect(os.environ.get('MQTT_HOST','mosquitto'),int(os.environ.get('MQTT_PORT','8883')),60)
    try:c.loop_forever(retry_first_connection=True)
    finally:c.disconnect()
if __name__=='__main__':main()
