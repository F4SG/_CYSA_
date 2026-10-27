from types import SimpleNamespace
import pytest
from cysa_detector.camera import open_source

class Cap:
    def __init__(self,opened=True):self.properties=[];self.closed=False;self.opened=opened
    def isOpened(self):return self.opened
    def set(self,p,v):self.properties.append((p,v));return False
    def release(self):self.closed=True

def fake(cap):
    calls=[]
    def capture(*args):calls.append(args);return cap
    cv=SimpleNamespace(CAP_ANY=0,CAP_MSMF=1400,CAP_DSHOW=700,CAP_PROP_FRAME_WIDTH=3,CAP_PROP_FRAME_HEIGHT=4,CAP_PROP_FPS=5,VideoCapture=capture)
    return cv,calls

def test_camara_solicita_hd_sin_fabricar_imagen():
    cap=Cap();cv,calls=fake(cap)
    result=open_source(cv,1,{'camera_width':1920,'camera_height':1080,'camera_fps':30,'camera_backend':'msmf'})
    assert result is cap and calls==[(1,1400)]
    assert cap.properties==[(3,1920),(4,1080),(5,30)]
    assert not cap.closed

def test_archivo_no_altera_fps_ni_tamano():
    cap=Cap();cv,calls=fake(cap)
    open_source(cv,'video.mp4',{'camera_width':1920,'camera_height':1080,'camera_fps':30})
    assert calls==[('video.mp4',)] and not cap.properties

def test_predeterminado_compatible():
    cap=Cap();cv,calls=fake(cap);open_source(cv,0,{})
    assert calls==[(0,0)] and not cap.properties

@pytest.mark.parametrize('value',[0,-1,True,'1920'])
def test_rechaza_dimension_invalida(value):
    cap=Cap();cv,calls=fake(cap)
    with pytest.raises(ValueError):open_source(cv,0,{'camera_width':value})
    assert not calls

def test_rechaza_backend():
    cv,calls=fake(Cap())
    with pytest.raises(ValueError):open_source(cv,0,{'camera_backend':'xyz'})

def test_libera_fuente_no_disponible():
    cap=Cap(False);cv,calls=fake(cap)
    with pytest.raises(RuntimeError):open_source(cv,0,{})
    assert cap.closed


def test_nombre_tiene_prioridad_sobre_indice(monkeypatch):
    import cysa_detector.camera as camera
    devices=[SimpleNamespace(name='Integrated Camera',index=0,backend=1400),
             SimpleNamespace(name='Galaxy S10+ (Windows Virtual Camera)',index=3,backend=1400)]
    monkeypatch.setattr(camera,'list_cameras',lambda *args:devices)
    cap=Cap();cv,calls=fake(cap)
    open_source(cv,0,{'camera_name':'Galaxy S10+ (Windows Virtual Camera)','camera_backend':'msmf'})
    assert calls==[(3,1400)]


def test_no_hay_celular_no_abre_laptop(monkeypatch):
    import cysa_detector.camera as camera
    monkeypatch.setattr(camera,'list_cameras',lambda *args:[SimpleNamespace(name='Integrated Camera',index=0,backend=1400)])
    cap=Cap();cv,calls=fake(cap)
    with pytest.raises(RuntimeError,match='No se usará otra cámara'):
        open_source(cv,0,{'camera_name':'Galaxy S10+'})
    assert calls==[]


def test_nombre_ambiguo_no_abre_ninguna():
    from cysa_detector.camera import select_named_camera
    devices=[SimpleNamespace(name='USB camera 1'),SimpleNamespace(name='USB camera 2')]
    with pytest.raises(RuntimeError):select_named_camera(devices,'USB')


def test_nombre_exacto_preferido_a_coincidencias_parciales():
    from cysa_detector.camera import select_named_camera
    target=SimpleNamespace(name='Galaxy S10+')
    assert select_named_camera([target,SimpleNamespace(name='Galaxy S10+ extra')],'Galaxy S10+') is target


def test_video_no_acepta_seleccion_de_camara():
    cap=Cap();cv,calls=fake(cap)
    with pytest.raises(ValueError):open_source(cv,'video.mp4',{'camera_name':'Galaxy S10+'})
    assert not calls
