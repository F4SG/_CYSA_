"""Reenlace opcional del LineCounter: vehículo tapado justo al cruzar la línea (apagado por defecto)."""
import pytest
from cysa_detector.counter import Lane, LineCounter, counter_options

LANE = Lane('N', 'N_0', (0.1, 0.5), (0.9, 0.5), 'negative_to_positive')   # cuenta hacia abajo


def recorrer(c, tid, ys, t0=0.0, clase='moto', x=0.5):
    for k, y in enumerate(ys):
        c.observe(tid, clase, (x, y), t0 + k * 0.1)


def total(c):
    return sum(c.snapshot().values())


def test_sin_reenlace_se_pierde_la_moto_tapada():
    c = LineCounter([LANE])
    recorrer(c, 1, [0.40, 0.44, 0.47])            # la tapa un auto antes de la linea
    recorrer(c, 2, [0.54, 0.60], t0=0.8)          # reaparece pasada la linea con otro ID
    assert total(c) == 0


def test_reenlace_cuenta_una_vez():
    c = LineCounter([LANE], relink_s=1.5, relink_dist=0.1)
    recorrer(c, 1, [0.40, 0.44, 0.47])
    recorrer(c, 2, [0.54, 0.60], t0=0.8)
    recorrer(c, 2, [0.70], t0=1.0)
    assert c.snapshot() == {('N', 'N_0', 'moto'): 1}


def test_reenlace_respeta_clase_tiempo_distancia_y_sentido():
    c = LineCounter([LANE], relink_s=1.5, relink_dist=0.1)
    recorrer(c, 1, [0.40, 0.47])
    recorrer(c, 2, [0.54], t0=0.5, clase='auto')              # otra clase
    recorrer(c, 3, [0.54], t0=5.0)                            # demasiado tarde
    recorrer(c, 4, [0.54], t0=0.5, x=0.8)                     # demasiado lejos
    recorrer(c, 5, [0.60, 0.53], t0=0.0, x=0.2)               # viene de abajo: queda del lado de destino
    recorrer(c, 6, [0.46], t0=0.5, x=0.2)                     # aparece del lado de origen: sentido contrario
    assert total(c) == 0


def test_no_reenlaza_con_un_id_que_sigue_visible():
    c = LineCounter([LANE], relink_s=1.5, relink_dist=0.1)
    recorrer(c, 1, [0.40, 0.47])
    c.observe(1, 'moto', (0.5, 0.48), 0.5)
    c.observe(2, 'moto', (0.5, 0.53), 0.5)                    # dos motos juntas en el mismo cuadro
    assert total(c) == 0


def test_opciones_desde_yaml():
    assert counter_options({}) == dict(relink_s=0.0, relink_dist=0.0)
    LineCounter([LANE], **counter_options({'conteo_reenlace_s': 1.5, 'conteo_reenlace_distancia': 0.08}))
    with pytest.raises(ValueError):
        LineCounter([LANE], relink_s=10)
