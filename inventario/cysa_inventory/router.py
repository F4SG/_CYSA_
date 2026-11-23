from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from cysa.contracts import Activo
class Carga(BaseModel):
    model_config=ConfigDict(extra='forbid')
    items:list[Activo]=Field(min_length=1,max_length=2000)

def build_router(repo,read_access,admin_access):
    router=APIRouter(prefix='/api/inventario',tags=['inventario'])
    @router.get('',dependencies=[Depends(read_access)])
    def list_assets():return {'items':repo.inventory()}
    @router.post('',status_code=201,dependencies=[Depends(admin_access)])
    def create_asset(body:Activo):
        if not repo.create_asset(body):raise HTTPException(409,'Ya existe un activo con ese ID. Usa Editar o elige otro identificador.')
        return body
    @router.post('/carga',dependencies=[Depends(admin_access)])
    def load_assets(body:Carga):
        ids=[a.activo_id for a in body.items]
        if len(ids)!=len(set(ids)):raise HTTPException(422,'activo_id duplicado en la carga')
        repo.upsert_assets(body.items);return {'procesados':len(body.items)}
    @router.put('/{activo_id}',dependencies=[Depends(admin_access)])
    def update_asset(activo_id:str,body:Activo):
        if activo_id!=body.activo_id:raise HTTPException(422,'El ID de la ruta y del cuerpo deben coincidir')
        if not repo.replace_asset(activo_id,body):raise HTTPException(404,'Activo no encontrado')
        return body
    @router.delete('/{activo_id}',dependencies=[Depends(admin_access)])
    def delete_asset(activo_id:str):
        if not repo.delete_asset(activo_id):raise HTTPException(404,'Activo no encontrado')
        return {'eliminado':activo_id}
    return router
