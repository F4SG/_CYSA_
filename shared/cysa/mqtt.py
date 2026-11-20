import os, ssl, threading
import paho.mqtt.client as mqtt

def client(client_id, *, manual_ack=False,persistent=False):
    c=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, manual_ack=manual_ack,clean_session=not persistent)
    context=ssl.create_default_context(cafile=os.environ['MQTT_CA'])
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    c.tls_set_context(context)
    c.username_pw_set(os.environ['MQTT_USER'],os.environ['MQTT_PASSWORD'])
    c.reconnect_delay_set(min_delay=1,max_delay=30)
    c.max_queued_messages_set(1000)
    return c
class Publisher:
    def __init__(self, client_id):
        self.client=client(client_id);self.connected=threading.Event()
        def connected(c,u,f,reason,properties):
            if not reason.is_failure:self.connected.set()
        self.client.on_connect=connected
        self.client.on_disconnect=lambda *args:self.connected.clear()
    def __enter__(self):
        self.client.connect(os.environ.get('MQTT_HOST','localhost'),int(os.environ.get('MQTT_PORT','8883')),60)
        self.client.loop_start()
        if not self.connected.wait(15):
            self.client.loop_stop();self.client.disconnect()
            raise ConnectionError('Broker no aceptó conexión TLS/autenticación')
        return self
    def publish(self,event):
        from .contracts import Conteo
        topic=(f'corredor/{event.interseccion}/{event.acceso}/conteos' if isinstance(event,Conteo)
               else f'corredor/{event.interseccion}/estado')
        info=self.client.publish(topic,event.model_dump_json(),qos=1,retain=False)
        if info.rc!=mqtt.MQTT_ERR_SUCCESS:raise ConnectionError('No se pudo encolar publicación')
        info.wait_for_publish(timeout=10)
        if not info.is_published():raise TimeoutError('No llegó PUBACK')
    def __exit__(self,*args):
        self.client.disconnect();self.client.loop_stop()
