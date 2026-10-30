import os
import jwt
from jwt import PyJWKClient
from fastapi import Depends,HTTPException,Request
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
bearer=HTTPBearer(auto_error=False)
_jwks=None
def principal(credentials:HTTPAuthorizationCredentials|None=Depends(bearer)):
    global _jwks
    if not credentials or credentials.scheme.lower()!='bearer':
        raise HTTPException(401,'Token requerido',headers={'WWW-Authenticate':'Bearer'})
    try:
        if _jwks is None:_jwks=PyJWKClient(os.environ['OIDC_JWKS_URL'],cache_keys=True,lifespan=300,timeout=5)
        signing_key=_jwks.get_signing_key_from_jwt(credentials.credentials)
        return jwt.decode(credentials.credentials,signing_key.key,algorithms=['RS256'],
           audience=os.environ.get('OIDC_AUDIENCE','cysa-api'),issuer=os.environ['OIDC_ISSUER'],
           options={'require':['exp','iat','sub','iss','aud']},leeway=5)
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503,'Servicio de identidad no disponible') from None
    except (jwt.PyJWTError,ValueError,KeyError):
        raise HTTPException(401,'Token inválido',headers={'WWW-Authenticate':'Bearer'}) from None

def require_roles(*allowed):
    def dependency(request:Request,claims=Depends(principal)):
        access=claims.get('realm_access',{})
        roles=access.get('roles',[]) if isinstance(access,dict) else []
        if not isinstance(roles,list) or not all(isinstance(role,str) for role in roles) or not set(roles).intersection(allowed):
            raise HTTPException(403,'Rol sin permiso')
        # Se verifica el estado vigente incluso si faltan secretos: falla cerrado con 503.
        request.app.state.identity.verify(claims,allowed)
        return claims
    return dependency
read_access=require_roles('operador','administrador')
admin_access=require_roles('administrador')
