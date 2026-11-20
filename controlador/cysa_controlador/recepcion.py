"""Solo planes firmados, vigentes y validados; aplicación al terminar todo rojo."""
import json,time
from pathlib import Path
from operacion.mensajes import verificar,firmar
from operacion.planes import validar

class ReceptorPlanes:
    def __init__(self,ctrl,key,recibos,publicar,reloj=time.monotonic,utc=time.time):
        self.ctrl,self.key,self.path,self.publicar=ctrl,key,Path(recibos),publicar
        self.reloj,self.utc=reloj,utc;self.pendiente=None;self.activo_desde=None;self.emergencia_hasta=0
        self.recibos=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
    def _guardar(self):
        self.path.parent.mkdir(parents=True,exist_ok=True);tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.recibos),encoding='utf-8');tmp.replace(self.path)
    def _respuesta(self,d,estado,detalle):
        result=dict(tipo='confirmacion',solicitud_id=d['solicitud_id'],huella_plan=d['huella_plan'],
                    estado=estado,detalle=detalle,vence=self.utc()+60)
        self.recibos[d['solicitud_id']]=result;self._guardar()
        self.publicar(firmar(result,self.key))
    def _espera(self):
        sec=self.ctrl.secuenciador;espera=max(0,sec.fase.duracion_s-(self.reloj()-sec.inicio))
        if sec.fase.todo_rojo:return espera
        for step in range(1,len(sec.plan.fases)+1):
            f=sec.plan.fases[(sec.indice+step)%len(sec.plan.fases)];espera+=f.duracion_s
            if f.todo_rojo:return espera
        raise ValueError('No existe transición segura')
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
        if self.ctrl.intermitente or not self.ctrl.modo.conectado:
            self._respuesta(d,'rechazado','Controlador sin centro o con falla del MMU');return
        if self.emergencia_hasta>self.reloj() and d['plan']['modo']!='emergencia':
            self._respuesta(d,'rechazado','Se está atendiendo una emergencia; micros y planes normales ceden');return
        cruce,plan=validar(d['plan'])
        if cruce.grupos!=self.ctrl.cruce.grupos:raise ValueError('Grupos incompatibles con la placa')
        if self.utc()+self._espera()+.5>=d['vence']:
            self._respuesta(d,'rechazado','No cabe en el plazo sin interrumpir el despeje o la transición segura');return
        self.ctrl.secuenciador.solicitar(plan)
        self.pendiente=d;self.activo_desde=None
    def tick(self):
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
                if d['plan']['modo']=='emergencia':
                    self.emergencia_hasta=self.reloj()+sum(f.duracion_s for f in self.ctrl.secuenciador.plan.fases)
                self._respuesta(d,'aplicado','Plan seleccionado tras todo rojo y sin falla MMU reportada')
                self.pendiente=None
