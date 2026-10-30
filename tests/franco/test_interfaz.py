"""Contratos de despliegue y coherencia visual del panel y el acceso."""
from pathlib import Path
import json
import yaml
import configurar_interfaz_local as interface
ROOT=Path(__file__).resolve().parents[2]


def test_tema_y_paleta_compartidos_entre_panel_y_acceso():
    theme=ROOT/'identidad/themes/cysa/login/resources'
    assert (ROOT/'panel/tokens.css').read_bytes()==(theme/'css/tokens.css').read_bytes()
    assert (ROOT/'panel/theme.js').read_bytes()==(theme/'js/theme.js').read_bytes()


def test_tema_disponible_en_instalacion_nueva_y_docker():
    realm=json.loads((ROOT/'identidad/realm.template.json').read_text(encoding='utf-8'))
    assert realm['loginTheme']=='cysa' and realm['defaultLocale']=='es'
    compose=yaml.safe_load((ROOT/'infra/compose.yaml').read_text(encoding='utf-8'))
    assert '../identidad/themes/cysa:/opt/keycloak/themes/cysa:ro' in compose['services']['keycloak']['volumes']


def test_actualizacion_visual_no_modifica_cuentas_clientes_o_roles(monkeypatch,tmp_path):
    calls=[]
    class Keycloak:
        def __init__(self,**kwargs):pass
        def transport(self,*args,**kwargs):return {'access_token':'token-sintetico'},{}
        def api(self,*args):calls.append(args);return None,{}
    monkeypatch.setattr(interface,'KeycloakUsers',Keycloak)
    monkeypatch.setattr(interface,'read_env',lambda path:{'KC_ADMIN_PASSWORD':'solo-prueba'})
    interface.configure(tmp_path)
    assert len(calls)==1
    method,path,payload=calls[0]
    assert method=='PUT' and path==''
    assert set(payload)=={'displayName','loginTheme','internationalizationEnabled','supportedLocales','defaultLocale'}
    assert payload['loginTheme']=='cysa'
