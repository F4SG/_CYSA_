"""Solo planes firmados, vigentes y validados; aplicación al terminar todo rojo."""
import json,time
from pathlib import Path
from operacion.mensajes import verificar,firmar
from operacion.planes import validar

class ReceptorPlanes:
    def __init__(self,ctrl,key,recibos,publicar,reloj=time.monotonic,utc=time.time):
        self.ctrl,self.key,self.path,self.publicar=ctrl,key,Path(recibos),publicar
        self.reloj,self.utc=reloj,utc;self.pendiente=None;self.activo_desde=None
        self.esperando_centro=None
        self.recibos=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
    def _guardar(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.recibos),encoding='utf-8');tmp.replace(self.path)
    def _respuesta(self,d,estado,detalle):
        result=dict(tipo='confirmacion',solicitud_id=d['solicitud_id'],huella_plan=d['huella_plan'],
                    estado=estado,detalle=detalle,vence=self.utc()+60)
        self.recibos[d['solicitud_id']]=result;self._guardar()
        self.publicar(firmar(result,self.key))
    def recibir(self,raw):
        d=verificar(raw,self.key,self.utc())
        if d['tipo']!='plan':raise ValueError('Mensaje no es un plan')
        if d['solicitud_id'] in self.recibos:
            old=dict(self.recibos[d['solicitud_id']]);old['vence']=self.utc()+60
            if old['huella_plan']!=d['huella_plan']:raise ValueError('SolicitudId usado con otro plan')
            self.publicar(firmar(old,self.key));return
        if self.pendiente:
            if self.pendiente['solicitud_id']==d['solicitud_id']:return
            self._respuesta(d,'rechazado','Hay un cambio autorizado pendiente de aplicar');return
        if self.ctrl.intermitente:
            self._respuesta(d,'rechazado','Controlador con falla del MMU');return
        if not self.ctrl.modo.conectado:
            if self.esperando_centro and self.esperando_centro['solicitud_id']!=d['solicitud_id']:
                self._respuesta(d,'rechazado','Hay una orden esperando la señal del centro');return
            self.esperando_centro=d;return
        sec=self.ctrl.secuenciador
        cruce,plan=validar(d['plan'])
        if cruce.grupos!=self.ctrl.cruce.grupos:raise ValueError('Grupos incompatibles con la placa')
        if self.utc()+sec.hasta_cambio(self.reloj())+.5>=d['vence']:
            self._respuesta(d,'rechazado','No cabe en el plazo una transición segura');return
        sec.solicitar(plan)
        self.pendiente=d;self.activo_desde=None
    def tick(self):
        if self.esperando_centro:
            d=self.esperando_centro
            if self.ctrl.intermitente or self.utc()>=d['vence']:
                self.esperando_centro=None;self._respuesta(d,'rechazado','Falta de centro o falla antes del vencimiento')
            elif self.ctrl.modo.conectado:
                self.esperando_centro=None;self.recibir(firmar(d,self.key))
        if not self.pendiente:return
        d=self.pendiente
        if self.ctrl.intermitente or not self.ctrl.modo.conectado or self.utc()>=d['vence']:
            queued=self.ctrl.secuenciador.pendiente
            if queued and queued.plan_id==d['plan']['plan_id']:
                self.ctrl.secuenciador.solicitar(self.ctrl.plan_centro if self.ctrl.modo.conectado else self.ctrl.plan_local)
            self._respuesta(d,'rechazado','Falla, pérdida del centro o plazo vencido antes de confirmar aplicación')
            self.pendiente=None;return
        if self.ctrl.plan_id==d['plan']['plan_id']:
            if self.activo_desde is None:self.activo_desde=self.reloj()
            if self.reloj()-self.activo_desde>=.4:
                self.ctrl.plan_centro=self.ctrl.secuenciador.plan
                self._respuesta(d,'aplicado','Plan seleccionado tras todo rojo y sin falla MMU reportada')
                self.pendiente=None
