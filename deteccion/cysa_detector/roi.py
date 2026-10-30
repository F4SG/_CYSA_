"""Recorte de inferencia por carriles fijos; las coordenadas de conteo siguen en el cuadro completo."""
import math

def crop_for_lanes(frame,lanes,config):
    enabled=config.get('crop_to_lanes',False)
    if not isinstance(enabled,bool):raise ValueError('crop_to_lanes debe ser booleano')
    if not enabled:return frame,(0,0)
    if config.get('auto_carriles',False):raise ValueError('El recorte requiere carriles fijos verificados')
    if not lanes or any(not lane.polygon for lane in lanes):
        raise ValueError('El recorte requiere poligonos de todos los carriles')
    padding=config.get('roi_padding',.15)
    if isinstance(padding,bool) or not isinstance(padding,(int,float)) or not math.isfinite(padding) or not 0<=padding<=.5:
        raise ValueError('roi_padding debe estar entre 0 y 0.5')
    h,w=frame.shape[:2]
    points=[p for lane in lanes for p in lane.polygon]
    min_x=min(p[0] for p in points)*w;max_x=max(p[0] for p in points)*w
    min_y=min(p[1] for p in points)*h;max_y=max(p[1] for p in points)*h
    dx=(max_x-min_x)*padding;dy=(max_y-min_y)*padding
    left=max(0,math.floor(min_x-dx));right=min(w,math.ceil(max_x+dx))
    top=max(0,math.floor(min_y-dy));bottom=min(h,math.ceil(max_y+dy))
    if right-left<2 or bottom-top<2:raise ValueError('La zona de inferencia es demasiado pequena')
    return frame[top:bottom,left:right],(left,top)

def restore_box(box,offset):
    x1,y1,x2,y2=box;dx,dy=offset
    return x1+dx,y1+dy,x2+dx,y2+dy
