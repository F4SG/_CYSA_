import pytest
from marcar_lineas import bloque_yaml, sentido_positivo
from preparar_calibracion import unir
from cysa_detector.counter import Lane, LineCounter


def test_sentido_coincide_con_el_contador():
    a, b = (0.1, 0.5), (0.4, 0.5)
    assert sentido_positivo(a, b) == 'hacia abajo'
    c = LineCounter([Lane('N', 'N_0', a, b, 'negative_to_positive')])
    c.observe(1, 'auto', (0.2, 0.3), 0); c.observe(1, 'auto', (0.2, 0.7), 1)   # se mueve hacia abajo
    assert c.snapshot() == {('N', 'N_0', 'auto'): 1}
    assert sentido_positivo(b, a) == 'hacia arriba'


def test_bloque_yaml_valido():
    import yaml
    data = yaml.safe_load(bloque_yaml([((0.1, 0.6), (0.4, 0.6))], 'N'))
    lane = data['lanes'][0]
    Lane(lane['acceso'], lane['carril'], tuple(lane['a']), tuple(lane['b']), lane['direction'])
    assert lane['carril'] == 'N_0'


def auto(ini, fin, n, clase='auto'):
    return {'interseccion': 'DEMO_INT_01', 'acceso': 'N', 'carril': 'N_0', 'clase': clase,
            'inicio': ini, 'fin': fin, 'cantidad': str(n), 'prueba': 'true'}


def manual(ini, fin, n):
    return {'interseccion': 'DEMO_INT_01', 'acceso': 'N', 'carril': 'N_0', 'clase': 'auto',
            'inicio': ini, 'fin': fin, 'manual': str(n), 'prueba': 'true'}


def test_suma_intervalos_dentro_de_la_ventana():
    filas = [auto('2026-11-01T12:00:00Z', '2026-11-01T12:00:30Z', 3),
             auto('2026-11-01T12:00:30Z', '2026-11-01T12:01:00Z', 4),
             auto('2026-11-01T12:00:30Z', '2026-11-01T12:01:00Z', 9, 'moto'),
             auto('2026-11-01T12:01:00Z', '2026-11-01T12:01:30Z', 5)]
    out = unir([manual('2026-11-01T08:00:00-04:00', '2026-11-01T08:01:00-04:00', 7)], filas)
    assert out[0]['automatico'] == '7'


def test_rechaza_ventana_sin_cobertura_completa():
    filas = [auto('2026-11-01T12:00:00Z', '2026-11-01T12:00:30Z', 3)]
    with pytest.raises(ValueError):
        unir([manual('2026-11-01T12:00:00Z', '2026-11-01T12:01:00Z', 3)], filas)
