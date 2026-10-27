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
