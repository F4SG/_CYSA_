"""API del banco S2 en Windows: SQL Server integrado, Keycloak y SUMO locales."""
import os,threading,logging,json
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI,Depends
from fastapi.responses import FileResponse
from .almacen import Almacen
from .api import router
from app.auth import read_access
from app.users import KeycloakUsers

ROOT=Path(__file__).resolve().parents[1]
def create_app(store=None,directory=None,worker=True):
    store=store or Almacen()
    @asynccontextmanager
    async def lifespan(app):
        store.ready();stop=threading.Event();threads=[]
        if worker:
            from .trabajador import ejecutar
            from .generar import planificar
            for funcion,nombre in ((ejecutar,'cysa-sql-mqtt'),(planificar,'cysa-planificador')):
                thread=threading.Thread(target=funcion,args=(store,stop),daemon=True,name=nombre)
                thread.start()
                threads.append(thread)
        try:
            yield
        finally:
            stop.set()
            for thread in threads:
                thread.join(timeout=8)
    app=FastAPI(title='CYSA S2 — SQL Server, SUMO y controlador',lifespan=lifespan)
    @app.middleware('http')
    async def no_cache(request,call_next):
        response=await call_next(request);response.headers['Cache-Control']='no-store';return response
    app.state.identity=directory or KeycloakUsers()
    app.include_router(router(store))
    @app.get('/health')
    def health():return dict(status='ok',persistencia='SQL Server',banco_prueba=True,
        mqtt_conectado=bool(getattr(store,'mqtt_ready',None) and store.mqtt_ready.is_set()))
    @app.get('/config.json')
    def config():
        path=Path(os.environ.get('CYSA_INSTALACION_DIR',ROOT))/'panel/config.json'
        panel=json.loads(path.read_text(encoding='utf-8-sig')).get('redirectUri') if path.exists() else None
        return dict(issuer=os.environ['OIDC_ISSUER'],clientId='cysa-panel',redirectUri=os.environ.get('CYSA_OPERACION_URL','http://localhost:5184')+'/',panelUrl=os.environ.get('CYSA_PANEL_URL',panel))
    @app.get('/api/estados',dependencies=[Depends(read_access)])
    def estados():return dict(items=store.states())
    @app.get('/')
    def index():return FileResponse(ROOT/'operacion/web/index.html')
    @app.get('/app.js')
    def js():return FileResponse(ROOT/'operacion/web/app.js',media_type='application/javascript')
    @app.get('/oidc.js')
    def oidc():return FileResponse(ROOT/'panel/oidc.js',media_type='application/javascript')
    @app.get('/home-link.js')
    def home_link():return FileResponse(ROOT/'panel/home-link.js',media_type='application/javascript')
    return app

if __name__=='__main__':
    from .entorno import cargar
    cargar();import uvicorn
    uvicorn.run(create_app(),host='127.0.0.1',port=int(os.environ.get('CYSA_OPERACION_PORT','5184')))
