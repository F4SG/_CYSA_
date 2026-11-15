import importlib.util
from pathlib import Path
import sys

import pytest

def manager():
    path=Path(__file__).resolve().parents[2]/'tools/cristhian/detector.py'
    spec=importlib.util.spec_from_file_location('gestor_detector',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def test_pid_reutilizado_no_se_considera_activo(monkeypatch,tmp_path):
    m=manager();monkeypatch.setattr(m,'process_stamp',lambda pid:'nuevo')
    state=dict(pid=123,stamp='anterior',done=str(tmp_path/'done'))
    assert not m.running(state)

def test_done_indica_finalizacion(monkeypatch,tmp_path):
    m=manager();monkeypatch.setattr(m,'process_stamp',lambda pid:'igual')
    done=tmp_path/'done';state=dict(pid=123,stamp='igual',done=str(done))
    assert m.running(state)
    done.touch();assert not m.running(state)

def test_parada_solo_genera_marcador(monkeypatch,tmp_path):
    from types import SimpleNamespace
    m=manager();stop=tmp_path/'stop'
    monkeypatch.setattr(m,'load_state',lambda:dict(stop=str(stop)))
    monkeypatch.setattr(m,'running',lambda state:not stop.exists())
    assert m.stop(SimpleNamespace(espera=1))==0
    assert stop.exists()

def test_comando_conserva_rutas_con_espacios(tmp_path):
    m=manager();config=tmp_path/'mi configuracion.yaml';output=tmp_path/'mis conteos.csv';stop=tmp_path/'stop'
    cmd=m.detector_command(config,output,stop)
    assert str(config) in cmd and str(output) in cmd
    assert cmd[-2:]==['--stop-file',str(stop)]


def test_editar_abre_editor_y_reinicia_con_misma_config_y_salida(monkeypatch,tmp_path):
    m=manager();config=tmp_path/'camara.yaml';output=tmp_path/'conteos.csv'
    original='lanes:\n- acceso: N\n  direction: both\n'
    config.write_text(original,encoding='utf-8')
    monkeypatch.setattr(m,'environment',lambda:{})
    calls=[];returns=iter([20,0,0])
    def call(command,**kw):calls.append(command);return next(returns)
    monkeypatch.setattr(m.subprocess,'call',call)
    assert m.foreground(config,output)==0
    assert len(calls)==3
    assert calls[0]==calls[2]==m.detector_command(config,output)
    assert calls[1][1].endswith('calibrar_via.py') and '--iniciar' not in calls[1]
    assert calls[1][-1]=='both'
    assert config.read_text(encoding='utf-8')==original


def test_fallo_editor_no_inicia_detector_otra_vez(monkeypatch,tmp_path):
    m=manager();config=tmp_path/'config.yaml';config.write_text('lanes: []',encoding='utf-8')
    monkeypatch.setattr(m,'environment',lambda:{})
    codes=iter([20,1]);calls=[]
    def call(command,**kw):calls.append(command);return next(codes)
    monkeypatch.setattr(m.subprocess,'call',call)
    assert m.foreground(config,tmp_path/'salida.csv')==1 and len(calls)==2


def test_marcar_abre_editor_antes_del_primer_conteo(monkeypatch,tmp_path):
    m=manager();config=tmp_path/'video.yaml';output=tmp_path/'conteos.csv'
    config.write_text('lanes: []\n',encoding='utf-8')
    monkeypatch.setattr(m,'environment',lambda:{})
    calls=[];returns=iter([0,0])
    def call(command,**kw):calls.append(command);return next(returns)
    monkeypatch.setattr(m.subprocess,'call',call)
    assert m.foreground(config,output,mark='zona')==0
    assert calls[0][1].endswith('calibrar_via.py') and calls[1]==m.detector_command(config,output)


def test_marcar_cancelado_con_error_no_inicia(monkeypatch,tmp_path):
    m=manager();config=tmp_path/'video.yaml';config.write_text('lanes: []\n',encoding='utf-8')
    monkeypatch.setattr(m,'environment',lambda:{})
    calls=[]
    def call(command,**kw):calls.append(command);return 2
    monkeypatch.setattr(m.subprocess,'call',call)
    assert m.foreground(config,tmp_path/'s.csv',mark='zona')==2 and len(calls)==1


def test_marcar_linea_usa_el_editor_de_dos_puntos(monkeypatch,tmp_path):
    m=manager();config=tmp_path/'video.yaml';output=tmp_path/'conteos.csv'
    config.write_text('lanes: []\n',encoding='utf-8')
    monkeypatch.setattr(m,'environment',lambda:{})
    calls=[];returns=iter([0,0])
    def call(command,**kw):calls.append(command);return next(returns)
    monkeypatch.setattr(m.subprocess,'call',call)
    assert m.foreground(config,output,mark='linea')==0
    assert calls[0][1].endswith('marcar_lineas.py')
    assert calls[0][-3:]==['--config',str(config),'--cancelar-inicio']


def test_interpretar_fuente(tmp_path):
    import pytest
    m=manager();video=tmp_path/'calle.mp4';video.write_bytes(b'')
    assert m.parse_source('1')==dict(tipo='camara',indice=1)
    assert m.parse_source('camara:Galaxy S10+')==dict(tipo='camara',indice=0,nombre='Galaxy S10+')
    assert m.parse_source(f'"{video}"')['tipo']=='video'
    with pytest.raises(ValueError):m.parse_source(str(tmp_path/'no_existe.mp4'))


def test_menu_elige_camara_por_nombre_y_video(tmp_path):
    m=manager();video=tmp_path/'calle.mp4';video.write_bytes(b'')
    respuestas=iter(['1','2'])
    choice=m.ask_source({},ask=lambda _:next(respuestas),cameras=[(0,'Integrada'),(1,'USB Cam')])
    assert choice==dict(tipo='camara',indice=1,nombre='USB Cam')
    choice=m.ask_source({},ask=lambda _:'2',pick_file=lambda:str(video))
    assert choice['tipo']=='video' and choice['valor'].endswith('calle.mp4')


def test_fuente_video_crea_sesion_sin_tocar_el_perfil(monkeypatch,tmp_path):
    import yaml
    m=manager();monkeypatch.setattr(m,'RUNTIME',tmp_path/'detector')
    perfil=tmp_path/'carriles.yaml'
    original={'source':1,'camera_name':'Galaxy S10+','async_inference':True,'capture_latest':True,
              'configuracion_verificada':True,'lanes':[{'acceso':'N','carril':'N_0'}]}
    perfil.write_text(yaml.safe_dump(original),encoding='utf-8')
    video=tmp_path/'calle.mp4';video.write_bytes(b'')
    sesion,marcar=m.session_config(perfil,m.parse_source(str(video)))
    s=yaml.safe_load(sesion.read_text(encoding='utf-8'))
    assert marcar and s['configuracion_verificada'] is False and 'camera_name' not in s
    assert s['async_inference'] is False and s['capture_latest'] is False and s['ritmo_real'] is True
    assert yaml.safe_load(perfil.read_text(encoding='utf-8'))==original          # el perfil no cambia
    s['lanes']=[{'acceso':'N','carril':'N_0','a':[0,0]}];s['configuracion_verificada']=True   # como si se hubiera marcado
    sesion.write_text(yaml.safe_dump(s),encoding='utf-8')
    sesion2,marcar2=m.session_config(perfil,m.parse_source(str(video)))         # misma fuente otra vez
    assert not marcar2 and yaml.safe_load(sesion2.read_text(encoding='utf-8'))['lanes']==s['lanes']


def test_misma_camara_del_perfil_no_obliga_a_marcar(monkeypatch,tmp_path):
    import yaml
    m=manager();monkeypatch.setattr(m,'RUNTIME',tmp_path/'detector')
    perfil=tmp_path/'carriles.yaml'
    perfil.write_text(yaml.safe_dump({'source':0,'camera_name':'USB Cam','configuracion_verificada':True}),encoding='utf-8')
    _,marcar=m.session_config(perfil,dict(tipo='camara',indice=0,nombre='USB Cam'))
    assert not marcar


def test_acceso_directo_elige_fuente_y_marca_antes_de_contar():
    raiz=Path(__file__).resolve().parents[2]
    ps1=(raiz/'iniciar_conteo.ps1').read_text(encoding='ascii')
    assert 'tools/cristhian/detector.py iniciar' in ps1 and '--fuente' in ps1 and '--marcar' in ps1
    assert 'iniciar_conteo.ps1' in (raiz/'iniciar_conteo.bat').read_text(encoding='ascii')


@pytest.mark.parametrize('salida_editor', [0, 130])
def test_iniciar_coordina_fuente_nueva_calibracion_y_conteo(monkeypatch, tmp_path, salida_editor):
    import yaml

    gestor = manager()
    runtime = tmp_path / 'sesiones'
    monkeypatch.setattr(gestor, 'RUNTIME', runtime)
    monkeypatch.setattr(gestor, 'STATE', runtime / 'estado.json')
    monkeypatch.setattr(gestor, 'environment', lambda: {})
    perfil = tmp_path / 'perfil.yaml'
    original = 'interseccion: DEMO_INT_01\nsource: 0\nconfiguracion_verificada: true\n'
    perfil.write_text(original, encoding='utf-8')
    video = tmp_path / 'calle.mp4'
    video.touch()
    salida = tmp_path / 'conteos.csv'
    sesion = runtime / 'sesion_perfil.yaml'
    llamadas = []

    def ejecutar(comando, **kwargs):
        llamadas.append(comando)
        if len(llamadas) == 1:
            assert Path(comando[1]).name == 'calibrar_via.py'
            assert '--cancelar-inicio' in comando
            datos = yaml.safe_load(sesion.read_text(encoding='utf-8'))
            assert Path(datos['source']) == video
            assert datos['configuracion_verificada'] is False
            if salida_editor == 0:
                datos['configuracion_verificada'] = True
                sesion.write_text(yaml.safe_dump(datos), encoding='utf-8')
            return salida_editor
        assert comando == gestor.detector_command(sesion, salida)
        assert yaml.safe_load(sesion.read_text(encoding='utf-8'))['configuracion_verificada'] is True
        return 0

    monkeypatch.setattr(gestor.subprocess, 'call', ejecutar)
    monkeypatch.setattr(sys, 'argv', ['detector.py', 'iniciar', '--config', str(perfil),
                                     '--fuente', str(video), '--salida', str(salida)])
    assert gestor.main() == salida_editor
    assert len(llamadas) == (2 if salida_editor == 0 else 1)
    assert perfil.read_text(encoding='utf-8') == original


def test_iniciar_rechaza_video_inexistente_antes_del_arranque(monkeypatch, tmp_path, capsys):
    gestor = manager()
    runtime = tmp_path / 'sesiones'
    monkeypatch.setattr(gestor, 'RUNTIME', runtime)
    monkeypatch.setattr(gestor, 'STATE', runtime / 'estado.json')
    perfil = tmp_path / 'perfil.yaml'
    perfil.write_text('source: 0\n', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['detector.py', 'iniciar', '--config', str(perfil),
                                     '--fuente', str(tmp_path / 'inexistente.mp4')])
    with pytest.raises(SystemExit) as error:
        gestor.main()
    assert error.value.code == 2
    assert 'No existe el archivo de video' in capsys.readouterr().err
    assert not runtime.exists()


def test_fachada_conserva_salida_exitosa_de_trabajador_rapido(monkeypatch, tmp_path):
    from types import SimpleNamespace

    gestor = manager()
    runtime = tmp_path / 'sesiones'
    monkeypatch.setattr(gestor, 'RUNTIME', runtime)
    monkeypatch.setattr(gestor, 'STATE', runtime / 'estado.json')
    monkeypatch.setattr(gestor, 'environment', lambda: {})
    monkeypatch.setattr(gestor, 'process_stamp', lambda pid: 'trabajador')
    proceso = SimpleNamespace(pid=123, poll=lambda: 0)
    monkeypatch.setattr(gestor.subprocess, 'Popen', lambda *args, **kwargs: proceso)
    perfil = tmp_path / 'perfil.yaml'
    perfil.write_text('source: 0\n', encoding='utf-8')

    assert gestor.FachadaConteo().iniciar(perfil, tmp_path / 'conteos.csv', segundo_plano=True) == 0
    assert gestor.load_state()['pid'] == proceso.pid
    assert not (runtime / 'inicio.lock').exists()
