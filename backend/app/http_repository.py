"""Adaptador de conteos hacia la Web API SQL Server; credencial de servicio explícita."""
import json
import os
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class HttpCountRepository:
    def __init__(self, base_url=None, token=None):
        self.base = (base_url or os.environ['CYSA_DATA_API']).rstrip('/')
        parsed = urlsplit(self.base)
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')):
            raise ValueError('La API de datos requiere HTTPS salvo en pruebas de loopback')
        self.token = token or os.environ['CYSA_DATA_API_TOKEN']

    def _request(self, path, data=None):
        request = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None,
                          headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as error:
            # No incluir tokens, cuerpos ni credenciales en los logs del consumidor.
            raise RuntimeError(f'API de datos: HTTP {error.code}') from None

    def ready(self):
        self._request('/api/integracion/health')

    def save(self, event):
        from cysa.contracts import Conteo
        if not isinstance(event, Conteo):
            raise ValueError('Este adaptador importa conteos; los estados usan EstadoControl y sus referencias explícitas')
        self._request('/api/integracion/conteos', event.model_dump(mode='json'))

    def counts(self, desde, hasta, interseccion=None, carril=None, prueba=None, limit=200, offset=0):
        args={'desde': desde.isoformat(), 'hasta': hasta.isoformat(), 'limit': limit, 'offset': offset}
        for name, value in [('interseccion', interseccion), ('carril', carril), ('prueba', prueba)]:
            if value is not None:
                args[name] = str(value).lower() if isinstance(value, bool) else value
        return self._request('/api/integracion/conteos?' + urlencode(args))['items']
