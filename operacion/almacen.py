"""Persistencia transaccional del banco S2 en SQL Server; independiente de Web III."""
import json,time
from pathlib import Path
from .planes import huella
from .sqlserver import connection as sql_connection,crear_base

def Jsonb(value):return json.dumps(value,ensure_ascii=True,allow_nan=False)
DDL=(Path(__file__).parent/'sql/001_operacion.sql').read_text(encoding='utf-8')
FUENTE_EJEMPLOS = 'ejemplos-autorizacion'

def firma_ejemplo(plan, origen):
    return huella(dict(caso=origen.get('caso'), demanda=origen.get('autos_por_acceso'), mezcla=origen.get('mezcla'),
                       plan={k: v for k, v in plan.items() if k != 'plan_id'}))

class EstadoInvalido(ValueError):pass

class Almacen:
    def __init__(self,connection=None):self.connection=connection or sql_connection
    def ready(self):
        crear_base()
        with self.connection() as c:c.execute(DDL)
    def guardar(self,id,documento,validacion,origen,usuario):
        with self.connection() as c:
            self.insertar_plan(c,id,documento,validacion,origen,usuario)
        return self.obtener(id)
    def insertar_plan(self,c,id,documento,validacion,origen,usuario):
        estado='validado' if validacion['aprobada'] else 'no_aprobado'
        c.execute('INSERT INTO control_planes(id,documento,validacion,origen,estado) VALUES(%s,%s,%s,%s,%s)',
                  (id,Jsonb(documento),Jsonb(validacion),Jsonb(origen),estado))
        self.audit(c,id,usuario,'simular','Comparación SUMO terminada',{},dict(estado=estado,huella=huella(documento)))
    def eliminar_ejemplos(self):
        with self.connection() as c:
            examples = self._ejemplos_actuales(c)
            if any(plan['estado_envio'] in ('pendiente', 'enviado') for plan in examples):
                raise EstadoInvalido('Espera el resultado del envío de práctica antes de eliminar los datos.')
            self._retirar_ejemplos(c, examples)

    @staticmethod
    def _ejemplos_actuales(c):
        c.execute("""
            IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
            DECLARE @resultado int;
            EXEC @resultado = sp_getapplock @Resource='CYSA_ejemplos_autorizacion',
                @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=10000;
            IF @resultado < 0 THROW 51000, 'No se pudo bloquear el lote de ejemplos', 1;
        """)
        return c.execute("""
            SELECT p.id, p.documento, p.origen, p.estado, p.creado, d.plan_id AS decidido, e.estado AS estado_envio
            FROM control_planes p WITH (UPDLOCK,HOLDLOCK)
            LEFT JOIN control_decisiones d ON d.plan_id=p.id
            LEFT JOIN control_envios e ON e.solicitud_id=d.solicitud_id
            WHERE COALESCE(JSON_VALUE(p.origen,'$.archivado'),'0')<>'1'
              AND (
                JSON_VALUE(p.origen,'$.fuente')=%s OR (
                  JSON_VALUE(p.documento,'$.modo')='webster'
                  AND EXISTS (SELECT 1 FROM OPENJSON(p.origen,'$.mensajes'))
                  AND NOT EXISTS (
                    SELECT 1 FROM OPENJSON(p.origen,'$.mensajes') m
                    LEFT JOIN control_conteos x ON x.mensaje_id=TRY_CONVERT(uniqueidentifier,m.value)
                      AND x.prueba=1 AND x.interseccion='DEMO_INT_01'
                      AND (LEFT(x.carril,10)='DEMO_PLAN_' OR LEFT(x.carril,6)='QA_QR_')
                    WHERE x.mensaje_id IS NULL
                  )
                )
              )
        """, (FUENTE_EJEMPLOS,)).fetchall()

    @staticmethod
    def _retirar_ejemplos(c, previous):
        for old in previous:
            if old['decidido']:
                c.execute("UPDATE control_planes SET origen=JSON_MODIFY(origen,'$.archivado',1) WHERE id=%s",
                          (old['id'],))
            else:
                c.execute('DELETE FROM control_auditoria WHERE plan_id=%s', (old['id'],))
                c.execute('DELETE FROM control_planes WHERE id=%s', (old['id'],))

    def reemplazar_ejemplos(self, examples, *, conservar_vigentes=False):
        if len(examples) != 5 or len({example[0] for example in examples}) != 5:
            raise ValueError('El lote debe contener cinco ejemplos distintos.')
        if any(not validation['aprobada'] or not validation.get('sumo_real')
               or validation['huella_plan'] != huella(plan) for _, plan, validation, _ in examples):
            raise ValueError('Todos los ejemplos deben estar validados por SUMO.')
        with self.connection() as c:
            previous = self._ejemplos_actuales(c)
            if conservar_vigentes and len(previous) == len(examples):
                now = time.time()
                current = {
                    firma_ejemplo(p['documento'], p['origen']) for p in previous
                    if p['origen'].get('fuente') == FUENTE_EJEMPLOS and not p['decidido']
                    and p['estado'] == 'validado' and 0 <= now - p['creado'].timestamp() < 600
                }
                requested = {firma_ejemplo(plan, origin) for _, plan, _, origin in examples}
                if len(current) == len(examples) and current == requested:
                    return False
            self._retirar_ejemplos(c, previous)
            for ident, plan, validation, origin in examples:
                self.insertar_plan(c,ident,plan,validation,{**origin,'fuente':FUENTE_EJEMPLOS},'lanzador-demo')
        return True
    def listar(self):
        with self.connection() as c:
            return c.execute('''SELECT p.*, d.usuario,d.accion,d.motivo,e.estado AS estado_envio,e.detalle AS detalle_envio
                FROM control_planes p LEFT JOIN control_decisiones d ON d.plan_id=p.id
                LEFT JOIN control_envios e ON e.solicitud_id=d.solicitud_id
                WHERE COALESCE(JSON_VALUE(p.origen,'$.archivado'),'0')<>'1'
                ORDER BY p.creado DESC LIMIT 100''').fetchall()
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
            if p['documento'].get('modo')!='webster':
                raise EstadoInvalido('Solo las propuestas Webster admiten decisiones operativas')
            now=time.time()
            c.execute('INSERT INTO control_decisiones(solicitud_id,plan_id,usuario,accion,motivo,mfa) VALUES(%s,%s,%s,%s,%s,%s)',
                      (solicitud,id,usuario,accion,motivo,Jsonb(mfa)))
            nuevo='autorizado' if accion=='autorizar' else 'rechazado'
            c.execute('UPDATE control_planes SET estado=%s WHERE id=%s',(nuevo,id))
            if accion=='autorizar':
                payload=dict(tipo='plan',solicitud_id=str(solicitud),plan=p['documento'],
                    huella_plan=huella(p['documento']),usuario=usuario,mfa_verificado=True,
                    emitido=now,vence=now+300)
                c.execute('INSERT INTO control_envios(solicitud_id,payload) VALUES(%s,%s)',(solicitud,Jsonb(payload)))
            self.audit(c,id,usuario,'decidir',motivo,dict(estado=p['estado']),dict(estado=nuevo,mfa=mfa))
        return False
    def pendientes(self):
        with self.connection() as c:
            return c.execute("SELECT * FROM control_envios WHERE estado IN ('pendiente','enviado') AND JSON_VALUE(payload,'$.plan.modo')='webster' ORDER BY actualizado LIMIT 20").fetchall()
    def envio(self,id,estado,detalle=''):
        with self.connection() as c:
            c.execute("UPDATE control_envios SET estado=%s,detalle=%s,intentos=intentos+1,actualizado=now() WHERE solicitud_id=%s AND estado IN ('pendiente','enviado')",(estado,detalle,id))
    def confirmar(self,d):
        if d.get('estado') not in ('aplicado','rechazado'):raise ValueError('Confirmación inválida')
        with self.connection() as c:
            row=c.execute('SELECT e.*,p.plan_id FROM control_envios e JOIN control_decisiones p ON p.solicitud_id=e.solicitud_id WHERE e.solicitud_id=%s FOR UPDATE',(d['solicitud_id'],)).fetchone()
            if not row:return
            if d.get('huella_plan')!=row['payload']['huella_plan']:raise ValueError('Confirmación de otra versión')
            if row['estado'] in ('aplicado','rechazado','caducado'):return
            c.execute('UPDATE control_envios SET estado=%s,detalle=%s,actualizado=now() WHERE solicitud_id=%s',
                      (d['estado'],str(d.get('detalle',''))[:500],d['solicitud_id']))
            self.audit(c,row['plan_id'],'controlador','confirmar',str(d.get('detalle',''))[:500],dict(estado=row['estado']),dict(estado=d['estado']))
    def auditoria(self,id):
        with self.connection() as c:return c.execute('SELECT * FROM control_auditoria WHERE plan_id=%s ORDER BY id',(id,)).fetchall()
    def counts(self,desde,hasta,interseccion=None,carril=None,prueba=None,limit=1000,offset=0):
        with self.connection() as c:
            return c.execute('''SELECT * FROM control_conteos WHERE inicio>=%s AND inicio<%s
                AND (%s IS NULL OR interseccion=%s) AND (%s IS NULL OR carril=%s)
                AND (%s IS NULL OR prueba=%s) ORDER BY inicio,mensaje_id OFFSET %s ROWS FETCH NEXT %s ROWS ONLY''',
                (desde,hasta,interseccion,interseccion,carril,carril,prueba,prueba,offset,limit)).fetchall()
    def states(self):
        with self.connection() as c:return c.execute('SELECT * FROM control_estados ORDER BY interseccion').fetchall()
    def save(self,event):
        from cysa.contracts import Conteo,Estado
        d=event.model_dump()
        with self.connection() as c:
            if isinstance(event,Conteo):
                old=c.execute('SELECT * FROM control_conteos WHERE mensaje_id=%s FOR UPDATE',(event.mensaje_id,)).fetchone()
                if old:
                    for k in ('interseccion','acceso','carril','clase','cantidad','inicio','fin','prueba'):
                        if old[k]!=d[k]:raise ValueError('Mensaje de conteo reutilizado con otro contenido')
                    return
                c.execute('INSERT INTO control_conteos(mensaje_id,interseccion,acceso,carril,clase,cantidad,inicio,fin,prueba) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',tuple(d[k] for k in ('mensaje_id','interseccion','acceso','carril','clase','cantidad','inicio','fin','prueba')))
            elif isinstance(event,Estado):
                old=c.execute('SELECT * FROM control_estados WHERE interseccion=%s FOR UPDATE',(event.interseccion,)).fetchone()
                if old and old['timestamp']>=event.timestamp:return
                if old:
                    c.execute('UPDATE control_estados SET mensaje_id=%s,fase_actual=%s,plan_activo=%s,estado_controlador=%s,timestamp=%s,prueba=%s WHERE interseccion=%s',tuple(d[k] for k in ('mensaje_id','fase_actual','plan_activo','estado_controlador','timestamp','prueba','interseccion')))
                else:c.execute('INSERT INTO control_estados(interseccion,mensaje_id,fase_actual,plan_activo,estado_controlador,timestamp,prueba) VALUES(%s,%s,%s,%s,%s,%s,%s)',tuple(d[k] for k in ('interseccion','mensaje_id','fase_actual','plan_activo','estado_controlador','timestamp','prueba')))
    @staticmethod
    def audit(c,id,usuario,operacion,motivo,anterior,nuevo):
        c.execute('INSERT INTO control_auditoria(plan_id,usuario,operacion,motivo,anterior,nuevo) VALUES(%s,%s,%s,%s,%s,%s)',
                  (id,usuario,operacion,motivo,Jsonb(anterior),Jsonb(nuevo)))
