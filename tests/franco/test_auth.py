from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import jwt,pytest
import app.auth as auth
from app.main import create_app

@pytest.fixture
def jwt_client(repository,identity_directory,monkeypatch):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    monkeypatch.setenv('OIDC_ISSUER','https://id.example.invalid/realms/cysa')
    monkeypatch.setenv('OIDC_AUDIENCE','cysa-api')
    class Keys:
        def get_signing_key_from_jwt(self,token):return SimpleNamespace(key=key.public_key())
    monkeypatch.setattr(auth,'_jwks',Keys())
    def token(**changes):
        now=datetime.now(timezone.utc)
        claims={'sub':'synthetic-user','iat':now,'exp':now+timedelta(minutes=5),'iss':'https://id.example.invalid/realms/cysa',
         'aud':'cysa-api','realm_access':{'roles':['operador']}}
        claims.update(changes);return jwt.encode(claims,key,algorithm='RS256')
    with TestClient(create_app(repository,identity_directory)) as c:yield c,token

def test_token_firmado_valido(jwt_client):
    c,token=jwt_client
    assert c.get('/api/estados',headers={'Authorization':'Bearer '+token()}).status_code==200
@pytest.mark.parametrize('changes',[{'aud':'otro'},{'iss':'https://incorrecto.invalid'},{'exp':0}])
def test_rechaza_claims(jwt_client,changes):
    c,token=jwt_client
    assert c.get('/api/estados',headers={'Authorization':'Bearer '+token(**changes)}).status_code==401
def test_rechaza_firma_ajena(jwt_client):
    c,token=jwt_client
    claims=jwt.decode(token(),options={'verify_signature':False})
    other=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    forged=jwt.encode(claims,other,algorithm='RS256')
    assert c.get('/api/estados',headers={'Authorization':'Bearer '+forged}).status_code==401
def test_rol_y_escritura(jwt_client):
    c,token=jwt_client
    assert c.get('/api/estados',headers={'Authorization':'Bearer '+token(realm_access={'roles':['visitante']})}).status_code==403
    assert c.post('/api/inventario/carga',json={'items':[]},headers={'Authorization':'Bearer '+token()}).status_code==403
