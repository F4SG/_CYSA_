"""Selección de cámara y negociación de captura, sin guardar imágenes."""
import sys


def list_cameras(cv2, backend='auto'):
    from cv2_enumerate_cameras import enumerate_cameras
    backends={'auto':cv2.CAP_ANY,'msmf':cv2.CAP_MSMF,'dshow':cv2.CAP_DSHOW}
    if backend not in backends:
        raise ValueError('camera_backend debe ser auto, msmf o dshow')
    api=backends[backend]
    if backend=='auto' and sys.platform=='win32':api=cv2.CAP_MSMF
    return enumerate_cameras(api)


def select_named_camera(cameras, name):
    if not isinstance(name,str) or not name.strip():
        raise ValueError('camera_name debe ser un nombre no vacío')
    name=name.strip().casefold()
    exact=[c for c in cameras if c.name.casefold()==name]
    matches=exact or [c for c in cameras if name in c.name.casefold()]
    if len(matches)!=1:
        available=', '.join(c.name for c in cameras) or 'ninguna'
        raise RuntimeError(f'Cámara solicitada ausente o ambigua. Disponibles: {available}. No se usará otra cámara.')
    return matches[0]


def open_source(cv2,source,config):
    if isinstance(source,int):
        backends={'auto':cv2.CAP_ANY,'msmf':cv2.CAP_MSMF,'dshow':cv2.CAP_DSHOW}
        backend=config.get('camera_backend','auto')
        if backend not in backends:raise ValueError('camera_backend debe ser auto, msmf o dshow')
        properties=[]
        for key,prop in [('camera_width',cv2.CAP_PROP_FRAME_WIDTH),('camera_height',cv2.CAP_PROP_FRAME_HEIGHT),('camera_fps',cv2.CAP_PROP_FPS)]:
            value=config.get(key)
            if value is not None:
                import math
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
                    raise ValueError(f'{key} debe ser positivo y finito')
                properties.append((prop,value))
        api=backends[backend]
        if config.get('camera_name') is not None:
            device=select_named_camera(list_cameras(cv2,backend),config['camera_name'])
            source,api=device.index,device.backend
            print(f'Camara seleccionada: {device.name} (indice {source}, backend {api})',flush=True)
        cap=cv2.VideoCapture(source,api)
    else:
        if config.get('camera_name'):
            raise ValueError('Para leer un video o URL elimina camera_name del YAML')
        cap=cv2.VideoCapture(source);properties=[]
    if not cap.isOpened():
        cap.release();raise RuntimeError('No se pudo abrir la fuente configurada')
    try:
        for prop,value in properties:cap.set(prop,value)
    except Exception:
        cap.release();raise
    return cap
