import pytest
from aceptar_rf03 import comparar


def muestra(manual, automatico):
    filas = [dict(interseccion='DEMO_INT_01', acceso='N', carril=carril, clase=clase,
                  inicio='2026-11-24T12:00:00Z', fin='2026-11-24T12:00:10Z',
                  prueba='true', manual='0', automatico='0')
             for carril in ('N_0', 'N_1', 'N_2') for clase in ('auto', 'micro', 'moto')]
    filas[0].update(manual=str(manual), automatico=str(automatico))
    return filas


@pytest.mark.parametrize('manual,automatico,esperado', [(10,12,'CUMPLE'), (10,8,'CUMPLE'),
                         (10,13,'NO_CUMPLE'), (0,0,'SIN_BASE_PORCENTUAL')])
def test_umbral_total(manual, automatico, esperado):
    assert comparar(muestra(manual, automatico))['resultado'] == esperado


def test_exige_tres_carriles_y_la_misma_ventana():
    filas = muestra(10,10)
    with pytest.raises(ValueError):
        comparar(filas[:-1])
    filas[-1]['fin'] = '2026-11-24T12:00:11Z'
    with pytest.raises(ValueError):
        comparar(filas)
