"""RNF-01: la base y el consumidor solo están en la red interna; la API es el único enlace con el panel."""
from pathlib import Path
import yaml

COMPOSE = yaml.safe_load((Path(__file__).resolve().parents[2] / 'infra/compose.yaml').read_text(encoding='utf-8'))


def redes(servicio):
    return set(COMPOSE['services'][servicio]['networks'])


def test_red_operacional_interna_y_aislada_del_panel():
    assert COMPOSE['networks']['operacional'].get('internal') is True
    assert redes('db') == {'operacional'} and redes('consumer') == {'operacional'}
    assert 'panel' not in redes('mosquitto')
    assert [s for s in COMPOSE['services'] if {'operacional', 'panel'} <= redes(s)] == ['api']
    assert 'operacional' not in redes('panel') | redes('keycloak')
