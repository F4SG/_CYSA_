import os
import psycopg
from psycopg.rows import dict_row
from cysa.contracts import Conteo,Estado
class Repository:
    def connection(self):
        return psycopg.connect(host=os.environ.get('DB_HOST','db'),dbname=os.environ.get('DB_NAME','cysa'),
          user=os.environ.get('DB_USER','cysa'),password=os.environ['DB_PASSWORD'],row_factory=dict_row,connect_timeout=5)
    def ready(self):
        with self.connection() as c:c.execute('SELECT 1')
    def save(self,event):
        d=event.model_dump()
        with self.connection() as c:
            if isinstance(event,Conteo):
                c.execute('''INSERT INTO conteos(mensaje_id,interseccion,acceso,carril,clase,cantidad,inicio,fin,prueba)
                 VALUES(%(mensaje_id)s,%(interseccion)s,%(acceso)s,%(carril)s,%(clase)s,%(cantidad)s,%(inicio)s,%(fin)s,%(prueba)s)
                 ON CONFLICT(mensaje_id,inicio) DO NOTHING''',d)
            elif isinstance(event,Estado):
                c.execute('''INSERT INTO estados(interseccion,mensaje_id,fase_actual,plan_activo,estado_controlador,timestamp,prueba)
                 VALUES(%(interseccion)s,%(mensaje_id)s,%(fase_actual)s,%(plan_activo)s,%(estado_controlador)s,%(timestamp)s,%(prueba)s)
                 ON CONFLICT(interseccion) DO UPDATE SET mensaje_id=excluded.mensaje_id,fase_actual=excluded.fase_actual,
                 plan_activo=excluded.plan_activo,estado_controlador=excluded.estado_controlador,timestamp=excluded.timestamp,
                 prueba=excluded.prueba WHERE excluded.timestamp>estados.timestamp''',d)
    def counts(self,desde,hasta,interseccion=None,carril=None,prueba=None,limit=200,offset=0):
        with self.connection() as c:
            return c.execute('''SELECT mensaje_id,interseccion,acceso,carril,clase,cantidad,inicio,fin,prueba FROM conteos
             WHERE inicio >= %s AND inicio < %s AND (%s::text IS NULL OR interseccion=%s)
             AND (%s::text IS NULL OR carril=%s) AND (%s::boolean IS NULL OR prueba=%s)
             ORDER BY inicio,interseccion,acceso,carril,clase,mensaje_id LIMIT %s OFFSET %s''',
             (desde,hasta,interseccion,interseccion,carril,carril,prueba,prueba,limit,offset)).fetchall()
    def states(self):
        with self.connection() as c:return c.execute('SELECT * FROM estados ORDER BY interseccion').fetchall()
    def inventory(self):
        with self.connection() as c:return c.execute('SELECT * FROM inventario ORDER BY interseccion,tipo,activo_id').fetchall()
    def upsert_assets(self,assets):
        with self.connection() as c:
            for a in assets:
                c.execute('''INSERT INTO inventario(activo_id,interseccion,acceso,tipo,ubicacion,protocolo,prueba)
                 VALUES(%(activo_id)s,%(interseccion)s,%(acceso)s,%(tipo)s,%(ubicacion)s,%(protocolo)s,%(prueba)s)
                 ON CONFLICT(activo_id) DO UPDATE SET interseccion=excluded.interseccion,acceso=excluded.acceso,
                 tipo=excluded.tipo,ubicacion=excluded.ubicacion,protocolo=excluded.protocolo,prueba=excluded.prueba''',a.model_dump())
    def replace_asset(self,asset_id,asset):
        with self.connection() as c:
            row=c.execute('SELECT activo_id FROM inventario WHERE activo_id=%s FOR UPDATE',(asset_id,)).fetchone()
            if not row:return False
            d=asset.model_dump()
            c.execute('''UPDATE inventario SET interseccion=%(interseccion)s,acceso=%(acceso)s,tipo=%(tipo)s,
             ubicacion=%(ubicacion)s,protocolo=%(protocolo)s,prueba=%(prueba)s WHERE activo_id=%(activo_id)s''',d)
            return True
