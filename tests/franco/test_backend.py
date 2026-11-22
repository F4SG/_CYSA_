from datetime import datetime,timedelta,timezone
from uuid import uuid4
import json,pytest
from cysa.contracts import Conteo,Estado,decode_message

def event(**changes):
    d={'mensaje_id':str(uuid4()),'interseccion':'DEMO_INT_01','acceso':'N','carril':'N_0','clase':'auto','cantidad':3,
      'inicio':'2026-10-26T12:00:00Z','fin':'2026-10-26T12:00:30Z','prueba':True}
    d.update(changes);return d
@pytest.mark.parametrize('change',[{'cantidad':-1},{'cantidad':True},{'clase':'placa'},{'imagen':'no-admitida'},
 {'prueba':'true'},{'inicio':'2026-10-26T12:00:00'},{'fin':'2026-10-26T11:00:00Z'},{'fin':'2026-10-26T12:01:00Z'}])
def test_rechaza_datos_fuera_de_contrato(change):
    with pytest.raises(ValueError):Conteo.model_validate(event(**change))
def test_topico_debe_coincidir():
    with pytest.raises(ValueError):decode_message('corredor/OTRA/N/conteos',json.dumps(event()).encode())
def test_flujo_sintetico_decodificacion_api(repository,operator):
    d=event();decoded=decode_message('corredor/DEMO_INT_01/N/conteos',json.dumps(d).encode())
    repository.save(decoded);repository.save(decoded)
    r=operator.get('/api/conteos',params={'desde':d['inicio'],'hasta':'2026-10-26T13:00:00Z','interseccion':'DEMO_INT_01','prueba':'true'})
    assert r.status_code==200 and len(r.json()['items'])==1
    assert r.json()['items'][0]['cantidad']==3 and r.json()['items'][0]['prueba'] is True
    assert operator.get('/api/conteos',params={'desde':d['inicio'],'hasta':d['inicio']}).status_code==422
    assert operator.get('/api/conteos?desde=2026-10-26T12:00:00').status_code==422
def test_sin_login_no_hay_datos(client):
    for route in ['/api/conteos','/api/estados','/api/inventario']:assert client.get(route).status_code==401
    assert client.get('/api/reportes/conteos', params={'desde':'2026-10-26T12:00:00Z','hasta':'2026-10-26T13:00:00Z'}).status_code == 401
    assert client.get('/health').json()['activacion_planes'] is False
    assert client.post('/api/planes').status_code==404
def test_estado_antiguo_no_reemplaza_actual(repository,operator):
    base={'mensaje_id':uuid4(),'interseccion':'DEMO_INT_01','fase_actual':'NS','plan_activo':'DEMO_FIJO','estado_controlador':'conectado','prueba':True}
    repository.save(Estado(**base,timestamp=datetime(2026,10,26,12,1,tzinfo=timezone.utc)))
    repository.save(Estado(**{**base,'fase_actual':'EW'},timestamp=datetime(2026,10,26,12,tzinfo=timezone.utc)))
    assert operator.get('/api/estados').json()['items'][0]['fase_actual']=='NS'


def test_reporte_agrega_todos_los_intervalos_y_separa_contextos(repository, operator):
    for _ in range(210):
        repository.save(Conteo.model_validate(event(cantidad=1)))
    for values in (
        {'clase': 'moto', 'cantidad': 5},
        {'clase': 'micro', 'cantidad': 3, 'carril': 'N_1'},
        {'clase': 'moto', 'cantidad': 4, 'prueba': False},
        {'interseccion': 'DEMO_INT_02', 'cantidad': 2, 'prueba': False},
        {'cantidad': 100, 'inicio': '2026-10-26T13:00:00Z', 'fin': '2026-10-26T13:00:30Z'},
    ):
        repository.save(Conteo.model_validate(event(**values)))
    url = '/api/reportes/conteos'
    period = {'desde': '2026-10-26T12:00:00Z', 'hasta': '2026-10-26T13:00:00Z'}
    result = operator.get(url, params=period).json()
    assert result['intersecciones'] == ['DEMO_INT_01', 'DEMO_INT_02']
    assert result['resumen'] == {
        'operacion': {'autos': 2, 'motos': 4, 'micros': 0, 'total': 6},
        'validacion': {'autos': 210, 'motos': 5, 'micros': 3, 'total': 218},
    }
    assert sum(row['total'] for row in result['items']) == 224
    filtered = operator.get(url, params={**period, 'interseccion':'DEMO_INT_01', 'prueba':'true'}).json()
    assert len(filtered['items']) == 2 and all(row['prueba'] for row in filtered['items'])
    assert filtered['resumen']['validacion']['total'] == 218
    assert filtered['resumen']['operacion']['total'] == 0
    assert operator.get(url, params={**period, 'hasta': period['desde']}).status_code == 422
    assert operator.get(url, params={**period, 'hasta':'2026-10-26T13:00:00'}).status_code == 422
    assert operator.get(url, params={**period, 'hasta':'2026-12-01T12:00:00Z'}).status_code == 422
