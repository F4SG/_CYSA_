"""Conexión SQL Server local por ODBC; no usa las credenciales de PostgreSQL."""
import json,os,re
from datetime import datetime,timezone
from uuid import UUID

JSON_COLUMNS={'documento','validacion','origen','mfa','payload','anterior','nuevo'}
DATABASES={'CYSA_Control_S2','CYSA_Control_S2_Pruebas'}
SERVERS={'localhost','.',r'localhost\SQLEXPRESS',r'.\SQLEXPRESS',r'(localdb)\MSSQLLocalDB'}

def cadena(database=None):
    server=os.environ.get('CYSA_SQL_SERVER','localhost');database=database or os.environ.get('CYSA_SQL_DATABASE','CYSA_Control_S2')
    if server not in SERVERS or database not in DATABASES|{'master'}:raise ValueError('Servidor/base fuera del banco SQL Server local')
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
