import pytest
from marcar_lineas import bloque_yaml, guardar, sentido_positivo
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


def test_limites_corridos_unos_milisegundos():
    # 10 intervalos de 30,033 s (30 s + 1 cuadro): el último termina después del límite de 5 min.
    from datetime import datetime, timedelta
    t0 = datetime.fromisoformat('2026-11-01T12:00:00+00:00')
    filas, t = [], t0
    for _ in range(11):
        fin = t + timedelta(seconds=30.033)
        filas.append(auto(t.isoformat(), fin.isoformat(), 1)); t = fin
    out = unir([manual(t0.isoformat(), (t0 + timedelta(minutes=5)).isoformat(), 10)], filas)
    assert out[0]['automatico'] == '10'


def test_guardar_lineas_en_el_yaml(tmp_path):
    import yaml
    ruta = tmp_path / 'video.yaml'
    ruta.write_text('source: video.mp4\ncrop_to_lanes: true\nconfiguracion_verificada: false\n', encoding='utf-8')
    guardar(ruta, [((0.3, 0.715), (0.63, 0.545))], 'N')
    c = yaml.safe_load(ruta.read_text(encoding='utf-8'))
    assert c['configuracion_verificada'] is True and c['crop_to_lanes'] is False and c['source'] == 'video.mp4'
    lane = c['lanes'][0]
    Lane(lane['acceso'], lane['carril'], tuple(lane['a']), tuple(lane['b']), lane['direction'])
    assert 'polygon' not in lane


def test_editor_de_lineas_devuelve_cancelacion_al_gestor(monkeypatch, tmp_path):
    import sys
    from types import SimpleNamespace

    import cv2
    import numpy as np
    from cysa_detector import camera
    from marcar_lineas import main

    perfil = tmp_path / 'perfil.yaml'
    original = 'source: 0\nconfiguracion_verificada: false\n'
    perfil.write_text(original, encoding='utf-8')
    liberaciones = []
    captura = SimpleNamespace(read=lambda: (True, np.zeros((20, 30, 3), np.uint8)),
                              release=lambda: liberaciones.append(True))
    monkeypatch.setattr(camera, 'open_source', lambda *args: captura)
    for nombre in ('namedWindow', 'setMouseCallback', 'imshow', 'destroyAllWindows'):
        monkeypatch.setattr(cv2, nombre, lambda *args: None)
    monkeypatch.setattr(cv2, 'waitKey', lambda _: 27)
    monkeypatch.setattr(sys, 'path', sys.path.copy())
    monkeypatch.setattr(sys, 'argv', ['marcar_lineas.py', '--config', str(perfil), '--cancelar-inicio'])

    assert main() == 130
    assert liberaciones == [True]
    assert perfil.read_text(encoding='utf-8') == original
