from datetime import datetime,timedelta,timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends,HTTPException,Query
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from cysa.contracts import Timed
from app.auth import read_access,admin_access
from app.repository import Repository
from app.users import KeycloakUsers,build_users_router
from cysa_inventory.router import build_router

def count_window(start, end):
    try:
        start, end = Timed.utc(start), Timed.utc(end)
    except ValueError:
        raise HTTPException(422, 'Fechas con zona horaria requeridas') from None
    if start >= end or end - start > timedelta(days=31):
        raise HTTPException(422, 'Rango válido: mayor a 0 y hasta 31 días')
    return start, end


def create_app(repository=None,user_directory=None):
    repo=repository or Repository()
    @asynccontextmanager
    async def lifespan(app):
        repo.ready()
        yield
    app=FastAPI(title='CYSA S1 — solo monitoreo',version='1.1.0',lifespan=lifespan)
    directory=user_directory or KeycloakUsers()
    app.state.identity=directory
    @app.exception_handler(RequestValidationError)
    async def validation(request,error):
        if request.url.path.startswith('/api/usuarios'):
            # No devolver contraseñas ni el cuerpo de alta en errores de validación.
            return JSONResponse(status_code=422,content={'detail':[
                {key:value for key,value in item.items() if key in ('loc','msg','type')}
                for item in error.errors()]})
        return await request_validation_exception_handler(request,error)
    @app.get('/health',include_in_schema=False)
    def health():return {'status':'ok','activacion_planes':False}
    @app.get('/api/conteos',dependencies=[Depends(read_access)])
    def counts(desde:datetime|None=None,hasta:datetime|None=None,interseccion:str|None=None,
               carril:str|None=None,prueba:bool|None=None,limit:int=Query(200,ge=1,le=1000),offset:int=Query(0,ge=0)):
        end=hasta or datetime.now(timezone.utc);start=desde or end-timedelta(hours=1)
        start,end=count_window(start,end)
        rows=repo.counts(start,end,interseccion,carril,prueba,limit,offset)
        return {'items':rows,'limit':limit,'offset':offset,'desde':start,'hasta':end}
    @app.get('/api/reportes/conteos', dependencies=[Depends(read_access)])
    def report_counts(desde: datetime, hasta: datetime, interseccion: str | None = None,
                      prueba: bool | None = None):
        start, end = count_window(desde, hasta)
        rows, intersections = repo.count_report(start, end, interseccion, prueba)
        columns = ('autos', 'motos', 'micros', 'total')
        summary = {name: dict.fromkeys(columns, 0) for name in ('operacion', 'validacion')}
        for row in rows:
            row['total'] = row['autos'] + row['motos'] + row['micros']
            totals = summary['validacion' if row['prueba'] else 'operacion']
            for column in columns:
                totals[column] += row[column]
        return {'desde': start, 'hasta': end, 'intersecciones': intersections, 'resumen': summary, 'items': rows}
    @app.get('/api/estados',dependencies=[Depends(read_access)])
    def states():return {'items':repo.states()}
    app.include_router(build_router(repo,read_access,admin_access))
    app.include_router(build_users_router(directory))
    return app
app=create_app()
