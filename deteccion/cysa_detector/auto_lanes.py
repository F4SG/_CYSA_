"""Estimación de carriles a partir de trayectorias; no almacena imágenes."""
from collections import deque
import numpy as np
from .counter import Lane

def clip_polygon(points):
    points=[np.asarray(p,dtype=float) for p in points]
    for axis,bound,sign in [(0,0,1),(0,1,-1),(1,0,1),(1,1,-1)]:
        output=[]
        if not points:return ()
        for previous,current in zip(points[-1:]+points[:-1],points):
            a=sign*(previous[axis]-bound)>=-1e-10
            b=sign*(current[axis]-bound)>=-1e-10
            if a!=b:
                t=(bound-previous[axis])/(current[axis]-previous[axis])
                output.append(previous+t*(current-previous))
            if b:output.append(current)
        points=output
    return tuple(tuple(float(v) for v in np.clip(p,0,1)) for p in points)

class AutoLanes:
    def __init__(self,access='N',min_tracks=2,max_lanes=8):
        self.access=access;self.min_tracks=min_tracks;self.max_lanes=max_lanes
        self.tracks={};self.last_seen={};self.lanes=[];self.assignments={}
    def observe(self,track_id,point,width,height,timestamp):
        if track_id not in self.tracks:self.tracks[track_id]=deque(maxlen=160)
        self.tracks[track_id].append((point,width,height))
        self.last_seen[track_id]=timestamp
        expired=[tid for tid,t in self.last_seen.items() if timestamp-t>120]
        for tid in expired:
            self.last_seen.pop(tid,None);self.tracks.pop(tid,None);self.assignments.pop(tid,None)
        if len(self.tracks)>1000:
            oldest=min(self.last_seen,key=self.last_seen.get)
            self.tracks.pop(oldest,None);self.last_seen.pop(oldest,None);self.assignments.pop(oldest,None)
    def infer(self):
        paths=[];directions=[]
        for records in self.tracks.values():
            points=np.array([r[0] for r in records])
            if len(points)<6:continue
            delta=points[-1]-points[0];length=np.linalg.norm(delta)
            if length<.07:continue
            paths.append((points,np.array([[r[1],r[2]] for r in records])))
            directions.append(delta/length)
        if len(paths)<self.min_tracks:return []
        # El eje principal admite tráfico en sentidos opuestos sin cancelar el movimiento.
        values,vectors=np.linalg.eigh(np.asarray(directions).T@np.asarray(directions))
        if values[-1]<2*max(values[0],1e-6):return []
        along=vectors[:,-1]
        if along[np.argmax(np.abs(along))]<0:along=-along
        along=np.array([0.,1.]) if abs(along[1])>=abs(along[0]) else np.array([1.,0.])
        across=np.array([along[1],-along[0]])
        reference=float(np.median(np.concatenate([p@along for p,_ in paths])))
        fits=[]
        for points,sizes in paths:
            depth=points@along;lateral=points@across
            if np.ptp(depth)<.06 or not depth.min()-.12<=reference<=depth.max()+.12:continue
            slope,intercept=np.polyfit(depth,lateral,1)
            if np.std(lateral-(slope*depth+intercept))>.025:continue
            widths=sizes@np.abs(across)
            width=float(np.polyval(np.polyfit(depth,widths,1),reference))
            if not .01<=width<=.45:continue
            fits.append(dict(center=slope*reference+intercept,slope=slope,width=width,
                             low=depth.min(),high=depth.max(),direction=np.sign(depth[-1]-depth[0])))
        if len(fits)<self.min_tracks:return []
        groups=[[f] for f in sorted(fits,key=lambda f:f['center'])]
        while len(groups)>1:
            candidates=[]
            for i,(left,right) in enumerate(zip(groups,groups[1:])):
                if np.median([f['direction'] for f in left])*np.median([f['direction'] for f in right])<0:continue
                width=float(np.median([f['width'] for f in left+right]))
                gap=abs(np.mean([f['center'] for f in left])-np.mean([f['center'] for f in right]))
                spread=max(f['center'] for f in left+right)-min(f['center'] for f in left+right)
                if gap<=.85*width and spread<=1.6*width:candidates.append((gap/width,i))
            if not candidates:break
            _,i=min(candidates);groups[i:i+2]=[groups[i]+groups[i+1]]
        groups=[g for g in groups if len(g)>=self.min_tracks]
        if not groups or len(groups)>self.max_lanes:return []
        centers=[]
        for g in groups:
            centers.append(dict(center=float(np.median([f['center'] for f in g])),
                                slope=float(np.median([f['slope'] for f in g])),
                                width=float(np.median([f['width'] for f in g])),
                                direction=float(np.median([f['direction'] for f in g]))))
        low=float(np.quantile([f['low'] for f in fits],.1));high=float(np.quantile([f['high'] for f in fits],.9))
        if high-low<.1:return []
        low=min(low,reference-.02);high=max(high,reference+.02)
        edges=[]
        first=centers[0];edges.append((first['center']-.8*first['width'],first['slope']))
        for left,right in zip(centers,centers[1:]):
            edges.append(((left['center']+right['center'])/2,(left['slope']+right['slope'])/2))
        last=centers[-1];edges.append((last['center']+.8*last['width'],last['slope']))
        lanes=[]
        point=lambda lateral,depth:across*lateral+along*depth
        for i,center in enumerate(centers):
            left,right=edges[i:i+2]
            # No extender carriles sobre separadores o huecos sin trayectorias.
            if left[0]<center['center']-.85*center['width']:
                left=(center['center']-.85*center['width'],center['slope'])
            if right[0]>center['center']+.85*center['width']:
                right=(center['center']+.85*center['width'],center['slope'])
            # Rechazar límites que se cruzan por perspectiva dentro de la zona observada.
            if any(left[0]+left[1]*(s-reference)>=right[0]+right[1]*(s-reference) for s in [low,high]):return []
            polygon=clip_polygon([point(left[0]+left[1]*(low-reference),low),
                                  point(right[0]+right[1]*(low-reference),low),
                                  point(right[0]+right[1]*(high-reference),high),
                                  point(left[0]+left[1]*(high-reference),high)])
            a=point(left[0],reference);b=point(right[0],reference)
            if len(polygon)<3 or np.any(a<0) or np.any(a>1) or np.any(b<0) or np.any(b>1):return []
            direction='negative_to_positive' if center['direction']>=0 else 'positive_to_negative'
            try:lanes.append(Lane(self.access,f'{self.access}_{i}',tuple(a),tuple(b),direction,polygon))
            except ValueError:return []
        return lanes
    def assign(self,track_id,point):
        candidates=[l for l in self.lanes if l.contains(point)]
        previous=self.assignments.get(track_id)
        lane=next((l for l in candidates if l.carril==previous),candidates[0] if candidates else None)
        if lane:self.assignments[track_id]=lane.carril
        else:self.assignments.pop(track_id,None)
        return lane
