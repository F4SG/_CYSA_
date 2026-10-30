import importlib.util
from pathlib import Path

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
