"""Persistencia transaccional del flujo IoT existente en PostgreSQL.

La Web API académica conserva sus migraciones SQL Server; estas tablas pertenecen
al despliegue IoT, que ya usa PostgreSQL. No se modifica su inventario ni sus conteos.
"""
import json,time
from uuid import uuid4
from psycopg.types.json import Jsonb
from .planes import huella

DDL='''
CREATE TABLE IF NOT EXISTS control_planes(
 id uuid PRIMARY KEY, documento jsonb NOT NULL, validacion jsonb NOT NULL,
 origen jsonb NOT NULL, estado text NOT NULL, creado timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS control_decisiones(
 solicitud_id uuid PRIMARY KEY, plan_id uuid NOT NULL UNIQUE REFERENCES control_planes(id),
 usuario text NOT NULL, accion text NOT NULL, motivo text NOT NULL, mfa jsonb NOT NULL,
 creado timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS control_envios(
 solicitud_id uuid PRIMARY KEY REFERENCES control_decisiones(solicitud_id), payload jsonb NOT NULL,
 estado text NOT NULL DEFAULT 'pendiente', intentos integer NOT NULL DEFAULT 0,
 detalle text NOT NULL DEFAULT '', actualizado timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS control_auditoria(
 id bigserial PRIMARY KEY, plan_id uuid, usuario text NOT NULL, operacion text NOT NULL,
 motivo text NOT NULL, anterior jsonb NOT NULL, nuevo jsonb NOT NULL,
 creado timestamptz NOT NULL DEFAULT now());
'''

class EstadoInvalido(ValueError):pass

class Almacen:
    def __init__(self,connection):self.connection=connection
    def ready(self):
        with self.connection() as c:c.execute(DDL)
    def guardar(self,id,documento,validacion,origen,usuario):
        estado='validado' if validacion['aprobada'] else 'no_aprobado'
        with self.connection() as c:
            c.execute('INSERT INTO control_planes(id,documento,validacion,origen,estado) VALUES(%s,%s,%s,%s,%s)',
                      (id,Jsonb(documento),Jsonb(validacion),Jsonb(origen),estado))
            self.audit(c,id,usuario,'simular','Comparación SUMO terminada',{},dict(estado=estado,huella=huella(documento)))
        return self.obtener(id)
    def listar(self):
        with self.connection() as c:
            return c.execute('''SELECT p.*, d.usuario,d.accion,d.motivo,e.estado AS estado_envio,e.detalle AS detalle_envio
                FROM control_planes p LEFT JOIN control_decisiones d ON d.plan_id=p.id
                LEFT JOIN control_envios e ON e.solicitud_id=d.solicitud_id ORDER BY p.creado DESC LIMIT 100''').fetchall()
    def obtener(self,id):
        with self.connection() as c:
            return c.execute('''SELECT p.*,d.solicitud_id,d.usuario,d.accion,d.motivo,e.estado AS estado_envio,e.detalle AS detalle_envio
                FROM control_planes p LEFT JOIN control_decisiones d ON d.plan_id=p.id
                LEFT JOIN control_envios e ON e.solicitud_id=d.solicitud_id WHERE p.id=%s''',(id,)).fetchone()
    def decidir(self,id,solicitud,accion,motivo,usuario,mfa):
        with self.connection() as c:
            p=c.execute('SELECT * FROM control_planes WHERE id=%s FOR UPDATE',(id,)).fetchone()
            if not p:raise KeyError('Plan inexistente')
            old=c.execute('SELECT * FROM control_decisiones WHERE solicitud_id=%s',(solicitud,)).fetchone()
            if old:
                if str(old['plan_id'])!=str(id) or (old['usuario'],old['accion'],old['motivo'])!=(usuario,accion,motivo):
                    raise EstadoInvalido('SolicitudId ya pertenece a otra decisión')
                return True
            if p['estado']!='validado' or not p['validacion']['aprobada'] or p['validacion']['huella_plan']!=huella(p['documento']):
                raise EstadoInvalido('Se requiere esta versión validada, vigente y sin decisión')
            if (time.time()-p['creado'].timestamp())>900:raise EstadoInvalido('La evaluación venció; repetir la simulación')
            c.execute('INSERT INTO control_decisiones(solicitud_id,plan_id,usuario,accion,motivo,mfa) VALUES(%s,%s,%s,%s,%s,%s)',
                      (solicitud,id,usuario,accion,motivo,Jsonb(mfa)))
            nuevo='autorizado' if accion=='autorizar' else 'rechazado'
            c.execute('UPDATE control_planes SET estado=%s WHERE id=%s',(nuevo,id))
            if accion=='autorizar':
                now=time.time();payload=dict(tipo='plan',solicitud_id=str(solicitud),plan=p['documento'],
                    huella_plan=huella(p['documento']),usuario=usuario,mfa_verificado=True,
                    emitido=now,vence=now+(10 if p['documento']['modo']=='emergencia' else 300))
                c.execute('INSERT INTO control_envios(solicitud_id,payload) VALUES(%s,%s)',(solicitud,Jsonb(payload)))
            self.audit(c,id,usuario,'decidir',motivo,dict(estado=p['estado']),dict(estado=nuevo,mfa=mfa))
        return False
    def pendientes(self):
        with self.connection() as c:
            return c.execute("SELECT * FROM control_envios WHERE estado IN ('pendiente','enviado') ORDER BY actualizado LIMIT 20").fetchall()
    def envio(self,id,estado,detalle=''):
        with self.connection() as c:
            c.execute("UPDATE control_envios SET estado=%s,detalle=%s,intentos=intentos+1,actualizado=now() WHERE solicitud_id=%s AND estado IN ('pendiente','enviado')",(estado,detalle,id))
    def confirmar(self,d):
        if d.get('estado') not in ('aplicado','rechazado'):raise ValueError('Confirmación inválida')
        with self.connection() as c:
            row=c.execute('SELECT e.*,p.plan_id FROM control_envios e JOIN control_decisiones p USING(solicitud_id) WHERE solicitud_id=%s FOR UPDATE',(d['solicitud_id'],)).fetchone()
            if not row:return
            if d.get('huella_plan')!=row['payload']['huella_plan']:raise ValueError('Confirmación de otra versión')
            if row['estado'] in ('aplicado','rechazado','caducado'):return
            c.execute('UPDATE control_envios SET estado=%s,detalle=%s,actualizado=now() WHERE solicitud_id=%s',
                      (d['estado'],str(d.get('detalle',''))[:500],d['solicitud_id']))
            self.audit(c,row['plan_id'],'controlador','confirmar',str(d.get('detalle',''))[:500],dict(estado=row['estado']),dict(estado=d['estado']))
    def auditoria(self,id):
        with self.connection() as c:return c.execute('SELECT * FROM control_auditoria WHERE plan_id=%s ORDER BY id',(id,)).fetchall()
    @staticmethod
    def audit(c,id,usuario,operacion,motivo,anterior,nuevo):
        c.execute('INSERT INTO control_auditoria(plan_id,usuario,operacion,motivo,anterior,nuevo) VALUES(%s,%s,%s,%s,%s,%s)',
                  (id,usuario,operacion,motivo,Jsonb(anterior),Jsonb(nuevo)))
