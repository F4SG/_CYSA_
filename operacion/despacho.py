"""Outbox: un PUBACK no acredita ejecución; solo el recibo firmado del controlador."""
import logging,os,threading,time
from .almacen import Almacen
from .mensajes import clave,firmar,verificar
log=logging.getLogger('cysa.control')

def iniciar(c,repo):
    store=Almacen();store.ready()
    key=clave(os.environ['CYSA_PLAN_KEY_FILE']);stop=threading.Event()
    def loop():
        while not stop.wait(2):
            if not c.is_connected():continue
            try:
                for row in store.pendientes():
                    d=row['payload']
                    if time.time()>=d['vence']:
                        store.envio(row['solicitud_id'],'caducado','No hubo ejecución confirmada dentro del plazo');continue
                    info=c.publish('corredor/DEMO_INT_01/plan',firmar(d,key),qos=1,retain=False)
                    info.wait_for_publish(timeout=5)
                    if info.is_published():store.envio(row['solicitud_id'],'enviado')
            except Exception:log.warning('Despacho no disponible; el outbox conserva la solicitud para reintentar')
    threading.Thread(target=loop,name='cysa-despacho',daemon=True).start()
    def confirmar(raw):
        d=verificar(raw,key)
        if d['tipo']!='confirmacion':raise ValueError('Se esperaba confirmación')
        store.confirmar(d)
    return stop,confirmar
