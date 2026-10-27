"""Login OIDC en navegador. Token solo en memoria y en el entorno del comando hijo."""
import argparse,sys,base64,hashlib,json,os,secrets,subprocess,time,urllib.parse,urllib.request,webbrowser
from http.server import BaseHTTPRequestHandler,HTTPServer
import jwt

def b64(data):return base64.urlsafe_b64encode(data).rstrip(b'=').decode()
def validate_tokens(tokens,issuer,nonce,jwks=None):
    jwks=jwks or jwt.PyJWKClient(issuer+'/protocol/openid-connect/certs',timeout=10)
    access=jwt.decode(tokens['access_token'],jwks.get_signing_key_from_jwt(tokens['access_token']).key,
      algorithms=['RS256'],audience='cysa-api',issuer=issuer,options={'require':['exp','iat','sub','iss','aud']})
    identity=jwt.decode(tokens['id_token'],jwks.get_signing_key_from_jwt(tokens['id_token']).key,
      algorithms=['RS256'],audience='cysa-cli',issuer=issuer,options={'require':['exp','iat','sub','iss','aud','nonce']})
    if identity['nonce']!=nonce:raise ValueError('Nonce incorrecto')
    return access

def login(issuer):
    issuer=issuer.rstrip('/');state=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32)
    verifier=secrets.token_urlsafe(48);challenge=b64(hashlib.sha256(verifier.encode()).digest())
    callback='http://127.0.0.1:8766/callback';result={}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass # Nunca registrar URL con código OIDC.
        def do_GET(self):
            u=urllib.parse.urlparse(self.path)
            if u.path!='/callback':self.send_error(404);return
            q=urllib.parse.parse_qs(u.query)
            if q.get('state')!=[state]:self.send_error(400,'Estado OIDC incorrecto');return
            if 'error' in q:result['error']='Login rechazado'
            elif 'code' in q:result['code']=q['code'][0]
            else:self.send_error(400);return
            self.send_response(200);self.send_header('Content-Type','text/plain; charset=utf-8');self.end_headers()
            self.wfile.write('Puedes cerrar esta pestaña y volver a PowerShell.'.encode())
    with HTTPServer(('127.0.0.1',8766),Handler) as server:
        server.timeout=1
        query=urllib.parse.urlencode({'client_id':'cysa-cli','redirect_uri':callback,'response_type':'code','scope':'openid profile',
          'state':state,'nonce':nonce,'code_challenge':challenge,'code_challenge_method':'S256','prompt':'login'})
        print('Se abrirá Keycloak. Ingresa con el rol indicado; no copies tokens ni contraseñas a informes.')
        url=issuer+'/protocol/openid-connect/auth?'+query
        if not webbrowser.open(url):raise RuntimeError('No se pudo abrir navegador. Comprueba el navegador predeterminado.')
        deadline=time.monotonic()+180
        while not result and time.monotonic()<deadline:server.handle_request()
    if 'code' not in result:raise RuntimeError(result.get('error','Tiempo de login agotado'))
    body=urllib.parse.urlencode({'grant_type':'authorization_code','client_id':'cysa-cli','redirect_uri':callback,
      'code':result['code'],'code_verifier':verifier}).encode()
    req=urllib.request.Request(issuer+'/protocol/openid-connect/token',data=body,headers={'Content-Type':'application/x-www-form-urlencoded'})
    with urllib.request.urlopen(req,timeout=10) as r:tokens=json.load(r)
    validate_tokens(tokens,issuer,nonce)
    return tokens['access_token']
def main():
    p=argparse.ArgumentParser();p.add_argument('--issuer',default='http://localhost:8080/realms/cysa');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    cmd=a.command[1:] if a.command[:1]==['--'] else a.command
    if not cmd:p.error('Indicar comando después de --')
    if cmd[0] in ['python','python3']:cmd=[sys.executable]+cmd[1:]  # en Windows evita el Python del sistema
    token=login(a.issuer);env=os.environ.copy();env['CYSA_TOKEN']=token
    try:raise SystemExit(subprocess.call(cmd,env=env))
    finally:token='';env.pop('CYSA_TOKEN',None)
if __name__=='__main__':main()
