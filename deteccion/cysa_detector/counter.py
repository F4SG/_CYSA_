"""Geometría y conteo sin dependencias de cámara; no conserva imágenes."""
from dataclasses import dataclass
from collections import Counter
@dataclass(frozen=True)
class Lane:
    acceso:str
    carril:str
    a:tuple[float,float]
    b:tuple[float,float]
    direction:str='negative_to_positive'
    polygon:tuple[tuple[float,float],...] = ()
    def __post_init__(self):
        if self.a==self.b:raise ValueError('La línea debe tener longitud')
        if self.direction not in ['negative_to_positive','positive_to_negative','both']:raise ValueError('Dirección inválida')
        if not all(0<=v<=1 for p in [self.a,self.b] for v in p):raise ValueError('Coordenadas normalizadas 0..1')
        if self.polygon:
            if len(self.polygon)<3 or not all(0<=v<=1 for p in self.polygon for v in p):
                raise ValueError('Zona de carril invalida')
            if abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(self.polygon,self.polygon[1:]+self.polygon[:1])))<1e-8:
                raise ValueError('Zona sin area')
            if not self.contains(self.a) or not self.contains(self.b):
                raise ValueError('La linea debe quedar dentro del carril')
    def contains(self,point):
        if not self.polygon:return True
        x,y=point;inside=False
        for a,b in zip(self.polygon,self.polygon[1:]+self.polygon[:1]):
            if abs(cross(a,b,point))<1e-8 and min(a[0],b[0])-1e-8<=x<=max(a[0],b[0])+1e-8 and min(a[1],b[1])-1e-8<=y<=max(a[1],b[1])+1e-8:
                return True
            if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
                inside=not inside
        return inside

def cross(a,b,p):return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
def on_segment(a,b,p,q):
    """El recorrido debe intersectar el segmento finito, no su prolongación."""
    return cross(p,q,a)*cross(p,q,b)<=0
class LineCounter:
    def __init__(self,lanes,ttl_s=120):
        self.lanes=lanes;self.ttl=ttl_s;self.tracks={};self.counts=Counter()
        if len({(l.acceso,l.carril) for l in lanes})!=len(lanes):raise ValueError('Carril repetido')
    def observe(self,track_id,clase,point,timestamp,lane_key=None):
        if clase not in ['auto','micro','moto']:return
        record=self.tracks.get(track_id,{'last':{},'counted':set(),'seen':timestamp})
        record['seen']=timestamp
        for i,l in enumerate(self.lanes):
            side=cross(l.a,l.b,point)
            if abs(side)<1e-7:continue
            prev=record['last'].get(i)
            if prev and i not in record['counted']:
                old,p=prev
                direction='negative_to_positive' if old<0<side else 'positive_to_negative'
                eligible=lane_key is None or (lane_key==(l.acceso,l.carril) and not record['counted'])
                if eligible and old*side<0 and (l.direction in ['both',direction]) and on_segment(l.a,l.b,p,point):
                    t=old/(old-side)
                    intersection=(p[0]+t*(point[0]-p[0]),p[1]+t*(point[1]-p[1]))
                    if l.contains(intersection):
                        self.counts[(l.acceso,l.carril,clase)]+=1;record['counted'].add(i)
            record['last'][i]=(side,point)
        self.tracks[track_id]=record
    def prune(self,timestamp):
        self.tracks={k:v for k,v in self.tracks.items() if timestamp-v['seen']<=self.ttl}
    def snapshot(self):return dict(self.counts)
    def reset_interval(self):self.counts.clear() # Conservar IDs para no duplicar al cambiar de intervalo.
