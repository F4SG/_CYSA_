"""Repositorio en memoria SOLO para pruebas. No sustituye TimescaleDB en producción."""
import pytest
from datetime import datetime,timezone
from fastapi.testclient import TestClient
from app.main import create_app
from app.auth import principal
from cysa.contracts import Estado
class MemoryRepository:
    def __init__(self):self.events={};self.assets={};self.status={}
    def ready(self):pass
    def save(self,event):
        if isinstance(event,Estado):
            prev=self.status.get(event.interseccion)
            if prev is None or event.timestamp>prev['timestamp']:self.status[event.interseccion]=event.model_dump()
        else:self.events.setdefault((str(event.mensaje_id),event.inicio),event.model_dump())
    def counts(self,start,end,intersection,lane,prueba,limit,offset):
        rows=[r for r in self.events.values() if start<=r['inicio']<end and (not intersection or r['interseccion']==intersection)
          and (not lane or r['carril']==lane) and (prueba is None or r['prueba']==prueba)]
        return sorted(rows,key=lambda r:(r['inicio'],str(r['mensaje_id'])))[offset:offset+limit]
    def states(self):return list(self.status.values())
    def inventory(self):return list(self.assets.values())
    def upsert_assets(self,assets):
        for a in assets:self.assets[a.activo_id]=a.model_dump()
    def replace_asset(self,asset_id,asset):
        if asset_id not in self.assets:return False
        self.assets[asset_id]=asset.model_dump();return True
class MemoryIdentity:
    """Identidad sustituida explícitamente en tests; nunca se usa en la aplicación."""
    def verify(self,claims,allowed):pass
@pytest.fixture
def identity_directory():return MemoryIdentity()
@pytest.fixture
def repository():return MemoryRepository()
@pytest.fixture
def client(repository,identity_directory):
    app=create_app(repository,identity_directory)
    with TestClient(app) as client:yield client
@pytest.fixture
def operator(client):
    client.app.dependency_overrides[principal]=lambda:{'sub':'test-operador','realm_access':{'roles':['operador']}}
    yield client
@pytest.fixture
def admin(client):
    client.app.dependency_overrides[principal]=lambda:{'sub':'test-admin','realm_access':{'roles':['administrador']}}
    yield client
