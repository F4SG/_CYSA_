"""Conexión SQL Server local por ODBC; no usa las credenciales de PostgreSQL."""
import json,os,re
from datetime import datetime,timezone
from uuid import UUID

JSON_COLUMNS={'documento','validacion','origen','mfa','payload','anterior','nuevo'}
DATABASES={'CYSA_Control_S2','CYSA_Control_S2_Pruebas'}
CONFIG_DATABASE='CYSA_WebIII_Demo'
PROJECT_CONFIG_DATABASE='CYSA_Proyecto'
SERVERS={'localhost','.',r'localhost\SQLEXPRESS',r'.\SQLEXPRESS',r'(localdb)\MSSQLLocalDB'}

def cadena(database=None):
    server=os.environ.get('CYSA_SQL_SERVER','localhost');database=database or os.environ.get('CYSA_SQL_DATABASE','CYSA_Control_S2')
    if server not in SERVERS or database not in DATABASES|{'master',CONFIG_DATABASE,PROJECT_CONFIG_DATABASE}:raise ValueError('Servidor/base fuera del banco SQL Server local')
    return f'Driver={{ODBC Driver 18 for SQL Server}};Server={server};Database={database};Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=10'

def crear_base():
    import pyodbc
    db=os.environ.get('CYSA_SQL_DATABASE','CYSA_Control_S2')
    if db not in DATABASES:raise ValueError('Base no permitida')
    with pyodbc.connect(cadena('master'),autocommit=True) as c:
        if not c.execute('SELECT DB_ID(?)',db).fetchone()[0]:c.execute(f'CREATE DATABASE [{db}]')

class Result:
    def __init__(self,cursor):self.cursor=cursor
    def row(self,r):
        if r is None:return None
        result=dict(zip([x[0] for x in self.cursor.description],r))
        for key,value in result.items():
            if key in JSON_COLUMNS and value is not None:result[key]=json.loads(value)
            elif isinstance(value,datetime) and value.tzinfo is None:result[key]=value.replace(tzinfo=timezone.utc)
        return result
    def fetchone(self):return self.row(self.cursor.fetchone())
    def fetchall(self):return [self.row(r) for r in self.cursor.fetchall()]

class Conexion:
    def __enter__(self):
        import pyodbc
        pyodbc.native_uuid=True
        self.db=pyodbc.connect(cadena(),autocommit=False);return self
    def __exit__(self,kind,error,tb):
        try:self.db.rollback() if error else self.db.commit()
        finally:self.db.close()
    def execute(self,sql,params=()):
        sql=sql.replace('%s','?').replace('now()','SYSUTCDATETIME()')
        match=re.search(r' LIMIT (\d+)$',sql,re.I)
        if match:sql=re.sub(r'^SELECT ',f'SELECT TOP {match[1]} ',sql,flags=re.I)[: -len(match[0])]
        if sql.endswith(' FOR UPDATE'):
            sql=sql[:-11]
            # Los dos bloqueos de decisión/confirmación se adquieren para actualizar,
            # evitando decisiones concurrentes sobre una misma versión.
            sql=re.sub(r'FROM (control_planes|control_envios|control_conteos|control_estados)( e)?',r'FROM \1\2 WITH(UPDLOCK,HOLDLOCK)',sql,count=1)
        params=tuple(str(x) if isinstance(x,UUID) else x for x in params)
        return Result(self.db.cursor().execute(sql,*params))

def connection():return Conexion()

def configuracion_aprobada():
    """Lee solo la versión aprobada cuya última escritura se hizo con MFA de Proyecto."""
    import pyodbc
    database = os.environ.get('CYSA_CONFIG_DATABASE', CONFIG_DATABASE)
    if database not in (CONFIG_DATABASE, PROJECT_CONFIG_DATABASE):
        raise ValueError('Base de configuraciones fuera de Proyecto de Sistemas')
    with pyodbc.connect(cadena(database)) as db:
        row=db.execute("""
            SELECT TOP 1 c.Id,c.Version,c.VerdeMinSegundos,c.VerdeMaxSegundos,
                c.AmbarSegundos,c.TodoRojoSegundos
            FROM ConfigTecnica c
            JOIN Interseccion i ON i.Id=c.InterseccionId
            CROSS APPLY (
                SELECT TOP 1 b.Motivo,b.MfaVerificado
                FROM Bitacora b WHERE b.ObjetoTipo=N'ConfigTecnica'
                    AND b.ObjetoId=CONVERT(nvarchar(32),c.Id)
                ORDER BY b.Id DESC
            ) a
            WHERE i.Nombre=N'DEMO_INT_01' AND i.Prueba=1 AND c.Prueba=1
                AND c.Estado=N'aprobada' AND c.AprobadaUtc<=SYSUTCDATETIME()
                AND a.MfaVerificado=1
                AND (?=1 OR a.Motivo=N'Configuración registrada mediante la API de Proyecto')
            ORDER BY c.Version DESC
            """, int(database == PROJECT_CONFIG_DATABASE)).fetchone()
    if row is None:
        return None
    campos=('verde_min_s','verde_max_s','ambar_s','todo_rojo_s')
    return dict(id=row[0],version=row[1],tiempos={k:float(v) for k,v in zip(campos,row[2:])})
