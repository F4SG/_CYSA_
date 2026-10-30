import importlib.util,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np

def module():
    path=Path(__file__).resolve().parents[2]/'tools/cristhian/calibrar_via.py'
    spec=importlib.util.spec_from_file_location('calibrador',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def detailed(value=120):
    frame=np.zeros((240,400,3),np.uint8)
    frame[80:220,80:320]=value
    return frame

def test_negro_no_se_puede_fijar():
    m=module();state=m.PreviewState();state.update(np.zeros((240,400,3),np.uint8))
    assert not state.ready and not state.toggle_freeze() and not state.frozen

def test_congelar_solo_copia_en_ram_y_reanudar_limpia_marcas():
    m=module();state=m.PreviewState();first=detailed(100);state.update(first)
    assert state.toggle_freeze()
    state.points.append((.1,.5));state.update(detailed(200))
    assert np.array_equal(state.frame,first)
    assert state.toggle_freeze() and state.points==[]
    state.update(detailed(200));assert np.array_equal(state.frame,detailed(200))

def test_calibrador_mantiene_camara_abierta_hasta_q(monkeypatch,tmp_path):
    import cv2,yaml
    import cysa_detector.camera as camera
    m=module()
    monkeypatch.setattr(m,'opening_size',lambda:(400,560))
    monkeypatch.setattr(cv2,'resizeWindow',lambda *a:None)
    class Cap:
        def __init__(self):self.releases=0;self.reads=0
        def read(self):
            assert self.releases==0
            self.reads+=1
            return True,np.zeros((240,400,3),np.uint8) if self.reads==1 else detailed()
        def release(self):self.releases+=1
    cap=Cap();monkeypatch.setattr(camera,'open_source',lambda *a:cap)
    monkeypatch.setattr(cv2,'namedWindow',lambda *a:None)
    monkeypatch.setattr(cv2,'setMouseCallback',lambda *a:None)
    monkeypatch.setattr(cv2,'imshow',lambda *a:None)
    monkeypatch.setattr(cv2,'getWindowProperty',lambda *a:1)
    monkeypatch.setattr(cv2,'destroyAllWindows',lambda:None)
    keys=iter([ord(' '),ord(' '),ord('q')])
    def key(*unused):
        assert cap.releases==0
        return next(keys)
    monkeypatch.setattr(cv2,'waitKey',key)
    config=tmp_path/'config.yaml';original='source: 1\nconfiguracion_verificada: false\n'
    config.write_text(original,encoding='utf-8')
    monkeypatch.setattr(sys,'argv',['calibrar_via.py','--config',str(config)])
    m.main()
    assert cap.reads==3 and cap.releases==1
    assert config.read_text(encoding='utf-8')==original


def test_guardar_libera_camara_antes_de_iniciar_detector(monkeypatch,tmp_path):
    import cv2,yaml,subprocess
    import cysa_detector.camera as camera
    m=module()
    monkeypatch.setattr(m,'opening_size',lambda:(400,560))
    monkeypatch.setattr(cv2,'resizeWindow',lambda *a:None)
    class Cap:
        releases=0
        def read(self):
            assert self.releases==0
            return True,detailed()
        def release(self):self.releases+=1
    cap=Cap();monkeypatch.setattr(camera,'open_source',lambda *a:cap)
    monkeypatch.setattr(cv2,'namedWindow',lambda *a:None)
    callback=[];monkeypatch.setattr(cv2,'setMouseCallback',lambda w,cb:callback.append(cb))
    monkeypatch.setattr(cv2,'imshow',lambda *a:None)
    monkeypatch.setattr(cv2,'getWindowProperty',lambda *a:1)
    monkeypatch.setattr(cv2,'destroyAllWindows',lambda:None)
    steps=iter([1,2,3])
    def key(*unused):
        assert cap.releases==0
        step=next(steps)
        if step==1:return ord(' ')
        if step==2:
            for x,y in [(40,100),(200,100),(360,220),(20,220)]:callback[0](cv2.EVENT_LBUTTONDOWN,x,y,None,None)
            return -1
        return ord('s')
    monkeypatch.setattr(cv2,'waitKey',key)
    launched=[]
    def launch(*a,**kw):
        assert cap.releases==1
        launched.append(a);return 0
    monkeypatch.setattr(subprocess,'call',launch)
    config=tmp_path/'config.yaml';config.write_text('source: 1\nconfiguracion_verificada: false\n',encoding='utf-8')
    monkeypatch.setattr(sys,'argv',['calibrar_via.py','--config',str(config),'--iniciar'])
    import pytest
    with pytest.raises(SystemExit) as result:m.main()
    assert result.value.code==0 and len(launched)==1
    saved=yaml.safe_load(config.read_text(encoding='utf-8'))
    assert saved['configuracion_verificada'] and not saved['auto_carriles'] and len(saved['lanes'])==3


def test_editor_vertical_mapea_clicks_solo_en_video():
    import cv2
    m=module();view=m.CalibrationView();view.size=(500,700)
    image=view.render(detailed(),'IMAGEN FIJA',3,'Prueba',cv2)
    x,y,w,h=view.rect
    assert view.point(x+w/2,y+h/2)==(.5,.5)
    assert view.point(10,690) is None
    assert image.shape==(700,500,3)
    assert all(rect[1]>=y+h for rect,key in view.buttons)
