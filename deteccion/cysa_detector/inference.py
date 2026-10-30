"""Parámetros de inferencia y umbrales por clase, independientes de la captura."""
import math

def probability(value,name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<=1:
        raise ValueError(f'{name} debe estar entre 0 y 1, excluyendo 0')
    return float(value)

def detection_settings(config,mapping):
    default=probability(config.get('confidence',.3),'confidence')
    thresholds={int(k):default for k in mapping}
    overrides=config.get('class_confidence',{})
    if not isinstance(overrides,dict):raise ValueError('class_confidence debe ser un mapa por clase COCO')
    for key,value in overrides.items():
        key=int(key)
        if key not in thresholds:raise ValueError('class_confidence contiene una clase no incluida en class_map')
        thresholds[key]=probability(value,'class_confidence')
    minimum=min(thresholds.values())
    confidence=probability(config.get('track_confidence',minimum),'track_confidence')
    if confidence>minimum:raise ValueError('track_confidence no puede descartar clases antes de su umbral')
    size=config.get('imgsz',640)
    if isinstance(size,bool) or not isinstance(size,int) or not 32<=size<=2048 or size%32:
        raise ValueError('imgsz debe ser entero múltiplo de 32 entre 32 y 2048')
    options=dict(persist=True,tracker=config.get('tracker','bytetrack.yaml'),classes=list(mapping),
                 conf=confidence,imgsz=size,device=config.get('device','cpu'),
                 save=False,save_txt=False,save_crop=False,save_frames=False,show=False,verbose=False)
    for key in ['end2end','agnostic_nms']:
        if key in config:
            if not isinstance(config[key],bool):raise ValueError(f'{key} debe ser booleano')
            options[key]=config[key]
    if 'iou' in config:options['iou']=probability(config['iou'],'iou')
    return options,thresholds
