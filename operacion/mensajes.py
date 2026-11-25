"""Sobres autenticados del banco: caducidad y huella verificadas también en el receptor."""
import hashlib,hmac,json,os,secrets,time
from pathlib import Path
from uuid import UUID
from .planes import huella,validar

def clave(path):
    data=Path(path).read_bytes()
    if len(data)!=32:raise ValueError('La clave de despacho debe tener 32 bytes')
    return data

def firmar(payload,key):
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
    return json.dumps({'payload':raw,'firma':hmac.new(key,raw.encode(),hashlib.sha256).hexdigest()},separators=(',',':'))

def verificar(raw,key,ahora=None):
    if len(raw)>32768:raise ValueError('Mensaje demasiado grande')
    envelope=json.loads(raw)
    if not isinstance(envelope,dict) or set(envelope)!={'payload','firma'}:raise ValueError('Sobre inválido')
    if not isinstance(envelope['payload'],str):raise ValueError('Payload inválido')
    payload=envelope['payload'];expected=hmac.new(key,payload.encode(),hashlib.sha256).hexdigest()
    if not isinstance(envelope['firma'],str) or not hmac.compare_digest(expected,envelope['firma']):raise ValueError('Firma inválida')
    d=json.loads(payload);now=time.time() if ahora is None else ahora
    if not isinstance(d,dict):raise ValueError('Contenido inválido')
    if not isinstance(d.get('vence'),(int,float)) or not now<d['vence']<=now+305:raise ValueError('Mensaje caducado o caducidad inválida')
    UUID(d['solicitud_id'])
    if d.get('tipo')=='plan':
        if d.get('mfa_verificado') is not True or not d.get('usuario'):raise ValueError('Falta autorización MFA')
        if d['plan'].get('modo')!='webster':raise ValueError('Solo se despachan planes Webster')
        validar(d['plan'])
        if huella(d['plan'])!=d.get('huella_plan'):raise ValueError('El plan cambió después de validarse')
    elif d.get('tipo')!='confirmacion':raise ValueError('Tipo no admitido')
    return d
